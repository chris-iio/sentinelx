/**
 * Enrichment polling orchestrator — polling loop, progress tracking,
 * result dispatch, and module state.
 *
 * Verdict computation lives in verdict-compute.ts.
 * DOM row construction lives in row-factory.ts.
 * This module owns the polling interval, dedup map, per-IOC state,
 * and coordinates rendering through imported functions.
 */

import type { EnrichmentItem, EnrichmentStatus } from "../types/api";
import { getProviderCounts } from "../types/ioc";
import { attr } from "../utils/dom";
import {
  findCardForIoc,
  updateCardVerdict,
  updateDashboardCounts,
  sortCardsBySeverity,
} from "./cards";
import type { VerdictEntry } from "./verdict-compute";
import { computeWorstVerdict, findWorstEntry } from "./verdict-compute";
import { CONTEXT_PROVIDERS, createContextRow, createDetailRow,
         updateSummaryRow,
         injectSectionHeadersAndNoDataSummary,
         updateContextLine } from "./row-factory";
import { computeResultDisplay, injectDetailLink, sortDetailRows as sharedSortDetailRows, initExportButton as sharedInitExportButton } from "./shared-rendering";

// ---- Module-private state ----

/** Debounce timers for sortDetailRows — keyed by ioc_value */
const sortTimers: Map<string, ReturnType<typeof setTimeout>> = new Map();

/** Debounce timers for updateSummaryRow — keyed by ioc_value */
const summaryTimers: Map<string, ReturnType<typeof setTimeout>> = new Map();

/** Accumulated enrichment results for export */
const allResults: EnrichmentItem[] = [];

// ---- Private helpers ----

/**
 * Sort all .provider-detail-row elements in a container by severity descending.
 * malicious (index 4) first, error (index 0) last.
 * Debounced at 100ms per IOC to avoid thrashing during batch result delivery.
 * Delegates to sharedSortDetailRows for the synchronous core sort logic.
 */
function sortDetailRows(detailsContainer: HTMLElement, iocValue: string): void {
  const existing = sortTimers.get(iocValue);
  if (existing !== undefined) {
    clearTimeout(existing);
  }
  const timer = setTimeout(() => {
    sortTimers.delete(iocValue);
    sharedSortDetailRows(detailsContainer);
  }, 100);
  sortTimers.set(iocValue, timer);
}

/**
 * Debounced wrapper for updateSummaryRow — keyed by ioc_value at 100ms.
 * Limits summary row DOM rebuilds to 1–2 per IOC during streaming enrichment.
 */
function debouncedUpdateSummaryRow(
  slot: HTMLElement,
  iocValue: string,
  iocVerdicts: Record<string, VerdictEntry[]>
): void {
  const existing = summaryTimers.get(iocValue);
  if (existing !== undefined) {
    clearTimeout(existing);
  }
  const timer = setTimeout(() => {
    summaryTimers.delete(iocValue);
    updateSummaryRow(slot, iocValue, iocVerdicts);
  }, 100);
  summaryTimers.set(iocValue, timer);
}

/**
 * Find the copy button for a given IOC value using a targeted attribute selector.
 * O(1) browser-native lookup — replaces the old O(N) querySelectorAll iteration.
 * CSS.escape() handles IOC values with special characters (URLs, quotes, etc.).
 * Source: main.js findCopyButtonForIoc() (lines 571-579).
 */
function findCopyButtonForIoc(iocValue: string): HTMLElement | null {
  return document.querySelector<HTMLElement>('.copy-btn[data-value="' + CSS.escape(iocValue) + '"]');
}

/**
 * Update the copy button's data-enrichment attribute with the worst verdict
 * summary text across all providers for the given IOC.
 * Source: main.js updateCopyButtonWorstVerdict() (lines 553-569).
 */
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

/**
 * Update the progress bar fill and text.
 * Source: main.js updateProgressBar() (lines 375-383).
 */
function updateProgressBar(done: number, total: number): void {
  const fill = document.getElementById("enrich-progress-fill");
  const text = document.getElementById("enrich-progress-text");
  if (!fill || !text) return;

  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  fill.style.width = pct + "%";
  text.textContent = done + "/" + total + " providers complete";
}

