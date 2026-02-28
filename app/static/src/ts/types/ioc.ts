/**
 * Domain types and constants for IOC (Indicator of Compromise) enrichment.
 *
 * This module defines the shared type layer for verdict values and IOC metadata.
 * All constants are sourced from app/static/main.js and must remain in sync
 * with the Flask backend verdict values.
 *
 * No runtime logic here — pure type definitions and typed constants.
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
export type IocType =
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
 * Expected provider counts per enrichable IOC type.
 *
 * VirusTotal supports all 7 types, MalwareBazaar supports md5/sha1/sha256,
 * ThreatFox supports all 7. Hash types (md5/sha1/sha256) therefore get 3
 * providers; network types (ipv4/ipv6/domain/url) get 2 providers.
 *
 * Typed as `Record<IocType, number>` to ensure all seven keys are present
 * and indexed access is type-safe.
 *
 * Source: main.js lines 242–250.
 */
export const IOC_PROVIDER_COUNTS: Record<IocType, number> = {
  ipv4: 2,
  ipv6: 2,
  domain: 2,
  url: 2,
  md5: 3,
  sha1: 3,
  sha256: 3,
} as const;
