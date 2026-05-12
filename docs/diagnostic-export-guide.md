# Diagnostic Export Guide

## Overview

The diagnostic export is a local troubleshooting ZIP bundle for SentinelX. Generate it when an analyst, maintainer, or support contact needs a compact snapshot of the app's health, cache/history state, provider configuration shape, and recent runtime diagnostics.

Use the bundle for problems such as:

- enrichment results that look stale, missing, or inconsistent
- provider or cache behavior that needs investigation
- history-save or health-check problems
- support handoffs where a reviewer needs evidence without direct access to your local app

The export is designed for safe sharing after redaction. It is not a remote upload feature: downloading the ZIP only saves a local file from your running SentinelX instance.

## How to generate

You can generate the diagnostic bundle in either of these ways.

### From the SentinelX navigation

1. Open SentinelX in your browser.
2. In the floating navigation, use the download icon between History and Settings.
3. Screen readers identify this icon-only link as `Download diagnostic export`.
4. Your browser should download a ZIP file named like `sentinelx-diagnostic-YYYY-MM-DD.zip`.

### From the command line

If SentinelX is running locally on port 5000, run:

```sh
curl http://localhost:5000/diagnostics/export -o sentinelx-diagnostic.zip
```

Keep the downloaded ZIP intact unless the person helping you asks for a specific file from inside it.

## What's in the bundle

Every bundle contains a top-level `manifest.json` file plus zero or more JSON diagnostic payloads under `runtime/`.

`manifest.json` is the inventory. It lists each diagnostic source that SentinelX considered, including whether that source was included, truncated, omitted, or hit a safe error. It also records source categories, archive paths, byte counts, truncation flags, omitted reasons, safe error summaries, and redaction labels.

The `runtime/*.json` files are the source payloads. Their categories can include:

- `health` — health and dependency checks
- `orchestrator` — enrichment job/provider runtime diagnostics when job context is available
- `cache` — cache statistics
- `history` — recent history summaries and history-save diagnostics
- `config` — configuration shape and provider secret inventory, without secret values
- `metadata` — bundle metadata such as generation time and available runtime objects

A default local export usually considers about seven sources. Some sources may be omitted when optional context is unavailable; check `manifest.json` for the exact status of each source.

To inspect the bundle:

1. Open the ZIP with your operating system's archive viewer, or unzip it into a temporary folder.
2. Open `manifest.json` first.
3. Review each `sources` entry and its `status`.
4. For entries with an archive path such as `runtime/cache-stats.json`, open the matching JSON file for the safe diagnostic payload.

## Redaction guarantees

SentinelX redacts configured provider API keys before writing any diagnostic payload into the ZIP. When a configured secret is found in an exported payload or error summary, the value is replaced with `[REDACTED]` before archiving.

The manifest can record redaction metadata such as:

- `redaction_count` — how many redaction events occurred
- `redaction_labels` — stable labels for what was redacted, for example `configured_secret:virustotal`

`manifest.json` never records the secret values themselves. It may tell you that a VirusTotal key was configured and redacted, but it must not include the key.

For sharing, this means the bundle is intended to be safe to send after redaction. It should contain enough context to diagnose the app state without exposing configured provider credentials.

## Safe sharing

You can safely share the diagnostic ZIP after redaction, including `manifest.json` and the `runtime/*.json` files, with the person or team helping you troubleshoot SentinelX.

Before sharing, do a quick review:

1. Open `manifest.json`.
2. Find `redaction_labels` on the manifest and on individual source records.
3. Confirm the labels match the provider secrets you expected SentinelX to catch, such as `configured_secret:virustotal`.
4. If a source has `status: "error"`, read its `safe_error_summary` to understand what failed without exposing raw stack traces or secrets.

Be extra careful with custom secrets that you added yourself outside the normal provider configuration flow. SentinelX redacts configured provider API keys and common secret patterns, but analyst-created notes, filenames, copied command output, or custom values may not always be recognizable as secrets. If you manually placed sensitive data into history, configuration labels, or local diagnostic text, review the relevant JSON before forwarding the ZIP.

If you are unsure, share the whole ZIP only with a trusted maintainer or support contact, or ask which specific files they need.

## Limits

The diagnostic export is intentionally bounded:

- The download endpoint is rate-limited to 3 requests per minute. A fourth request inside the same minute returns HTTP `429`.
- Each source has a 256 KiB cap. If a source is larger, the exported payload is truncated and `manifest.json` records the truncation.
- A default bundle considers about seven sources, though optional context can make some sources omitted.
- Source failures are isolated: one source can be marked `error` without preventing other sources from appearing in the bundle.
- The export downloads a ZIP to your machine; it does not upload the bundle anywhere automatically.

## Troubleshooting

### The request returns 429

You hit the rate limit of 3 requests per minute. Wait about 1 minute, then try again.

### The request returns 500

Bundle assembly failed. The response body will be:

```text
Diagnostic export failed. Check server logs.
```

Check the server logs for the underlying assembly failure. The browser or curl response is intentionally brief so it does not expose stack traces or secrets.

### A source is missing, omitted, or marked error

Open `manifest.json` and find the source record.

- `omitted` means SentinelX intentionally skipped that source; read `omitted_reason` for why.
- `error` means SentinelX tried to collect the source but could not; read `safe_error_summary` for the bounded, secret-free explanation.
- `truncated` means the source exceeded the per-source size cap; read the byte counts and truncation fields in the manifest.

Unexpected omitted or error sources are usually still useful: the manifest shows what was attempted and why a source did not produce a full payload.

### The ZIP opens but a JSON file looks incomplete

Check the matching source record in `manifest.json`. If `truncated` is true, the file hit the 256 KiB per-source cap. Share the bundle as-is and mention that the affected source was truncated.
