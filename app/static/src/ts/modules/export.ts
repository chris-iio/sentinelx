/**
 * Export module -- JSON download, CSV download, and copy-all-IOCs.
 *
 * All exports operate on the accumulated results array built during
 * the enrichment polling loop. No server roundtrip required.
 */

import type { EnrichmentItem } from "../types/api";
import { writeToClipboard } from "./clipboard";

// ---- Helpers ----

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

export function exportFilenameTimestamp(now = new Date()): string {
  const iso = now.toISOString();
  return (
    iso.slice(0, 13)
    + "-"
    + iso.slice(14, 16)
    + "-"
    + iso.slice(17, 19)
  );
}

function csvEscape(value: string): string {
  if (value.indexOf(",") !== -1 || value.indexOf('"') !== -1 || value.indexOf("\n") !== -1) {
    return '"' + value.replace(/"/g, '""') + '"';
  }
  return value;
}

function rawStatField(raw: Record<string, unknown> | undefined, key: string): string {
  if (!raw) return "";
  const val = raw[key];
  if (val === undefined || val === null) return "";
  if (Array.isArray(val)) {
    if (val.length === 0) return "";
    if (val.length === 1) return String(val[0]);
    if (val.length === 2) return String(val[0]) + "; " + String(val[1]);
    if (val.length === 3) return String(val[0]) + "; " + String(val[1]) + "; " + String(val[2]);
    let text = String(val[0]);
    for (let i = 1; i < val.length; i += 1) {
      const item = val[i];
      text += "; " + String(item);
    }
    return text;
  }
  return String(val);
}

// ---- Public API ----

const CSV_HEADER = "ioc_value,ioc_type,provider,verdict,detection_count,total_engines,scan_date,signature,malware_printable,threat_type,countryCode,isp,top_detections";

function appendUniqueIocValue(
  values: string[],
  seen: Set<string> | null,
  value: string | null | undefined
): Set<string> | null {
  if (!value) return seen;
  if (values.length === 0) {
    values[0] = value;
    return seen;
  }
  if (seen === null) {
    if (values.length === 1 && values[0] === value) return seen;
    seen = new Set<string>();
    for (let i = 0; i < values.length; i += 1) {
      const existing = values[i];
      if (existing !== undefined) seen.add(existing);
    }
  }
  if (seen.has(value)) return seen;
  seen.add(value);
  values[values.length] = value;
  return seen;
}

function joinIocValues(values: string[]): string {
  if (values.length === 0) return "";
  if (values.length === 1) return values[0] ?? "";
  if (values.length === 2) return (values[0] ?? "") + "\n" + (values[1] ?? "");
  if (values.length === 3) {
    return (values[0] ?? "") + "\n" + (values[1] ?? "") + "\n" + (values[2] ?? "");
  }
  return values.join("\n");
}

export function exportJSON(results: EnrichmentItem[]): void {
  const json = JSON.stringify(results, null, 2);
  const blob = new Blob([json], { type: "application/json" });
  downloadBlob(blob, "sentinelx-export-" + exportFilenameTimestamp() + ".json");
}

export function buildCSV(results: EnrichmentItem[]): string {
  let csv = CSV_HEADER;

  for (let i = 0; i < results.length; i += 1) {
    const r = results[i];
    if (!r) continue;
    if (r.type !== "result") continue;
    const raw = r.raw_stats;
    csv += "\n"
      + csvEscape(r.ioc_value) + ","
      + csvEscape(r.ioc_type) + ","
      + csvEscape(r.provider) + ","
      + csvEscape(r.verdict) + ","
      + String(r.detection_count) + ","
      + String(r.total_engines) + ","
      + csvEscape(r.scan_date ?? "") + ","
      + csvEscape(rawStatField(raw, "signature")) + ","
      + csvEscape(rawStatField(raw, "malware_printable")) + ","
      + csvEscape(rawStatField(raw, "threat_type")) + ","
      + csvEscape(rawStatField(raw, "countryCode")) + ","
      + csvEscape(rawStatField(raw, "isp")) + ","
      + csvEscape(rawStatField(raw, "top_detections"));
  }

  return csv;
}

export function exportCSV(results: EnrichmentItem[]): void {
  const csv = buildCSV(results);
  const blob = new Blob([csv], { type: "text/csv" });
  downloadBlob(blob, "sentinelx-export-" + exportFilenameTimestamp() + ".csv");
}

export function buildIocListText(cards: ArrayLike<HTMLElement>): string {
  let seen: Set<string> | null = null;
  const values: string[] = [];

  for (let i = 0; i < cards.length; i += 1) {
    const card = cards[i];
    if (!card) continue;
    seen = appendUniqueIocValue(values, seen, card.getAttribute("data-ioc-value"));
  }

  return joinIocValues(values);
}

export function buildIocListTextFromResults(results: EnrichmentItem[]): string {
  let seen: Set<string> | null = null;
  const values: string[] = [];

  for (let i = 0; i < results.length; i += 1) {
    const result = results[i];
    if (!result) continue;
    seen = appendUniqueIocValue(values, seen, result.ioc_value);
  }

  return joinIocValues(values);
}

export function copyAllIOCs(btn: HTMLElement, results?: EnrichmentItem[]): void {
  const text = results
    ? buildIocListTextFromResults(results)
    : buildIocListText(document.querySelectorAll<HTMLElement>(".ioc-card[data-ioc-value]"));
  writeToClipboard(text, btn);
}
