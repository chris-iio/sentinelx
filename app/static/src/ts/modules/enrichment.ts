/**
 * Enrichment polling module — polling loop, progress bar, result rendering,
 * warning banner, and export button.
 *
 * Extracted from main.js lines 316-643.
 * This is a direct behavioral translation: DOM mutations, fetch calls,
 * and timing are byte-for-byte equivalent to the original.
 *
 * Depends on:
 *   - cards.ts    for findCardForIoc, updateCardVerdict, updateDashboardCounts, sortCardsBySeverity
 *   - types/api.ts for EnrichmentItem, EnrichmentStatus
 *   - types/ioc.ts for VerdictKey, VERDICT_LABELS, verdictSeverityIndex, getProviderCounts
 *   - utils/dom.ts for attr
 */

import type { EnrichmentItem, EnrichmentResultItem, EnrichmentStatus } from "../types/api";
import type { VerdictKey } from "../types/ioc";
import { VERDICT_LABELS, verdictSeverityIndex, getProviderCounts } from "../types/ioc";
import { attr } from "../utils/dom";
import {
  findCardForIoc,
  updateCardVerdict,
  updateDashboardCounts,
  sortCardsBySeverity,
} from "./cards";
import { exportJSON, exportCSV, copyAllIOCs } from "./export";
import type { VerdictEntry } from "./verdict-compute";
import { computeWorstVerdict, computeConsensus, computeAttribution,
         consensusBadgeClass, findWorstEntry } from "./verdict-compute";

// ---- Module-private state ----

/** Debounce timers for sortDetailRows — keyed by ioc_value */
const sortTimers: Map<string, ReturnType<typeof setTimeout>> = new Map();

/** Accumulated enrichment results for export */
const allResults: EnrichmentItem[] = [];

// ---- Private helpers ----

/**
 * Format an ISO 8601 date string for display.
 * Returns "" for null input (scan_date can be null per API contract).
 * Source: main.js formatDate() (lines 581-588).
 */
