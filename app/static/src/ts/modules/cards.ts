/**
 * Card management module — verdict updates, dashboard counts, severity sorting.
 *
 * Extracted from main.js lines 252-336.
 * Provides the public API consumed by Phase 22's enrichment module.
 */

import type { VerdictKey } from "../types/ioc";
import { VERDICT_SEVERITY, VERDICT_LABELS } from "../types/ioc";
import { attr } from "../utils/dom";

/**
 * Module-level debounce timer for sortCardsBySeverity.
 * Uses ReturnType<typeof setTimeout> to avoid NodeJS.Timeout conflict.
 */
let sortTimer: ReturnType<typeof setTimeout> | null = null;

/**
 * Initialise the cards module.
 * Cards have no DOMContentLoaded setup — their functions are called by the
 * enrichment module. Exported for consistency with the module pattern;
 * main.ts will call it in Phase 22.
 */
export function init(): void {
  // No-op for Phase 21 — cards module has no DOMContentLoaded wiring.
  // Called by main.ts for consistent module initialisation.
}

/**
 * Find the IOC card element for a given IOC value using CSS.escape.
 * Returns null if no matching card is found.
 */
export function findCardForIoc(iocValue: string): HTMLElement | null {
  return document.querySelector<HTMLElement>(
    '.ioc-card[data-ioc-value="' + CSS.escape(iocValue) + '"]'
  );
}

/**
 * Update a card's verdict: sets data-verdict attribute, verdict label text,
 * and verdict label CSS class.
 */
export function updateCardVerdict(
  iocValue: string,
  worstVerdict: VerdictKey
): void {
  const card = findCardForIoc(iocValue);
  if (!card) return;

  // Update data-verdict attribute (drives CSS border colour)
  card.setAttribute("data-verdict", worstVerdict);

  // Update verdict label text and class
  const label = card.querySelector(".verdict-label");
  if (label) {
    // Remove all verdict-label--* classes, then add the correct one
    const classes = label.className
      .split(" ")
      .filter((c) => !c.startsWith("verdict-label--"));
    classes.push("verdict-label--" + worstVerdict);
    label.className = classes.join(" ");
    label.textContent = VERDICT_LABELS[worstVerdict] || worstVerdict.toUpperCase();
  }
}

/**
 * Count cards by verdict and update dashboard count elements.
 */
export function updateDashboardCounts(): void {
  const dashboard = document.getElementById("verdict-dashboard");
  if (!dashboard) return;

  const cards = document.querySelectorAll<HTMLElement>(".ioc-card");
  const counts: Record<string, number> = {
    malicious: 0,
    suspicious: 0,
    clean: 0,
    no_data: 0,
  };

  cards.forEach((card) => {
    const v = attr(card, "data-verdict");
    if (Object.prototype.hasOwnProperty.call(counts, v)) {
      counts[v] = (counts[v] ?? 0) + 1;
    }
  });

  const verdicts = ["malicious", "suspicious", "clean", "no_data"];
  verdicts.forEach((verdict) => {
    const countEl = dashboard.querySelector<HTMLElement>(
      '[data-verdict-count="' + verdict + '"]'
    );
    if (countEl) {
      countEl.textContent = String(counts[verdict] ?? 0);
    }
  });
}

/**
 * Debounced entry point: schedules doSortCards with a 100 ms delay.
 * Calling this multiple times in quick succession only triggers one sort.
 */
export function sortCardsBySeverity(): void {
  if (sortTimer !== null) clearTimeout(sortTimer);
  sortTimer = setTimeout(doSortCards, 100);
}

// ---- Private helpers ----

/**
 * Returns the severity index for a verdict key.
 * Higher index = higher severity. Returns -1 if not found.
 */
function verdictSeverityIndex(verdict: VerdictKey): number {
  return VERDICT_SEVERITY.indexOf(verdict);
}

/**
 * Reorders .ioc-card elements in #ioc-cards-grid by verdict severity (most
 * severe first). Called by sortCardsBySeverity via setTimeout debounce.
 */
function doSortCards(): void {
  const grid = document.getElementById("ioc-cards-grid");
  if (!grid) return;

  const cards = Array.from(grid.querySelectorAll<HTMLElement>(".ioc-card"));
  if (cards.length === 0) return;

  cards.sort((a, b) => {
    const va = verdictSeverityIndex(
      attr(a, "data-verdict", "no_data") as VerdictKey
    );
    const vb = verdictSeverityIndex(
      attr(b, "data-verdict", "no_data") as VerdictKey
    );
    // Higher severity first (descending)
    return vb - va;
  });

  // Reorder DOM elements without removing them from the document
  cards.forEach((card) => grid.appendChild(card));
}
