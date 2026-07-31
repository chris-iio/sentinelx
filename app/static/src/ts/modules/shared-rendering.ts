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
 * Mark locally extracted Offline results separately from provider no-data results.
 * Preserve the server verdict because filters use the explicit not-queried state.
 */
export function initOfflineExtractionStates(
  pageResults: HTMLElement | null = pageResultsElement()
): void {
  if (!pageResults || pageResults.getAttribute("data-mode") !== "offline") return;

  const cards = pageResults.querySelectorAll<HTMLElement>(
    ".ioc-card[data-verdict='no_data'], .ioc-card[data-verdict='not_queried']"
  );
  for (let i = 0; i < cards.length; i += 1) {
    const card = cards[i];
    if (!card) continue;

    card.setAttribute("data-provider-query-state", "not_queried");

    const label = card.querySelector<HTMLElement>(".verdict-label");
    if (label) {
      label.textContent = "EXTRACTED";
      label.setAttribute("aria-label", "Extracted locally; providers not queried");
    }

    const context = card.querySelector<HTMLElement>(".ioc-context-line");
    if (context) {
      context.textContent = "Extracted locally · Providers not queried";
    }
  }

  const noDataFilter = pageResults.querySelector<HTMLElement>(
    "[data-filter-verdict='no_data'], [data-filter-verdict='not_queried']"
  );
  if (noDataFilter) noDataFilter.textContent = "Extracted";
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
 * malicious (rank 5) first, error (rank 0) last.
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

  const resolvedExportBtn = cachedElements.exportButton ?? document.getElementById("export-btn");
  const resolvedDropdown = cachedElements.dropdown ?? document.getElementById("export-dropdown");
  if (!resolvedExportBtn || !resolvedDropdown) return;
  const exportBtn: HTMLElement = resolvedExportBtn;
  const dropdown: HTMLElement = resolvedDropdown;

  function setExpanded(expanded: boolean): void {
    dropdown.hidden = !expanded;
    exportBtn.setAttribute("aria-expanded", String(expanded));
  }

  function closeDropdown(restoreFocus: boolean): void {
    setExpanded(false);
    if (restoreFocus) exportBtn.focus();
  }

  function openDropdown(focusFirstAction: boolean): void {
    setExpanded(true);
    if (focusFirstAction) {
      dropdown.querySelector<HTMLElement>("[data-export]")?.focus();
    }
  }

  exportBtn.setAttribute("aria-expanded", String(!dropdown.hidden));
  if (dropdown.id) exportBtn.setAttribute("aria-controls", dropdown.id);

  exportBtn.addEventListener("click", function () {
    setExpanded(dropdown.hasAttribute("hidden"));
  });

  exportBtn.addEventListener("keydown", function (event) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      openDropdown(true);
    } else if (event.key === "Escape" && !dropdown.hidden) {
      event.preventDefault();
      closeDropdown(false);
    }
  });

  dropdown.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      event.preventDefault();
      closeDropdown(true);
    }
  });

  // Close dropdown when clicking outside
  document.addEventListener("click", function (e) {
    const target = e.target;
    if (!(target instanceof Element) || !target.closest(".export-group")) {
      closeDropdown(false);
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
    closeDropdown(true);
  });

  pageResults.setAttribute("data-results-export-wired", "true");
}
