/**
 * Clipboard module — copy buttons, copy-with-enrichment, and fallback copy.
 *
 * Extracted from main.js initCopyButtons(), showCopiedFeedback(),
 * fallbackCopy(), and writeToClipboard() (lines 166-223).
 *
 * writeToClipboard is exported for use by Phase 22's enrichment module
 * (export button needs to copy multi-IOC text to clipboard).
 */

import { attr } from "../utils/dom";

// ---- Private helpers ----

/**
 * Temporarily replace button text with "Copied!" then restore after 1500ms.
 * textContent is typed string|null — ?? ensures the original value is never null.
 */
function showCopiedFeedback(btn: HTMLElement): void {
  const original = btn.textContent ?? "Copy";
  btn.textContent = "Copied!";
  btn.classList.add("copied");
  setTimeout(function () {
    btn.textContent = original;
    btn.classList.remove("copied");
  }, 1500);
}

/**
 * Fallback copy via a temporary off-screen textarea and execCommand("copy").
 * Used when navigator.clipboard is unavailable (non-HTTPS, older browser).
 */
function fallbackCopy(text: string, btn: HTMLElement): void {
  // Create a temporary textarea, select its content, and copy
  const tmp = document.createElement("textarea");
  tmp.value = text;
  tmp.style.position = "fixed";
  tmp.style.top = "-9999px";
  tmp.style.left = "-9999px";
  document.body.appendChild(tmp);
  tmp.focus();
  tmp.select();
  try {
    document.execCommand("copy");
    showCopiedFeedback(btn);
  } catch {
    // Copy failed silently — user can still manually select the value
  } finally {
    document.body.removeChild(tmp);
  }
}

// ---- Public API ----

/**
 * Copy text to the clipboard using the Clipboard API, falling back to
 * execCommand when unavailable. Shows feedback on the triggering button.
 *
 * Exported so Phase 22's enrichment module can call it for the export button.
 */
export function writeToClipboard(text: string, btn: HTMLElement): void {
  if (!navigator.clipboard) {
    fallbackCopy(text, btn);
    return;
  }
  navigator.clipboard.writeText(text).then(function () {
    showCopiedFeedback(btn);
  }).catch(function () {
    fallbackCopy(text, btn);
  });
}

/**
 * Attach click handlers to all .copy-btn elements present in the DOM.
 * Each button reads data-value (IOC) and optionally data-enrichment (worst verdict).
 */
export function init(): void {
  const copyButtons = document.querySelectorAll<HTMLElement>(".copy-btn");

  copyButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      const value = attr(btn, "data-value");
      if (!value) return;

      // Check for enrichment summary set by polling loop (worst verdict)
      const enrichment = attr(btn, "data-enrichment");
      // attr() returns "" when attribute is absent (falsy) — same ternary as original
      const copyText = enrichment ? (value + " | " + enrichment) : value;

      writeToClipboard(copyText, btn);
    });
  });
}
