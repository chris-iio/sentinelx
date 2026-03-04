/**
 * Settings page module — tab switching, accordion, and API key toggles.
 */

/** Wire up the Providers | About tab bar. */
function initTabs(): void {
  const tabs = document.querySelectorAll<HTMLButtonElement>(".settings-tab");
  const panels = document.querySelectorAll<HTMLElement>(".settings-tab-panel");
  if (tabs.length === 0) return;

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;
      if (!target) return;

      tabs.forEach((t) => t.setAttribute("aria-selected", "false"));
      tab.setAttribute("aria-selected", "true");

      panels.forEach((p) => {
        if (p.dataset.panel === target) {
          p.setAttribute("data-active", "");
        } else {
          p.removeAttribute("data-active");
        }
      });
    });
  });
}

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

  // Auto-expand first unconfigured provider, or first provider if all configured
  const firstUnconfigured = document.querySelector<HTMLElement>(
    ".settings-section:has(.api-key-status--missing)"
  );
  const target = firstUnconfigured ?? sections[0];
  if (target) expandSection(target);
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
  initTabs();
  initAccordion();
  initKeyToggles();
}
