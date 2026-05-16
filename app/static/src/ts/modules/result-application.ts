/**
 * Shared stateful result-application coordinator for live polling and history replay.
 *
 * Owns the shared "apply one EnrichmentItem into cards/slots" path while keeping
 * transport concerns out of scope. Callers decide when to flush dirty IOC state:
 * live polling can debounce flushes, while history replay can flush synchronously.
 */

import type { EnrichmentItem } from "../types/api";
import { getProviderCounts } from "../types/ioc";
import { attr } from "../utils/dom";
import { applyCardVerdict, findCardForIoc, updateDashboardCounts, sortCardsBySeverity } from "./cards";
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
  verdictLabel: HTMLElement | null;
  copyButton: HTMLElement | null;
  contextLine: HTMLElement | null;
  summaryRow: HTMLElement | null;
  contextSection: HTMLElement | null;
  reputationSection: HTMLElement | null;
  noDataSection: HTMLElement | null;
  reputationRowCount: number;
  spinnerWrapper: HTMLElement | null;
  pendingIndicator: HTMLElement | null;
  detailsPanel: HTMLElement | null;
  noDataSummaryInjected: boolean;
  detailLinkInjected: boolean;
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
    if (handles.pendingIndicator) {
      slot.removeChild(handles.pendingIndicator);
      handles.pendingIndicator = null;
    }
    return;
  }

  if (!handles.pendingIndicator) {
    handles.pendingIndicator = document.createElement("span");
    handles.pendingIndicator.className = "enrichment-waiting-text enrichment-pending-text";
    slot.appendChild(handles.pendingIndicator);
  }
  handles.pendingIndicator.textContent = remaining + " provider" + (remaining !== 1 ? "s" : "") + " still loading...";
}

function providerCountForType(providerCounts: Record<string, number>, iocType: string): number {
  const count = providerCounts[iocType];
  return typeof count === "number" ? count : 0;
}

export function createResultApplicationCoordinator(): ResultApplicationCoordinator {
  const providerCounts = getProviderCounts();
  const iocVerdicts: Record<string, VerdictEntry[]> = {};
  const iocResultCounts: Record<string, number> = {};
  let dirtyIocs: Set<string> | null = null;
  const dirtyIocValues: string[] = [];
  const handleCache = new Map<string, CachedIocHandles>();
  const cachedIocValues: string[] = [];

  function getCachedHandles(iocValue: string): CachedIocHandles | null {
    const cached = handleCache.get(iocValue);
    if (cached) return cached;

    const card = findCardForIoc(iocValue);
    if (!card) return null;

    const slot = card.querySelector<HTMLElement>(".enrichment-slot");
    if (!slot) return null;

    const iocType = attr(card, "data-ioc-type");
    const totalExpected = providerCountForType(providerCounts, iocType);

    const handles: CachedIocHandles = {
      card,
      slot,
      verdictLabel: card.querySelector<HTMLElement>(".verdict-label"),
      copyButton: card.querySelector<HTMLElement>(".copy-btn"),
      contextLine: card.querySelector<HTMLElement>(".ioc-context-line"),
      summaryRow: null,
      contextSection: slot.querySelector<HTMLElement>(".enrichment-section--context"),
      reputationSection: slot.querySelector<HTMLElement>(".enrichment-section--reputation"),
      noDataSection: slot.querySelector<HTMLElement>(".enrichment-section--no-data"),
      reputationRowCount: 0,
      spinnerWrapper: slot.querySelector<HTMLElement>(".spinner-wrapper"),
      pendingIndicator: slot.querySelector<HTMLElement>(".enrichment-waiting-text"),
      detailsPanel: slot.querySelector<HTMLElement>(".enrichment-details"),
      noDataSummaryInjected: false,
      detailLinkInjected: false,
      totalExpected,
    };
    handleCache.set(iocValue, handles);
    cachedIocValues.push(iocValue);
    return handles;
  }

  function flushIoc(iocValue: string): boolean {
    const entries = iocVerdicts[iocValue] ?? [];
    if (entries.length === 0) return false;

    const handles = getCachedHandles(iocValue);
    if (!handles) return false;

    const previousVerdict = attr(handles.card, "data-verdict", "no_data");
    const worstVerdict = computeWorstVerdict(entries);

    handles.summaryRow = updateSummaryRow(
      handles.slot,
      iocValue,
      iocVerdicts,
      handles.summaryRow,
      handles.detailsPanel
    );
    applyCardVerdict(handles.card, worstVerdict, handles.verdictLabel);
    updateCopyButtonWorstVerdict(handles.copyButton, entries);

    if (handles.reputationSection && handles.reputationRowCount > 1) {
      sortDetailRows(handles.reputationSection);
    }

    return previousVerdict !== worstVerdict;
  }
  function flush(): void {
    if (!dirtyIocs || dirtyIocs.size === 0) return;

    let severityChanged = false;
    for (let index = 0; index < dirtyIocValues.length; index += 1) {
      const iocValue = dirtyIocValues[index];
      if (!iocValue) continue;
      severityChanged = flushIoc(iocValue) || severityChanged;
    }
    dirtyIocs.clear();
    dirtyIocValues.length = 0;

    if (severityChanged) {
      updateDashboardCounts();
      sortCardsBySeverity();
    }
  }

  function apply(result: EnrichmentItem): void {
    if (!isMinimalEnrichmentItem(result)) return;

    const handles = getCachedHandles(result.ioc_value);
    if (!handles) return;

    const { card, slot } = handles;
    if (handles.spinnerWrapper) {
      slot.removeChild(handles.spinnerWrapper);
      handles.spinnerWrapper = null;
    }
    slot.classList.add("enrichment-slot--loaded");

    iocResultCounts[result.ioc_value] = (iocResultCounts[result.ioc_value] ?? 0) + 1;
    const receivedCount = iocResultCounts[result.ioc_value] ?? 1;

    if (CONTEXT_PROVIDERS.has(result.provider)) {
      if (handles.contextSection && result.type === "result") {
        const contextRow = createContextRow(result);
        handles.contextSection.appendChild(contextRow);
        updateContextLine(card, result, handles.contextLine);
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
      if (!isNoData) {
        handles.reputationRowCount += 1;
      }
    }

    if (!dirtyIocs) dirtyIocs = new Set<string>();
    if (!dirtyIocs.has(result.ioc_value)) {
      dirtyIocs.add(result.ioc_value);
      dirtyIocValues[dirtyIocValues.length] = result.ioc_value;
    }
    updatePendingIndicator(handles, receivedCount);
  }

  function finalize(): void {
    flush();

    for (let index = 0; index < cachedIocValues.length; index += 1) {
      const iocValue = cachedIocValues[index];
      if (!iocValue) continue;
      const handles = handleCache.get(iocValue);
      if (!handles) continue;
      if (!handles.noDataSummaryInjected) {
        injectSectionHeadersAndNoDataSummary(handles.slot, handles.noDataSection);
        handles.noDataSummaryInjected = true;
      }
      if (!handles.detailLinkInjected && handles.slot.classList.contains("enrichment-slot--loaded")) {
        injectDetailLink(handles.slot, handles.card, handles.detailsPanel);
        handles.detailLinkInjected = true;
      }
    }
  }

  return {
    apply,
    flush,
    finalize,
  };
}
