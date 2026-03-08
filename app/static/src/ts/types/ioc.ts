/**
 * Domain types and constants for IOC (Indicator of Compromise) enrichment.
 *
 * This module defines the shared type layer for verdict values and IOC metadata.
 * All constants are sourced from app/static/main.js and must remain in sync
 * with the Flask backend verdict values.
 *
 * Shared type definitions, typed constants, and verdict utility functions.
 */

/**
 * The five verdict keys returned by the Flask enrichment API.
 *
 * Source: main.js VERDICT_LABELS keys (lines 231–237).
 * Used as discriminant values throughout enrichment result processing.
 */
export type VerdictKey =
  | "error"
  | "no_data"
  | "clean"
  | "suspicious"
  | "malicious";

/**
 * The seven IOC types supported for enrichment.
 *
 * Only enrichable types are included — NOT "cve" (CVEs are extracted but
 * never enriched, and IOC_PROVIDER_COUNTS has no "cve" entry).
 *
 * Source: main.js IOC_PROVIDER_COUNTS keys (lines 242–250).
 */
type IocType =
  | "ipv4"
  | "ipv6"
  | "domain"
  | "url"
  | "md5"
  | "sha1"
  | "sha256";

/**
 * Severity order for verdicts — index 0 is least severe, index 4 is most severe.
 *
 * Used by the worst-verdict computation: iterate over results and track the
 * highest index in this array. Tuple type is preserved by `as const`.
 *
 * Source: main.js line 228.
 */
export const VERDICT_SEVERITY = [
  "error",
  "no_data",
  "clean",
  "suspicious",
  "malicious",
] as const satisfies readonly VerdictKey[];

/**
 * Returns the severity index for a verdict key.
 * Higher index = higher severity. Returns -1 if not found.
 */
export function verdictSeverityIndex(verdict: VerdictKey): number {
  return VERDICT_SEVERITY.indexOf(verdict);
}

/**
 * Human-readable display labels for each verdict key.
 *
 * Typed as `Record<VerdictKey, string>` to ensure all five keys are present
 * and that indexing with an invalid key produces a compile error under
 * `noUncheckedIndexedAccess`.
 *
 * Source: main.js lines 231–237.
 */
export const VERDICT_LABELS: Record<VerdictKey, string> = {
  malicious: "MALICIOUS",
  suspicious: "SUSPICIOUS",
  clean: "CLEAN",
  no_data: "NO DATA",
  error: "ERROR",
} as const;

/**
 * Hardcoded fallback provider counts per enrichable IOC type.
 *
 * Used as a fallback when the data-provider-counts DOM attribute is absent
 * (offline mode or server error). Reflects the baseline 3-provider setup:
 * VirusTotal supports all 7 types, MalwareBazaar supports md5/sha1/sha256,
 * ThreatFox supports all 7.
 *
 * Private — callers must use getProviderCounts() to allow runtime override
 * from the DOM attribute populated by the Flask route.
 */
const _defaultProviderCounts: Record<IocType, number> = {
  ipv4: 2,
  ipv6: 2,
  domain: 2,
  url: 2,
  md5: 3,
  sha1: 3,
  sha256: 3,
} as const;

/**
 * Return provider counts per IOC type, reading from the DOM when available.
 *
 * On the results page in online mode, Flask injects the actual registry counts
 * via data-provider-counts on .page-results. This function reads that attribute
 * so the pending-indicator logic reflects the real configured provider set
 * (e.g., 8+ providers in v4.0) rather than a stale hardcoded value.
 *
 * Falls back to _defaultProviderCounts when:
 *   - .page-results element is absent (not on results page)
 *   - data-provider-counts attribute is missing (offline mode)
 *   - JSON parse fails (malformed attribute)
 *
 * Returns:
 *   Record mapping IOC type string → configured provider count.
 */
export function getProviderCounts(): Record<string, number> {
  const el = document.querySelector<HTMLElement>(".page-results");
  if (el === null) return _defaultProviderCounts;
  const raw = el.getAttribute("data-provider-counts");
  if (raw === null) return _defaultProviderCounts;
  try {
    return JSON.parse(raw) as Record<string, number>;
  } catch {
    return _defaultProviderCounts;
  }
}
