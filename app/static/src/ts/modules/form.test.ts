/**
 * Focused tests for the index form mode toggle state synchronization.
 */

import { init } from "./form";

function renderIndexForm(options: { mode?: string; ariaChecked?: string } = {}): void {
  const mode = options.mode ?? "offline";
  const ariaChecked = options.ariaChecked ? ` aria-checked="${options.ariaChecked}"` : "";

  document.body.innerHTML = `
    <form id="analyze-form">
      <textarea id="ioc-text"></textarea>
      <span id="paste-feedback" style="display:none;"></span>
      <div class="mode-toggle" aria-labelledby="mode-title" aria-describedby="mode-help mode-status">
        <div class="mode-toggle-copy">
          <h2 id="mode-title" class="mode-toggle-title">Analysis mode</h2>
          <p id="mode-help" class="mode-toggle-help">Offline mode is the safe default: extract locally without contacting external providers. Use Online only when configured providers should enrich the results.</p>
          <p id="mode-status" class="mode-toggle-status" aria-live="polite">stale status</p>
        </div>
        <div id="mode-toggle-widget" class="mode-toggle-widget" data-mode="${mode}">
          <span class="mode-toggle-label mode-toggle-label--offline">Offline</span>
          <button id="mode-toggle-btn" type="button" aria-pressed="false" aria-label="Toggle analysis mode" aria-describedby="mode-help mode-status"${ariaChecked}>
            <span class="mode-toggle-thumb"></span>
          </button>
          <span class="mode-toggle-label mode-toggle-label--online">Online</span>
        </div>
        <input id="mode-input" name="mode" type="hidden" value="${mode}">
      </div>
      <button id="clear-btn" type="button">Clear</button>
      <button id="submit-btn" type="submit" class="btn btn-primary" disabled>Extract</button>
    </form>
  `;
}

function modeState(): {
  widgetMode: string | null;
  hiddenValue: string;
  ariaPressed: string | null;
  ariaChecked: string | null;
  status: string;
  submitText: string | null;
  submitClass: string;
} {
  const widget = document.querySelector<HTMLElement>("#mode-toggle-widget");
  const input = document.querySelector<HTMLInputElement>("#mode-input");
  const toggle = document.querySelector<HTMLButtonElement>("#mode-toggle-btn");
  const status = document.querySelector<HTMLElement>("#mode-status");
  const submit = document.querySelector<HTMLButtonElement>("#submit-btn");

  if (!widget || !input || !toggle || !status || !submit) {
    throw new Error("Mode test fixture is missing required elements");
  }

  return {
    widgetMode: widget.getAttribute("data-mode"),
    hiddenValue: input.value,
    ariaPressed: toggle.getAttribute("aria-pressed"),
    ariaChecked: toggle.getAttribute("aria-checked"),
    status: status.textContent ?? "",
    submitText: submit.textContent,
    submitClass: submit.className,
  };
}