/**
 * Show or update the pending provider indicator after the first result for an IOC.
 * Reads provider counts from the DOM via getProviderCounts() — reflects the actual
 * configured provider set injected by the Flask route into data-provider-counts.
 * Source: main.js updatePendingIndicator() (lines 412-441).
 */
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
    // All providers accounted for — remove waiting indicator if present
    const existingIndicator = slot.querySelector(".enrichment-waiting-text");
    if (existingIndicator) {
      slot.removeChild(existingIndicator);
    }
    return;
  }

  // Find or create the waiting indicator span
  let indicator = slot.querySelector<HTMLElement>(".enrichment-waiting-text");
  if (!indicator) {
    indicator = document.createElement("span");
    indicator.className = "enrichment-waiting-text enrichment-pending-text";
    slot.appendChild(indicator);
  }
  indicator.textContent = remaining + " provider" + (remaining !== 1 ? "s" : "") + " still loading...";
}

/**
 * Show a warning banner for rate-limit or authentication errors.
 * Source: main.js showEnrichWarning() (lines 605-611).
 */
function showEnrichWarning(message: string): void {
  const banner = document.getElementById("enrich-warning");
  if (!banner) return;
  banner.style.display = "block";
  // Use textContent to safely set the warning message (SEC-08)
  banner.textContent = "Warning: " + message + " Consider using offline mode or checking your API key in Settings.";
}

/**
 * Mark enrichment complete: add .complete class to progress container,
 * update text, and enable the export button.
 * Source: main.js markEnrichmentComplete() (lines 590-603).
 */
function markEnrichmentComplete(): void {
  const container = document.getElementById("enrich-progress");
  if (container) {
    container.classList.add("complete");
  }
  const text = document.getElementById("enrich-progress-text");
  if (text) {
    text.textContent = "Enrichment complete";
  }
  const exportBtn = document.getElementById("export-btn");
  if (exportBtn) {
    exportBtn.removeAttribute("disabled");
  }

  // VIS-03 + GRP-02: Inject section headers and no-data collapse for all slots
  document.querySelectorAll<HTMLElement>(".enrichment-slot").forEach(slot => {
    injectSectionHeadersAndNoDataSummary(slot);
  });

  // R004: Inject "View full detail →" link into each loaded slot's details panel
  document.querySelectorAll<HTMLElement>(".enrichment-slot--loaded").forEach(slot => {
    injectDetailLink(slot);
  });
}

/**
 * Render a single enrichment result item into the appropriate IOC card slot.
 * Handles both "result" and "error" discriminated union branches.
 *
 * New behavior (Plan 02):
 * - ALL results go into .enrichment-details container (no direct slot append)
 * - Summary row updated on each result: worst verdict badge + attribution + consensus badge
 * - Detail rows sorted by severity descending (debounced 100ms)
 * - .enrichment-slot--loaded class added on first result (reveals chevron via CSS)
 *
 * Source: main.js renderEnrichmentResult() (lines 443-540).
 */
