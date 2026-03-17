/**
 * DOM row construction for enrichment result display.
 *
 * Extracted from enrichment.ts (Phase 2). Owns all DOM element creation
 * for provider rows, summary rows, and context fields. The CONTEXT_PROVIDERS
 * set lives here as it controls row rendering dispatch.
 *
 * Depends on:
 *   - verdict-compute.ts for VerdictEntry type and computation functions
 *   - types/api.ts       for EnrichmentResultItem, EnrichmentItem
 *   - types/ioc.ts       for VerdictKey, VERDICT_LABELS
 */

import type { EnrichmentItem, EnrichmentResultItem } from "../types/api";
import type { VerdictKey } from "../types/ioc";
import { VERDICT_LABELS } from "../types/ioc";
import type { VerdictEntry } from "./verdict-compute";
import { computeWorstVerdict, computeAttribution } from "./verdict-compute";

// ---- Private helpers ----

/**
 * Compute verdict category counts from entries for micro-bar rendering.
 */
function computeVerdictCounts(entries: VerdictEntry[]): {
  malicious: number; suspicious: number; clean: number; noData: number; total: number;
} {
  let malicious = 0, suspicious = 0, clean = 0, noData = 0;
  for (const e of entries) {
    if (e.verdict === "malicious") malicious++;
    else if (e.verdict === "suspicious") suspicious++;
    else if (e.verdict === "clean") clean++;
    else noData++;
  }
  return { malicious, suspicious, clean, noData, total: entries.length };
}

/**
 * Format an ISO 8601 date string for display.
 * Returns "" for null input (scan_date can be null per API contract).
 * Source: main.js formatDate() (lines 581-588).
 */
export function formatDate(iso: string | null): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
}

/**
 * Format an ISO 8601 timestamp as a relative time string (e.g. "2h ago").
 * Falls back to the raw ISO string if parsing fails.
 */
function formatRelativeTime(iso: string): string {
  try {
    const diffMs = Date.now() - new Date(iso).getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return "just now";
    if (diffMin < 60) return diffMin + "m ago";
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return diffHr + "h ago";
    const diffDay = Math.floor(diffHr / 24);
    return diffDay + "d ago";
  } catch {
    return iso;
  }
}

// ---- Provider context field definitions ----

/** Mapping of provider name -> fields to extract from raw_stats. */
interface ContextFieldDef {
  key: string;
  label: string;
  type: "text" | "tags";
}

const PROVIDER_CONTEXT_FIELDS: Record<string, ContextFieldDef[]> = {
  VirusTotal: [
    { key: "top_detections", label: "Detections", type: "tags" },
    { key: "reputation", label: "Reputation", type: "text" },
  ],
  MalwareBazaar: [
    { key: "signature", label: "Signature", type: "text" },
    { key: "tags", label: "Tags", type: "tags" },
    { key: "file_type", label: "File type", type: "text" },
    { key: "first_seen", label: "First seen", type: "text" },
    { key: "last_seen", label: "Last seen", type: "text" },
  ],
  ThreatFox: [
    { key: "malware_printable", label: "Malware", type: "text" },
    { key: "threat_type", label: "Threat type", type: "text" },
    { key: "confidence_level", label: "Confidence", type: "text" },
  ],
  AbuseIPDB: [
    { key: "abuseConfidenceScore", label: "Confidence", type: "text" },
    { key: "totalReports", label: "Reports", type: "text" },
    { key: "countryCode", label: "Country", type: "text" },
    { key: "isp", label: "ISP", type: "text" },
    { key: "usageType", label: "Usage", type: "text" },
  ],
  "Shodan InternetDB": [
    { key: "ports", label: "Ports", type: "tags" },
    { key: "vulns", label: "Vulns", type: "tags" },
    { key: "hostnames", label: "Hostnames", type: "tags" },
    { key: "cpes", label: "CPEs", type: "tags" },      // EPROV-01
    { key: "tags", label: "Tags", type: "tags" },      // EPROV-01
  ],
  "CIRCL Hashlookup": [
    { key: "file_name", label: "File", type: "text" },
    { key: "source", label: "Source", type: "text" },
  ],
  "GreyNoise Community": [
    { key: "noise", label: "Noise", type: "text" },
    { key: "riot", label: "RIOT", type: "text" },
    { key: "classification", label: "Classification", type: "text" },
  ],
  URLhaus: [
    { key: "threat", label: "Threat", type: "text" },
    { key: "url_status", label: "Status", type: "text" },
    { key: "tags", label: "Tags", type: "tags" },
  ],
  "OTX AlienVault": [
    { key: "pulse_count", label: "Pulses", type: "text" },
    { key: "reputation", label: "Reputation", type: "text" },
  ],
  "IP Context": [
    { key: "geo", label: "Location", type: "text" },
    { key: "reverse", label: "PTR", type: "text" },
    { key: "flags", label: "Flags", type: "tags" },
  ],
  "DNS Records": [
    { key: "a",   label: "A",   type: "tags" },
    { key: "mx",  label: "MX",  type: "tags" },
    { key: "ns",  label: "NS",  type: "tags" },
    { key: "txt", label: "TXT", type: "tags" },
  ],
  "Cert History": [
    { key: "cert_count", label: "Certs",      type: "text" },
    { key: "earliest",   label: "First seen", type: "text" },
    { key: "latest",     label: "Latest",     type: "text" },
    { key: "subdomains", label: "Subdomains", type: "tags" },
  ],
  ThreatMiner: [
    { key: "passive_dns", label: "Passive DNS", type: "tags" },
    { key: "samples",     label: "Samples",     type: "tags" },
  ],
  "ASN Intel": [
    { key: "asn",       label: "ASN",       type: "text" },
    { key: "prefix",    label: "Prefix",    type: "text" },
    { key: "rir",       label: "RIR",       type: "text" },
    { key: "allocated", label: "Allocated", type: "text" },
  ],
};

