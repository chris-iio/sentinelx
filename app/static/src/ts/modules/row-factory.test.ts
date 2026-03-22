/**
 * Unit tests for row-factory.ts DOM builders.
 *
 * Covers all 7 exported functions and the CONTEXT_PROVIDERS set.
 * Requirement mapping:
 *   VIS-01 → createDetailRow verdict badge class
 *   VIS-02 → updateSummaryRow micro-bar segments
 *   GRP-01 → createContextRow context rendering path
 *   GRP-02 → createDetailRow no-data class + injectSectionHeadersAndNoDataSummary toggle
 *   CTX-01 → updateContextLine inline context fields
 *   CTX-02 → updateSummaryRow staleness badge
 */

import {
  formatDate,
  getOrCreateSummaryRow,
  updateSummaryRow,
  createDetailRow,
  createContextRow,
  updateContextLine,
  injectSectionHeadersAndNoDataSummary,
  CONTEXT_PROVIDERS,
} from "./row-factory";
import type { VerdictEntry } from "./verdict-compute";
import type { EnrichmentResultItem, EnrichmentItem } from "../types/api";
import type { VerdictKey } from "../types/ioc";

/* ------------------------------------------------------------------ */
/*  Test helpers                                                       */
/* ------------------------------------------------------------------ */

/** Build a VerdictEntry with sensible defaults — override only what matters. */
function entry(
  overrides: Partial<VerdictEntry> & Pick<VerdictEntry, "provider" | "verdict">,
): VerdictEntry {
  return {
    summaryText: "",
    detectionCount: 0,
    totalEngines: 0,
    statText: "",
    ...overrides,
  };
}

/** Build an EnrichmentResultItem with sensible defaults. */
function resultItem(
  overrides: Partial<EnrichmentResultItem> & Pick<EnrichmentResultItem, "provider">,
): EnrichmentResultItem {
  return {
    type: "result",
    ioc_value: "1.2.3.4",
    ioc_type: "ipv4",
    verdict: "clean",
    detection_count: 0,
    total_engines: 0,
    scan_date: null,
    raw_stats: {},
    ...overrides,
  };
}

/** Create a minimal enrichment slot DOM matching the real template. */
function makeSlot(): HTMLElement {
  const slot = document.createElement("div");
  slot.className = "enrichment-slot";

  const details = document.createElement("div");
  details.className = "enrichment-details";

  const repSection = document.createElement("div");
  repSection.className = "enrichment-section enrichment-section--reputation";
  details.appendChild(repSection);

  const ctxSection = document.createElement("div");
  ctxSection.className = "enrichment-section enrichment-section--context";
  details.appendChild(ctxSection);

  const noDataSection = document.createElement("div");
  noDataSection.className = "enrichment-section enrichment-section--no-data";
  details.appendChild(noDataSection);

  slot.appendChild(details);
  return slot;
}

/** Create a minimal IOC card DOM with .ioc-context-line. */
function makeCard(): HTMLElement {
  const card = document.createElement("div");
  card.className = "ioc-card";
  const contextLine = document.createElement("div");
  contextLine.className = "ioc-context-line";
  card.appendChild(contextLine);
  return card;
}

/* ------------------------------------------------------------------ */
/*  CONTEXT_PROVIDERS                                                  */
/* ------------------------------------------------------------------ */

describe("CONTEXT_PROVIDERS", () => {
  it("contains the expected context-only providers", () => {
    expect(CONTEXT_PROVIDERS.has("IP Context")).toBe(true);
    expect(CONTEXT_PROVIDERS.has("DNS Records")).toBe(true);
    expect(CONTEXT_PROVIDERS.has("Cert History")).toBe(true);
    expect(CONTEXT_PROVIDERS.has("ThreatMiner")).toBe(true);
    expect(CONTEXT_PROVIDERS.has("ASN Intel")).toBe(true);
  });

  it("does not contain reputation providers", () => {
    expect(CONTEXT_PROVIDERS.has("VirusTotal")).toBe(false);
    expect(CONTEXT_PROVIDERS.has("AbuseIPDB")).toBe(false);
  });
});

/* ------------------------------------------------------------------ */
/*  formatDate                                                         */
/* ------------------------------------------------------------------ */

