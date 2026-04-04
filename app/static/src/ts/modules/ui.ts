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
 * Initialise all UI enhancements: scroll-aware filter bar and card stagger.
 */
export function init(): void {
  initScrollAwareFilterBar();
  initCardStagger();
}
