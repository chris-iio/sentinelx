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
  cachedAt?: string;        // ISO timestamp from result.cached_at when served from cache
}

/**
 * Compute the worst (highest severity) verdict from a list of VerdictEntry records.
 *
 * Precedence is malicious > suspicious > known_good > clean > no_data > error.
 * A known-good signal wins over benign or absent data, but it cannot erase a
 * suspicious or malicious signal from another provider.
 */
export function computeWorstVerdict(entries: VerdictEntry[]): VerdictKey {
  if (entries.length === 0) return "no_data";

  let worst: VerdictKey = "error";
  for (let i = 0; i < entries.length; i++) {
    const entry = entries[i];
    if (!entry) continue;
    if (verdictSeverityIndex(entry.verdict) > verdictSeverityIndex(worst)) {
      worst = entry.verdict;
      if (worst === "malicious") return worst;
    }
  }
  return worst;
}

/**
 * Compute attribution: find the "most detailed" provider to show in summary.
 * Heuristic: highest totalEngines wins. Ties broken by verdict severity descending.
 * Providers with no_data or error are excluded as candidates.
 */
export function computeAttribution(entries: VerdictEntry[]): { provider: string; text: string } {
  let best: VerdictEntry | undefined;
  for (let i = 0; i < entries.length; i++) {
    const entry = entries[i];
    if (!entry) continue;
    if (entry.verdict === "no_data" || entry.verdict === "error") continue;
    if (!best) {
      best = entry;
      continue;
    }
    if (entry.totalEngines > best.totalEngines) {
      best = entry;
      continue;
    }
    if (
      entry.totalEngines === best.totalEngines &&
      verdictSeverityIndex(entry.verdict) > verdictSeverityIndex(best.verdict)
    ) {
      best = entry;
    }
  }

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
  if (entries.length === 1) return first;

  const second = entries[1];
  if (entries.length === 2) {
    if (!second) return first;
    return verdictSeverityIndex(second.verdict) > verdictSeverityIndex(first.verdict)
      ? second
      : first;
  }

  let worst = first;
  let worstSeverity = verdictSeverityIndex(first.verdict);
  for (let i = 1; i < entries.length; i++) {
    const current = entries[i];
    if (!current) continue;
    const currentSeverity = verdictSeverityIndex(current.verdict);
    if (currentSeverity > worstSeverity) {
      worst = current;
      worstSeverity = currentSeverity;
      if (current.verdict === "malicious") {
        return current;
      }
    }
  }
  return worst;
}
