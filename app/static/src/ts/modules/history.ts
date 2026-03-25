/**
 * History replay module — renders stored analysis results on history-loaded pages.
 *
 * When a user navigates to /history/<id>, the Flask route injects serialized
 * enrichment results as a `data-history-results` JSON attribute on .page-results.
 * This module detects that attribute, parses the results, and replays them
 * through the same rendering pipeline used by the live enrichment polling loop,
 * making history pages visually identical to completed live analyses.
 *
 * Unlike enrichment.ts, there is no polling or debouncing — all results are
 * available synchronously and rendered in a single pass.
 */

import type { EnrichmentItem } from "../types/api";
import type { VerdictKey } from "../types/ioc";
import { verdictSeverityIndex } from "../types/ioc";
import {
  findCardForIoc,
  updateCardVerdict,
  updateDashboardCounts,
  sortCardsBySeverity,
} from "./cards";
import type { VerdictEntry } from "./verdict-compute";
import { computeWorstVerdict } from "./verdict-compute";
import {
  CONTEXT_PROVIDERS,
  createContextRow,
  createDetailRow,
  updateSummaryRow,
  formatDate,
  injectSectionHeadersAndNoDataSummary,
  updateContextLine,
} from "./row-factory";
import { wireExpandToggles } from "./enrichment";
import { exportJSON, exportCSV, copyAllIOCs } from "./export";

// ---- Module state ----

/** All replayed results — used for export functionality. */
const allResults: EnrichmentItem[] = [];

// ---- Private helpers ----

/**
 * Inject a "View full detail →" link footer into the .enrichment-details panel
 * for a given enrichment slot. Identical to the private injectDetailLink in
 * enrichment.ts — duplicated here because that function uses closures and is
 * not exported.
 */
function injectDetailLink(slot: HTMLElement): void {
  const details = slot.querySelector<HTMLElement>(".enrichment-details");
  if (!details) return;

  if (details.querySelector(".detail-link-footer")) return;

  const card = slot.closest<HTMLElement>(".ioc-card");
  if (!card) return;

  const iocType = card.getAttribute("data-ioc-type") ?? "";
  const iocValue = card.getAttribute("data-ioc-value") ?? "";
  if (!iocType || !iocValue) return;

  const footer = document.createElement("div");
  footer.className = "detail-link-footer";

  const anchor = document.createElement("a");
  anchor.className = "detail-link";
  anchor.textContent = "View full detail \u2192";
  anchor.setAttribute(
    "href",
    "/ioc/" + iocType + "/" + encodeURIComponent(iocValue)
  );

  footer.appendChild(anchor);
  details.appendChild(footer);
}

/**
 * Wire the export dropdown for history pages.
 * Uses the module-level allResults array populated during replay.
 */
function initExportButton(): void {
  const exportBtn = document.getElementById("export-btn");
  const dropdown = document.getElementById("export-dropdown");
  if (!exportBtn || !dropdown) return;

  exportBtn.addEventListener("click", function () {
    const isVisible = dropdown.style.display !== "none";
    dropdown.style.display = isVisible ? "none" : "";
  });

  document.addEventListener("click", function (e) {
    const target = e.target as HTMLElement;
    if (!target.closest(".export-group")) {
      dropdown.style.display = "none";
    }
  });

  const buttons = dropdown.querySelectorAll<HTMLElement>("[data-export]");
  buttons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      const action = btn.getAttribute("data-export");
      if (action === "json") {
        exportJSON(allResults);
      } else if (action === "csv") {
        exportCSV(allResults);
      } else if (action === "iocs") {
        copyAllIOCs(btn);
      }
      dropdown.style.display = "none";
    });
  });
}

/**
 * Replay a single enrichment result into the DOM, updating all display state.
 *
 * Mirrors the rendering logic from enrichment.ts renderEnrichmentResult() but
 * without debouncing or polling-related state — all results are available
 * synchronously and processed in order.
 */
function replayResult(
  result: EnrichmentItem,
  iocVerdicts: Record<string, VerdictEntry[]>,
  iocResultCounts: Record<string, number>
): void {
  const card = findCardForIoc(result.ioc_value);
  if (!card) return;

  const slot = card.querySelector<HTMLElement>(".enrichment-slot");
  if (!slot) return;

  // Context providers — separate rendering path, no verdict tracking
  if (CONTEXT_PROVIDERS.has(result.provider)) {
    const spinnerWrapper = slot.querySelector(".spinner-wrapper");
    if (spinnerWrapper) slot.removeChild(spinnerWrapper);
    slot.classList.add("enrichment-slot--loaded");

    iocResultCounts[result.ioc_value] =
      (iocResultCounts[result.ioc_value] ?? 0) + 1;

    const contextSection = slot.querySelector<HTMLElement>(
      ".enrichment-section--context"
    );
    if (contextSection && result.type === "result") {
      const contextRow = createContextRow(result);
      contextSection.appendChild(contextRow);
      updateContextLine(card, result);
    }
    return;
  }

  // Reputation / error result path
  const spinnerWrapper = slot.querySelector(".spinner-wrapper");
  if (spinnerWrapper) slot.removeChild(spinnerWrapper);
  slot.classList.add("enrichment-slot--loaded");

  iocResultCounts[result.ioc_value] =
    (iocResultCounts[result.ioc_value] ?? 0) + 1;

  // Compute verdict and stat text
  let verdict: VerdictKey;
  let statText: string;
  let summaryText: string;
  let detectionCount = 0;
  let totalEngines = 0;

  if (result.type === "result") {
    verdict = result.verdict;
    detectionCount = result.detection_count;
    totalEngines = result.total_engines;

    if (verdict === "malicious") {
      statText = result.detection_count + "/" + result.total_engines + " engines";
    } else if (verdict === "suspicious") {
      statText =
        result.total_engines > 1
          ? result.detection_count + "/" + result.total_engines + " engines"
          : "Suspicious";
    } else if (verdict === "clean") {
      statText = "Clean, " + result.total_engines + " engines";
    } else if (verdict === "known_good") {
      statText = "NSRL match";
    } else {
      statText = "Not in database";
    }

    const scanDateStr = formatDate(result.scan_date);
    summaryText =
      result.provider +
      ": " +
      verdict +
      " (" +
      statText +
      (scanDateStr ? ", scanned " + scanDateStr : "") +
      ")";
  } else {
    verdict = "error";
    statText = result.error;
    summaryText = result.provider + ": error, " + result.error;
  }

  // Track verdict entries
  const entries = iocVerdicts[result.ioc_value] ?? [];
  iocVerdicts[result.ioc_value] = entries;
  entries.push({
    provider: result.provider,
    verdict,
    summaryText,
    detectionCount,
    totalEngines,
    statText,
    cachedAt:
      result.type === "result" ? result.cached_at ?? undefined : undefined,
  });

  // Build detail row and route to correct section
  const isNoData = verdict === "no_data" || verdict === "error";
  const sectionSelector = isNoData
    ? ".enrichment-section--no-data"
    : ".enrichment-section--reputation";
  const sectionContainer = slot.querySelector<HTMLElement>(sectionSelector);
  if (sectionContainer) {
    const detailRow = createDetailRow(result.provider, verdict, statText, result);
    sectionContainer.appendChild(detailRow);
  }
}

