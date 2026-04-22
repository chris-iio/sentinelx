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
import {
  findCardForIoc,
  updateCardVerdict,
  updateDashboardCounts,
  sortCardsBySeverity,
} from "./cards";
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

function isMinimalEnrichmentItem(value: EnrichmentItem): value is EnrichmentItem & MinimalEnrichmentItem {
  return Boolean(
    value &&
    (value.type === "result" || value.type === "error") &&
    typeof value.ioc_value === "string" &&
    typeof value.provider === "string"
  );
}

function findCopyButtonForIoc(iocValue: string): HTMLElement | null {
  return document.querySelector<HTMLElement>(
    '.copy-btn[data-value="' + CSS.escape(iocValue) + '"]'
  );
}

function updateCopyButtonWorstVerdict(
  iocValue: string,
  iocVerdicts: Record<string, VerdictEntry[]>
): void {
  const copyBtn = findCopyButtonForIoc(iocValue);
  if (!copyBtn) return;

  const worstEntry = findWorstEntry(iocVerdicts[iocValue] ?? []);
  if (!worstEntry) return;

  copyBtn.setAttribute("data-enrichment", worstEntry.summaryText);
}

function updatePendingIndicator(
  slot: HTMLElement,
  card: HTMLElement | null,
  receivedCount: number
): void {
  const iocType = card ? attr(card, "data-ioc-type") : "";
  const providerCounts = getProviderCounts();
  const totalExpected = Object.prototype.hasOwnProperty.call(providerCounts, iocType)
    ? (providerCounts[iocType] ?? 0)
    : 0;
  const remaining = totalExpected - receivedCount;

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

function flushIoc(
  iocValue: string,
  iocVerdicts: Record<string, VerdictEntry[]>
): void {
  const entries = iocVerdicts[iocValue] ?? [];
  if (entries.length === 0) return;

  const card = findCardForIoc(iocValue);
  if (!card) return;

  const slot = card.querySelector<HTMLElement>(".enrichment-slot");
  if (!slot) return;

  updateSummaryRow(slot, iocValue, iocVerdicts);
  updateCardVerdict(iocValue, computeWorstVerdict(entries));
  updateCopyButtonWorstVerdict(iocValue, iocVerdicts);

  const reputationSection = slot.querySelector<HTMLElement>(
    ".enrichment-section--reputation"
  );
  if (reputationSection) {
    sortDetailRows(reputationSection);
  }
}

export function createResultApplicationCoordinator(): ResultApplicationCoordinator {
  const iocVerdicts: Record<string, VerdictEntry[]> = {};
  const iocResultCounts: Record<string, number> = {};
  const dirtyIocs = new Set<string>();

  function apply(result: EnrichmentItem): void {
    if (!isMinimalEnrichmentItem(result)) return;

    const card = findCardForIoc(result.ioc_value);
    if (!card) return;

    const slot = card.querySelector<HTMLElement>(".enrichment-slot");
    if (!slot) return;

    const spinnerWrapper = slot.querySelector(".spinner-wrapper");
    if (spinnerWrapper) {
      slot.removeChild(spinnerWrapper);
    }
    slot.classList.add("enrichment-slot--loaded");

    iocResultCounts[result.ioc_value] = (iocResultCounts[result.ioc_value] ?? 0) + 1;
    const receivedCount = iocResultCounts[result.ioc_value] ?? 1;

    if (CONTEXT_PROVIDERS.has(result.provider)) {
      const contextSection = slot.querySelector<HTMLElement>(
        ".enrichment-section--context"
      );
      if (contextSection && result.type === "result") {
        const contextRow = createContextRow(result);
        contextSection.appendChild(contextRow);
        updateContextLine(card, result);
      }

      updatePendingIndicator(slot, card, receivedCount);
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
    const sectionSelector = isNoData
      ? ".enrichment-section--no-data"
      : ".enrichment-section--reputation";
    const sectionContainer = slot.querySelector<HTMLElement>(sectionSelector);
    if (sectionContainer) {
      const detailRow = createDetailRow(result.provider, verdict, statText, result);
      sectionContainer.appendChild(detailRow);
    }

    dirtyIocs.add(result.ioc_value);
    updatePendingIndicator(slot, card, receivedCount);
  }

  function flush(): void {
    if (dirtyIocs.size === 0) return;

    for (const iocValue of dirtyIocs) {
      flushIoc(iocValue, iocVerdicts);
    }
    dirtyIocs.clear();

    updateDashboardCounts();
    sortCardsBySeverity();
  }

  function finalize(): void {
    flush();

    document.querySelectorAll<HTMLElement>(".enrichment-slot").forEach((slot) => {
      if (!slot.querySelector(".no-data-summary-row")) {
        injectSectionHeadersAndNoDataSummary(slot);
      }
    });

    document
      .querySelectorAll<HTMLElement>(".enrichment-slot--loaded")
      .forEach((slot) => {
        injectDetailLink(slot);
      });
  }

  return {
    apply,
    flush,
    finalize,
  };
}
