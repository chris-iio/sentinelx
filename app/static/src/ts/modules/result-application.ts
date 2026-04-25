/**
 * Shared stateful result-application coordinator for live polling and history replay.
 *
 * Owns the shared "apply one EnrichmentItem into cards/slots" path while keeping
 * transport concerns out of scope. Callers decide when to flush dirty IOC state:
 * live polling can debounce flushes, while history replay can flush synchronously.
 */

import type { EnrichmentItem } from "../types/api";
import { getProviderCounts, VERDICT_LABELS } from "../types/ioc";
import type { VerdictKey } from "../types/ioc";
import { attr } from "../utils/dom";
import { findCardForIoc, updateDashboardCounts, sortCardsBySeverity } from "./cards";
import type { VerdictEntry } from "./verdict-compute";
import { findWorstEntry, computeWorstVerdict } from "./verdict-compute";
import {
  CONTEXT_PROVIDERS,
  createContextRow,
  createDetailRow,
  injectSectionHeadersAndNoDataSummary,
  updateContextLine,
  updateSummaryRow,
} from "./row-factory";
import {
  computeResultDisplay,
  injectDetailLink,
  sortDetailRows,
} from "./shared-rendering";

interface ResultApplicationCoordinator {
  apply(result: EnrichmentItem): void;
  flush(): void;
  finalize(): void;
}

interface MinimalEnrichmentItem {
  type: "result" | "error";
  ioc_value: string;
  provider: string;
}

interface CachedIocHandles {
  card: HTMLElement;
  slot: HTMLElement;
  copyButton: HTMLElement | null;
  contextSection: HTMLElement | null;
  reputationSection: HTMLElement | null;
  noDataSection: HTMLElement | null;
  totalExpected: number;
}

function isMinimalEnrichmentItem(value: EnrichmentItem): value is EnrichmentItem & MinimalEnrichmentItem {
  return Boolean(
    value &&
    (value.type === "result" || value.type === "error") &&
    typeof value.ioc_value === "string" &&
    typeof value.provider === "string"
  );
}

function updateCardVerdictLabel(card: HTMLElement, worstVerdict: VerdictKey): void {
  card.setAttribute("data-verdict", worstVerdict);

  const label = card.querySelector<HTMLElement>(".verdict-label");
  if (!label) return;

  const classes = label.className
    .split(" ")
    .filter((className) => !className.startsWith("verdict-label--"));
  classes.push("verdict-label--" + worstVerdict);
  label.className = classes.join(" ");
  label.textContent = VERDICT_LABELS[worstVerdict] || worstVerdict.toUpperCase();
}

function updateCopyButtonWorstVerdict(
  copyButton: HTMLElement | null,
  entries: VerdictEntry[]
): void {
  if (!copyButton) return;

  const worstEntry = findWorstEntry(entries);
  if (!worstEntry) return;

  copyButton.setAttribute("data-enrichment", worstEntry.summaryText);
}

function updatePendingIndicator(
  handles: CachedIocHandles,
  receivedCount: number
): void {
  const remaining = handles.totalExpected - receivedCount;
  const { slot } = handles;

  if (remaining <= 0) {
    const existingIndicator = slot.querySelector(".enrichment-waiting-text");
    if (existingIndicator) {
      slot.removeChild(existingIndicator);
    }
    return;
  }

  let indicator = slot.querySelector<HTMLElement>(".enrichment-waiting-text");
  if (!indicator) {
    indicator = document.createElement("span");
    indicator.className = "enrichment-waiting-text enrichment-pending-text";
    slot.appendChild(indicator);
  }
  indicator.textContent = remaining + " provider" + (remaining !== 1 ? "s" : "") + " still loading...";
}

