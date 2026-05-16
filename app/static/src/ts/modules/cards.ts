/**
 * Card management module — verdict updates, dashboard counts, severity sorting.
 *
 * Extracted from main.js lines 252-336.
 * Provides the public API consumed by Phase 22's enrichment module.
 */

import type { VerdictKey } from "../types/ioc";
import { VERDICT_LABELS, verdictSeverityIndex } from "../types/ioc";
import { attr } from "../utils/dom";

const VERDICT_LABEL_CLASSES = [
  "verdict-label--malicious",
  "verdict-label--suspicious",
  "verdict-label--clean",
  "verdict-label--known_good",
  "verdict-label--no_data",
  "verdict-label--error",
] as const;

interface DashboardCounts {
  malicious: number;
  suspicious: number;
  clean: number;
  known_good: number;
  no_data: number;
}

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

  applyCardVerdict(card, worstVerdict);
}

export function applyCardVerdict(
  card: HTMLElement,
  worstVerdict: VerdictKey,
  verdictLabel: Element | null = null
): void {
  // Update data-verdict attribute (drives CSS border colour)
  card.setAttribute("data-verdict", worstVerdict);

  // Update verdict label text and class
  const label = verdictLabel ?? card.querySelector(".verdict-label");
  if (label) {
    label.classList.remove(...VERDICT_LABEL_CLASSES);
    label.classList.add("verdict-label--" + worstVerdict);
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
  const counts: DashboardCounts = {
    malicious: 0,
    suspicious: 0,
    clean: 0,
    known_good: 0,
    no_data: 0,
  };

  for (let i = 0; i < cards.length; i += 1) {
    const card = cards[i];
    if (!card) continue;
    incrementDashboardCount(counts, attr(card, "data-verdict"));
  }

  const countEls = dashboard.querySelectorAll<HTMLElement>("[data-verdict-count]");
  for (let i = 0; i < countEls.length; i += 1) {
    const countEl = countEls[i];
    if (!countEl) continue;
    const verdict = attr(countEl, "data-verdict-count");
    const count = dashboardCount(counts, verdict);
    if (count !== null) {
      countEl.textContent = String(count);
    }
  }
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

function incrementDashboardCount(counts: DashboardCounts, verdict: string): void {
  switch (verdict) {
    case "malicious":
      counts.malicious += 1;
      return;
    case "suspicious":
      counts.suspicious += 1;
      return;
    case "clean":
      counts.clean += 1;
      return;
    case "known_good":
      counts.known_good += 1;
      return;
    case "no_data":
      counts.no_data += 1;
      return;
    default:
      return;
  }
}

function dashboardCount(counts: DashboardCounts, verdict: string): number | null {
  switch (verdict) {
    case "malicious":
      return counts.malicious;
    case "suspicious":
      return counts.suspicious;
    case "clean":
      return counts.clean;
    case "known_good":
      return counts.known_good;
    case "no_data":
      return counts.no_data;
    default:
      return null;
  }
}

/**
 * Reorders .ioc-card elements in #ioc-cards-grid by verdict severity (most
 * severe first). Called by sortCardsBySeverity via setTimeout debounce.
 */
function doSortCards(): void {
  const grid = document.getElementById("ioc-cards-grid");
  if (!grid) return;

  const cardNodes = grid.querySelectorAll<HTMLElement>(".ioc-card");
  if (cardNodes.length <= 1) return;
  const cards: Array<{ card: HTMLElement; severity: number }> = [];
  for (let i = 0; i < cardNodes.length; i += 1) {
    const card = cardNodes[i];
    if (!card) continue;
    cards.push({
      card,
      severity: verdictSeverityIndex(attr(card, "data-verdict", "no_data") as VerdictKey),
    });
  }
  if (cards.length === 2) {
    const first = cards[0];
    const second = cards[1];
    if (first && second && first.severity < second.severity) {
      cards[0] = second;
      cards[1] = first;
    }
  } else if (cards.length === 3) {
    let first = cards[0];
    let second = cards[1];
    let third = cards[2];
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
      cards[0] = first;
      cards[1] = second;
      cards[2] = third;
    }
  } else {
    cards.sort((a, b) => {
      // Higher severity first (descending)
      return b.severity - a.severity;
    });
  }

  let orderChanged = false;
  for (let i = 0; i < cards.length; i += 1) {
    if (cards[i]?.card !== cardNodes[i]) {
      orderChanged = true;
      break;
    }
  }
  if (!orderChanged) return;

  // Reorder DOM elements without removing them from the document
  for (let i = 0; i < cards.length; i += 1) {
    const record = cards[i];
    if (!record) continue;
    grid.appendChild(record.card);
  }
}
