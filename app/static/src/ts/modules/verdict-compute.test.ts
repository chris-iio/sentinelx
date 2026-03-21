/**
 * Unit tests for verdict-compute.ts pure functions.
 *
 * Covers: computeWorstVerdict, computeConsensus, consensusBadgeClass,
 *         computeAttribution, findWorstEntry.
 */

import {
  computeWorstVerdict,
  computeConsensus,
  consensusBadgeClass,
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
/*  computeConsensus                                                   */
/* ------------------------------------------------------------------ */

describe("computeConsensus", () => {
  it("returns {flagged:0, responded:0} for an empty array", () => {
    expect(computeConsensus([])).toEqual({ flagged: 0, responded: 0 });
  });

  it("counts clean entries as responded but not flagged", () => {
    const entries = [
      entry({ provider: "VT", verdict: "clean" }),
      entry({ provider: "TF", verdict: "clean" }),
    ];
    expect(computeConsensus(entries)).toEqual({ flagged: 0, responded: 2 });
  });

  it("counts malicious and suspicious as both flagged and responded", () => {
    const entries = [
      entry({ provider: "VT", verdict: "malicious" }),
      entry({ provider: "TF", verdict: "suspicious" }),
    ];
    expect(computeConsensus(entries)).toEqual({ flagged: 2, responded: 2 });
  });

  it("excludes no_data and error from both counts", () => {
    const entries = [
      entry({ provider: "VT", verdict: "malicious" }),
      entry({ provider: "MB", verdict: "no_data" }),
      entry({ provider: "TF", verdict: "error" }),
      entry({ provider: "SB", verdict: "clean" }),
    ];
    expect(computeConsensus(entries)).toEqual({ flagged: 1, responded: 2 });
  });

  it("all no_data/error entries → {flagged:0, responded:0}", () => {
    const entries = [
      entry({ provider: "VT", verdict: "no_data" }),
      entry({ provider: "MB", verdict: "error" }),
    ];
    expect(computeConsensus(entries)).toEqual({ flagged: 0, responded: 0 });
  });
});

/* ------------------------------------------------------------------ */
/*  consensusBadgeClass                                                */
/* ------------------------------------------------------------------ */

describe("consensusBadgeClass", () => {
  it("returns green class for 0 flagged", () => {
    expect(consensusBadgeClass(0)).toBe("consensus-badge--green");
  });

  it("returns yellow class for 1 flagged", () => {
    expect(consensusBadgeClass(1)).toBe("consensus-badge--yellow");
  });

  it("returns yellow class for 2 flagged", () => {
    expect(consensusBadgeClass(2)).toBe("consensus-badge--yellow");
  });

  it("returns red class for 3+ flagged", () => {
    expect(consensusBadgeClass(3)).toBe("consensus-badge--red");
    expect(consensusBadgeClass(10)).toBe("consensus-badge--red");
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

  it("returns the first entry when all have equal severity", () => {
    const entries = [
      entry({ provider: "VT", verdict: "clean" }),
      entry({ provider: "TF", verdict: "clean" }),
    ];
    const result = findWorstEntry(entries);
    expect(result!.provider).toBe("VT");
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
