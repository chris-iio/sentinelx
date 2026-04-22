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
import { wireExpandToggles } from "./enrichment";
import { initExportButton } from "./shared-rendering";
import { createResultApplicationCoordinator } from "./result-application";

// ---- Module state ----

/** All replayed results — used for export functionality. */
const allResults: EnrichmentItem[] = [];

// ---- Public API ----

export function init(): void {
  const pageResults = document.querySelector<HTMLElement>(".page-results");
  if (!pageResults) return;

  const historyAttr = pageResults.getAttribute("data-history-results");
  if (!historyAttr) return;

  let results: EnrichmentItem[];
  try {
    results = JSON.parse(historyAttr) as EnrichmentItem[];
  } catch {
    console.error("[history] Failed to parse data-history-results JSON");
    return;
  }

  if (!Array.isArray(results) || results.length === 0) return;

  const coordinator = createResultApplicationCoordinator();

  for (const result of results) {
    allResults.push(result);
    coordinator.apply(result);
  }

  coordinator.finalize();

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

  wireExpandToggles();
  initExportButton(allResults);
}
