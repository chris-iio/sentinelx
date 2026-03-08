# Phase 01: Quality-of-Life Features (Retroactive Summary)

> **Note:** This phase was built ad-hoc after v4.0 shipped (2026-03-03 to 2026-03-09) and adopted retroactively into GSD as v5.0. No prospective PLAN documents exist -- this SUMMARY records what was delivered.

## Features Delivered

### 1. Enrichment Result Cache

SQLite-backed cache (`app/cache/store.py`) that stores provider responses to avoid redundant API calls on re-submission of the same IOC.

- **Storage:** SQLite with `(ioc_value, provider_name)` composite key
- **TTL:** Configurable via ConfigStore (`cache_ttl_minutes`, default 60)
- **Thread safety:** `check_same_thread=False` for Flask's threaded mode
- **Settings UI:** TTL input + clear cache button on settings page
- **Orchestrator integration:** Check cache before API call, store result after
- **UX:** Cache hit badge on result rows showing age of cached data

**Files:** `app/cache/__init__.py`, `app/cache/store.py`, `app/enrichment/orchestrator.py`, `app/enrichment/config_store.py`, `app/templates/settings.html`, `app/static/src/ts/modules/enrichment.ts`
**Tests:** `tests/test_cache_store.py` (11 tests)

### 2. Export Menu

Client-side export replacing the single copy button with a dropdown offering JSON, CSV, and clipboard export.

- **Formats:** JSON (full result data), CSV (flattened rows), clipboard (text summary)
- **Implementation:** New `export.ts` module with format-specific serializers
- **UX:** Dropdown menu with format icons, click-outside-to-close

**Files:** `app/static/src/ts/modules/export.ts`, `app/static/src/ts/modules/enrichment.ts`, `app/static/src/input.css`, `app/templates/results.html`
**Tests:** Covered by existing enrichment integration tests

### 3. Bulk IOC Input Mode

One-per-line IOC input mode that bypasses free-text extraction, allowing analysts to paste a list of known IOCs directly.

- **Parser:** `app/pipeline/bulk.py` -- splits on newlines, validates each line as a single IOC, deduplicates
- **UI toggle:** Checkbox on index page switches between free-text and bulk mode
- **Route branching:** `/analyze` checks `bulk_mode` form field to select parser
- **Validation:** Invalid lines silently skipped (not IOCs)

**Files:** `app/pipeline/bulk.py`, `app/routes.py`, `app/static/src/ts/modules/form.ts`, `app/templates/index.html`
**Tests:** `tests/test_bulk_parser.py` (8 tests)

### 4. Provider Context Fields

Additional context fields from VirusTotal responses (top detections, reputation score) rendered in per-provider detail rows for all 8 providers.

- **VT fields:** `top_detections` (up to 5 engine names), `reputation` score
- **Adapter changes:** `virustotal.py` extracts new fields from `last_analysis_results`
- **Frontend rendering:** `enrichment.ts` renders context fields as key-value pairs in detail rows
- **Generic:** Field rendering works for any provider returning `context_fields` dict

**Files:** `app/enrichment/adapters/virustotal.py`, `app/static/src/ts/modules/enrichment.ts`, `app/static/src/ts/types/api.ts`
**Tests:** `tests/test_vt_context_fields.py` (7 tests)

## Summary

| Metric | Before (v4.0) | After (v5.0) |
|--------|---------------|--------------|
| Python LOC | ~3,127 | ~3,515 |
| Frontend LOC (TS+CSS) | ~3,072 | ~3,619 |
| Template LOC | ~386 | ~449 |
| Test LOC | ~8,006 | ~8,408 |
| Unit/Integration Tests | 457 | 483 |
| New test files | -- | 3 |
| Files modified | -- | 16 |
| Files created | -- | 5 |

## Key Decisions

- **Single phase, no PLANs:** Work was done ad-hoc; writing retroactive PLANs would be dishonest documentation
- **2 logical commits:** Cache + export + context field changes are interwoven in shared files (`enrichment.ts`, `main.js`), making per-feature commits impossible without phantom intermediate states
- **SQLite for cache:** Lightweight, zero-config, file-based -- fits the localhost-only deployment model
- **Client-side export:** No server roundtrip needed; all data already in the DOM