/**
 * Providers that use the context row rendering path (no verdict badge, pinned to top).
 * Extend this set when adding new context-only providers.
 */
export const CONTEXT_PROVIDERS = new Set(["IP Context", "DNS Records", "Cert History", "ThreatMiner", "ASN Intel"]);

/**
 * Create a labeled context field element with the provider-context-field class.
 * All DOM construction uses createElement + textContent (SEC-08).
 */
function createLabeledField(label: string): HTMLElement {
  const fieldEl = document.createElement("span");
  fieldEl.className = "provider-context-field";

  const labelEl = document.createElement("span");
  labelEl.className = "provider-context-label";
  labelEl.textContent = label + ": ";
  fieldEl.appendChild(labelEl);

  return fieldEl;
}

/**
 * Create contextual fields from a provider result's raw_stats.
 * Returns null if no context fields are available for this provider.
 * All DOM construction uses createElement + textContent (SEC-08).
 */
function createContextFields(result: EnrichmentResultItem): HTMLElement | null {
  const fieldDefs = PROVIDER_CONTEXT_FIELDS[result.provider];
  if (!fieldDefs) return null;

  const stats = result.raw_stats;
  if (!stats) return null;

  const container = document.createElement("div");
  container.className = "provider-context";

  let hasFields = false;

  for (const def of fieldDefs) {
    const value = stats[def.key];
    if (value === undefined || value === null || value === "") continue;

    if (def.type === "tags" && Array.isArray(value) && value.length > 0) {
      const fieldEl = createLabeledField(def.label);
      for (const tag of value) {
        if (typeof tag !== "string" && typeof tag !== "number") continue;
        const tagEl = document.createElement("span");
        tagEl.className = "context-tag";
        tagEl.textContent = String(tag);
        fieldEl.appendChild(tagEl);
      }
      container.appendChild(fieldEl);
      hasFields = true;
    } else if (def.type === "text" && (typeof value === "string" || typeof value === "number" || typeof value === "boolean")) {
      const fieldEl = createLabeledField(def.label);
      const valEl = document.createElement("span");
      valEl.textContent = String(value);
      fieldEl.appendChild(valEl);
      container.appendChild(fieldEl);
      hasFields = true;
    }
  }

  return hasFields ? container : null;
}

// ---- Exported row builders ----

/**
 * Get or create the .ioc-summary-row element inside the slot.
 * Inserts before .chevron-toggle if present, otherwise as first child.
 */
export function getOrCreateSummaryRow(slot: HTMLElement): HTMLElement {
  const existing = slot.querySelector<HTMLElement>(".ioc-summary-row");
  if (existing) return existing;

  const row = document.createElement("div");
  row.className = "ioc-summary-row";

  // Insert before chevron-toggle if present
  const chevron = slot.querySelector(".chevron-toggle");
  if (chevron) {
    slot.insertBefore(row, chevron);
  } else {
    slot.appendChild(row);
  }

  return row;
}

