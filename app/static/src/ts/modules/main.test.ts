/**
 * Focused tests for main.ts results-surface dispatch.
 */

vi.mock("./form", () => ({ init: vi.fn() }));
vi.mock("./clipboard", () => ({ init: vi.fn() }));
vi.mock("./cards", () => ({ init: vi.fn() }));
vi.mock("./filter", () => ({ init: vi.fn() }));
vi.mock("./enrichment", () => ({ init: vi.fn() }));
vi.mock("./history", () => ({ init: vi.fn() }));
vi.mock("./settings", () => ({ init: vi.fn() }));
vi.mock("./ui", () => ({ init: vi.fn() }));
vi.mock("./graph", () => ({ init: vi.fn() }));

describe("results surface dispatch", () => {
  beforeEach(() => {
    vi.resetModules();
    document.body.innerHTML = "";
    Object.defineProperty(document, "readyState", {
      configurable: true,
      value: "loading",
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("dispatches explicit history pages to the history initializer only", async () => {
    document.body.innerHTML = `
      <div class="page-results"
           data-results-owner="history"
           data-job-id="history"
           data-mode="online"
           data-history-results='[]'></div>
    `;

    const main = await import("../main");
    const enrichment = await import("./enrichment");
    const history = await import("./history");

    main.initResultsSurface(document.querySelector<HTMLElement>(".page-results"));

    expect(history.init).toHaveBeenCalledTimes(1);
    expect(enrichment.init).not.toHaveBeenCalled();
    expect(document.querySelector(".page-results")?.getAttribute("data-results-owner-resolved")).toBe(
      "history"
    );
  });

  it("treats malformed explicit live ownership as static instead of starting polling", async () => {
    document.body.innerHTML = `
      <div class="page-results"
           data-results-owner="live"
           data-mode="online"></div>
    `;

    const main = await import("../main");
    const enrichment = await import("./enrichment");
    const history = await import("./history");

    main.initResultsSurface(document.querySelector<HTMLElement>(".page-results"));

    expect(enrichment.init).not.toHaveBeenCalled();
    expect(history.init).not.toHaveBeenCalled();
    expect(document.querySelector(".page-results")?.getAttribute("data-results-owner-resolved")).toBe(
      "static"
    );
  });
});
