/**
 * Settings page module — per-provider API key show/hide toggles.
 *
 * Handles multiple provider sections independently. Each section contains a
 * toggle button (data-role="toggle-key") that controls the password/text
 * state of the nearest API key input within that section.
 */

/**
 * Initialise show/hide toggles for all provider API key inputs on the settings page.
 *
 * Finds every .settings-section element and wires up its toggle button to
 * its password input independently, so each provider's visibility is controlled
 * separately.
 */
export function init(): void {
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
