/**
 * Filter bar module — verdict/type/search filtering with dashboard badge sync.
 *
 * Extracted from main.js initFilterBar() (lines 677-788).
 * Manages filterState and wires up all filter event listeners.
 */

import { attr } from "../utils/dom";

/**
 * Internal state for all active filter dimensions.
 * Not exported — this is private to the module closure inside init().
 */
interface FilterState {
  verdict: string;
  type: string;
  search: string;
}

type CardFilterRecord = {
  card: HTMLElement;
  typeLC: string;
  valueLC: string;
};

type ControlFilterRecord = {
  element: HTMLElement;
  value: string;
};

function collectCardFilterRecords(cards: NodeListOf<HTMLElement>): CardFilterRecord[] {
  const records: CardFilterRecord[] = [];
  for (let i = 0; i < cards.length; i += 1) {
    const card = cards.item(i);
    records[records.length] = {
      card,
      typeLC: attr(card, "data-ioc-type").toLowerCase(),
      valueLC: attr(card, "data-ioc-value").toLowerCase(),
    };
  }
  return records;
}

function collectControlFilterRecords(
  elements: NodeListOf<HTMLElement>,
  attributeName: string
): ControlFilterRecord[] {
  const records: ControlFilterRecord[] = [];
  for (let i = 0; i < elements.length; i += 1) {
    const element = elements.item(i);
    records[records.length] = {
      element,
      value: attr(element, attributeName),
    };
  }
  return records;
}

/**
 * Initialise the filter bar.
 * Wires verdict buttons, type pills, search input, and dashboard badge clicks.
 * All event listeners share the filterState closure.
 */
export function init(): void {
  const filterRootEl = document.getElementById("filter-root");
  if (!filterRootEl) return; // Not on results page
  const filterRoot: HTMLElement = filterRootEl;

  const filterState: FilterState = {
    verdict: "all",
    type: "all",
    search: "",
  };
  const cards = filterRoot.querySelectorAll<HTMLElement>(".ioc-card");
  const verdictBtns = filterRoot.querySelectorAll<HTMLElement>(
    "[data-filter-verdict]"
  );
  const typePills = filterRoot.querySelectorAll<HTMLElement>(
    "[data-filter-type]"
  );
  const cardRecords = collectCardFilterRecords(cards);
  const verdictButtonRecords = collectControlFilterRecords(verdictBtns, "data-filter-verdict");
  const typePillRecords = collectControlFilterRecords(typePills, "data-filter-type");

  // Apply filter state: show/hide each card and update active button styles
  function applyFilter(): void {
    const verdictLC = filterState.verdict.toLowerCase();
    const typeLC = filterState.type.toLowerCase();
    const searchLC = filterState.search.toLowerCase();

    for (let i = 0; i < cardRecords.length; i += 1) {
      const record = cardRecords[i];
      if (!record) continue;
      const { card } = record;
      const cardVerdict = attr(card, "data-verdict").toLowerCase();

      const verdictMatch = verdictLC === "all" || cardVerdict === verdictLC;
      const typeMatch = typeLC === "all" || record.typeLC === typeLC;
      const searchMatch = searchLC === "" || record.valueLC.indexOf(searchLC) !== -1;

      card.style.display =
        verdictMatch && typeMatch && searchMatch ? "" : "none";
    }

    // Update active state on verdict buttons
    for (let i = 0; i < verdictButtonRecords.length; i += 1) {
      const record = verdictButtonRecords[i];
      if (!record) continue;
      if (record.value === filterState.verdict) {
        record.element.classList.add("filter-btn--active");
      } else {
        record.element.classList.remove("filter-btn--active");
      }
    }

    // Update active state on type pills
    for (let i = 0; i < typePillRecords.length; i += 1) {
      const record = typePillRecords[i];
      if (!record) continue;
      if (record.value === filterState.type) {
        record.element.classList.add("filter-pill--active");
      } else {
        record.element.classList.remove("filter-pill--active");
      }
    }
  }

  // Verdict button click handler
  for (let i = 0; i < verdictButtonRecords.length; i += 1) {
    const record = verdictButtonRecords[i];
    if (!record) continue;
    const { element: btn, value: verdict } = record;
    btn.addEventListener("click", () => {
      if (verdict === "all") {
        filterState.verdict = "all";
      } else {
        // Toggle: clicking active verdict resets to 'all'
        filterState.verdict = filterState.verdict === verdict ? "all" : verdict;
      }
      applyFilter();
    });
  }

  // Type pill click handler
  for (let i = 0; i < typePillRecords.length; i += 1) {
    const record = typePillRecords[i];
    if (!record) continue;
    const { element: pill, value: type } = record;
    pill.addEventListener("click", () => {
      if (type === "all") {
        filterState.type = "all";
      } else {
        filterState.type = filterState.type === type ? "all" : type;
      }
      applyFilter();
    });
  }

  // Search input handler (debounced at 100ms — R023 O(N²) fix)
  const searchInput = document.getElementById(
    "filter-search-input"
  ) as HTMLInputElement | null;
  if (searchInput) {
    let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;
    searchInput.addEventListener("input", () => {
      filterState.search = searchInput.value;
      if (searchDebounceTimer !== null) clearTimeout(searchDebounceTimer);
      searchDebounceTimer = setTimeout(() => {
        applyFilter();
      }, 100);
    });
  }

  // Verdict dashboard badge click handler (toggle filter from dashboard)
  const dashboard = document.getElementById("verdict-dashboard");
  if (dashboard) {
    const dashBadges = dashboard.querySelectorAll<HTMLElement>(
      ".verdict-kpi-card[data-verdict]"
    );
    const dashboardBadgeRecords = collectControlFilterRecords(dashBadges, "data-verdict");
    for (let i = 0; i < dashboardBadgeRecords.length; i += 1) {
      const record = dashboardBadgeRecords[i];
      if (!record) continue;
      const { element: badge, value: verdict } = record;
      badge.addEventListener("click", () => {
        filterState.verdict =
          filterState.verdict === verdict ? "all" : verdict;
        applyFilter();
      });
    }
  }

}
