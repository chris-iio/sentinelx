import { readFileSync } from "node:fs";

import { getProviderCounts, verdictSeverityIndex } from "./ioc";

describe("verdictSeverityIndex", () => {
  it("preserves severity ordering without lookup-table construction", () => {
    const source = readFileSync(`${process.cwd()}/app/static/src/ts/types/ioc.ts`, "utf8");
    const mapGetSpy = vi.spyOn(Map.prototype, "get");
    mapGetSpy.mockImplementation(() => {
      throw new Error("verdictSeverityIndex should not need a Map lookup");
    });

    try {
      expect(verdictSeverityIndex("error")).toBe(0);
      expect(verdictSeverityIndex("no_data")).toBe(1);
      expect(verdictSeverityIndex("clean")).toBe(2);
      expect(verdictSeverityIndex("suspicious")).toBe(3);
      expect(verdictSeverityIndex("malicious")).toBe(4);
      expect(verdictSeverityIndex("known_good")).toBe(-1);
    } finally {
      mapGetSpy.mockRestore();
    }

    expect(source).not.toContain("new Map");
    expect(source).not.toContain("VERDICT_SEVERITY.map");
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
    const source = readFileSync(`${process.cwd()}/app/static/src/ts/types/ioc.ts`, "utf8");

    expect(getProviderCounts().ipv4).toBe(4);
    expect(getProviderCounts().ipv4).toBe(4);

    expect(parseSpy).toHaveBeenCalledTimes(1);
    expect(source).toContain("pageResultsElement()");
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
