/**
 * API response interfaces for the Flask enrichment status endpoint.
 *
 * These interfaces model the JSON shape returned by:
 *   GET /enrichment/status/<job_id>
 *
 * The shape is produced by `_serialize_result` in app/routes.py and the
 * `EnrichmentResult` / `EnrichmentError` dataclasses in app/enrichment/models.py.
 *
 * No runtime code here — pure interface definitions for type-checking only.
 */

import type { VerdictKey } from "./ioc";

/**
 * A successful enrichment result item from one provider for one IOC.
 *
 * Matches the `"type": "result"` branch of `_serialize_result` in routes.py
 * (lines 63–73), which serializes an `EnrichmentResult` dataclass instance.
 *
 * The `type` field is a literal string discriminant used to narrow the
 * `EnrichmentItem` union to this branch.
 */
export interface EnrichmentResultItem {
  /** Discriminant literal — always "result" for this branch. */
  type: "result";
  /** Raw IOC value (e.g. "1.2.3.4", "evil.com"). */
  ioc_value: string;
  /** IOC type string from the extraction pipeline (e.g. "ipv4", "domain"). */
  ioc_type: string;
  /** TI provider name (e.g. "VirusTotal", "MalwareBazaar", "ThreatFox"). */
  provider: string;
  /**
   * Enrichment verdict from the provider.
   *
   * Typed as `VerdictKey` (not `string`) so that downstream code must handle
   * all five verdict values and invalid strings are caught at compile time.
   */
  verdict: VerdictKey;
  /** Number of engines/rules that flagged the IOC. */
  detection_count: number;
  /** Total number of engines/rules that analysed the IOC. */
  total_engines: number;
  /**
   * ISO 8601 scan date string, or null if the provider did not return one.
   *
   * This field is always present in the JSON — use `string | null` not
   * optional `?: string` to require callers to handle the null case.
   */
  scan_date: string | null;
  /**
   * Raw statistics dict from the provider response.
   *
   * Typed as `Record<string, unknown>` (not `object` or `any`) so downstream
   * code must narrow before accessing individual fields.
   */
  raw_stats: Record<string, unknown>;
}

/**
 * An enrichment error item — one provider failed for one IOC.
 *
 * Matches the `"type": "error"` branch of `_serialize_result` in routes.py
 * (lines 74–80), which serializes an `EnrichmentError` dataclass instance
 * from app/enrichment/models.py.
 *
 * The `type` field is a literal string discriminant used to narrow the
 * `EnrichmentItem` union to this branch.
 */
export interface EnrichmentErrorItem {
  /** Discriminant literal — always "error" for this branch. */
  type: "error";
  /** Raw IOC value (e.g. "1.2.3.4", "evil.com"). */
  ioc_value: string;
  /** IOC type string from the extraction pipeline. */
  ioc_type: string;
  /** TI provider name that failed (e.g. "VirusTotal"). */
  provider: string;
  /** Human-readable error message from the provider adapter. */
  error: string;
}

/**
 * Discriminated union of all possible enrichment item types.
 *
 * Narrow with `item.type === "result"` / `item.type === "error"` to access
 * branch-specific fields. TypeScript will narrow the type correctly in each
 * branch of the conditional.
 */
export type EnrichmentItem = EnrichmentResultItem | EnrichmentErrorItem;

/**
 * Top-level response from GET /enrichment/status/<job_id>.
 *
 * Matches the JSON object returned by the `enrichment_status` route in
 * routes.py (lines 228–234). The browser polls this endpoint until
 * `complete` is `true`.
 */
export interface EnrichmentStatus {
  /** Total number of enrichment tasks dispatched (IOCs × providers). */
  total: number;
  /** Number of tasks completed so far (results + errors). */
  done: number;
  /** True when all tasks have completed and polling should stop. */
  complete: boolean;
  /** Incremental list of results received so far — may be partial. */
  results: EnrichmentItem[];
}
