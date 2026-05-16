/**
 * Unit tests for verdict-compute.ts pure functions.
 *
 * Covers: computeWorstVerdict, computeAttribution, findWorstEntry.
 */

import {
  computeWorstVerdict,
  computeAttribution,
  findWorstEntry,
  type VerdictEntry,
} from "./verdict-compute";

/* ------------------------------------------------------------------ */
/*  Test helpers                                                       */
/* ------------------------------------------------------------------ */

/** Build a VerdictEntry with sensible defaults — override only what matters. */
function entry(overrides: Partial<VerdictEntry> & Pick<VerdictEntry, "provider" | "verdict">): VerdictEntry {
  return {
    summaryText: "",
    detectionCount: 0,
    totalEngines: 0,
    statText: "",
    ...overrides,
  };
}

/* ------------------------------------------------------------------ */
/*  computeWorstVerdict                                                */
/* ------------------------------------------------------------------ */

describe("computeWorstVerdict", () => {
  it("returns 'no_data' for an empty array", () => {
    expect(computeWorstVerdict([])).toBe("no_data");
  });

  it("returns the verdict of a single entry", () => {
    expect(computeWorstVerdict([entry({ provider: "VT", verdict: "clean" })])).toBe("clean");
  });

  it("returns the highest severity verdict from a mixed array", () => {
    const entries: VerdictEntry[] = [
      entry({ provider: "VT", verdict: "clean" }),
      entry({ provider: "TF", verdict: "suspicious" }),
      entry({ provider: "MB", verdict: "no_data" }),
    ];
    expect(computeWorstVerdict(entries)).toBe("suspicious");
  });

  it("returns 'malicious' when it is the worst verdict present", () => {
    const entries: VerdictEntry[] = [
      entry({ provider: "VT", verdict: "malicious" }),
      entry({ provider: "TF", verdict: "clean" }),
      entry({ provider: "MB", verdict: "suspicious" }),
    ];
    expect(computeWorstVerdict(entries)).toBe("malicious");
  });

  it("computes worst verdict without an extra some() pre-scan", () => {
    const originalSome = Array.prototype.some;
    Array.prototype.some = function failSome() {
      throw new Error("computeWorstVerdict should scan once");
    };

    try {
      expect(
        computeWorstVerdict([
          entry({ provider: "VT", verdict: "clean" }),
          entry({ provider: "TF", verdict: "suspicious" }),
          entry({ provider: "MB", verdict: "malicious" }),
        ]),
      ).toBe("malicious");
    } finally {
      Array.prototype.some = originalSome;
    }
  });

  it("computes worst verdict with indexed entry access", () => {
    const entries = [
      entry({ provider: "VT", verdict: "clean" }),
      entry({ provider: "TF", verdict: "suspicious" }),
    ];
    Object.defineProperty(entries, Symbol.iterator, {
      value: () => {
        throw new Error("computeWorstVerdict should not require array iteration");
      },
    });

    expect(computeWorstVerdict(entries)).toBe("suspicious");
  });

  it("known_good overrides all other verdicts (design rule)", () => {
    const entries: VerdictEntry[] = [
      entry({ provider: "VT", verdict: "malicious" }),
      entry({ provider: "NSRL", verdict: "known_good" }),
      entry({ provider: "TF", verdict: "suspicious" }),
    ];
    expect(computeWorstVerdict(entries)).toBe("known_good");
  });

  it("known_good alone returns known_good", () => {
    expect(computeWorstVerdict([entry({ provider: "NSRL", verdict: "known_good" })])).toBe("known_good");
  });
});

/* ------------------------------------------------------------------ */
/*  computeAttribution                                                 */
/* ------------------------------------------------------------------ */