describe("formatDate", () => {
  it("returns empty string for null input", () => {
    expect(formatDate(null)).toBe("");
  });

  it("returns empty string for empty string input", () => {
    expect(formatDate("")).toBe("");
  });

  it("formats a valid ISO 8601 date", () => {
    const result = formatDate("2024-06-15T10:30:00Z");
    expect(result).toBeTruthy();
    // The exact format depends on locale, but it should not be empty
    expect(result.length).toBeGreaterThan(0);
  });

  it("returns the raw string for an invalid date", () => {
    // "not-a-date" produces an invalid Date → toLocaleDateString may throw or return "Invalid Date"
    // The catch block returns the raw string
    const result = formatDate("not-a-date");
    expect(typeof result).toBe("string");
  });
});

/* ------------------------------------------------------------------ */
/*  getOrCreateSummaryRow                                              */
/* ------------------------------------------------------------------ */

describe("getOrCreateSummaryRow", () => {
  it("creates .ioc-summary-row with correct a11y attributes", () => {
    const slot = makeSlot();
    const row = getOrCreateSummaryRow(slot);

    expect(row.classList.contains("ioc-summary-row")).toBe(true);
    expect(row.getAttribute("role")).toBe("button");
    expect(row.getAttribute("tabindex")).toBe("0");
    expect(row.getAttribute("aria-expanded")).toBe("false");
  });

  it("contains a .chevron-icon-wrapper with SVG", () => {
    const slot = makeSlot();
    const row = getOrCreateSummaryRow(slot);

    const chevron = row.querySelector(".chevron-icon-wrapper");
    expect(chevron).not.toBeNull();

    const svg = chevron!.querySelector("svg");
    expect(svg).not.toBeNull();
    expect(svg!.getAttribute("class")).toBe("chevron-icon");
  });

  it("is idempotent — calling twice returns the same element", () => {
    const slot = makeSlot();
    const first = getOrCreateSummaryRow(slot);
    const second = getOrCreateSummaryRow(slot);

    expect(first).toBe(second);
    // Only one summary row in the slot
    expect(slot.querySelectorAll(".ioc-summary-row").length).toBe(1);
  });

  it("inserts before .enrichment-details when present", () => {
    const slot = makeSlot();
    const row = getOrCreateSummaryRow(slot);

    const details = slot.querySelector(".enrichment-details");
    expect(row.nextElementSibling).toBe(details);
  });

  it("appends to slot when .enrichment-details is absent", () => {
    const slot = document.createElement("div");
    slot.className = "enrichment-slot";
    // No .enrichment-details child
    const row = getOrCreateSummaryRow(slot);
    expect(slot.lastElementChild).toBe(row);
  });
});

/* ------------------------------------------------------------------ */
/*  updateSummaryRow — VIS-02, CTX-02                                  */
/* ------------------------------------------------------------------ */

