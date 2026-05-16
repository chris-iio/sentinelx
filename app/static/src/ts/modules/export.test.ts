import type { EnrichmentItem } from "../types/api";
import { buildCSV, buildIocListText, buildIocListTextFromResults, exportFilenameTimestamp } from "./export";

describe("exportFilenameTimestamp", () => {
  it("formats export filenames from fixed ISO positions without regex replacement", async () => {
    expect(exportFilenameTimestamp(new Date("2026-01-02T03:04:05.678Z"))).toBe(
      "2026-01-02T03-04-05"
    );

    const source = await import("node:fs/promises").then((fs) =>
      fs.readFile("app/static/src/ts/modules/export.ts", "utf8")
    );
    const helperBody = source.slice(
      source.indexOf("export function exportFilenameTimestamp"),
      source.indexOf("function csvEscape")
    );

    expect(helperBody).not.toContain(".replace(");
    expect(helperBody).toContain("iso.slice(0, 13)");
    expect(helperBody).toContain("iso.slice(14, 16)");
    expect(helperBody).toContain("iso.slice(17, 19)");
  });
});

describe("buildCSV", () => {
  it("keeps the static header literal instead of joining module-load columns", async () => {
    const source = await import("node:fs/promises").then((fs) =>
      fs.readFile("app/static/src/ts/modules/export.ts", "utf8")
    );

    expect(source).not.toContain("CSV_COLUMNS.join");
    expect(source).toContain(
      'const CSV_HEADER = "ioc_value,ioc_type,provider,verdict,detection_count,total_engines,scan_date,signature,malware_printable,threat_type,countryCode,isp,top_detections";'
    );
  });

  it("builds CSV without accumulating intermediate row arrays", () => {
    const push = Array.prototype.push;
    const join = Array.prototype.join;
    Array.prototype.push = function () {
      throw new Error("buildCSV should not push rows into an accumulator array");
    };
    Array.prototype.join = function () {
      throw new Error("buildCSV should not join per-row arrays");
    };

    try {
      const results: EnrichmentItem[] = [
        {
          type: "result",
          ioc_value: "evil.example",
          ioc_type: "domain",
          provider: "VirusTotal",
          verdict: "malicious",
          detection_count: 3,
          total_engines: 70,
          scan_date: "2026-01-02T03:04:05Z",
          raw_stats: {
            signature: 'quoted "value"',
            top_detections: ["alpha", "beta"],
          },
        },
        {
          type: "error",
          ioc_value: "evil.example",
          ioc_type: "domain",
          provider: "Example",
          error: "timeout",
        },
      ];

      const csv = buildCSV(results);

      Array.prototype.push = push;
      Array.prototype.join = join;

      expect(csv.split("\n")).toHaveLength(2);
      expect(csv).toContain("ioc_value,ioc_type,provider,verdict");
      expect(csv).toContain("evil.example,domain,VirusTotal,malicious,3,70");
      expect(csv).toContain('"quoted ""value"""');
      expect(csv).toContain("alpha; beta");
      expect(csv).not.toContain("timeout");
    } finally {
      Array.prototype.push = push;
      Array.prototype.join = join;
    }
  });

  it("builds CSV with indexed result iteration", () => {
    const results: EnrichmentItem[] = [
      {
        type: "result",
        ioc_value: "evil.example",
        ioc_type: "domain",
        provider: "VirusTotal",
        verdict: "malicious",
        detection_count: 3,
        total_engines: 70,
      },
    ];
    Object.defineProperty(results, Symbol.iterator, {
      value() {
        throw new Error("buildCSV should not allocate an array iterator");
      },
    });

    expect(buildCSV(results)).toContain("evil.example,domain,VirusTotal,malicious,3,70");
  });

  it("formats array raw-stat fields with indexed iteration", () => {
    const topDetections = ["alpha", "beta"];
    Object.defineProperty(topDetections, Symbol.iterator, {
      value() {
        throw new Error("rawStatField should not iterate array raw stats");
      },
    });
    const results: EnrichmentItem[] = [
      {
        type: "result",
        ioc_value: "evil.example",
        ioc_type: "domain",
        provider: "VirusTotal",
        verdict: "malicious",
        detection_count: 3,
        total_engines: 70,
        raw_stats: {
          top_detections: topDetections,
        },
      },
    ];

    expect(buildCSV(results)).toContain("alpha; beta");
  });

  it("skips separator loop work for empty, single, pair, or triple array raw-stat fields", async () => {
    const source = await import("node:fs/promises").then((fs) =>
      fs.readFile("app/static/src/ts/modules/export.ts", "utf8")
    );
    const helperBody = source.slice(
      source.indexOf("function rawStatField"),
      source.indexOf("// ---- Public API ----")
    );

    const results: EnrichmentItem[] = [
      {
        type: "result",
        ioc_value: "empty.example",
        ioc_type: "domain",
        provider: "VirusTotal",
        verdict: "clean",
        detection_count: 0,
        total_engines: 1,
        raw_stats: {
          signature: [],
          top_detections: ["only"],
        },
      },
    ];

    const csv = buildCSV(results);

    expect(csv).toContain("empty.example,domain,VirusTotal,clean,0,1,,,,,,,only");
    expect(helperBody).toContain("if (val.length === 0) return \"\";");
    expect(helperBody).toContain("if (val.length === 1) return String(val[0]);");
    expect(helperBody).toContain("if (val.length === 2) return String(val[0]) + \"; \" + String(val[1]);");
    expect(helperBody).toContain("if (val.length === 3) return String(val[0]) + \"; \" + String(val[1]) + \"; \" + String(val[2]);");
    expect(helperBody).toContain("let text = String(val[0]);");
    expect(helperBody).toContain("for (let i = 1; i < val.length; i += 1)");
    expect(helperBody).not.toContain("text ? \"; \"");
  });

  it("formats two-value raw-stat arrays without join", () => {
    const join = Array.prototype.join;
    Array.prototype.join = function failJoin() {
      throw new Error("two-value raw-stat fields should not call join");
    };

    try {
      expect(
        buildCSV([
          {
            type: "result",
            ioc_value: "evil.example",
            ioc_type: "domain",
            provider: "VirusTotal",
            verdict: "malicious",
            detection_count: 2,
            total_engines: 70,
            raw_stats: { top_detections: ["alpha", "beta"] },
          },
        ])
      ).toContain("alpha; beta");
    } finally {
      Array.prototype.join = join;
    }
  });

  it("formats three-value raw-stat arrays without join", () => {
    const join = Array.prototype.join;
    Array.prototype.join = function failJoin() {
      throw new Error("three-value raw-stat fields should not call join");
    };

    try {
      expect(
        buildCSV([
          {
            type: "result",
            ioc_value: "evil.example",
            ioc_type: "domain",
            provider: "VirusTotal",
            verdict: "malicious",
            detection_count: 3,
            total_engines: 70,
            raw_stats: { top_detections: ["alpha", "beta", "gamma"] },
          },
        ])
      ).toContain("alpha; beta; gamma");
    } finally {
      Array.prototype.join = join;
    }
  });
});

