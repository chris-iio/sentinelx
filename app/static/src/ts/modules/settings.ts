/**
 * Settings page module — API key show/hide toggle.
 *
 * Extracted from main.js initSettingsPage() (lines 792-805).
 */

/**
 * Initialise the settings page show/hide toggle for the API key input.
 * Toggles input.type between "password" and "text" and updates button label.
 */
export function init(): void {
  const btn = document.getElementById("toggle-key-btn");
  const input = document.getElementById("api-key") as HTMLInputElement | null;
  if (!btn || !input) return;

  btn.addEventListener("click", function () {
    if (input.type === "password") {
      input.type = "text";
      btn.textContent = "Hide";
    } else {
      input.type = "password";
      btn.textContent = "Show";
    }
  });
}