describe("updateSummaryRow", () => {
  it("VIS-02: creates micro-bar with correct segment classes and widths", () => {
    const slot = makeSlot();
    const verdicts: Record<string, VerdictEntry[]> = {
      "1.2.3.4": [
        entry({ provider: "VT", verdict: "malicious" }),
        entry({ provider: "TF", verdict: "malicious" }),
        entry({ provider: "MB", verdict: "clean" }),
        entry({ provider: "SB", verdict: "no_data" }),
      ],
    };

    updateSummaryRow(slot, "1.2.3.4", verdicts);

    const microBar = slot.querySelector(".verdict-micro-bar");
    expect(microBar).not.toBeNull();

    const segments = microBar!.querySelectorAll<HTMLElement>(".micro-bar-segment");
    expect(segments.length).toBe(3); // malicious, clean, no_data (0 suspicious skipped)

    // Verify segment classes
    const segClasses = Array.from(segments).map((s) => s.className);
    expect(segClasses[0]).toContain("micro-bar-segment--malicious");
    expect(segClasses[1]).toContain("micro-bar-segment--clean");
    expect(segClasses[2]).toContain("micro-bar-segment--no_data");

    // Verify widths: 2/4=50%, 1/4=25%, 1/4=25%
    expect(segments[0]!.style.width).toBe("50%");
    expect(segments[1]!.style.width).toBe("25%");
    expect(segments[2]!.style.width).toBe("25%");
  });

  it("VIS-02: micro-bar title attribute encodes counts", () => {
    const slot = makeSlot();
    const verdicts: Record<string, VerdictEntry[]> = {
      "1.2.3.4": [
        entry({ provider: "VT", verdict: "malicious" }),
        entry({ provider: "TF", verdict: "suspicious" }),
        entry({ provider: "MB", verdict: "clean" }),
      ],
    };

    updateSummaryRow(slot, "1.2.3.4", verdicts);

    const microBar = slot.querySelector<HTMLElement>(".verdict-micro-bar");
    expect(microBar).not.toBeNull();

    const title = microBar!.getAttribute("title");
    expect(title).toBe("1 malicious, 1 suspicious, 1 clean, 0 no data");
  });

  it("VIS-02: no .consensus-badge exists in updated summary row", () => {
    const slot = makeSlot();
    const verdicts: Record<string, VerdictEntry[]> = {
      "test.com": [entry({ provider: "VT", verdict: "clean" })],
    };

    updateSummaryRow(slot, "test.com", verdicts);

    const badge = slot.querySelector(".consensus-badge");
    expect(badge).toBeNull();
  });

  it("renders worst verdict badge", () => {
    const slot = makeSlot();
    const verdicts: Record<string, VerdictEntry[]> = {
      "evil.com": [
        entry({ provider: "VT", verdict: "malicious", statText: "5/72 engines" }),
        entry({ provider: "TF", verdict: "clean", statText: "0 matches" }),
      ],
    };

    updateSummaryRow(slot, "evil.com", verdicts);

    const verdictBadge = slot.querySelector(".verdict-badge");
    expect(verdictBadge).not.toBeNull();
    expect(verdictBadge!.classList.contains("verdict-malicious")).toBe(true);
    expect(verdictBadge!.textContent).toBe("MALICIOUS");
  });

  it("renders attribution text from best provider", () => {
    const slot = makeSlot();
    const verdicts: Record<string, VerdictEntry[]> = {
      "1.2.3.4": [
        entry({ provider: "VirusTotal", verdict: "malicious", totalEngines: 72, statText: "45/72 engines" }),
      ],
    };

    updateSummaryRow(slot, "1.2.3.4", verdicts);

    const attribution = slot.querySelector(".ioc-summary-attribution");
    expect(attribution).not.toBeNull();
    expect(attribution!.textContent).toBe("VirusTotal: 45/72 engines");
  });

  it("CTX-02: shows staleness badge when entries have cachedAt", () => {
    const slot = makeSlot();
    // Set a cachedAt 2 hours in the past
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    const verdicts: Record<string, VerdictEntry[]> = {
      "1.2.3.4": [
        entry({ provider: "VT", verdict: "clean", cachedAt: twoHoursAgo }),
        entry({ provider: "TF", verdict: "clean" }),
      ],
    };

    updateSummaryRow(slot, "1.2.3.4", verdicts);

    const staleBadge = slot.querySelector(".staleness-badge");
    expect(staleBadge).not.toBeNull();
    expect(staleBadge!.textContent).toMatch(/cached \d+h ago/);
  });

  it("CTX-02: no staleness badge when no entries have cachedAt", () => {
    const slot = makeSlot();
    const verdicts: Record<string, VerdictEntry[]> = {
      "1.2.3.4": [
        entry({ provider: "VT", verdict: "clean" }),
        entry({ provider: "TF", verdict: "clean" }),
      ],
    };

    updateSummaryRow(slot, "1.2.3.4", verdicts);

    const staleBadge = slot.querySelector(".staleness-badge");
    expect(staleBadge).toBeNull();
  });

  it("edge: empty entries array causes early return without crash", () => {
    const slot = makeSlot();
    const verdicts: Record<string, VerdictEntry[]> = {
      "1.2.3.4": [],
    };

    // Should not throw
    expect(() => updateSummaryRow(slot, "1.2.3.4", verdicts)).not.toThrow();

    // No summary row created because entries is empty
    const summaryRow = slot.querySelector(".ioc-summary-row");
    expect(summaryRow).toBeNull();
  });

  it("edge: missing iocValue key causes early return without crash", () => {
    const slot = makeSlot();
    const verdicts: Record<string, VerdictEntry[]> = {};

    expect(() => updateSummaryRow(slot, "missing-ioc", verdicts)).not.toThrow();
  });

  it("preserves chevron wrapper after re-render", () => {
    const slot = makeSlot();
    const verdicts: Record<string, VerdictEntry[]> = {
      "1.2.3.4": [entry({ provider: "VT", verdict: "clean" })],
    };

    updateSummaryRow(slot, "1.2.3.4", verdicts);

    const chevron = slot.querySelector(".chevron-icon-wrapper");
    expect(chevron).not.toBeNull();

    // Chevron should be the last child of summary row
    const row = slot.querySelector(".ioc-summary-row");
    expect(row!.lastElementChild).toBe(chevron);
  });
});