/**
 * Sort detail rows within a reputation section by verdict severity (descending).
 * Called once after all results are replayed — no debouncing needed.
 */
function sortDetailRows(container: HTMLElement): void {
  const rows = Array.from(
    container.querySelectorAll<HTMLElement>(".provider-detail-row")
  );
  rows.sort((a, b) => {
    const aVerdict = a.getAttribute("data-verdict") as VerdictKey | null;
    const bVerdict = b.getAttribute("data-verdict") as VerdictKey | null;
    const aIdx = aVerdict ? verdictSeverityIndex(aVerdict) : -1;
    const bIdx = bVerdict ? verdictSeverityIndex(bVerdict) : -1;
    return bIdx - aIdx;
  });
  for (const row of rows) {
    container.appendChild(row);
  }
}

// ---- Public API ----

/**
 * Initialize history replay.
 *
 * Guards on `data-history-results` attribute presence on `.page-results`.
 * Returns early on live enrichment pages (no history data) — enrichment.ts
 * handles those. When history data is present, replays all results through
 * the rendering pipeline and marks enrichment as complete.
 */
export function init(): void {
  const pageResults = document.querySelector<HTMLElement>(".page-results");
  if (!pageResults) return;

  const historyAttr = pageResults.getAttribute("data-history-results");
  if (!historyAttr) return;

  // Parse the JSON array of enrichment results
  let results: EnrichmentItem[];
  try {
    results = JSON.parse(historyAttr) as EnrichmentItem[];
  } catch {
    console.error("[history] Failed to parse data-history-results JSON");
    return;
  }

  if (!Array.isArray(results) || results.length === 0) return;

  // Per-IOC verdict and result count tracking
  const iocVerdicts: Record<string, VerdictEntry[]> = {};
  const iocResultCounts: Record<string, number> = {};

  // Replay all results through the rendering pipeline
  for (const result of results) {
    allResults.push(result);
    replayResult(result, iocVerdicts, iocResultCounts);
  }

  // After all results replayed: update summary rows and card verdicts per IOC
  const processedIocs = new Set<string>();
  for (const result of results) {
    if (processedIocs.has(result.ioc_value)) continue;
    processedIocs.add(result.ioc_value);

    const card = findCardForIoc(result.ioc_value);
    if (!card) continue;

    const slot = card.querySelector<HTMLElement>(".enrichment-slot");
    if (!slot) continue;

    // Update summary row (no debouncing needed — all results available)
    updateSummaryRow(slot, result.ioc_value, iocVerdicts);

    // Compute and set card verdict
    const entries = iocVerdicts[result.ioc_value] ?? [];
    // Filter out context-only IOCs (no reputation entries)
    const reputationEntries = entries.filter(
      (e) => !CONTEXT_PROVIDERS.has(e.provider)
    );
    if (reputationEntries.length > 0) {
      const worstVerdict = computeWorstVerdict(reputationEntries);
      updateCardVerdict(result.ioc_value, worstVerdict);
    }

    // Sort reputation detail rows by severity
    const repSection = slot.querySelector<HTMLElement>(
      ".enrichment-section--reputation"
    );
    if (repSection) {
      sortDetailRows(repSection);
    }
  }

  // Global post-processing
  updateDashboardCounts();
  sortCardsBySeverity();

  // Inject section headers and no-data collapse for all slots
  document.querySelectorAll<HTMLElement>(".enrichment-slot").forEach((slot) => {
    injectSectionHeadersAndNoDataSummary(slot);
  });

  // Inject "View full detail →" link into each loaded slot
  document.querySelectorAll<HTMLElement>(".enrichment-slot--loaded").forEach(
    (slot) => {
      injectDetailLink(slot);
    }
  );

  // Mark enrichment complete: progress bar, export button
  const container = document.getElementById("enrich-progress");
  if (container) {
    container.classList.add("complete");
  }
  const progressText = document.getElementById("enrich-progress-text");
  if (progressText) {
    progressText.textContent = "Enrichment complete";
  }
  const exportBtn = document.getElementById("export-btn");
  if (exportBtn) {
    exportBtn.removeAttribute("disabled");
  }

  // Wire expand/collapse toggles and export button
  wireExpandToggles();
  initExportButton();
}