function formatDate(iso: string | null): string {
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

/**
 * Get or create the .ioc-summary-row element inside the slot.
 * Inserts before .chevron-toggle if present, otherwise as first child.
 */
function getOrCreateSummaryRow(slot: HTMLElement): HTMLElement {
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
function updateSummaryRow(
  slot: HTMLElement,
  iocValue: string,
  iocVerdicts: Record<string, VerdictEntry[]>
): void {
  const entries = iocVerdicts[iocValue];
  if (!entries || entries.length === 0) return;

  const worstVerdict = computeWorstVerdict(entries);
  const attribution = computeAttribution(entries);
  const { flagged, responded } = computeConsensus(entries);

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

  // c. Consensus badge
  const consensusBadge = document.createElement("span");
  consensusBadge.className = "consensus-badge " + consensusBadgeClass(flagged);
  consensusBadge.textContent = "[" + flagged + "/" + responded + "]";
  summaryRow.appendChild(consensusBadge);
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
const CONTEXT_PROVIDERS = new Set(["IP Context", "DNS Records", "Cert History", "ThreatMiner", "ASN Intel"]);

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

/**
 * Create a context row — purely informational, no verdict badge.
 * Context providers (IP Context, DNS Records, Cert History) carry metadata
 * and must not participate in consensus/attribution or card verdict updates.
 * All DOM construction uses createElement + textContent (SEC-08).
 */
function createContextRow(result: EnrichmentResultItem): HTMLElement {
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
function createDetailRow(
  provider: string,
  verdict: VerdictKey,
  statText: string,
  result?: EnrichmentItem
): HTMLElement {
  const row = document.createElement("div");
  row.className = "provider-detail-row";
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
 * Sort all .provider-detail-row elements in a container by severity descending.
 * malicious (index 4) first, error (index 0) last.
 * Debounced at 100ms per IOC to avoid thrashing during batch result delivery.
 */
function sortDetailRows(detailsContainer: HTMLElement, iocValue: string): void {
  const existing = sortTimers.get(iocValue);
  if (existing !== undefined) {
    clearTimeout(existing);
  }
  const timer = setTimeout(() => {
    sortTimers.delete(iocValue);
    const rows = Array.from(
      detailsContainer.querySelectorAll<HTMLElement>(".provider-detail-row")
    );
    rows.sort((a, b) => {
      const aVerdict = a.getAttribute("data-verdict") as VerdictKey | null;
      const bVerdict = b.getAttribute("data-verdict") as VerdictKey | null;
      const aIdx = aVerdict ? verdictSeverityIndex(aVerdict) : -1;
      const bIdx = bVerdict ? verdictSeverityIndex(bVerdict) : -1;
      return bIdx - aIdx; // descending: malicious first
    });
    for (const row of rows) {
      detailsContainer.appendChild(row);
    }

    // Pin context rows (IP Context) to top after severity sort
    const contextRows = Array.from(
      detailsContainer.querySelectorAll<HTMLElement>('.provider-detail-row[data-verdict="context"]')
    );
    for (const cr of contextRows) {
      detailsContainer.insertBefore(cr, detailsContainer.firstChild);
    }
  }, 100);
  sortTimers.set(iocValue, timer);
}

/**
 * Find the copy button for a given IOC value by iterating .copy-btn elements.
 * Source: main.js findCopyButtonForIoc() (lines 571-579).
 */
function findCopyButtonForIoc(iocValue: string): HTMLElement | null {
  const btns = document.querySelectorAll<HTMLElement>(".copy-btn");
  for (let i = 0; i < btns.length; i++) {
    const btn = btns[i];
    if (btn && attr(btn, "data-value") === iocValue) {
      return btn;
    }
  }
  return null;
}

/**
 * Update the copy button's data-enrichment attribute with the worst verdict
 * summary text across all providers for the given IOC.
 * Source: main.js updateCopyButtonWorstVerdict() (lines 553-569).
 */
function updateCopyButtonWorstVerdict(
  iocValue: string,
  iocVerdicts: Record<string, VerdictEntry[]>
): void {
  const copyBtn = findCopyButtonForIoc(iocValue);
  if (!copyBtn) return;

  const worstEntry = findWorstEntry(iocVerdicts[iocValue] ?? []);
  if (!worstEntry) return;

  copyBtn.setAttribute("data-enrichment", worstEntry.summaryText);
}

/**
 * Update the progress bar fill and text.
 * Source: main.js updateProgressBar() (lines 375-383).
 */
function updateProgressBar(done: number, total: number): void {
  const fill = document.getElementById("enrich-progress-fill");
  const text = document.getElementById("enrich-progress-text");
  if (!fill || !text) return;

  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  fill.style.width = pct + "%";
  text.textContent = done + "/" + total + " providers complete";
}

/**
 * Show or update the pending provider indicator after the first result for an IOC.
 * Reads provider counts from the DOM via getProviderCounts() — reflects the actual
 * configured provider set injected by the Flask route into data-provider-counts.
 * Source: main.js updatePendingIndicator() (lines 412-441).
 */
function updatePendingIndicator(
  slot: HTMLElement,
  card: HTMLElement | null,
  receivedCount: number
): void {
  const iocType = card ? attr(card, "data-ioc-type") : "";
  const providerCounts = getProviderCounts();
  const totalExpected = Object.prototype.hasOwnProperty.call(providerCounts, iocType)
    ? (providerCounts[iocType] ?? 0)
    : 0;
  const remaining = totalExpected - receivedCount;

  if (remaining <= 0) {
    // All providers accounted for — remove waiting indicator if present
    const existingIndicator = slot.querySelector(".enrichment-waiting-text");
    if (existingIndicator) {
      slot.removeChild(existingIndicator);
    }
    return;
  }

  // Find or create the waiting indicator span
  let indicator = slot.querySelector<HTMLElement>(".enrichment-waiting-text");
  if (!indicator) {
    indicator = document.createElement("span");
    indicator.className = "enrichment-waiting-text enrichment-pending-text";
    slot.appendChild(indicator);
  }
  indicator.textContent = remaining + " provider" + (remaining !== 1 ? "s" : "") + " still loading...";
}

/**
 * Show a warning banner for rate-limit or authentication errors.
 * Source: main.js showEnrichWarning() (lines 605-611).
 */
function showEnrichWarning(message: string): void {
  const banner = document.getElementById("enrich-warning");
  if (!banner) return;
  banner.style.display = "block";
  // Use textContent to safely set the warning message (SEC-08)
  banner.textContent = "Warning: " + message + " Consider using offline mode or checking your API key in Settings.";
}

/**
 * Mark enrichment complete: add .complete class to progress container,
 * update text, and enable the export button.
 * Source: main.js markEnrichmentComplete() (lines 590-603).
 */
function markEnrichmentComplete(): void {
  const container = document.getElementById("enrich-progress");
  if (container) {
    container.classList.add("complete");
  }
  const text = document.getElementById("enrich-progress-text");
  if (text) {
    text.textContent = "Enrichment complete";
  }
  const exportBtn = document.getElementById("export-btn");
  if (exportBtn) {
    exportBtn.removeAttribute("disabled");
  }
}

/**
 * Render a single enrichment result item into the appropriate IOC card slot.
 * Handles both "result" and "error" discriminated union branches.
 *
 * New behavior (Plan 02):
 * - ALL results go into .enrichment-details container (no direct slot append)
 * - Summary row updated on each result: worst verdict badge + attribution + consensus badge
 * - Detail rows sorted by severity descending (debounced 100ms)
 * - .enrichment-slot--loaded class added on first result (reveals chevron via CSS)
 *
 * Source: main.js renderEnrichmentResult() (lines 443-540).
 */
function renderEnrichmentResult(
  result: EnrichmentItem,
  iocVerdicts: Record<string, VerdictEntry[]>,
  iocResultCounts: Record<string, number>
): void {
  // Find the card for this IOC value
  const card = findCardForIoc(result.ioc_value);
  if (!card) return;

  const slot = card.querySelector<HTMLElement>(".enrichment-slot");
  if (!slot) return;

  // Context providers (IP Context, DNS Records, Cert History) are purely informational —
  // separate rendering path. No VerdictEntry accumulation, no consensus/attribution,
  // no card verdict update.
  if (CONTEXT_PROVIDERS.has(result.provider)) {
    // Remove spinner on first result
    const spinnerWrapper = slot.querySelector(".spinner-wrapper");
    if (spinnerWrapper) slot.removeChild(spinnerWrapper);
    slot.classList.add("enrichment-slot--loaded");

    // Track result count for pending indicator
    iocResultCounts[result.ioc_value] = (iocResultCounts[result.ioc_value] ?? 0) + 1;

    // Render context row and PREPEND to details container (first position)
    const detailsContainer = slot.querySelector<HTMLElement>(".enrichment-details");
    if (detailsContainer && result.type === "result") {
      const contextRow = createContextRow(result);
      detailsContainer.insertBefore(contextRow, detailsContainer.firstChild);
    }

    // Update pending indicator
    updatePendingIndicator(slot, card, iocResultCounts[result.ioc_value] ?? 1);
    return; // Skip all verdict/summary/sort/dashboard logic
  }

  // Remove spinner wrapper on first result for this IOC
  const spinnerWrapper = slot.querySelector(".spinner-wrapper");
  if (spinnerWrapper) {
    slot.removeChild(spinnerWrapper);
  }

  // Add .enrichment-slot--loaded class — triggers chevron visibility via CSS guard
  slot.classList.add("enrichment-slot--loaded");

  // Track received count for this IOC
  iocResultCounts[result.ioc_value] = (iocResultCounts[result.ioc_value] ?? 0) + 1;
  const receivedCount = iocResultCounts[result.ioc_value] ?? 1;

  // Determine verdict and statText
  let verdict: VerdictKey;
  let statText: string;
  let summaryText: string;
  let detectionCount = 0;
  let totalEngines = 0;

  if (result.type === "result") {
    verdict = result.verdict;
    detectionCount = result.detection_count;
    totalEngines = result.total_engines;

    if (verdict === "malicious") {
      statText = result.detection_count + "/" + result.total_engines + " engines";
    } else if (verdict === "suspicious") {
      statText =
        result.total_engines > 1
          ? result.detection_count + "/" + result.total_engines + " engines"
          : "Suspicious";
    } else if (verdict === "clean") {
      statText = "Clean, " + result.total_engines + " engines";
    } else if (verdict === "known_good") {
      statText = "NSRL match";
    } else {
      // no_data
      statText = "Not in database";
    }

    const scanDateStr = formatDate(result.scan_date);
    summaryText =
      result.provider +
      ": " +
      verdict +
      " (" +
      statText +
      (scanDateStr ? ", scanned " + scanDateStr : "") +
      ")";
  } else {
    // Error result
    verdict = "error";
    statText = result.error;
    summaryText = result.provider + ": error, " + result.error;
  }

  // Push to iocVerdicts with extended fields
  const entries = iocVerdicts[result.ioc_value] ?? [];
  iocVerdicts[result.ioc_value] = entries;
  entries.push({ provider: result.provider, verdict, summaryText, detectionCount, totalEngines, statText });

  // Build detail row and append to .enrichment-details container
  const detailsContainer = slot.querySelector<HTMLElement>(".enrichment-details");
  if (detailsContainer) {
    const detailRow = createDetailRow(result.provider, verdict, statText, result);
    detailsContainer.appendChild(detailRow);
    sortDetailRows(detailsContainer, result.ioc_value);
  }

  // Update summary row (worst verdict + attribution + consensus)
  updateSummaryRow(slot, result.ioc_value, iocVerdicts);

  // Update pending indicator for remaining providers
  updatePendingIndicator(slot, card, receivedCount);

  // Compute worst verdict for this IOC
  const worstVerdict = computeWorstVerdict(iocVerdicts[result.ioc_value] ?? []);

  // Update card verdict, dashboard, and sort
  updateCardVerdict(result.ioc_value, worstVerdict);
  updateDashboardCounts();
  sortCardsBySeverity();

  // Update copy button with worst verdict across all providers for this IOC
  updateCopyButtonWorstVerdict(result.ioc_value, iocVerdicts);
}

/**
 * Wire expand/collapse toggle for all .chevron-toggle buttons on the page.
 * Called once from init(). Click listener toggles .is-open on the sibling
 * .enrichment-details container and sets aria-expanded accordingly.
 * Multiple cards can be independently opened — no collapse-others logic.
 */
function wireExpandToggles(): void {
  const toggles = document.querySelectorAll<HTMLElement>(".chevron-toggle");
  toggles.forEach((toggle) => {
    toggle.addEventListener("click", () => {
      const details = toggle.nextElementSibling as HTMLElement | null;
      if (!details || !details.classList.contains("enrichment-details")) return;
      const isOpen = details.classList.toggle("is-open");
      toggle.classList.toggle("is-open", isOpen);
      toggle.setAttribute("aria-expanded", String(isOpen));
    });
  });
}

// ---- Private init helpers ----

/**
 * Wire the export dropdown with JSON, CSV, and copy-all-IOCs options.
 */
function initExportButton(): void {
  const exportBtn = document.getElementById("export-btn");
  const dropdown = document.getElementById("export-dropdown");
  if (!exportBtn || !dropdown) return;

  exportBtn.addEventListener("click", function () {
    const isVisible = dropdown.style.display !== "none";
    dropdown.style.display = isVisible ? "none" : "";
  });

  // Close dropdown when clicking outside
  document.addEventListener("click", function (e) {
    const target = e.target as HTMLElement;
    if (!target.closest(".export-group")) {
      dropdown.style.display = "none";
    }
  });

  const buttons = dropdown.querySelectorAll<HTMLElement>("[data-export]");
  buttons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      const action = btn.getAttribute("data-export");
      if (action === "json") {
        exportJSON(allResults);
      } else if (action === "csv") {
        exportCSV(allResults);
      } else if (action === "iocs") {
        copyAllIOCs(btn);
      }
      dropdown.style.display = "none";
    });
  });
}

// ---- Public API ----

/**
 * Initialise the enrichment polling module.
 *
 * Guards on .page-results presence and data-mode="online" — returns early
 * on offline mode or when enrichment UI elements are absent.
 *
 * Wires chevron expand/collapse toggles once at init time (before polling
 * starts) so they work regardless of when results populate details.
 *
 * Starts a 750ms polling interval for /enrichment/status/<job_id>,
 * renders incremental results, shows warning banners for errors, and
 * marks enrichment complete when all tasks are done.
 *
 * Source: main.js initEnrichmentPolling() (lines 316-373) +
 *         initExportButton() (lines 615-643).
 */
export function init(): void {
  const pageResults = document.querySelector<HTMLElement>(".page-results");
  if (!pageResults) return;

  const jobId = attr(pageResults, "data-job-id");
  const mode = attr(pageResults, "data-mode");

  if (!jobId || mode !== "online") return;

  // Wire expand/collapse toggles once at init (before polling starts)
  wireExpandToggles();

  // Dedup key: "ioc_value|provider" — each provider result per IOC rendered once
  const rendered: Record<string, boolean> = {};

  // Per-IOC verdict tracking for worst-verdict copy/export computation
  // iocVerdicts[ioc_value] = [{provider, verdict, summaryText, detectionCount, totalEngines, statText}]
  const iocVerdicts: Record<string, VerdictEntry[]> = {};

  // Per-IOC result count tracking for pending indicator
  const iocResultCounts: Record<string, number> = {};

  // Use ReturnType<typeof setInterval> to avoid NodeJS.Timeout conflict
  const intervalId: ReturnType<typeof setInterval> = setInterval(function () {
    fetch("/enrichment/status/" + jobId)
      .then(function (resp) {
        if (!resp.ok) return null;
        return resp.json() as Promise<EnrichmentStatus>;
      })
      .then(function (data) {
        if (!data) return;

        updateProgressBar(data.done, data.total);

        // Render any new results not yet displayed, and check for warnings
        const results = data.results;
        for (let i = 0; i < results.length; i++) {
          const result = results[i];
          if (!result) continue;
          const dedupKey = result.ioc_value + "|" + result.provider;
          if (!rendered[dedupKey]) {
            rendered[dedupKey] = true;
            allResults.push(result);
            renderEnrichmentResult(result, iocVerdicts, iocResultCounts);
          }

          // Show warning banner for rate-limit or auth errors
          if (result.type === "error" && result.error) {
            const errLower = result.error.toLowerCase();
            if (
              errLower.indexOf("rate limit") !== -1 ||
              errLower.indexOf("429") !== -1
            ) {
              showEnrichWarning("Rate limit reached for " + result.provider + ".");
            } else if (
              errLower.indexOf("authentication") !== -1 ||
              errLower.indexOf("401") !== -1 ||
              errLower.indexOf("403") !== -1
            ) {
              showEnrichWarning(
                "Authentication error for " +
                  result.provider +
                  ". Please check your API key in Settings."
              );
            }
          }
        }

        if (data.complete) {
          clearInterval(intervalId);
          markEnrichmentComplete();
        }
      })
      .catch(function () {
        // Fetch error — silently continue; retry on next interval tick
      });
  }, 750);

  // Wire the export button
  initExportButton();
}
