/**
 * UI utilities module — scroll-aware filter bar and card stagger animation.
 *
 * Extracted from main.js initScrollAwareFilterBar() (lines 811-826)
 * and initCardStagger() (lines 830-835).
 */

/**
 * Add scroll listener that toggles "is-scrolled" class on .filter-bar-wrapper
 * once the page scrolls past 40px.
 */
function initScrollAwareFilterBar(): void {
  const filterBar = document.querySelector<HTMLElement>(".filter-bar-wrapper");
  if (!filterBar) return;

  let scrolled = false;
  window.addEventListener(
    "scroll",
    function () {
      const isScrolled = window.scrollY > 40;
      if (isScrolled !== scrolled) {
        scrolled = isScrolled;
        filterBar.classList.toggle("is-scrolled", scrolled);
      }
    },
    { passive: true }
  );
}

/**
 * Set --card-index CSS custom property on each .ioc-card element,
 * capped at 15 to limit stagger delay on long lists.
 */
function initCardStagger(): void {
  const cards = document.querySelectorAll<HTMLElement>(".ioc-card");
  cards.forEach((card, i) => {
    card.style.setProperty("--card-index", String(Math.min(i, 15)));
  });
}

/**
 * Wire the Recent Analyses collapsible section on the index page.
 * Collapsed by default; toggled via the header button.
 */
function initRecentAnalysesToggle(): void {
  const section = document.querySelector<HTMLElement>(".recent-analyses");
  if (!section) return;

  const toggle = section.querySelector<HTMLButtonElement>(".recent-analyses-toggle");
  if (!toggle) return;

  toggle.addEventListener("click", () => {
    const isOpen = section.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", String(isOpen));
  });
}

/**
 * Initialise all UI enhancements: scroll-aware filter bar and card stagger.
 */
export function init(): void {
  initScrollAwareFilterBar();
  initCardStagger();
  initRecentAnalysesToggle();
}
