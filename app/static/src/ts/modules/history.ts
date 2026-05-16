/**
 * History replay module — renders stored analysis results on history-loaded pages.
 *
 * When a user navigates to /history/<id>, the Flask route injects serialized
 * enrichment results as a `data-history-results` JSON attribute on .page-results.
 * This module detects that attribute, parses the results, and replays them
 * through the same rendering pipeline used by the live enrichment polling loop,
 * making history pages visually identical to completed live analyses.
 *
 * Unlike enrichment.ts, there is no polling or debounce scheduling — all results
 * are available synchronously and rendered in a single pass.
 */

import type { EnrichmentItem } from "../types/api";
import { pageResultsElement, resolveResultsSurfaceOwner } from "../utils/dom";
import { wireExpandToggles } from "./enrichment";
import { initExportButton } from "./shared-rendering";
import { createResultApplicationCoordinator } from "./result-application";

// ---- Module state ----

/** All replayed results — used for export functionality. */
const allResults: EnrichmentItem[] = [];

type HistoryReplayElements = {
  progressContainer: HTMLElement | null;
  progressText: HTMLElement | null;
  exportButton: HTMLElement | null;
  exportDropdown: HTMLElement | null;
};

function isHistoryResultsPage(pageResults: HTMLElement): boolean {
  return resolveResultsSurfaceOwner(pageResults) === "history";
}

function getHistoryReplayElements(): HistoryReplayElements {
  return {
    progressContainer: document.getElementById("enrich-progress"),
    progressText: document.getElementById("enrich-progress-text"),
    exportButton: document.getElementById("export-btn"),
    exportDropdown: document.getElementById("export-dropdown"),
  };
}

function markHistoryReplayComplete(results: EnrichmentItem[], elements: HistoryReplayElements): void {
  const container = elements.progressContainer;
  if (container) {
    container.classList.add("complete");
  }

  const progressText = elements.progressText;
  if (progressText) {
    progressText.textContent = "Enrichment complete";
  }

  const exportBtn = elements.exportButton;
  if (exportBtn && results.length > 0) {
    exportBtn.removeAttribute("disabled");
  }
}

// ---- Public API ----

export function init(): void {
  const pageResults = pageResultsElement();
  if (!pageResults || !isHistoryResultsPage(pageResults)) return;

  const historyAttr = pageResults.getAttribute("data-history-results");
  const elements = getHistoryReplayElements();
  if (!historyAttr) {
    markHistoryReplayComplete([], elements);
    pageResults.setAttribute("data-results-runtime", "history");
    return;
  }

  allResults.length = 0;
  if (historyAttr === "[]") {
    initExportButton(allResults, pageResults, {
      exportButton: elements.exportButton,
      dropdown: elements.exportDropdown,
    });
    markHistoryReplayComplete(allResults, elements);
    pageResults.setAttribute("data-results-runtime", "history");
    return;
  }

  let results: EnrichmentItem[];
  try {
    results = JSON.parse(historyAttr) as EnrichmentItem[];
  } catch {
    console.error("[history] Failed to parse data-history-results JSON");
    return;
  }

  const coordinator = createResultApplicationCoordinator();

  if (Array.isArray(results)) {
    for (let i = 0; i < results.length; i += 1) {
      const result = results[i];
      if (!result) continue;
      allResults.push(result);
      coordinator.apply(result);
    }
  }

  coordinator.finalize();
  wireExpandToggles(pageResults);
  initExportButton(allResults, pageResults, {
    exportButton: elements.exportButton,
    dropdown: elements.exportDropdown,
  });
  markHistoryReplayComplete(allResults, elements);
  pageResults.setAttribute("data-results-runtime", "history");
}
