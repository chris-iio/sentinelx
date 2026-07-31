/**
 * Settings page module — accordion, API key, and static result state setup.
 */

import { initOfflineExtractionStates } from "./shared-rendering";

type AccordionRecord = { section: HTMLElement; header: HTMLElement };
type KeyToggleRecord = {
  button: HTMLButtonElement;
  input: HTMLInputElement;
  maskedValue: string | null;
};
type SectionRecords = {
  accordionRecords: AccordionRecord[];
  keyToggleRecords: KeyToggleRecord[];
};

function isMaskedCredential(value: string): boolean {
  return /^\*+.{4}$/.test(value);
}

function prepareSecretInput(section: HTMLElement, input: HTMLInputElement): string | null {
  const initialValue = input.value;
  const maskedValue = isMaskedCredential(initialValue) ? initialValue : null;
  const configured =
    maskedValue !== null || section.querySelector(".api-key-status--configured") !== null;

  input.setAttribute("data-configured", String(configured));
  if (maskedValue === null) return null;

  input.value = "";
  input.placeholder = "Configured — paste a new API key to replace it";
  return maskedValue;
}

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
    if (button && input) {
      keyToggleRecords.push({
        button,
        input,
        maskedValue: prepareSecretInput(section, input),
      });
    }
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
    const { button, input, maskedValue } = record;

    button.setAttribute("aria-pressed", "false");

    button.addEventListener("click", () => {
      if (input.type === "password") {
        input.type = "text";
        button.textContent = "Hide";
        button.setAttribute("aria-pressed", "true");
      } else {
        input.type = "password";
        button.textContent = "Show";
        button.setAttribute("aria-pressed", "false");
      }
    });

    if (maskedValue !== null && input.form) {
      input.form.addEventListener("submit", () => {
        if (input.value === maskedValue) {
          input.value = "";
        }
      });
    }
  }
}

export function init(): void {
  initOfflineExtractionStates();
  const sections = document.querySelectorAll<HTMLElement>(".settings-section");
  const { accordionRecords, keyToggleRecords } = collectSectionRecords(sections);
  initAccordion(accordionRecords);
  initKeyToggles(keyToggleRecords);
}
