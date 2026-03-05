/**
 * Settings page module — accordion and API key toggles.
 */

/** Wire up accordion sections — one open at a time. */
function initAccordion(): void {
  const sections = document.querySelectorAll<HTMLElement>(
    ".settings-section[data-provider]"
  );
  if (sections.length === 0) return;

  function expandSection(section: HTMLElement): void {
    sections.forEach((s) => {
      if (s !== section) {
        s.removeAttribute("data-expanded");
        const btn = s.querySelector(".accordion-header");
        if (btn) btn.setAttribute("aria-expanded", "false");
      }
    });
    section.setAttribute("data-expanded", "");
    const btn = section.querySelector(".accordion-header");
    if (btn) btn.setAttribute("aria-expanded", "true");
  }

  sections.forEach((section) => {
    const header = section.querySelector(".accordion-header");
    if (!header) return;
    header.addEventListener("click", () => {
      if (section.hasAttribute("data-expanded")) {
        section.removeAttribute("data-expanded");
        header.setAttribute("aria-expanded", "false");
      } else {
        expandSection(section);
      }
    });
  });

}

/** Wire up per-provider API key show/hide toggles. */
function initKeyToggles(): void {
  const sections = document.querySelectorAll(".settings-section");
  sections.forEach((section) => {
    const btn = section.querySelector(
      "[data-role='toggle-key']"
    ) as HTMLButtonElement | null;
    const input = section.querySelector(
      "input[type='password'], input[type='text']"
    ) as HTMLInputElement | null;
    if (!btn || !input) return;

    btn.addEventListener("click", () => {
      if (input.type === "password") {
        input.type = "text";
        btn.textContent = "Hide";
      } else {
        input.type = "password";
        btn.textContent = "Show";
      }
    });
  });
}

export function init(): void {
  initAccordion();
  initKeyToggles();
}
