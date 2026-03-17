/**
 * Pure verdict computation functions — no DOM access, no side effects.
 *
 * Extracted from enrichment.ts (Phase 2). These functions take VerdictEntry[]
 * arrays and return computed results. They are the shared computation layer
 * used by both row-factory.ts (summary row rendering) and enrichment.ts
 * (orchestrator verdict tracking).
 */

import type { VerdictKey } from "../types/ioc";
import { verdictSeverityIndex } from "../types/ioc";

/**
 * Per-provider verdict record accumulated during the polling loop.
 * Used for worst-verdict computation across all providers for an IOC.
 */
export interface VerdictEntry {
  provider: string;
  verdict: VerdictKey;
  summaryText: string;
  detectionCount: number;   // from result.detection_count (0 for errors)
  totalEngines: number;     // from result.total_engines (0 for errors)
  statText: string;         // key stat string for display (e.g., "45/72 engines")
}

/**
 * Compute the worst (highest severity) verdict from a list of VerdictEntry records.
 *
 * known_good from any provider overrides all other verdicts at summary level.
 * This is an intentional design decision: known_good (e.g. NSRL match) means
 * the IOC is a recognized safe artifact regardless of other signals.
 *
 * Source: main.js computeWorstVerdict() (lines 542-551).
 */
export function computeWorstVerdict(entries: VerdictEntry[]): VerdictKey {
  // known_good from any provider overrides everything at summary level
  if (entries.some((e) => e.verdict === "known_good")) {
    return "known_good";
  }
  const worst = findWorstEntry(entries);
  return worst ? worst.verdict : "no_data";
}

/**
 * Compute consensus: count flagged (malicious/suspicious) and responded
 * (malicious + suspicious + clean) providers.
 * Per design: no_data and error do NOT count as votes.
 */
export function computeConsensus(entries: VerdictEntry[]): { flagged: number; responded: number } {
  let flagged = 0;
  let responded = 0;
  for (const entry of entries) {
    if (entry.verdict === "malicious" || entry.verdict === "suspicious") {
      flagged++;
      responded++;
    } else if (entry.verdict === "clean") {
      responded++;
    }
    // error and no_data do NOT count
  }
  return { flagged, responded };
}

/**
 * Return the CSS modifier class for the consensus badge based on flagged count.
 * 0 flagged → green, 1-2 → yellow, 3+ → red.
 *
 * Phase 3: No longer consumed by row-factory (replaced by verdict micro-bar).
 * Kept exported for API stability.
 */
export function consensusBadgeClass(flagged: number): string {
  if (flagged === 0) return "consensus-badge--green";
  if (flagged <= 2) return "consensus-badge--yellow";
  return "consensus-badge--red";
}

/**
 * Compute attribution: find the "most detailed" provider to show in summary.
 * Heuristic: highest totalEngines wins. Ties broken by verdict severity descending.
 * Providers with no_data or error are excluded as candidates.
 */
export function computeAttribution(entries: VerdictEntry[]): { provider: string; text: string } {
  // Only candidates with actual data (not no_data or error)
  const candidates = entries.filter(
    (e) => e.verdict !== "no_data" && e.verdict !== "error"
  );

  if (candidates.length === 0) {
    return { provider: "", text: "No providers returned data for this IOC" };
  }

  // Sort: highest totalEngines first. Ties broken by severity descending.
  const sorted = [...candidates].sort((a, b) => {
    if (b.totalEngines !== a.totalEngines) return b.totalEngines - a.totalEngines;
    return verdictSeverityIndex(b.verdict) - verdictSeverityIndex(a.verdict);
  });

  const best = sorted[0];
  if (!best) return { provider: "", text: "No providers returned data for this IOC" };

  return { provider: best.provider, text: best.provider + ": " + best.statText };
}

/**
 * Find the worst (highest severity) VerdictEntry from a list.
 * Returns undefined if the list is empty.
 */
export function findWorstEntry(entries: VerdictEntry[]): VerdictEntry | undefined {
  const first = entries[0];
  if (!first) return undefined;

  let worst = first;
  for (let i = 1; i < entries.length; i++) {
    const current = entries[i];
    if (!current) continue;
    if (verdictSeverityIndex(current.verdict) > verdictSeverityIndex(worst.verdict)) {
      worst = current;
    }
  }
  return worst;
}