describe("buildIocListText", () => {
  it("shares one deduplicated value append helper across copy sources", async () => {
    const source = await import("node:fs/promises").then((fs) =>
      fs.readFile("app/static/src/ts/modules/export.ts", "utf8")
    );

    expect(source.match(/function appendUniqueIocValue/g) ?? []).toHaveLength(1);
    expect(source.match(/seen = appendUniqueIocValue\(values, seen/g) ?? []).toHaveLength(2);
    expect(source).not.toContain('text += (text ? "\\n" : "")');
    expect(source).not.toContain('return text + (text ? "\\n" : "") + value');
    expect(source).toContain("function joinIocValues");
    expect(source).not.toContain("const seen = new Set<string>();");
  });

  it("builds deduplicated IOC copy text without join for two or three values", () => {
    function card(value: string | null): HTMLElement {
      return {
        getAttribute(name: string): string | null {
          return name === "data-ioc-value" ? value : null;
        },
      } as HTMLElement;
    }

    const join = Array.prototype.join;
    Array.prototype.join = function () {
      throw new Error("two-value IOC copy text should not call join");
    };

    try {
      expect(buildIocListText([
        card("1.2.3.4"),
        card("1.2.3.4"),
        card("evil.example"),
        card(null),
      ])).toBe("1.2.3.4\nevil.example");
      expect(buildIocListText([
        card("1.2.3.4"),
        card("evil.example"),
        card("hashvalue"),
      ])).toBe("1.2.3.4\nevil.example\nhashvalue");
    } finally {
      Array.prototype.join = join;
    }
  });

  it("builds IOC copy text with indexed card access", () => {
    function card(value: string): HTMLElement {
      return {
        getAttribute(name: string): string | null {
          return name === "data-ioc-value" ? value : null;
        },
      } as HTMLElement;
    }

    const cards = [card("1.2.3.4"), card("evil.example")];
    Object.defineProperty(cards, Symbol.iterator, {
      value() {
        throw new Error("buildIocListText should not allocate a card iterator");
      },
    });

    expect(buildIocListText(cards)).toBe("1.2.3.4\nevil.example");
  });

  it("skips Set and join allocation for empty, single, or duplicate-only IOC copy text", () => {
    function card(value: string | null): HTMLElement {
      return {
        getAttribute(name: string): string | null {
          return name === "data-ioc-value" ? value : null;
        },
      } as HTMLElement;
    }

    const OriginalSet = globalThis.Set;
    const join = Array.prototype.join;
    globalThis.Set = function failSet() {
      throw new Error("single IOC copy text should not allocate a dedupe Set");
    } as unknown as SetConstructor;
    Array.prototype.join = function failJoin() {
      throw new Error("empty/single IOC copy text should not call join");
    };

    try {
      expect(buildIocListText([])).toBe("");
      expect(buildIocListText([card(null)])).toBe("");
      expect(buildIocListText([card("1.2.3.4"), card("1.2.3.4")])).toBe("1.2.3.4");
      expect(buildIocListTextFromResults([{ type: "result", ioc_value: "1.2.3.4" } as EnrichmentItem])).toBe(
        "1.2.3.4"
      );
    } finally {
      globalThis.Set = OriginalSet;
      Array.prototype.join = join;
    }
  });
});

describe("buildIocListTextFromResults", () => {
  it("builds deduplicated IOC copy text directly from export results", () => {
    const results = [
      { type: "error", ioc_value: "1.2.3.4" },
      { type: "result", ioc_value: "1.2.3.4" },
      { type: "result", ioc_value: "evil.example" },
    ] as EnrichmentItem[];
    Object.defineProperty(results, Symbol.iterator, {
      value() {
        throw new Error("result-backed IOC copying should not allocate an array iterator");
      },
    });

    const querySelectorAllSpy = vi.spyOn(document, "querySelectorAll").mockImplementation(() => {
      throw new Error("result-backed IOC copying should not scan card DOM");
    });

    try {
      expect(buildIocListTextFromResults(results)).toBe("1.2.3.4\nevil.example");
      expect(querySelectorAllSpy).not.toHaveBeenCalled();
    } finally {
      querySelectorAllSpy.mockRestore();
    }
  });
});
