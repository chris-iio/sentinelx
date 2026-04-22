/**
 * SentinelX main entry point — imports and initializes all feature modules.
 *
 * This file is the esbuild entry point (JS_ENTRY in Makefile).
 * esbuild wraps the output in an IIFE automatically (--format=iife).
 *
 * Module init order matches the original main.js init() function
 * (lines 815-826) to preserve identical DOMContentLoaded behavior.
 */

import { init as initForm } from "./modules/form";
import { init as initClipboard } from "./modules/clipboard";
import { init as initCards } from "./modules/cards";
import { init as initFilter } from "./modules/filter";
import { init as initEnrichment } from "./modules/enrichment";
import { init as initHistory } from "./modules/history";
import { init as initSettings } from "./modules/settings";
import { init as initUi } from "./modules/ui";
import { init as initGraph } from "./modules/graph";
import { attr } from "./utils/dom";

export type ResultsSurfaceOwner = "live" | "history" | "static";

export function resolveResultsSurfaceOwner(
  pageResults: HTMLElement | null = document.querySelector<HTMLElement>(".page-results")
): ResultsSurfaceOwner | null {
  if (!pageResults) return null;

  const explicitOwner = attr(pageResults, "data-results-owner");
  const mode = attr(pageResults, "data-mode");
  const jobId = attr(pageResults, "data-job-id");
  const hasHistoryResults = pageResults.hasAttribute("data-history-results");

  if (explicitOwner === "history") {
    return "history";
  }

  if (explicitOwner === "live") {
    return mode === "online" && jobId ? "live" : "static";
  }

  if (hasHistoryResults) {
    return "history";
  }

  if (mode === "online" && jobId) {
    return "live";
  }

  return "static";
}

export function initResultsSurface(
  pageResults: HTMLElement | null = document.querySelector<HTMLElement>(".page-results")
): void {
  const owner = resolveResultsSurfaceOwner(pageResults);
  if (!pageResults || !owner) return;

  pageResults.setAttribute("data-results-owner-resolved", owner);

  if (owner === "live") {
    initEnrichment();
    return;
  }

  if (owner === "history") {
    initHistory();
  }
}

function init(): void {
  initForm();
  initClipboard();
  initCards();
  initFilter();
  initResultsSurface();
  initSettings();
  initUi();
  initGraph();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
