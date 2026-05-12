---
estimated_steps: 11
estimated_files: 1
skills_used: []
---

# T02: Write analyst guide for safe diagnostic bundle generation and sharing

Create `docs/diagnostic-export-guide.md` — an analyst-facing guide (distinct from the developer contract in `docs/diagnostic-export-contract.md`) covering how to use the diagnostic export feature safely.

Read `docs/diagnostic-export-contract.md` first for technical accuracy, then read `app/routes/diagnostics.py` to confirm the rate limit (3/minute), the URL (`/diagnostics/export`), and the error response shape.

Write for an analyst audience (not a developer). The guide must include at minimum these `## ` sections:
- **Overview** — what the bundle is, when to generate it, and what class of problems it helps diagnose
- **How to generate** — two methods: click the download icon in the nav (describe where it is and what the aria-label says), or `curl http://localhost:5000/diagnostics/export -o sentinelx-diagnostic.zip`
- **What's in the bundle** — `manifest.json` (per-source inventory), `runtime/*.json` sources (list the categories: health, orchestrator, cache, history, config, metadata), how to open the ZIP and read the manifest
- **Redaction guarantees** — all configured provider API keys are replaced with `[REDACTED]` before archiving; `manifest.json` records `redaction_labels` (e.g. `configured_secret:virustotal`) but never secret values; what this means for sharing
- **Safe sharing** — what can safely be shared (everything in the bundle after redaction), what to review first (manifest.json `redaction_labels` to confirm secrets were caught), edge cases (custom secrets configured by the analyst themselves)
- **Limits** — rate limit of 3 requests per minute (429 response if exceeded), per-source 256 KiB cap with truncation recorded in manifest, ~7 default sources
- **Troubleshooting** — 500 response means assembly failed (check server logs; the response body will say 'Diagnostic export failed. Check server logs.'); 429 means rate-limited (wait ~1 minute); unexpected omitted/error sources (read manifest.json for safe_error_summary)

Do not include internal implementation paths (`.gsd/`, `app/diagnostics/`) — keep it operational, not architectural.

## Inputs

- `docs/diagnostic-export-contract.md`
- `app/routes/diagnostics.py`

## Expected Output

- `docs/diagnostic-export-guide.md`

## Verification

test -f docs/diagnostic-export-guide.md && python3 -c "import re, sys; text=open('docs/diagnostic-export-guide.md').read(); sections=re.findall(r'^## ', text, re.MULTILINE); sys.exit(0 if len(sections) >= 5 else 1)" && echo 'GUIDE PASS'
