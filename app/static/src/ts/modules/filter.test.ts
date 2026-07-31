import { init } from "./filter";

function buildDom(): void {
  document.body.innerHTML = `
    <div id="filter-root">
      <button data-filter-verdict="all" class="filter-btn">All</button>
      <button data-filter-verdict="malicious" class="filter-btn">Malicious</button>
      <button data-filter-type="all" class="filter-pill">All</button>
      <button data-filter-type="domain" class="filter-pill">Domain</button>
      <input id="filter-search-input" />
      <div class="ioc-card" data-verdict="malicious" data-ioc-type="domain" data-ioc-value="bad.example"></div>
      <div class="ioc-card" data-verdict="clean" data-ioc-type="ipv4" data-ioc-value="1.2.3.4"></div>
    </div>
    <div id="verdict-dashboard">
      <button class="verdict-kpi-card" data-verdict="malicious">Malicious</button>
    </div>
  `;
}

describe("filter init", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    buildDom();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("reuses static filter node lists across repeated filter applications", async () => {
    const querySelectorAllSpy = vi.spyOn(HTMLElement.prototype, "querySelectorAll");

    init();
    const initQueries = querySelectorAllSpy.mock.calls.length;

    document.querySelector<HTMLElement>('[data-filter-verdict="malicious"]')?.click();
    document.querySelector<HTMLElement>('[data-filter-type="domain"]')?.click();
    const searchInput = document.getElementById("filter-search-input") as HTMLInputElement;
    searchInput.value = "bad";
    searchInput.dispatchEvent(new Event("input"));
    await vi.advanceTimersByTimeAsync(150);

    const badCard = document.querySelector<HTMLElement>('[data-ioc-value="bad.example"]');
    const cleanCard = document.querySelector<HTMLElement>('[data-ioc-value="1.2.3.4"]');

    expect(badCard?.hidden).toBe(false);
    expect(cleanCard?.hidden).toBe(true);
    expect(
      document.querySelector('[data-filter-verdict="malicious"]')?.classList.contains("filter-btn--active")
    ).toBe(true);
    expect(
      document.querySelector('[data-filter-type="domain"]')?.classList.contains("filter-pill--active")
    ).toBe(true);
    expect(querySelectorAllSpy.mock.calls.length).toBe(initQueries);
  });

  it("uses indexed NodeList loops for controls and filter applications", async () => {
    vi.spyOn(NodeList.prototype, "forEach").mockImplementation(() => {
      throw new Error("filter init should use indexed NodeList loops");
    });

    init();

    document.querySelector<HTMLElement>('[data-filter-verdict="malicious"]')?.click();
    document.querySelector<HTMLElement>('[data-filter-type="domain"]')?.click();
    document.querySelector<HTMLElement>(".verdict-kpi-card")?.click();
    const searchInput = document.getElementById("filter-search-input") as HTMLInputElement;
    searchInput.value = "bad";
    searchInput.dispatchEvent(new Event("input"));
    await vi.advanceTimersByTimeAsync(150);

    const badCard = document.querySelector<HTMLElement>('[data-ioc-value="bad.example"]');
    const cleanCard = document.querySelector<HTMLElement>('[data-ioc-value="1.2.3.4"]');

    expect(badCard?.hidden).toBe(false);
    expect(cleanCard?.hidden).toBe(true);
  });

  it("caches static card fields while preserving live verdict updates", () => {
    init();

    const badCard = document.querySelector<HTMLElement>('[data-ioc-value="bad.example"]')!;
    const cleanCard = document.querySelector<HTMLElement>('[data-ioc-value="1.2.3.4"]')!;
    cleanCard.setAttribute("data-verdict", "malicious");

    document.querySelector<HTMLElement>('[data-filter-verdict="malicious"]')?.click();

    expect(badCard.hidden).toBe(false);
    expect(cleanCard.hidden).toBe(false);
  });

  it("does not reread static card or control attributes during filter applications", () => {
    init();
    const verdictButton = document.querySelector<HTMLElement>('[data-filter-verdict="malicious"]');
    const typePill = document.querySelector<HTMLElement>('[data-filter-type="domain"]');
    const dashboardBadge = document.querySelector<HTMLElement>(".verdict-kpi-card");

    const getAttributeSpy = vi.spyOn(HTMLElement.prototype, "getAttribute");

    verdictButton?.click();
    typePill?.click();
    dashboardBadge?.click();

    expect(getAttributeSpy.mock.calls.some(([name]) => name === "data-ioc-type")).toBe(false);
    expect(getAttributeSpy.mock.calls.some(([name]) => name === "data-ioc-value")).toBe(false);
    expect(getAttributeSpy.mock.calls.some(([name]) => name === "data-filter-verdict")).toBe(false);
    expect(getAttributeSpy.mock.calls.some(([name]) => name === "data-filter-type")).toBe(false);
    expect(getAttributeSpy.mock.calls.some(([name]) => name === "data-verdict")).toBe(true);
  });
});