/* ------------------------------------------------------------------ */
/*  createDetailRow — VIS-01, GRP-02                                   */
/* ------------------------------------------------------------------ */

describe("createDetailRow", () => {
  it("creates a row with .provider-detail-row class and data-verdict attribute", () => {
    const row = createDetailRow("VirusTotal", "malicious", "45/72 engines");

    expect(row.classList.contains("provider-detail-row")).toBe(true);
    expect(row.getAttribute("data-verdict")).toBe("malicious");
  });

  it("VIS-01: verdict badge has correct class matching verdict", () => {
    const row = createDetailRow("VirusTotal", "malicious", "45/72 engines");

    const badge = row.querySelector(".verdict-badge");
    expect(badge).not.toBeNull();
    expect(badge!.classList.contains("verdict-malicious")).toBe(true);
    expect(badge!.textContent).toBe("MALICIOUS");
  });

  it("renders provider name and stat text", () => {
    const row = createDetailRow("AbuseIPDB", "suspicious", "confidence 85%");

    const name = row.querySelector(".provider-detail-name");
    expect(name).not.toBeNull();
    expect(name!.textContent).toBe("AbuseIPDB");

    const stat = row.querySelector(".provider-detail-stat");
    expect(stat).not.toBeNull();
    expect(stat!.textContent).toBe("confidence 85%");
  });

  it("GRP-02: no_data verdict row has provider-row--no-data class", () => {
    const row = createDetailRow("MalwareBazaar", "no_data", "Not found");

    expect(row.classList.contains("provider-row--no-data")).toBe(true);
    expect(row.getAttribute("data-verdict")).toBe("no_data");
  });

  it("GRP-02: error verdict row has provider-row--no-data class", () => {
    const row = createDetailRow("ThreatFox", "error", "Timeout");

    expect(row.classList.contains("provider-row--no-data")).toBe(true);
    expect(row.getAttribute("data-verdict")).toBe("error");
  });

  it("GRP-02: malicious verdict row does NOT have provider-row--no-data class", () => {
    const row = createDetailRow("VirusTotal", "malicious", "45/72 engines");

    expect(row.classList.contains("provider-row--no-data")).toBe(false);
  });

  it("shows cache badge when result has cached_at", () => {
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    const result: EnrichmentItem = resultItem({
      provider: "VirusTotal",
      cached_at: twoHoursAgo,
    });

    const row = createDetailRow("VirusTotal", "clean", "0/72 engines", result);

    const cacheBadge = row.querySelector(".cache-badge");
    expect(cacheBadge).not.toBeNull();
    expect(cacheBadge!.textContent).toMatch(/cached \d+h ago/);
  });

  it("no cache badge when result has no cached_at", () => {
    const result: EnrichmentItem = resultItem({ provider: "VirusTotal" });

    const row = createDetailRow("VirusTotal", "clean", "0/72 engines", result);

    const cacheBadge = row.querySelector(".cache-badge");
    expect(cacheBadge).toBeNull();
  });

  it("renders context fields from raw_stats when present", () => {
    const result: EnrichmentItem = resultItem({
      provider: "AbuseIPDB",
      raw_stats: {
        abuseConfidenceScore: 85,
        totalReports: 42,
        countryCode: "US",
      },
    });

    const row = createDetailRow("AbuseIPDB", "suspicious", "confidence 85%", result);

    const contextDiv = row.querySelector(".provider-context");
    expect(contextDiv).not.toBeNull();

    // Should have context fields for the matched stats
    const fields = contextDiv!.querySelectorAll(".provider-context-field");
    expect(fields.length).toBeGreaterThan(0);
  });
});

/* ------------------------------------------------------------------ */
/*  createContextRow — GRP-01                                          */
/* ------------------------------------------------------------------ */

