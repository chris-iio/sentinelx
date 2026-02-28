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

  // Apply filter state: show/hide each card and update active button styles
  function applyFilter(): void {
    const cards = filterRoot.querySelectorAll<HTMLElement>(".ioc-card");
    const verdictLC = filterState.verdict.toLowerCase();
    const typeLC = filterState.type.toLowerCase();
    const searchLC = filterState.search.toLowerCase();

    cards.forEach((card) => {
      const cardVerdict = attr(card, "data-verdict").toLowerCase();
      const cardType = attr(card, "data-ioc-type").toLowerCase();
      const cardValue = attr(card, "data-ioc-value").toLowerCase();

      const verdictMatch = verdictLC === "all" || cardVerdict === verdictLC;
      const typeMatch = typeLC === "all" || cardType === typeLC;
      const searchMatch = searchLC === "" || cardValue.indexOf(searchLC) !== -1;

      card.style.display = verdictMatch && typeMatch && searchMatch ? "" : "none";
    });

    // Update active state on verdict buttons
    const verdictBtns = filterRoot.querySelectorAll<HTMLElement>(
      "[data-filter-verdict]"
    );
    verdictBtns.forEach((btn) => {
      const btnVerdict = attr(btn, "data-filter-verdict");
      if (btnVerdict === filterState.verdict) {
        btn.classList.add("filter-btn--active");
      } else {
        btn.classList.remove("filter-btn--active");
      }
    });

    // Update active state on type pills
    const typePills = filterRoot.querySelectorAll<HTMLElement>(
      "[data-filter-type]"
    );
    typePills.forEach((pill) => {
      const pillType = attr(pill, "data-filter-type");
      if (pillType === filterState.type) {
        pill.classList.add("filter-pill--active");
      } else {
        pill.classList.remove("filter-pill--active");
      }
    });
  }

  // Verdict button click handler
  const verdictBtns = filterRoot.querySelectorAll<HTMLElement>(
    "[data-filter-verdict]"
  );
  verdictBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const verdict = attr(btn, "data-filter-verdict");
      if (verdict === "all") {
        filterState.verdict = "all";
      } else {
        // Toggle: clicking active verdict resets to 'all'
        filterState.verdict = filterState.verdict === verdict ? "all" : verdict;
      }
      applyFilter();
    });
  });

  // Type pill click handler
  const typePills = filterRoot.querySelectorAll<HTMLElement>(
    "[data-filter-type]"
  );
  typePills.forEach((pill) => {
    pill.addEventListener("click", () => {
      const type = attr(pill, "data-filter-type");
      if (type === "all") {
        filterState.type = "all";
      } else {
        filterState.type = filterState.type === type ? "all" : type;
      }
      applyFilter();
    });
  });

  // Search input handler
  const searchInput = document.getElementById(
    "filter-search-input"
  ) as HTMLInputElement | null;
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      filterState.search = searchInput.value;
      applyFilter();
    });
  }

  // Verdict dashboard badge click handler (toggle filter from dashboard)
  const dashboard = document.getElementById("verdict-dashboard");
  if (dashboard) {
    const dashBadges = dashboard.querySelectorAll<HTMLElement>(
      ".verdict-kpi-card[data-verdict]"
    );
    dashBadges.forEach((badge) => {
      badge.addEventListener("click", () => {
        const verdict = attr(badge, "data-verdict");
        filterState.verdict =
          filterState.verdict === verdict ? "all" : verdict;
        applyFilter();
      });
    });
  }
}
