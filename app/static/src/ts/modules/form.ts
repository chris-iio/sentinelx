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

// ---- Submit label (mode-aware) ----

function updateSubmitLabel(mode: string): void {
  const submitBtn = document.getElementById("submit-btn");
  if (!submitBtn) return;
  submitBtn.textContent = mode === "online" ? "Extract & Enrich" : "Extract IOCs";
  // Mode-aware button color
  submitBtn.classList.remove("mode-online", "mode-offline");
  submitBtn.classList.add(mode === "online" ? "mode-online" : "mode-offline");
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
  const widget = document.getElementById("mode-toggle-widget");
  const toggleBtn = document.getElementById("mode-toggle-btn");
  const modeInput = document.querySelector<HTMLInputElement>("#mode-input");
  if (!widget || !toggleBtn || !modeInput) return;

  // Non-nullable aliases for closures
  const w: HTMLElement = widget;
  const tb: HTMLElement = toggleBtn;
  const mi: HTMLInputElement = modeInput;

  tb.addEventListener("click", function () {
    const current = attr(w, "data-mode");
    const next = current === "offline" ? "online" : "offline";
    w.setAttribute("data-mode", next);
    mi.value = next;
    tb.setAttribute("aria-pressed", next === "online" ? "true" : "false");
    updateSubmitLabel(next);
  });

  // Set initial label based on current mode (defensive)
  updateSubmitLabel(mi.value);
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