describe("computeAttribution", () => {
  it("returns fallback text for an empty array", () => {
    const result = computeAttribution([]);
    expect(result.provider).toBe("");
    expect(result.text).toMatch(/No providers returned data/);
  });

  it("returns fallback when all entries are no_data or error", () => {
    const entries = [
      entry({ provider: "VT", verdict: "no_data" }),
      entry({ provider: "MB", verdict: "error" }),
    ];
    const result = computeAttribution(entries);
    expect(result.provider).toBe("");
    expect(result.text).toMatch(/No providers returned data/);
  });

  it("returns the single entry's provider and statText", () => {
    const entries = [
      entry({ provider: "VirusTotal", verdict: "malicious", totalEngines: 72, statText: "45/72 engines" }),
    ];
    const result = computeAttribution(entries);
    expect(result.provider).toBe("VirusTotal");
    expect(result.text).toBe("VirusTotal: 45/72 engines");
  });

  it("picks the provider with highest totalEngines", () => {
    const entries = [
      entry({ provider: "ThreatFox", verdict: "malicious", totalEngines: 1, statText: "1 match" }),
      entry({ provider: "VirusTotal", verdict: "clean", totalEngines: 72, statText: "0/72 engines" }),
    ];
    const result = computeAttribution(entries);
    expect(result.provider).toBe("VirusTotal");
    expect(result.text).toBe("VirusTotal: 0/72 engines");
  });

  it("breaks ties by verdict severity descending", () => {
    const entries = [
      entry({ provider: "ThreatFox", verdict: "malicious", totalEngines: 10, statText: "10 matches" }),
      entry({ provider: "VirusTotal", verdict: "clean", totalEngines: 10, statText: "0/10 engines" }),
    ];
    const result = computeAttribution(entries);
    // malicious (severity 4) > clean (severity 2), so ThreatFox wins the tie
    expect(result.provider).toBe("ThreatFox");
  });

  it("selects attribution provider without sorting candidates", () => {
    const originalSort = Array.prototype.sort;
    Array.prototype.sort = function failSort() {
      throw new Error("computeAttribution should not sort candidates");
    };

    try {
      const result = computeAttribution([
        entry({ provider: "ThreatFox", verdict: "malicious", totalEngines: 10, statText: "10 matches" }),
        entry({ provider: "VirusTotal", verdict: "clean", totalEngines: 72, statText: "0/72 engines" }),
      ]);

      expect(result.provider).toBe("VirusTotal");
      expect(result.text).toBe("VirusTotal: 0/72 engines");
    } finally {
      Array.prototype.sort = originalSort;
    }
  });

  it("selects attribution provider with indexed entry access", () => {
    const entries = [
      entry({ provider: "ThreatFox", verdict: "malicious", totalEngines: 10, statText: "10 matches" }),
      entry({ provider: "VirusTotal", verdict: "clean", totalEngines: 72, statText: "0/72 engines" }),
    ];
    Object.defineProperty(entries, Symbol.iterator, {
      value: () => {
        throw new Error("computeAttribution should not require array iteration");
      },
    });

    const result = computeAttribution(entries);

    expect(result.provider).toBe("VirusTotal");
    expect(result.text).toBe("VirusTotal: 0/72 engines");
  });

  it("excludes no_data/error entries from attribution candidates", () => {
    const entries = [
      entry({ provider: "VT", verdict: "no_data", totalEngines: 100, statText: "100 engines" }),
      entry({ provider: "TF", verdict: "clean", totalEngines: 1, statText: "1 match" }),
    ];
    const result = computeAttribution(entries);
    // VT has higher engines but is no_data, so TF is the only candidate
    expect(result.provider).toBe("TF");
  });
});

/* ------------------------------------------------------------------ */
/*  findWorstEntry                                                     */
/* ------------------------------------------------------------------ */

describe("findWorstEntry", () => {
  it("returns undefined for an empty array", () => {
    expect(findWorstEntry([])).toBeUndefined();
  });

  it("returns the single entry from a single-element array", () => {
    const e = entry({ provider: "VT", verdict: "clean" });
    expect(findWorstEntry([e])).toBe(e);
  });

  it("returns the highest severity entry from a mixed array", () => {
    const entries = [
      entry({ provider: "VT", verdict: "clean" }),
      entry({ provider: "TF", verdict: "malicious" }),
      entry({ provider: "MB", verdict: "suspicious" }),
    ];
    const result = findWorstEntry(entries);
    expect(result).toBeDefined();
    expect(result!.provider).toBe("TF");
    expect(result!.verdict).toBe("malicious");
  });

  it("short-circuits once malicious is found", () => {
    const result = findWorstEntry([
      entry({ provider: "VT", verdict: "clean" }),
      entry({ provider: "TF", verdict: "malicious" }),
      {
        get verdict(): never {
          throw new Error("findWorstEntry should stop after malicious");
        },
        provider: "Late",
        summaryText: "",
        detectionCount: 0,
        totalEngines: 0,
        statText: "",
      },
    ]);

    expect(result!.provider).toBe("TF");
    expect(result!.verdict).toBe("malicious");
  });

  it("returns the first entry when all have equal severity", () => {
    const entries = [
      entry({ provider: "VT", verdict: "clean" }),
      entry({ provider: "TF", verdict: "clean" }),
    ];
    const result = findWorstEntry(entries);
    expect(result!.provider).toBe("VT");
  });

  it("compares two entries directly without array iteration", () => {
    const entries = [
      entry({ provider: "VT", verdict: "clean" }),
      entry({ provider: "TF", verdict: "suspicious" }),
    ];
    Object.defineProperty(entries, Symbol.iterator, {
      value: () => {
        throw new Error("two-entry worst verdict lookup should not allocate an iterator");
      },
    });

    const result = findWorstEntry(entries);

    expect(result!.provider).toBe("TF");
    expect(result!.verdict).toBe("suspicious");
  });

  it("correctly ranks error below no_data below clean", () => {
    // severity order: error(0) < no_data(1) < clean(2) < suspicious(3) < malicious(4)
    const entries = [
      entry({ provider: "E", verdict: "error" }),
      entry({ provider: "N", verdict: "no_data" }),
      entry({ provider: "C", verdict: "clean" }),
    ];
    const result = findWorstEntry(entries);
    expect(result!.provider).toBe("C");
    expect(result!.verdict).toBe("clean");
  });
});