export function createResultApplicationCoordinator(): ResultApplicationCoordinator {
  const providerCounts = getProviderCounts();
  const iocVerdicts: Record<string, VerdictEntry[]> = {};
  const iocResultCounts: Record<string, number> = {};
  const dirtyIocs = new Set<string>();
  const handleCache = new Map<string, CachedIocHandles>();

  function getCachedHandles(iocValue: string): CachedIocHandles | null {
    const cached = handleCache.get(iocValue);
    if (cached) return cached;

    const card = findCardForIoc(iocValue);
    if (!card) return null;

    const slot = card.querySelector<HTMLElement>(".enrichment-slot");
    if (!slot) return null;

    const iocType = attr(card, "data-ioc-type");
    const totalExpected = Object.prototype.hasOwnProperty.call(providerCounts, iocType)
      ? (providerCounts[iocType] ?? 0)
      : 0;

    const handles: CachedIocHandles = {
      card,
      slot,
      copyButton: card.querySelector<HTMLElement>(".copy-btn"),
      contextSection: slot.querySelector<HTMLElement>(".enrichment-section--context"),
      reputationSection: slot.querySelector<HTMLElement>(".enrichment-section--reputation"),
      noDataSection: slot.querySelector<HTMLElement>(".enrichment-section--no-data"),
      totalExpected,
    };
    handleCache.set(iocValue, handles);
    return handles;
  }

  function flushIoc(iocValue: string): void {
    const entries = iocVerdicts[iocValue] ?? [];
    if (entries.length === 0) return;

    const handles = getCachedHandles(iocValue);
    if (!handles) return;

    updateSummaryRow(handles.slot, iocValue, iocVerdicts);
    updateCardVerdictLabel(handles.card, computeWorstVerdict(entries));
    updateCopyButtonWorstVerdict(handles.copyButton, entries);

    if (handles.reputationSection) {
      sortDetailRows(handles.reputationSection);
    }
  }

  function apply(result: EnrichmentItem): void {
    if (!isMinimalEnrichmentItem(result)) return;

    const handles = getCachedHandles(result.ioc_value);
    if (!handles) return;

    const { card, slot } = handles;
    const spinnerWrapper = slot.querySelector(".spinner-wrapper");
    if (spinnerWrapper) {
      slot.removeChild(spinnerWrapper);
    }
    slot.classList.add("enrichment-slot--loaded");

    iocResultCounts[result.ioc_value] = (iocResultCounts[result.ioc_value] ?? 0) + 1;
    const receivedCount = iocResultCounts[result.ioc_value] ?? 1;

    if (CONTEXT_PROVIDERS.has(result.provider)) {
      if (handles.contextSection && result.type === "result") {
        const contextRow = createContextRow(result);
        handles.contextSection.appendChild(contextRow);
        updateContextLine(card, result);
      }

      updatePendingIndicator(handles, receivedCount);
      return;
    }

    const { verdict, statText, summaryText, detectionCount, totalEngines } =
      computeResultDisplay(result);

    const entries = iocVerdicts[result.ioc_value] ?? [];
    iocVerdicts[result.ioc_value] = entries;
    entries.push({
      provider: result.provider,
      verdict,
      summaryText,
      detectionCount,
      totalEngines,
      statText,
      cachedAt: result.type === "result" ? result.cached_at ?? undefined : undefined,
    });

    const isNoData = verdict === "no_data" || verdict === "error";
    const sectionContainer = isNoData
      ? handles.noDataSection
      : handles.reputationSection;
    if (sectionContainer) {
      const detailRow = createDetailRow(result.provider, verdict, statText, result);
      sectionContainer.appendChild(detailRow);
    }

    dirtyIocs.add(result.ioc_value);
    updatePendingIndicator(handles, receivedCount);
  }

  function flush(): void {
    if (dirtyIocs.size === 0) return;

    for (const iocValue of dirtyIocs) {
      flushIoc(iocValue);
    }
    dirtyIocs.clear();

    updateDashboardCounts();
    sortCardsBySeverity();
  }

  function finalize(): void {
    flush();

    for (const handles of handleCache.values()) {
      if (!handles.slot.querySelector(".no-data-summary-row")) {
        injectSectionHeadersAndNoDataSummary(handles.slot);
      }
      if (handles.slot.classList.contains("enrichment-slot--loaded")) {
        injectDetailLink(handles.slot);
      }
    }
  }

  return {
    apply,
    flush,
    finalize,
  };
}