describe("createContextRow", () => {
  it("GRP-01: creates a row with .provider-context-row class", () => {
    const result = resultItem({
      provider: "IP Context",
      raw_stats: { geo: "US, New York" },
    });

    const row = createContextRow(result);

    expect(row.classList.contains("provider-detail-row")).toBe(true);
    expect(row.classList.contains("provider-context-row")).toBe(true);
  });

  it("GRP-01: sets data-verdict='context' for sort pinning", () => {
    const result = resultItem({
      provider: "IP Context",
      raw_stats: { geo: "US, New York" },
    });

    const row = createContextRow(result);

    expect(row.getAttribute("data-verdict")).toBe("context");
  });

  it("GRP-01: does NOT render a verdict badge", () => {
    const result = resultItem({
      provider: "IP Context",
      raw_stats: { geo: "US, New York" },
    });

    const row = createContextRow(result);

    const badge = row.querySelector(".verdict-badge");
    expect(badge).toBeNull();
  });

  it("renders provider name", () => {
    const result = resultItem({
      provider: "DNS Records",
      raw_stats: { a: ["93.184.216.34"] },
    });

    const row = createContextRow(result);

    const name = row.querySelector(".provider-detail-name");
    expect(name).not.toBeNull();
    expect(name!.textContent).toBe("DNS Records");
  });

  it("renders context fields from raw_stats", () => {
    const result = resultItem({
      provider: "IP Context",
      raw_stats: { geo: "US, New York", reverse: "host.example.com" },
    });

    const row = createContextRow(result);

    const contextDiv = row.querySelector(".provider-context");
    expect(contextDiv).not.toBeNull();

    const fields = contextDiv!.querySelectorAll(".provider-context-field");
    expect(fields.length).toBe(2); // geo + reverse
  });

  it("renders cache badge when result has cached_at", () => {
    const oneHourAgo = new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString();
    const result = resultItem({
      provider: "IP Context",
      raw_stats: { geo: "US, NY" },
      cached_at: oneHourAgo,
    });

    const row = createContextRow(result);

    const cacheBadge = row.querySelector(".cache-badge");
    expect(cacheBadge).not.toBeNull();
    expect(cacheBadge!.textContent).toMatch(/cached \d+h ago/);
  });
});

/* ------------------------------------------------------------------ */
/*  injectSectionHeadersAndNoDataSummary — GRP-02                      */
/* ------------------------------------------------------------------ */