function renderEnrichmentResult(
  result: EnrichmentItem,
  iocVerdicts: Record<string, VerdictEntry[]>,
  iocResultCounts: Record<string, number>
): void {
  // Find the card for this IOC value
  const card = findCardForIoc(result.ioc_value);
  if (!card) return;

  const slot = card.querySelector<HTMLElement>(".enrichment-slot");
  if (!slot) return;

  // Context providers (IP Context, DNS Records, Cert History) are purely informational —
  // separate rendering path. No VerdictEntry accumulation, no consensus/attribution,
  // no card verdict update.
  if (CONTEXT_PROVIDERS.has(result.provider)) {
    // Remove spinner on first result
    const spinnerWrapper = slot.querySelector(".spinner-wrapper");
    if (spinnerWrapper) slot.removeChild(spinnerWrapper);
    slot.classList.add("enrichment-slot--loaded");

    // Track result count for pending indicator
    iocResultCounts[result.ioc_value] = (iocResultCounts[result.ioc_value] ?? 0) + 1;

    // Render context row and append to context section container
    const contextSection = slot.querySelector<HTMLElement>(".enrichment-section--context");
    if (contextSection && result.type === "result") {
      const contextRow = createContextRow(result);
      contextSection.appendChild(contextRow);

      // Populate inline context line in card header (CTX-01)
      updateContextLine(card, result);
    }

    // Update pending indicator
    updatePendingIndicator(slot, card, iocResultCounts[result.ioc_value] ?? 1);
    return; // Skip all verdict/summary/sort/dashboard logic
  }

  // Remove spinner wrapper on first result for this IOC
  const spinnerWrapper = slot.querySelector(".spinner-wrapper");
  if (spinnerWrapper) {
    slot.removeChild(spinnerWrapper);
  }

  // Add .enrichment-slot--loaded class — triggers chevron visibility via CSS guard
  slot.classList.add("enrichment-slot--loaded");

  // Track received count for this IOC
  iocResultCounts[result.ioc_value] = (iocResultCounts[result.ioc_value] ?? 0) + 1;
  const receivedCount = iocResultCounts[result.ioc_value] ?? 1;

  // Determine verdict and statText
  const { verdict, statText, summaryText, detectionCount, totalEngines } = computeResultDisplay(result);

  // Push to iocVerdicts with extended fields
  const entries = iocVerdicts[result.ioc_value] ?? [];
  iocVerdicts[result.ioc_value] = entries;
  entries.push({ provider: result.provider, verdict, summaryText, detectionCount, totalEngines, statText, cachedAt: result.type === "result" ? result.cached_at ?? undefined : undefined });

  // Build detail row and route to correct section container
  const isNoData = verdict === "no_data" || verdict === "error";
  const sectionSelector = isNoData
    ? ".enrichment-section--no-data"
    : ".enrichment-section--reputation";
  const sectionContainer = slot.querySelector<HTMLElement>(sectionSelector);
  if (sectionContainer) {
    const detailRow = createDetailRow(result.provider, verdict, statText, result);
    sectionContainer.appendChild(detailRow);
    // Sort only reputation rows (no-data rows don't need severity sorting)
    if (!isNoData) {
      sortDetailRows(sectionContainer, result.ioc_value);
    }
  }

  // Update summary row (worst verdict + attribution + consensus)
  debouncedUpdateSummaryRow(slot, result.ioc_value, iocVerdicts);

  // Update pending indicator for remaining providers
  updatePendingIndicator(slot, card, receivedCount);

  // Compute worst verdict for this IOC
  const worstVerdict = computeWorstVerdict(iocVerdicts[result.ioc_value] ?? []);

  // Update card verdict (per-result — sets data-verdict on each card)
  updateCardVerdict(result.ioc_value, worstVerdict);

  // Update copy button with worst verdict across all providers for this IOC
  updateCopyButtonWorstVerdict(result.ioc_value, iocVerdicts);
}

/**
 * Wire expand/collapse toggle using event delegation on .page-results.
 * Called once from init(). Handles clicks and keyboard Enter/Space on any
 * .ioc-summary-row that appears in the page — including ones created after
 * init() (summary rows are built by row-factory.ts during polling).
 * Toggles .is-open on both the summary row and its .enrichment-details container.
 * Updates aria-expanded on the summary row accordingly.
 * Multiple rows remain independently expandable — no accordion logic.
 *
 * Exported for reuse by history.ts — history replay needs the same expand/collapse
 * behavior but runs outside the enrichment polling guard.
 */
