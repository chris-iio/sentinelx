/**
 * Enrichment polling module — polling loop, progress bar, result rendering,
 * warning banner, and export button.
 *
 * Extracted from main.js lines 316-643.
 * This is a direct behavioral translation: DOM mutations, fetch calls,
 * and timing are byte-for-byte equivalent to the original.
 *
 * Depends on:
 *   - cards.ts    for findCardForIoc, updateCardVerdict, updateDashboardCounts, sortCardsBySeverity
 *   - clipboard.ts for writeToClipboard
 *   - types/api.ts for EnrichmentItem, EnrichmentStatus
 *   - types/ioc.ts for VerdictKey, IocType, VERDICT_LABELS, VERDICT_SEVERITY, IOC_PROVIDER_COUNTS
 *   - utils/dom.ts for attr
 */

import type { EnrichmentItem, EnrichmentStatus } from "../types/api";
import type { VerdictKey, IocType } from "../types/ioc";
import { VERDICT_LABELS, VERDICT_SEVERITY, IOC_PROVIDER_COUNTS } from "../types/ioc";
import { attr } from "../utils/dom";
import {
  findCardForIoc,
  updateCardVerdict,
  updateDashboardCounts,
  sortCardsBySeverity,
} from "./cards";
import { writeToClipboard } from "./clipboard";

// ---- Module-private types ----

/**
 * Per-provider verdict record accumulated during the polling loop.
 * Used for worst-verdict computation across all providers for an IOC.
 */
interface VerdictEntry {
  provider: string;
  verdict: VerdictKey;
  summaryText: string;
}

// ---- Private helpers ----

/**
 * Format an ISO 8601 date string for display.
 * Returns "" for null input (scan_date can be null per API contract).
 * Source: main.js formatDate() (lines 581-588).
 */
function formatDate(iso: string | null): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
}

/**
 * Returns the severity index for a verdict key.
 * Higher index = higher severity. Returns -1 if not found.
 * Source: main.js verdictSeverity() (lines 230-233).
 */
function verdictSeverityIndex(verdict: VerdictKey): number {
  const idx = VERDICT_SEVERITY.indexOf(verdict);
  return idx === -1 ? -1 : idx;
}

/**
 * Compute the worst (highest severity) verdict from a list of VerdictEntry records.
 * Guards array[0] with `if (!worst)` for noUncheckedIndexedAccess.
 * Source: main.js computeWorstVerdict() (lines 542-551).
 */
function computeWorstVerdict(entries: VerdictEntry[]): VerdictKey {
  if (entries.length === 0) return "no_data";
  const worst = entries[0];
  if (!worst) return "no_data";

  let worstEntry = worst;
  for (let i = 1; i < entries.length; i++) {
    const current = entries[i];
    if (!current) continue;
    if (verdictSeverityIndex(current.verdict) > verdictSeverityIndex(worstEntry.verdict)) {
      worstEntry = current;
    }
  }
  return worstEntry.verdict;
}

/**
 * Find the copy button for a given IOC value by iterating .copy-btn elements.
 * Source: main.js findCopyButtonForIoc() (lines 571-579).
 */
