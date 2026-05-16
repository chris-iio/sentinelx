import { init } from "./settings";
import { readFileSync } from "node:fs";

describe("settings init", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("uses cached accordion headers after initialization", () => {
    document.body.innerHTML = `
      <section class="settings-section" data-provider="alpha">
        <button class="accordion-header" aria-expanded="false" type="button">Alpha</button>
      </section>
      <section class="settings-section" data-provider="beta">
        <button class="accordion-header" aria-expanded="false" type="button">Beta</button>
      </section>
    `;

    init();

    const sectionQuerySpy = vi.spyOn(Element.prototype, "querySelector");
    const alpha = document.querySelector<HTMLElement>('[data-provider="alpha"]')!;
    const beta = document.querySelector<HTMLElement>('[data-provider="beta"]')!;
    const alphaHeader = alpha.querySelector<HTMLButtonElement>(".accordion-header")!;
    const betaHeader = beta.querySelector<HTMLButtonElement>(".accordion-header")!;
    sectionQuerySpy.mockClear();

    alphaHeader.click();
    betaHeader.click();

    expect(sectionQuerySpy).not.toHaveBeenCalled();
    expect(alpha.hasAttribute("data-expanded")).toBe(false);
    expect(alphaHeader.getAttribute("aria-expanded")).toBe("false");
    expect(beta.hasAttribute("data-expanded")).toBe(true);
    expect(betaHeader.getAttribute("aria-expanded")).toBe("true");
  });

  it("toggles API key visibility", () => {
    document.body.innerHTML = `
      <section class="settings-section">
        <button data-role="toggle-key" type="button">Show</button>
        <input type="password" value="secret" />
      </section>
    `;

    init();

    const button = document.querySelector<HTMLButtonElement>("[data-role='toggle-key']")!;
    const input = document.querySelector<HTMLInputElement>("input")!;

    button.click();
    expect(input.type).toBe("text");
    expect(button.textContent).toBe("Hide");

    button.click();
    expect(input.type).toBe("password");
    expect(button.textContent).toBe("Show");
  });

  it("reuses one settings-section query for accordion and key toggles", () => {
    document.body.innerHTML = `
      <section class="settings-section" data-provider="alpha">
        <button class="accordion-header" aria-expanded="false" type="button">Alpha</button>
      </section>
      <section class="settings-section">
        <button data-role="toggle-key" type="button">Show</button>
        <input type="password" value="fallback" />
      </section>
    `;
    const querySelectorAllSpy = vi.spyOn(document, "querySelectorAll");

    init();

    expect(querySelectorAllSpy.mock.calls.filter(([selector]) => selector === ".settings-section")).toHaveLength(1);
    expect(
      querySelectorAllSpy.mock.calls.some(([selector]) => selector === ".settings-section[data-provider]")
    ).toBe(false);

    const button = document.querySelector<HTMLButtonElement>("[data-role='toggle-key']")!;
    const input = document.querySelector<HTMLInputElement>("input")!;
    button.click();

    expect(input.type).toBe("text");
  });

  it("uses indexed loops for accordion records and key toggles", () => {
    document.body.innerHTML = `
      <section class="settings-section" data-provider="alpha">
        <button class="accordion-header" aria-expanded="false" type="button">Alpha</button>
      </section>
      <section class="settings-section" data-provider="beta">
        <button class="accordion-header" aria-expanded="false" type="button">Beta</button>
      </section>
      <section class="settings-section">
        <button data-role="toggle-key" type="button">Show</button>
        <input type="password" value="fallback" />
      </section>
    `;
    init();

    const alpha = document.querySelector<HTMLElement>('[data-provider="alpha"]')!;
    const beta = document.querySelector<HTMLElement>('[data-provider="beta"]')!;
    const alphaHeader = alpha.querySelector<HTMLButtonElement>(".accordion-header")!;
    const betaHeader = beta.querySelector<HTMLButtonElement>(".accordion-header")!;
    const button = document.querySelector<HTMLButtonElement>("[data-role='toggle-key']")!;
    const input = document.querySelector<HTMLInputElement>("input")!;

    alphaHeader.click();
    betaHeader.click();
    button.click();

    expect(alpha.hasAttribute("data-expanded")).toBe(false);
    expect(beta.hasAttribute("data-expanded")).toBe(true);
    expect(betaHeader.getAttribute("aria-expanded")).toBe("true");
    expect(input.type).toBe("text");

    const source = readFileSync(
      `${process.cwd()}/app/static/src/ts/modules/settings.ts`,
      "utf8"
    );
    expect(source).not.toContain(".forEach(");
    expect(source).toContain("for (let i = 0; i < sections.length; i += 1)");
    expect(source).toContain("for (let i = 0; i < sectionRecords.length; i += 1)");
    expect(source).toContain("for (let i = 0; i < keyToggleRecords.length; i += 1)");
  });

  it("collects accordion and key-toggle handles in one section pass", () => {
    document.body.innerHTML = `
      <section class="settings-section" data-provider="alpha">
        <button class="accordion-header" aria-expanded="false" type="button">Alpha</button>
        <button data-role="toggle-key" type="button">Show</button>
        <input type="password" value="alpha-key" />
      </section>
      <section class="settings-section" data-provider="beta">
        <button class="accordion-header" aria-expanded="false" type="button">Beta</button>
      </section>
    `;

    init();

    const alpha = document.querySelector<HTMLElement>('[data-provider="alpha"]')!;
    const beta = document.querySelector<HTMLElement>('[data-provider="beta"]')!;
    const alphaHeader = alpha.querySelector<HTMLButtonElement>(".accordion-header")!;
    const betaHeader = beta.querySelector<HTMLButtonElement>(".accordion-header")!;
    const button = alpha.querySelector<HTMLButtonElement>("[data-role='toggle-key']")!;
    const input = alpha.querySelector<HTMLInputElement>("input")!;

    alphaHeader.click();
    button.click();
    betaHeader.click();

    expect(alpha.hasAttribute("data-expanded")).toBe(false);
    expect(beta.hasAttribute("data-expanded")).toBe(true);
    expect(input.type).toBe("text");

    const source = readFileSync(
      `${process.cwd()}/app/static/src/ts/modules/settings.ts`,
      "utf8"
    );
    expect(source.match(/for \(let i = 0; i < sections\.length; i \+= 1\)/g)).toHaveLength(1);
    expect(source).toContain("collectSectionRecords(sections)");
    expect(source).not.toContain("initAccordion(sections)");
    expect(source).not.toContain("initKeyToggles(sections)");
  });
});