/**
 * Update (or create) the summary row for an IOC in its enrichment slot.
 * Shows worst verdict badge, attribution text, and consensus badge.
 * All DOM construction uses createElement + textContent (SEC-08).
 */
export function updateSummaryRow(
  slot: HTMLElement,
  iocValue: string,
  iocVerdicts: Record<string, VerdictEntry[]>
): void {
  const entries = iocVerdicts[iocValue];
  if (!entries || entries.length === 0) return;

  const worstVerdict = computeWorstVerdict(entries);
  const attribution = computeAttribution(entries);

  const summaryRow = getOrCreateSummaryRow(slot);

  // Clear existing children (immutable rebuild pattern)
  summaryRow.textContent = "";

  // a. Verdict badge
  const verdictBadge = document.createElement("span");
  verdictBadge.className = "verdict-badge verdict-" + worstVerdict;
  verdictBadge.textContent = VERDICT_LABELS[worstVerdict];
  summaryRow.appendChild(verdictBadge);

  // b. Attribution text
  const attributionSpan = document.createElement("span");
  attributionSpan.className = "ioc-summary-attribution";
  attributionSpan.textContent = attribution.text;
  summaryRow.appendChild(attributionSpan);

  // c. Verdict micro-bar (replaces consensus badge)
  const counts = computeVerdictCounts(entries);
  const total = Math.max(1, counts.total);
  const microBar = document.createElement("div");
  microBar.className = "verdict-micro-bar";
  microBar.setAttribute("title",
    `${counts.malicious} malicious, ${counts.suspicious} suspicious, ${counts.clean} clean, ${counts.noData} no data`
  );
  const segments: Array<[number, string]> = [
    [counts.malicious, "malicious"],
    [counts.suspicious, "suspicious"],
    [counts.clean, "clean"],
    [counts.noData, "no_data"],
  ];
  for (const [count, verdict] of segments) {
    if (count === 0) continue;
    const seg = document.createElement("div");
    seg.className = "micro-bar-segment micro-bar-segment--" + verdict;
    seg.style.width = Math.round((count / total) * 100) + "%";
    microBar.appendChild(seg);
  }
  summaryRow.appendChild(microBar);
}

/**
 * Create a context row — purely informational, no verdict badge.
 * Context providers (IP Context, DNS Records, Cert History) carry metadata
 * and must not participate in consensus/attribution or card verdict updates.
 * All DOM construction uses createElement + textContent (SEC-08).
 */
export function createContextRow(result: EnrichmentResultItem): HTMLElement {
  const row = document.createElement("div");
  row.className = "provider-detail-row provider-context-row";
  row.setAttribute("data-verdict", "context"); // sentinel for sort pinning

  const nameSpan = document.createElement("span");
  nameSpan.className = "provider-detail-name";
  nameSpan.textContent = result.provider;
  row.appendChild(nameSpan);

  // NO verdict badge — IP Context is purely informational

  // Add context fields (geo, PTR, flags) using existing createContextFields()
  const contextEl = createContextFields(result);
  if (contextEl) {
    row.appendChild(contextEl);
  }

  // Cache badge if result was served from cache
  if (result.cached_at) {
    const cacheBadge = document.createElement("span");
    cacheBadge.className = "cache-badge";
    cacheBadge.textContent = "cached " + formatRelativeTime(result.cached_at);
    row.appendChild(cacheBadge);
  }

  return row;
}

/**
 * Create a single provider detail row for the .enrichment-details container.
 * All DOM construction uses createElement + textContent (SEC-08).
 */
export function createDetailRow(
  provider: string,
  verdict: VerdictKey,
  statText: string,
  result?: EnrichmentItem
): HTMLElement {
  const row = document.createElement("div");
  const isNoData = verdict === "no_data" || verdict === "error";
  row.className = "provider-detail-row" + (isNoData ? " provider-row--no-data" : "");
  row.setAttribute("data-verdict", verdict);

  const nameSpan = document.createElement("span");
  nameSpan.className = "provider-detail-name";
  nameSpan.textContent = provider;

  const badge = document.createElement("span");
  badge.className = "verdict-badge verdict-" + verdict;
  badge.textContent = VERDICT_LABELS[verdict];

  const statSpan = document.createElement("span");
  statSpan.className = "provider-detail-stat";
  statSpan.textContent = statText;

  row.appendChild(nameSpan);
  row.appendChild(badge);
  row.appendChild(statSpan);

  // Cache badge — show relative time if result was served from cache
  if (result && result.type === "result" && result.cached_at) {
    const cacheBadge = document.createElement("span");
    cacheBadge.className = "cache-badge";
    const ago = formatRelativeTime(result.cached_at);
    cacheBadge.textContent = "cached " + ago;
    row.appendChild(cacheBadge);
  }

  // Context fields — provider-specific intelligence from raw_stats
  if (result && result.type === "result") {
    const contextEl = createContextFields(result);
    if (contextEl) {
      row.appendChild(contextEl);
    }
  }

  return row;
}

