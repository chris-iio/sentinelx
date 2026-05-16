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
import {
  pageResultsElement,
  resolveResultsSurfaceOwner as resolveDomResultsSurfaceOwner,
  type ResultsSurfaceOwner,
} from "./utils/dom";

export type { ResultsSurfaceOwner } from "./utils/dom";

export function resolveResultsSurfaceOwner(
  pageResults: HTMLElement | null = pageResultsElement()
): ResultsSurfaceOwner | null {
  return resolveDomResultsSurfaceOwner(pageResults);
}

export function initResultsSurface(
  pageResults: HTMLElement | null = pageResultsElement()
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
