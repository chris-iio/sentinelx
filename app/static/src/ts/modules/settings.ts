/**
 * Settings page module — accordion and API key toggles.
 */

type AccordionRecord = { section: HTMLElement; header: HTMLElement };
type KeyToggleRecord = { button: HTMLButtonElement; input: HTMLInputElement };
type SectionRecords = {
  accordionRecords: AccordionRecord[];
  keyToggleRecords: KeyToggleRecord[];
};

function collectSectionRecords(sections: NodeListOf<HTMLElement>): SectionRecords {
  const accordionRecords: AccordionRecord[] = [];
  const keyToggleRecords: KeyToggleRecord[] = [];

  for (let i = 0; i < sections.length; i += 1) {
    const section = sections[i];
    if (!section) continue;

    if (section.hasAttribute("data-provider")) {
      const header = section.querySelector<HTMLElement>(".accordion-header");
      if (header) accordionRecords.push({ section, header });
    }

    const button = section.querySelector(
      "[data-role='toggle-key']"
    ) as HTMLButtonElement | null;
    const input = section.querySelector(
      "input[type='password'], input[type='text']"
    ) as HTMLInputElement | null;
    if (button && input) keyToggleRecords.push({ button, input });
  }

  return { accordionRecords, keyToggleRecords };
}

/** Wire up accordion sections — one open at a time. */
function initAccordion(sectionRecords: AccordionRecord[]): void {
  function expandSection(section: HTMLElement, activeHeader: HTMLElement): void {
    for (let i = 0; i < sectionRecords.length; i += 1) {
      const record = sectionRecords[i];
      if (!record) continue;
      const { section: s, header } = record;
      if (s !== section) {
        s.removeAttribute("data-expanded");
        header.setAttribute("aria-expanded", "false");
      }
    }
    section.setAttribute("data-expanded", "");
    activeHeader.setAttribute("aria-expanded", "true");
  }

  for (let i = 0; i < sectionRecords.length; i += 1) {
    const record = sectionRecords[i];
    if (!record) continue;
    const { section, header } = record;
    header.addEventListener("click", () => {
      if (section.hasAttribute("data-expanded")) {
        section.removeAttribute("data-expanded");
        header.setAttribute("aria-expanded", "false");
      } else {
        expandSection(section, header);
      }
    });
  }
}

/** Wire up per-provider API key show/hide toggles. */
function initKeyToggles(keyToggleRecords: KeyToggleRecord[]): void {
  for (let i = 0; i < keyToggleRecords.length; i += 1) {
    const record = keyToggleRecords[i];
    if (!record) continue;
    const { button, input } = record;

    button.addEventListener("click", () => {
      if (input.type === "password") {
        input.type = "text";
        button.textContent = "Hide";
      } else {
        input.type = "password";
        button.textContent = "Show";
      }
    });
  }
}

export function init(): void {
  const sections = document.querySelectorAll<HTMLElement>(".settings-section");
  const { accordionRecords, keyToggleRecords } = collectSectionRecords(sections);
  initAccordion(accordionRecords);
  initKeyToggles(keyToggleRecords);
}