describe("injectSectionHeadersAndNoDataSummary", () => {
  it("GRP-02: creates no-data-summary-row with count text", () => {
    const slot = makeSlot();
    const noDataSection = slot.querySelector<HTMLElement>(".enrichment-section--no-data")!;

    // Add 3 no-data rows
    for (let i = 0; i < 3; i++) {
      const row = document.createElement("div");
      row.className = "provider-detail-row provider-row--no-data";
      noDataSection.appendChild(row);
    }

    injectSectionHeadersAndNoDataSummary(slot);

    const summaryRow = noDataSection.querySelector(".no-data-summary-row");
    expect(summaryRow).not.toBeNull();
    expect(summaryRow!.textContent).toBe("3 providers had no record");
  });

  it("GRP-02: uses singular 'provider' for count of 1", () => {
    const slot = makeSlot();
    const noDataSection = slot.querySelector<HTMLElement>(".enrichment-section--no-data")!;

    const row = document.createElement("div");
    row.className = "provider-detail-row provider-row--no-data";
    noDataSection.appendChild(row);

    injectSectionHeadersAndNoDataSummary(slot);

    const summaryRow = noDataSection.querySelector(".no-data-summary-row");
    expect(summaryRow).not.toBeNull();
    expect(summaryRow!.textContent).toBe("1 provider had no record");
  });

  it("GRP-02: summary row has correct a11y attributes", () => {
    const slot = makeSlot();
    const noDataSection = slot.querySelector<HTMLElement>(".enrichment-section--no-data")!;

    const row = document.createElement("div");
    row.className = "provider-detail-row provider-row--no-data";
    noDataSection.appendChild(row);

    injectSectionHeadersAndNoDataSummary(slot);

    const summaryRow = noDataSection.querySelector<HTMLElement>(".no-data-summary-row")!;
    expect(summaryRow.getAttribute("role")).toBe("button");
    expect(summaryRow.getAttribute("tabindex")).toBe("0");
    expect(summaryRow.getAttribute("aria-expanded")).toBe("false");
  });

  it("GRP-02: click toggles .no-data-expanded on section", () => {
    const slot = makeSlot();
    const noDataSection = slot.querySelector<HTMLElement>(".enrichment-section--no-data")!;

    for (let i = 0; i < 2; i++) {
      const row = document.createElement("div");
      row.className = "provider-detail-row provider-row--no-data";
      noDataSection.appendChild(row);
    }

    injectSectionHeadersAndNoDataSummary(slot);

    const summaryRow = noDataSection.querySelector<HTMLElement>(".no-data-summary-row")!;

    // Initially not expanded
    expect(noDataSection.classList.contains("no-data-expanded")).toBe(false);
    expect(summaryRow.getAttribute("aria-expanded")).toBe("false");

    // First click → expands
    summaryRow.click();
    expect(noDataSection.classList.contains("no-data-expanded")).toBe(true);
    expect(summaryRow.getAttribute("aria-expanded")).toBe("true");

    // Second click → collapses
    summaryRow.click();
    expect(noDataSection.classList.contains("no-data-expanded")).toBe(false);
    expect(summaryRow.getAttribute("aria-expanded")).toBe("false");
  });

  it("GRP-02: summary row is inserted before the first no-data row", () => {
    const slot = makeSlot();
    const noDataSection = slot.querySelector<HTMLElement>(".enrichment-section--no-data")!;

    const row1 = document.createElement("div");
    row1.className = "provider-detail-row provider-row--no-data";
    row1.textContent = "first-no-data";
    noDataSection.appendChild(row1);

    injectSectionHeadersAndNoDataSummary(slot);

    const summaryRow = noDataSection.querySelector(".no-data-summary-row")!;
    // Summary row should come before the first no-data row
    expect(summaryRow.nextElementSibling).toBe(row1);
  });

  it("edge: zero no-data rows → no summary row created", () => {
    const slot = makeSlot();

    injectSectionHeadersAndNoDataSummary(slot);

    const summaryRow = slot.querySelector(".no-data-summary-row");
    expect(summaryRow).toBeNull();
  });

  it("edge: no .enrichment-section--no-data element → no crash", () => {
    const slot = document.createElement("div");
    // Missing no-data section entirely
    expect(() => injectSectionHeadersAndNoDataSummary(slot)).not.toThrow();
  });
});

/* ------------------------------------------------------------------ */
/*  updateContextLine — CTX-01                                         */
/* ------------------------------------------------------------------ */

