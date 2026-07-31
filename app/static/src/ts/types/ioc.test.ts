import type { VerdictKey } from "./ioc";
import { getProviderCounts, verdictSeverityIndex } from "./ioc";

describe("verdictSeverityIndex", () => {
  it("uses malicious-to-error precedence for summary and display ordering", () => {
    const worstToBest: VerdictKey[] = [
      "malicious",
      "suspicious",
      "known_good",
      "clean",
      "no_data",
      "error",
    ];

    expect(worstToBest.map(verdictSeverityIndex)).toEqual([5, 4, 3, 2, 1, 0]);
  });
});

describe("getProviderCounts", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("reuses parsed provider-count metadata while the raw attribute is unchanged", () => {
    document.body.innerHTML = `<div class="page-results" data-provider-counts='{"ipv4":4}'></div>`;
    const parseSpy = vi.spyOn(JSON, "parse");

    expect(getProviderCounts().ipv4).toBe(4);
    expect(getProviderCounts().ipv4).toBe(4);

    expect(parseSpy).toHaveBeenCalledTimes(1);
  });

  it("reparses provider-count metadata when the raw attribute changes", () => {
    document.body.innerHTML = `<div class="page-results" data-provider-counts='{"ipv4":5}'></div>`;
    const pageResults = document.querySelector<HTMLElement>(".page-results")!;
    const parseSpy = vi.spyOn(JSON, "parse");

    expect(getProviderCounts().ipv4).toBe(5);
    pageResults.setAttribute("data-provider-counts", '{"ipv4":7}');

    expect(getProviderCounts().ipv4).toBe(7);
    expect(parseSpy).toHaveBeenCalledTimes(2);
  });

  it("caches malformed provider-count fallback for the same raw attribute", () => {
    document.body.innerHTML = `<div class="page-results" data-provider-counts='not-json'></div>`;
    const parseSpy = vi.spyOn(JSON, "parse");

    expect(getProviderCounts().ipv4).toBe(2);
    expect(getProviderCounts().ipv4).toBe(2);

    expect(parseSpy).toHaveBeenCalledTimes(1);
  });

  it("skips JSON parsing for the literal empty provider-count payload", () => {
    document.body.innerHTML = `<div class="page-results" data-provider-counts='{}'></div>`;
    const parseSpy = vi.spyOn(JSON, "parse").mockImplementation(() => {
      throw new Error("empty provider-count payload should skip JSON.parse");
    });

    expect(getProviderCounts()).toEqual({});
    expect(getProviderCounts()).toEqual({});

    expect(parseSpy).not.toHaveBeenCalled();
  });
});
