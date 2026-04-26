/**
 * Form controls module — submit button state, auto-grow textarea,
 * mode toggle, and paste feedback.
 *
 * Extracted from main.js initSubmitButton(), initAutoGrow(),
 * initModeToggle(), updateSubmitLabel(), showPasteFeedback() (lines 34-162).
 */

import { attr } from "../utils/dom";

// Module-level timer for paste feedback animation — avoids storing on HTMLElement
let pasteTimer: ReturnType<typeof setTimeout> | null = null;

// ---- Paste character count feedback (INPUT-02) ----

function showPasteFeedback(charCount: number): void {
  const feedback = document.getElementById("paste-feedback");
  if (!feedback) return;
  feedback.textContent = charCount + " characters pasted";
  feedback.style.display = "";
  feedback.classList.remove("is-hiding");
  feedback.classList.add("is-visible");
  if (pasteTimer !== null) clearTimeout(pasteTimer);
  pasteTimer = setTimeout(function () {
    feedback.classList.remove("is-visible");
    feedback.classList.add("is-hiding");
    setTimeout(function () {
      feedback.style.display = "none";
      feedback.classList.remove("is-hiding");
    }, 250);
  }, 2000);
}

// ---- Mode rendering ----

type AnalysisMode = "offline" | "online";

const MODE_COPY: Record<AnalysisMode, string> = {
  offline: "Offline selected — local extraction only; no provider enrichment requests are sent.",
  online: "Online selected — configured providers may enrich submitted indicators.",
};

function normalizeMode(mode: string): AnalysisMode {
  return mode === "online" ? "online" : "offline";
}

function renderModeState(mode: string, elements: {
  widget: HTMLElement;
  toggleBtn: HTMLElement;
  modeInput: HTMLInputElement;
  modeStatus: HTMLElement;
  submitBtn: HTMLElement | null;
}): void {
  const normalizedMode = normalizeMode(mode);
  const isOnline = normalizedMode === "online";

  elements.widget.setAttribute("data-mode", normalizedMode);
  elements.modeInput.value = normalizedMode;
  elements.toggleBtn.setAttribute("aria-pressed", isOnline ? "true" : "false");
  if (elements.toggleBtn.hasAttribute("aria-checked")) {
    elements.toggleBtn.setAttribute("aria-checked", isOnline ? "true" : "false");
  }
  elements.modeStatus.textContent = MODE_COPY[normalizedMode];

  if (elements.submitBtn) {
    elements.submitBtn.textContent = "Extract";
    elements.submitBtn.classList.remove("mode-online", "mode-offline");
    elements.submitBtn.classList.add(isOnline ? "mode-online" : "mode-offline");
  }
}

// ---- Submit button: disable when textarea is empty ----

function initSubmitButton(): void {
  const form = document.getElementById("analyze-form");
  if (!form) return;

  const textarea = document.querySelector<HTMLTextAreaElement>("#ioc-text");
  const submitBtn = document.querySelector<HTMLButtonElement>("#submit-btn");
  const clearBtn = document.getElementById("clear-btn");

  if (!textarea || !submitBtn) return;

  // Re-bind to non-nullable aliases so closures below don't need assertions.
  // TypeScript narrows the outer `const` after the if-check, but closures
  // (even non-async ones) cannot see that narrowing — we therefore introduce
  // new `const` bindings that are guaranteed non-null.
  const ta: HTMLTextAreaElement = textarea;
  const sb: HTMLButtonElement = submitBtn;

  function updateSubmitState(): void {
    sb.disabled = ta.value.trim().length === 0;
  }

  ta.addEventListener("input", updateSubmitState);

  // Also handle paste events (browser may not fire "input" immediately)
  ta.addEventListener("paste", function () {
    // Defer until after paste content is applied
    setTimeout(function () {
      updateSubmitState();
      showPasteFeedback(ta.value.length);
    }, 0);
  });

  // Initial state (page load with pre-filled content)
  updateSubmitState();

  // ---- Clear button ----
  if (clearBtn) {
    clearBtn.addEventListener("click", function () {
      ta.value = "";
      updateSubmitState();
      ta.focus();
    });
  }
}

// ---- Auto-grow textarea (INP-02) ----

function initAutoGrow(): void {
  const textarea = document.querySelector<HTMLTextAreaElement>("#ioc-text");
  if (!textarea) return;

  // Non-nullable alias for use inside closures (TypeScript can't narrow through closures)
  const ta: HTMLTextAreaElement = textarea;

  function grow(): void {
    ta.style.height = "auto";
    ta.style.height = ta.scrollHeight + "px";
  }

  ta.addEventListener("input", grow);

  ta.addEventListener("paste", function () {
    setTimeout(grow, 0);
  });

  grow();
}

// ---- Mode toggle switch (INPUT-01, INPUT-03) ----

function initModeToggle(): void {
  const form = document.getElementById("analyze-form");
  const widget = document.getElementById("mode-toggle-widget");
  const toggleBtn = document.getElementById("mode-toggle-btn");
  const modeInput = document.querySelector<HTMLInputElement>("#mode-input");
  const modeStatus = document.getElementById("mode-status");
  const submitBtn = document.querySelector<HTMLButtonElement>("#submit-btn");

  if (!form && !widget && !toggleBtn && !modeInput && !modeStatus) return;
  if (!form || !widget || !toggleBtn || !modeInput || !modeStatus) {
    throw new Error("Missing mode toggle markup required for form state synchronization");
  }

  // Non-nullable aliases for closures
  const w: HTMLElement = widget;
  const tb: HTMLElement = toggleBtn;
  const mi: HTMLInputElement = modeInput;
  const ms: HTMLElement = modeStatus;
  const sb: HTMLButtonElement | null = submitBtn;

  const render = (mode: string): void => {
    renderModeState(mode, {
      widget: w,
      toggleBtn: tb,
      modeInput: mi,
      modeStatus: ms,
      submitBtn: sb,
    });
  };

  tb.addEventListener("click", function () {
    const current = normalizeMode(attr(w, "data-mode", mi.value));
    const next: AnalysisMode = current === "offline" ? "online" : "offline";
    render(next);
  });

  // Set initial synchronized state based on the hidden form contract first.
  render(mi.value || attr(w, "data-mode", "offline"));
}

// ---- Public API ----

/**
 * Initialise all form controls: submit button state, auto-grow, and mode toggle.
 */
export function init(): void {
  initSubmitButton();
  initAutoGrow();
  initModeToggle();
}