describe("updateContextLine", () => {
  it("CTX-01: IP Context with geo renders context-field span", () => {
    const card = makeCard();
    const result = resultItem({
      provider: "IP Context",
      raw_stats: { geo: "US, New York, NY" },
    });

    updateContextLine(card, result);

    const contextLine = card.querySelector(".ioc-context-line")!;
    const span = contextLine.querySelector<HTMLElement>('span[data-context-provider="IP Context"]');
    expect(span).not.toBeNull();
    expect(span!.className).toBe("context-field");
    expect(span!.textContent).toBe("US, New York, NY");
  });

  it("CTX-01: ASN Intel renders when no IP Context is present", () => {
    const card = makeCard();
    const result = resultItem({
      provider: "ASN Intel",
      raw_stats: { asn: "AS13335", prefix: "1.1.1.0/24" },
    });

    updateContextLine(card, result);

    const contextLine = card.querySelector(".ioc-context-line")!;
    const span = contextLine.querySelector<HTMLElement>('span[data-context-provider="ASN Intel"]');
    expect(span).not.toBeNull();
    expect(span!.textContent).toBe("AS13335 · 1.1.1.0/24");
  });

  it("CTX-01: ASN Intel is NOT added when IP Context already present (priority)", () => {
    const card = makeCard();

    // First, add IP Context
    updateContextLine(
      card,
      resultItem({
        provider: "IP Context",
        raw_stats: { geo: "US, Cloudflare" },
      }),
    );

    // Then attempt to add ASN Intel — should be skipped
    updateContextLine(
      card,
      resultItem({
        provider: "ASN Intel",
        raw_stats: { asn: "AS13335", prefix: "1.1.1.0/24" },
      }),
    );

    const contextLine = card.querySelector(".ioc-context-line")!;
    const asnSpan = contextLine.querySelector('span[data-context-provider="ASN Intel"]');
    expect(asnSpan).toBeNull();

    // IP Context should still be there
    const ipSpan = contextLine.querySelector('span[data-context-provider="IP Context"]');
    expect(ipSpan).not.toBeNull();
  });

  it("CTX-01: IP Context removes existing ASN Intel span", () => {
    const card = makeCard();

    // First, add ASN Intel
    updateContextLine(
      card,
      resultItem({
        provider: "ASN Intel",
        raw_stats: { asn: "AS13335" },
      }),
    );

    // Confirm ASN Intel is present
    const contextLine = card.querySelector(".ioc-context-line")!;
    expect(contextLine.querySelector('span[data-context-provider="ASN Intel"]')).not.toBeNull();

    // Now add IP Context — should remove ASN Intel
    updateContextLine(
      card,
      resultItem({
        provider: "IP Context",
        raw_stats: { geo: "US, Cloudflare" },
      }),
    );

    expect(contextLine.querySelector('span[data-context-provider="ASN Intel"]')).toBeNull();
    expect(contextLine.querySelector('span[data-context-provider="IP Context"]')).not.toBeNull();
  });

  it("CTX-01: DNS Records renders A-record text (max 3)", () => {
    const card = makeCard();
    const result = resultItem({
      provider: "DNS Records",
      raw_stats: {
        a: ["93.184.216.34", "93.184.216.35", "93.184.216.36", "93.184.216.37"],
      },
    });

    updateContextLine(card, result);

    const contextLine = card.querySelector(".ioc-context-line")!;
    const span = contextLine.querySelector<HTMLElement>('span[data-context-provider="DNS Records"]');
    expect(span).not.toBeNull();
    // Only first 3 IPs shown
    expect(span!.textContent).toBe("A: 93.184.216.34, 93.184.216.35, 93.184.216.36");
  });

  it("CTX-01: upsert — calling twice with same provider updates text, doesn't duplicate", () => {
    const card = makeCard();

    updateContextLine(
      card,
      resultItem({
        provider: "IP Context",
        raw_stats: { geo: "US, Old City" },
      }),
    );

    updateContextLine(
      card,
      resultItem({
        provider: "IP Context",
        raw_stats: { geo: "US, New City" },
      }),
    );

    const contextLine = card.querySelector(".ioc-context-line")!;
    const spans = contextLine.querySelectorAll('span[data-context-provider="IP Context"]');
    expect(spans.length).toBe(1);
    expect(spans[0]!.textContent).toBe("US, New City");
  });

  it("no-op when card has no .ioc-context-line", () => {
    const card = document.createElement("div");
    // No .ioc-context-line child
    const result = resultItem({
      provider: "IP Context",
      raw_stats: { geo: "US, New York" },
    });

    expect(() => updateContextLine(card, result)).not.toThrow();
  });

  it("no-op when result has no raw_stats", () => {
    const card = makeCard();
    const result = resultItem({
      provider: "IP Context",
      raw_stats: undefined as unknown as Record<string, unknown>,
    });

    // Reset raw_stats to simulate missing data
    (result as { raw_stats: unknown }).raw_stats = undefined;

    expect(() => updateContextLine(card, result)).not.toThrow();

    const contextLine = card.querySelector(".ioc-context-line")!;
    expect(contextLine.children.length).toBe(0);
  });

  it("no-op when IP Context geo is not a string", () => {
    const card = makeCard();
    const result = resultItem({
      provider: "IP Context",
      raw_stats: { geo: 12345 },
    });

    updateContextLine(card, result);

    const contextLine = card.querySelector(".ioc-context-line")!;
    expect(contextLine.children.length).toBe(0);
  });

  it("DNS Records: no-op when a-records array is empty", () => {
    const card = makeCard();
    const result = resultItem({
      provider: "DNS Records",
      raw_stats: { a: [] },
    });

    updateContextLine(card, result);

    const contextLine = card.querySelector(".ioc-context-line")!;
    expect(contextLine.children.length).toBe(0);
  });

  it("ignores unhandled providers without crash", () => {
    const card = makeCard();
    const result = resultItem({
      provider: "VirusTotal",
      raw_stats: { reputation: -5 },
    });

    expect(() => updateContextLine(card, result)).not.toThrow();

    const contextLine = card.querySelector(".ioc-context-line")!;
    expect(contextLine.children.length).toBe(0);
  });
});