describe("index form mode state", () => {
  afterEach(() => {
    vi.useRealTimers();
    document.body.innerHTML = "";
  });

  it("renders the initial offline state across hidden input, widget, ARIA, status, and submit style", () => {
    renderIndexForm();

    init();

    expect(modeState()).toMatchObject({
      widgetMode: "offline",
      hiddenValue: "offline",
      ariaPressed: "false",
      status: "Offline selected — local extraction only; no provider enrichment requests are sent.",
      submitText: "Extract",
    });
    expect(modeState().submitClass).toContain("mode-offline");
    expect(modeState().submitClass).not.toContain("mode-online");
  });

  it("click toggles to online and back to offline without changing the Extract label", () => {
    renderIndexForm();
    init();

    document.querySelector<HTMLButtonElement>("#mode-toggle-btn")?.click();

    expect(modeState()).toMatchObject({
      widgetMode: "online",
      hiddenValue: "online",
      ariaPressed: "true",
      status: "Online selected — configured providers may enrich submitted indicators.",
      submitText: "Extract",
    });
    expect(modeState().submitClass).toContain("mode-online");
    expect(modeState().submitClass).not.toContain("mode-offline");

    document.querySelector<HTMLButtonElement>("#mode-toggle-btn")?.click();

    expect(modeState()).toMatchObject({
      widgetMode: "offline",
      hiddenValue: "offline",
      ariaPressed: "false",
      status: "Offline selected — local extraction only; no provider enrichment requests are sent.",
      submitText: "Extract",
    });
    expect(modeState().submitClass).toContain("mode-offline");
    expect(modeState().submitClass).not.toContain("mode-online");
  });

  it("keeps optional aria-checked synchronized when markup already provides it", () => {
    renderIndexForm({ ariaChecked: "false" });
    init();

    document.querySelector<HTMLButtonElement>("#mode-toggle-btn")?.click();
    expect(modeState().ariaChecked).toBe("true");

    document.querySelector<HTMLButtonElement>("#mode-toggle-btn")?.click();
    expect(modeState().ariaChecked).toBe("false");
  });

  it("normalizes an invalid initial mode back to offline", () => {
    renderIndexForm({ mode: "unexpected" });

    init();

    expect(modeState()).toMatchObject({
      widgetMode: "offline",
      hiddenValue: "offline",
      ariaPressed: "false",
      status: "Offline selected — local extraction only; no provider enrichment requests are sent.",
    });
  });

  it("fails fast when the index form is missing T01 mode markup", () => {
    document.body.innerHTML = `
      <form id="analyze-form">
        <textarea id="ioc-text"></textarea>
        <button id="submit-btn" type="submit">Extract</button>
      </form>
    `;

    expect(() => init()).toThrow("Missing mode toggle markup");
  });

  it("keeps submit enablement independent from mode toggles", () => {
    renderIndexForm();
    init();

    const textarea = document.querySelector<HTMLTextAreaElement>("#ioc-text");
    const submit = document.querySelector<HTMLButtonElement>("#submit-btn");
    const toggle = document.querySelector<HTMLButtonElement>("#mode-toggle-btn");
    if (!textarea || !submit || !toggle) {
      throw new Error("Mode test fixture is missing required elements");
    }

    expect(submit.disabled).toBe(true);
    textarea.value = "192.0.2.1";
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    expect(submit.disabled).toBe(false);

    toggle.click();
    expect(submit.disabled).toBe(false);
    expect(submit.className).toContain("mode-online");
  });

  it("updates submit enablement without trim allocation", async () => {
    renderIndexForm();
    init();

    const textarea = document.querySelector<HTMLTextAreaElement>("#ioc-text");
    const submit = document.querySelector<HTMLButtonElement>("#submit-btn");
    if (!textarea || !submit) {
      throw new Error("Mode test fixture is missing required elements");
    }

    textarea.value = " \n\t ";
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    expect(submit.disabled).toBe(true);

    textarea.value = " \n\t 192.0.2.1";
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    expect(submit.disabled).toBe(false);

    const source = await import("node:fs/promises").then((fs) =>
      fs.readFile("app/static/src/ts/modules/form.ts", "utf8")
    );
    expect(source).toContain("function hasNonWhitespace");
    expect(source).not.toContain(".trim(");
    expect(source).not.toContain(".trim().length");
  });

  it("reuses form element lookups across init helpers", () => {
    renderIndexForm();
    const querySelectorSpy = vi.spyOn(document, "querySelector");

    init();

    expect(querySelectorSpy.mock.calls.filter(([selector]) => selector === "#ioc-text")).toHaveLength(1);
    expect(querySelectorSpy.mock.calls.filter(([selector]) => selector === "#submit-btn")).toHaveLength(1);
    expect(querySelectorSpy.mock.calls.filter(([selector]) => selector === "#mode-input")).toHaveLength(1);
  });
});