function findCopyButtonForIoc(iocValue: string): HTMLElement | null {
  const btns = document.querySelectorAll<HTMLElement>(".copy-btn");
  for (let i = 0; i < btns.length; i++) {
    const btn = btns[i];
    if (btn && attr(btn, "data-value") === iocValue) {
      return btn;
    }
  }
  return null;
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

  const verdicts = iocVerdicts[iocValue] ?? [];
  if (verdicts.length === 0) return;

  const first = verdicts[0];
  if (!first) return;

  let worstEntry = first;
  for (let i = 1; i < verdicts.length; i++) {
    const current = verdicts[i];
    if (!current) continue;
    if (verdictSeverityIndex(current.verdict) > verdictSeverityIndex(worstEntry.verdict)) {
      worstEntry = current;
    }
  }

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
 * Get or create the collapsed no-data section inside an enrichment slot.
 * Source: main.js getOrCreateNodataSection() (lines 386-401).
 */
function getOrCreateNodataSection(slot: HTMLElement): HTMLDetailsElement {
  const existing = slot.querySelector<HTMLDetailsElement>(".enrichment-nodata-section");
  if (existing) return existing;

  const details = document.createElement("details");
  details.className = "enrichment-nodata-section";
  // Collapsed by default — no open attribute

  const summary = document.createElement("summary");
  summary.className = "enrichment-nodata-summary";
  summary.textContent = "1 provider: no record";

  details.appendChild(summary);
  slot.appendChild(details);
  return details;
}

/**
 * Update the summary count text after appending a no_data result row.
 * Source: main.js updateNodataSummary() (lines 403-410).
 */
function updateNodataSummary(detailsEl: HTMLDetailsElement): void {
  const rows = detailsEl.querySelectorAll(".provider-result-row");
  const count = rows.length;
  const summary = detailsEl.querySelector("summary");
  if (!summary) return;
  summary.textContent = count + " provider" + (count !== 1 ? "s" : "") + ": no record";
}

/**
 * Show or update the pending provider indicator after the first result for an IOC.
 * Uses hasOwnProperty check for IOC_PROVIDER_COUNTS access with iocType as IocType.
 * Source: main.js updatePendingIndicator() (lines 412-441).
 */
function updatePendingIndicator(
  slot: HTMLElement,
  card: HTMLElement | null,
  receivedCount: number
): void {
  const iocType = card ? attr(card, "data-ioc-type") : "";
  const totalExpected = Object.prototype.hasOwnProperty.call(IOC_PROVIDER_COUNTS, iocType)
    ? (IOC_PROVIDER_COUNTS[iocType as IocType] ?? 0)
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
    // Insert before nodata section if present, otherwise append
    const nodataSection = slot.querySelector(".enrichment-nodata-section");
    if (nodataSection) {
      slot.insertBefore(indicator, nodataSection);
    } else {
      slot.appendChild(indicator);
    }
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
function markEnrichmentComplete(done: number, total: number): void {
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
  // Suppress unused parameter warning — done/total mirror original signature
  void done;
  void total;
}

/**
 * Render a single enrichment result item into the appropriate IOC card slot.
 * Handles both "result" and "error" discriminated union branches.
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

  // Remove spinner wrapper on first result for this IOC
  const spinnerWrapper = slot.querySelector(".spinner-wrapper");
  if (spinnerWrapper) {
    slot.removeChild(spinnerWrapper);
  }

  // Track received count for this IOC before rendering
  iocResultCounts[result.ioc_value] = (iocResultCounts[result.ioc_value] ?? 0) + 1;
  const receivedCount = iocResultCounts[result.ioc_value] ?? 1;

  // Build provider result row div (appended, not replacing)
  const providerRow = document.createElement("div");
  providerRow.className = "provider-result-row";

  const badge = document.createElement("span");
  const detail = document.createElement("span");
  detail.className = "enrichment-detail";

  let summaryText = "";
  let verdict: VerdictKey;

  if (result.type === "result") {
    verdict = result.verdict;
    badge.className = "verdict-badge verdict-" + verdict;
    // Use VERDICT_LABELS for display — never raw verdict strings (UI-06)
    badge.textContent = VERDICT_LABELS[verdict];

    let verdictText = "";
    if (verdict === "malicious") {
      verdictText = result.detection_count + "/" + result.total_engines + " malicious";
    } else if (verdict === "suspicious") {
      verdictText = "Suspicious";
    } else if (verdict === "clean") {
      // Explicitly mention engine count to distinguish from no_data (UI-06)
      verdictText = "Clean — scanned by " + result.total_engines + " engines";
    } else {
      // no_data: analyst-friendly phrasing (UI-06)
      verdictText = "Not in " + result.provider + " database";
    }

    const scanDateStr = formatDate(result.scan_date);
    detail.textContent =
      result.provider + ": " + verdictText + (scanDateStr ? " — Scanned " + scanDateStr : "");

    summaryText = result.provider + ": " + verdict + " (" + verdictText + ")";
  } else {
    // Error result
    verdict = "error";
    badge.className = "verdict-badge verdict-error";
    badge.textContent = VERDICT_LABELS["error"];
    detail.textContent = result.provider + ": " + result.error;
    summaryText = result.provider + ": error — " + result.error;
  }

  providerRow.appendChild(badge);
  providerRow.appendChild(detail);

  if (verdict === "no_data") {
    // Route no_data results into the collapsed details section (UI-06)
    const nodataSection = getOrCreateNodataSection(slot);
    nodataSection.appendChild(providerRow);
    updateNodataSummary(nodataSection);
  } else {
    // Active results go directly into the slot
    slot.appendChild(providerRow);
  }

  // Update pending indicator for remaining providers
  updatePendingIndicator(slot, card, receivedCount);

  // Track per-IOC verdicts for worst-verdict computation
  const entries = iocVerdicts[result.ioc_value] ?? [];
  iocVerdicts[result.ioc_value] = entries;
  entries.push({ provider: result.provider, verdict, summaryText });

  // Compute worst verdict for this IOC
  const worstVerdict = computeWorstVerdict(iocVerdicts[result.ioc_value] ?? []);

  // Update card verdict, dashboard, and sort
  updateCardVerdict(result.ioc_value, worstVerdict);
  updateDashboardCounts();
  sortCardsBySeverity();

  // Update copy button with worst verdict across all providers for this IOC
  updateCopyButtonWorstVerdict(result.ioc_value, iocVerdicts);
}

// ---- Private init helpers ----

/**
 * Wire the export button click handler.
 * Iterates .ioc-card elements, builds lines with IOC values + enrichment summaries,
 * and calls writeToClipboard.
 * Source: main.js initExportButton() (lines 615-643).
 */
function initExportButton(): void {
  const exportBtn = document.getElementById("export-btn");
  if (!exportBtn) return;

  exportBtn.addEventListener("click", function () {
    const lines: string[] = [];
    const iocCards = document.querySelectorAll<HTMLElement>(".ioc-card");

    iocCards.forEach(function (card) {
      const valueEl = card.querySelector(".ioc-value");
      if (!valueEl) return;

      const iocValue = (valueEl.textContent ?? "").trim();
      const copyBtn = findCopyButtonForIoc(iocValue);
      // data-enrichment holds the worst verdict summary (set by polling loop)
      const enrichment = copyBtn ? copyBtn.getAttribute("data-enrichment") : null;

      if (enrichment) {
        lines.push(iocValue + " | " + enrichment);
      } else {
        lines.push(iocValue);
      }
    });

    const exportText = lines.join("\n");
    writeToClipboard(exportText, exportBtn);
  });
}

// ---- Public API ----

/**
 * Initialise the enrichment polling module.
 *
 * Guards on .page-results presence and data-mode="online" — returns early
 * on offline mode or when enrichment UI elements are absent.
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

  // Dedup key: "ioc_value|provider" — each provider result per IOC rendered once
  const rendered: Record<string, boolean> = {};

  // Per-IOC verdict tracking for worst-verdict copy/export computation
  // iocVerdicts[ioc_value] = [{provider, verdict, summaryText}]
  const iocVerdicts: Record<string, VerdictEntry[]> = {};

  // Per-IOC result count tracking for pending indicator
  const iocResultCounts: Record<string, number> = {};

  // Use ReturnType<typeof setInterval> to avoid NodeJS.Timeout conflict
  const intervalId: ReturnType<typeof setInterval> = setInterval(function () {
    fetch("/enrichment/status/" + jobId)
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
          const dedupKey = result.ioc_value + "|" + result.provider;
          if (!rendered[dedupKey]) {
            rendered[dedupKey] = true;
            renderEnrichmentResult(result, iocVerdicts, iocResultCounts);
          }

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

        if (data.complete) {
          clearInterval(intervalId);
          markEnrichmentComplete(data.done, data.total);
        }
      })
      .catch(function () {
        // Fetch error — silently continue; retry on next interval tick
      });
  }, 750);

  // Wire the export button
  initExportButton();
}
