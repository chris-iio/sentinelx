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

function timestamp(): string {
  return new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
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
  if (Array.isArray(val)) return val.join("; ");
  return String(val);
}

// ---- Public API ----

const CSV_COLUMNS = [
  "ioc_value", "ioc_type", "provider", "verdict",
  "detection_count", "total_engines", "scan_date",
  "signature", "malware_printable", "threat_type",
  "countryCode", "isp", "top_detections",
] as const;

export function exportJSON(results: EnrichmentItem[]): void {
  const json = JSON.stringify(results, null, 2);
  const blob = new Blob([json], { type: "application/json" });
  downloadBlob(blob, "sentinelx-export-" + timestamp() + ".json");
}

export function exportCSV(results: EnrichmentItem[]): void {
  const header = CSV_COLUMNS.join(",") + "\n";
  const rows: string[] = [];

  for (const r of results) {
    if (r.type !== "result") continue;
    const raw = r.raw_stats;
    const row = [
      csvEscape(r.ioc_value),
      csvEscape(r.ioc_type),
      csvEscape(r.provider),
      csvEscape(r.verdict),
      String(r.detection_count),
      String(r.total_engines),
      csvEscape(r.scan_date ?? ""),
      csvEscape(rawStatField(raw, "signature")),
      csvEscape(rawStatField(raw, "malware_printable")),
      csvEscape(rawStatField(raw, "threat_type")),
      csvEscape(rawStatField(raw, "countryCode")),
      csvEscape(rawStatField(raw, "isp")),
      csvEscape(rawStatField(raw, "top_detections")),
    ];
    rows.push(row.join(","));
  }

  const csv = header + rows.join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  downloadBlob(blob, "sentinelx-export-" + timestamp() + ".csv");
}

export function copyAllIOCs(btn: HTMLElement): void {
  const cards = document.querySelectorAll<HTMLElement>(".ioc-card[data-ioc-value]");
  const seen = new Set<string>();
  const values: string[] = [];

  cards.forEach((card) => {
    const val = card.getAttribute("data-ioc-value");
    if (val && !seen.has(val)) {
      seen.add(val);
      values.push(val);
    }
  });

  writeToClipboard(values.join("\n"), btn);
}