export function wireExpandToggles(): void {
  const pageResults = document.querySelector<HTMLElement>(".page-results");
  if (!pageResults) return;

  function handleToggle(target: HTMLElement): void {
    const summaryRow = target.closest<HTMLElement>(".ioc-summary-row");
    if (!summaryRow) return;

    // .ioc-summary-row and .enrichment-details are siblings inside .enrichment-slot
    const slot = summaryRow.closest<HTMLElement>(".enrichment-slot");
    const details = slot ? slot.querySelector<HTMLElement>(".enrichment-details") : null;
    if (!details) return;

    const isOpen = details.classList.toggle("is-open");
    summaryRow.classList.toggle("is-open", isOpen);
    summaryRow.setAttribute("aria-expanded", String(isOpen));
  }

  pageResults.addEventListener("click", (event: MouseEvent) => {
    handleToggle(event.target as HTMLElement);
  });

  pageResults.addEventListener("keydown", (event: KeyboardEvent) => {
    if (event.key === "Enter" || event.key === " ") {
      const target = event.target as HTMLElement;
      if (target.closest(".ioc-summary-row")) {
        event.preventDefault();
        handleToggle(target);
      }
    }
  });
}

// ---- Public API ----

/**
 * Initialise the enrichment polling module.
 *
 * Guards on .page-results presence and data-mode="online" — returns early
 * on offline mode or when enrichment UI elements are absent.
 *
 * Wires chevron expand/collapse toggles once at init time (before polling
 * starts) so they work regardless of when results populate details.
 *
 * Starts a 750ms polling interval for /enrichment/status/<job_id>,
 * renders incremental results, shows warning banners for errors, and
 * marks enrichment complete when all tasks are done.
 *
 * Source: main.js initEnrichmentPolling() (lines 316-373) +
 *         initExportButton() (lines 615-643).
 */
export function init(): void {
  const pageResults = document.querySelector<HTMLElement>(".page-results");
  if (!pageResults) return;

  const jobId = attr(pageResults, "data-job-id");
  const mode = attr(pageResults, "data-mode");

  if (!jobId || mode !== "online") return;

  // Wire expand/collapse toggles once at init (before polling starts)
  wireExpandToggles();

  // Cursor-based dedup: ?since=N returns only new results, no client-side tracking needed
  let since = 0;

  // Per-IOC verdict tracking for worst-verdict copy/export computation
  // iocVerdicts[ioc_value] = [{provider, verdict, summaryText, detectionCount, totalEngines, statText}]
  const iocVerdicts: Record<string, VerdictEntry[]> = {};

  // Per-IOC result count tracking for pending indicator
  const iocResultCounts: Record<string, number> = {};

  // Use ReturnType<typeof setInterval> to avoid NodeJS.Timeout conflict
  const intervalId: ReturnType<typeof setInterval> = setInterval(function () {
    fetch("/enrichment/status/" + jobId + "?since=" + since)
      .then(function (resp) {
        if (!resp.ok) return null;
        return resp.json() as Promise<EnrichmentStatus>;
      })
      .then(function (data) {
        if (!data) return;

        updateProgressBar(data.done, data.total);

        // Render any new results not yet displayed, and check for warnings
        const results = data.results;
        for (let i = 0; i < results.length; i++) {
          const result = results[i];
          if (!result) continue;
          allResults.push(result);
          renderEnrichmentResult(result, iocVerdicts, iocResultCounts);

          // Show warning banner for rate-limit or auth errors
          if (result.type === "error" && result.error) {
            const errLower = result.error.toLowerCase();
            if (
              errLower.indexOf("rate limit") !== -1 ||
              errLower.indexOf("429") !== -1
            ) {
              showEnrichWarning("Rate limit reached for " + result.provider + ".");
            } else if (
              errLower.indexOf("authentication") !== -1 ||
              errLower.indexOf("401") !== -1 ||
              errLower.indexOf("403") !== -1
            ) {
              showEnrichWarning(
                "Authentication error for " +
                  result.provider +
                  ". Please check your API key in Settings."
              );
            }
          }
        }

        // Batch dashboard + sort once per tick (not per-result) — R023 O(N²) fix
        if (results.length > 0) {
          updateDashboardCounts();
          sortCardsBySeverity();
        }

        since = data.next_since;

        if (data.complete) {
          clearInterval(intervalId);
          markEnrichmentComplete();
        }
      })
      .catch(function () {
        // Fetch error — silently continue; retry on next interval tick
      });
  }, 750);

  // Wire the export button
  sharedInitExportButton(allResults);
}