/**
 * Unified row creation dispatcher — routes to createContextRow or createDetailRow
 * based on the kind parameter. Provides a stable API for Phase 3 visual work.
 */
export function createProviderRow(
  result: EnrichmentResultItem,
  kind: "context" | "detail",
  statText: string
): HTMLElement {
  if (kind === "context") {
    return createContextRow(result);
  }
  return createDetailRow(result.provider, result.verdict, statText, result);
}

/**
 * Create a category section header element (VIS-03).
 * All DOM construction uses createElement + textContent (SEC-08).
 */
export function createSectionHeader(label: string): HTMLElement {
  const header = document.createElement("div");
  header.className = "provider-section-header";
  header.setAttribute("data-section-label", label);
  header.textContent = label;
  return header;
}

/**
 * Inject category section headers (VIS-03) and no-data collapse summary (GRP-02)
 * into an enrichment slot's details container. Must be called AFTER enrichment
 * completes and sortDetailRows() has finalized the DOM order.
 *
 * Section headers: Scans .provider-detail-row elements in DOM order. Context rows
 * (.provider-context-row) are pinned to the top, verdict rows below. Inserts
 * "Infrastructure Context" header before the first context row and "Reputation"
 * header before the first non-context row (when each group exists).
 *
 * No-data collapse: Counts .provider-row--no-data elements. If any exist, creates
 * a clickable summary row that toggles .no-data-expanded on the details container.
 *
 * Edge cases: zero rows, zero context rows, zero verdict rows, zero no-data rows
 * all handled gracefully (no crash, no empty headers).
 *
 * All DOM construction uses createElement + textContent (SEC-08).
 */
export function injectSectionHeadersAndNoDataSummary(slot: HTMLElement): void {
  const detailsContainer = slot.querySelector<HTMLElement>(".enrichment-details");
  if (!detailsContainer) return;

  const rows = Array.from(
    detailsContainer.querySelectorAll<HTMLElement>(".provider-detail-row")
  );
  if (rows.length === 0) return;

  // --- VIS-03: Section headers ---
  let firstContextRow: HTMLElement | null = null;
  let firstVerdictRow: HTMLElement | null = null;

  for (const row of rows) {
    if (row.classList.contains("provider-context-row")) {
      if (!firstContextRow) firstContextRow = row;
    } else {
      if (!firstVerdictRow) firstVerdictRow = row;
    }
    // Early exit once both found
    if (firstContextRow && firstVerdictRow) break;
  }

  // Insert headers BEFORE the first row of each category
  if (firstContextRow) {
    detailsContainer.insertBefore(
      createSectionHeader("Infrastructure Context"),
      firstContextRow
    );
  }
  if (firstVerdictRow) {
    detailsContainer.insertBefore(
      createSectionHeader("Reputation"),
      firstVerdictRow
    );
  }

  // --- GRP-02: No-data collapse ---
  const noDataRows = detailsContainer.querySelectorAll<HTMLElement>(
    ".provider-row--no-data"
  );
  if (noDataRows.length === 0) return;

  const count = noDataRows.length;
  const summaryRow = document.createElement("div");
  summaryRow.className = "no-data-summary-row";
  summaryRow.setAttribute("role", "button");
  summaryRow.setAttribute("tabindex", "0");
  summaryRow.setAttribute("aria-expanded", "false");
  summaryRow.textContent = count + " provider" + (count !== 1 ? "s" : "") + " had no record";

  // Insert summary row before the first no-data row
  const firstNoData = noDataRows[0];
  if (firstNoData) {
    detailsContainer.insertBefore(summaryRow, firstNoData);
  }

  // Wire click → toggle .no-data-expanded on detailsContainer
  summaryRow.addEventListener("click", () => {
    const isExpanded = detailsContainer.classList.toggle("no-data-expanded");
    summaryRow.setAttribute("aria-expanded", String(isExpanded));
  });

  // Wire keyboard Enter/Space for accessibility
  summaryRow.addEventListener("keydown", (e: KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      summaryRow.click();
    }
  });
}
