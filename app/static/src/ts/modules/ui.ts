/**
 * UI utilities module — scroll-aware filter bar behavior.
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

/** Initialise the scroll-aware filter enhancement. */
export function init(): void {
  initScrollAwareFilterBar();
}
