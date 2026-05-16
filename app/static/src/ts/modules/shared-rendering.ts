/**
 * Shared rendering functions extracted from enrichment.ts and history.ts.
 *
 * These functions were duplicated verbatim (or near-verbatim) in both modules.
 * This module provides a single source of truth for:
 *   - computeResultDisplay: verdict/statText/summaryText computation
 *   - injectDetailLink: "View full detail →" footer injection
 *   - sortDetailRows: severity-based detail row sorting (synchronous core)
 *   - initExportButton: export dropdown wiring (parameterized, no closure)
 */

import type { EnrichmentItem } from "../types/api";
import type { VerdictKey } from "../types/ioc";
import { verdictSeverityIndex } from "../types/ioc";
import { pageResultsElement } from "../utils/dom";
import { formatDate } from "./row-factory";
import { exportJSON, exportCSV, copyAllIOCs } from "./export";

// ---- Types ----

/** Return shape of computeResultDisplay — verdict + display strings. */
interface ResultDisplay {
  verdict: VerdictKey;
  statText: string;
  summaryText: string;
  detectionCount: number;
  totalEngines: number;
}

// ---- Functions ----

/**
 * Compute verdict, statText, summaryText, detectionCount, and totalEngines
 * from a single EnrichmentItem. Handles both "result" and "error" branches
 * of the discriminated union.
 *
 * Extracted from the duplicated ~45-line block in enrichment.ts
 * renderEnrichmentResult() and history.ts replayResult().
 */
export function computeResultDisplay(result: EnrichmentItem): ResultDisplay {
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
      // no_data
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
    // Error result
    verdict = "error";
    statText = result.error;
    summaryText = result.provider + ": error, " + result.error;
  }

  return { verdict, statText, summaryText, detectionCount, totalEngines };
}

/**
 * Inject a "View full detail →" link footer into the .enrichment-details panel
 * for a given enrichment slot. Reads data-ioc-type and data-ioc-value from the
 * ancestor .ioc-card and constructs href as /ioc/<type>/<encoded-value>.
 *
 * Idempotent: no-op if .detail-link-footer already exists in the panel.
 * All DOM construction uses createElement + textContent + setAttribute (SEC-08).
 */
export function injectDetailLink(
  slot: HTMLElement,
  cachedCard: HTMLElement | null = null,
  cachedDetails: HTMLElement | null = null
): void {
  const details = cachedDetails ?? slot.querySelector<HTMLElement>(".enrichment-details");
  if (!details) return;

  // Idempotency guard — only inject once per panel
  if (details.querySelector(".detail-link-footer")) return;

  const card = cachedCard ?? slot.closest<HTMLElement>(".ioc-card");
  if (!card) return;

  const iocType = card.getAttribute("data-ioc-type") ?? "";
  const iocValue = card.getAttribute("data-ioc-value") ?? "";
  if (!iocType || !iocValue) return;

  const footer = document.createElement("div");
  footer.className = "detail-link-footer";

  const anchor = document.createElement("a");
  anchor.className = "detail-link";
  anchor.textContent = "View full detail \u2192";
  anchor.setAttribute("href", "/ioc/" + iocType + "/" + encodeURIComponent(iocValue));

  footer.appendChild(anchor);
  details.appendChild(footer);
}

/**
 * Sort all .provider-detail-row elements in a container by severity descending.
 * malicious (index 4) first, error (index 0) last.
 *
 * This is the synchronous core — enrichment.ts wraps it in a debounce timer,
 * history.ts calls it directly after replay.
 */
export function sortDetailRows(container: HTMLElement): void {
  const rowNodes = container.querySelectorAll<HTMLElement>(".provider-detail-row");
  if (rowNodes.length <= 1) return;
  const rows: Array<{ row: HTMLElement; severity: number }> = [];
  for (let i = 0; i < rowNodes.length; i += 1) {
    const row = rowNodes[i];
    if (!row) continue;
    const verdict = row.getAttribute("data-verdict") as VerdictKey | null;
    rows.push({
      row,
      severity: verdict ? verdictSeverityIndex(verdict) : -1,
    });
  }
  if (rows.length === 2) {
    const first = rows[0];
    const second = rows[1];
    if (first && second && first.severity < second.severity) {
      rows[0] = second;
      rows[1] = first;
    }
  } else if (rows.length === 3) {
    let first = rows[0];
    let second = rows[1];
    let third = rows[2];
    if (first && second && third) {
      if (first.severity < second.severity) {
        const previousFirst = first;
        first = second;
        second = previousFirst;
      }
      if (second.severity < third.severity) {
        const previousSecond = second;
        second = third;
        third = previousSecond;
        if (first.severity < second.severity) {
          const previousFirst = first;
          first = second;
          second = previousFirst;
        }
      }
      rows[0] = first;
      rows[1] = second;
      rows[2] = third;
    }
  } else {
    rows.sort((a, b) => {
      return b.severity - a.severity; // descending: malicious first
    });
  }
  let orderChanged = false;
  for (let i = 0; i < rows.length; i += 1) {
    if (rows[i]?.row !== rowNodes[i]) {
      orderChanged = true;
      break;
    }
  }
  if (!orderChanged) return;

  for (let i = 0; i < rows.length; i += 1) {
    const item = rows[i];
    if (!item) continue;
    container.appendChild(item.row);
  }
}

/**
 * Wire the export dropdown with JSON, CSV, and copy-all-IOCs options.
 *
 * Parameterized with the results array — enrichment.ts and history.ts each
 * maintain their own module-private allResults array.
 */
export function initExportButton(
  allResults: EnrichmentItem[],
  pageResults: HTMLElement | null = pageResultsElement(),
  cachedElements: {
    exportButton?: HTMLElement | null;
    dropdown?: HTMLElement | null;
  } = {}
): void {
  if (!pageResults) return;
  if (pageResults.getAttribute("data-results-export-wired") === "true") return;

  const exportBtn = cachedElements.exportButton ?? document.getElementById("export-btn");
  const dropdown = cachedElements.dropdown ?? document.getElementById("export-dropdown");
  if (!exportBtn || !dropdown) return;

  exportBtn.addEventListener("click", function () {
    const isVisible = dropdown.style.display !== "none";
    dropdown.style.display = isVisible ? "none" : "";
  });

  // Close dropdown when clicking outside
  document.addEventListener("click", function (e) {
    const target = e.target as HTMLElement;
    if (!target.closest(".export-group")) {
      dropdown.style.display = "none";
    }
  });

  dropdown.addEventListener("click", function (event) {
    const target = event.target;
    if (!(target instanceof Element)) return;

    const btn = target.closest<HTMLElement>("[data-export]");
    if (!btn) return;

    const action = btn.getAttribute("data-export");
    if (action === "json") {
      exportJSON(allResults);
    } else if (action === "csv") {
      exportCSV(allResults);
    } else if (action === "iocs") {
      copyAllIOCs(btn, allResults);
    }
    dropdown.style.display = "none";
  });

  pageResults.setAttribute("data-results-export-wired", "true");
}
