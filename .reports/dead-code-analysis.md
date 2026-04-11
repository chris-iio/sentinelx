# Dead Code Analysis Report

**Project:** SentinelX
**Date:** 2026-04-12
**Scope:** Runtime code (`app/`, `app/templates/`, `app/static/src/ts/`), tests (`tests/`), dependencies
**Tools Used:** `ruff` (F401/F841/F811), `tsc --noEmit`, `rg` cross-reference scans, parallel subagent analysis

---

## Summary

| Category | Result | Status |
|----------|--------|--------|
| TypeScript exports | 0 unused exports | Clean |
| Python runtime symbols | 0 unused functions/classes | Clean |
| Python imports | 0 unused imports | Clean (13 removed this run) |
| Runtime templates/partials | 0 orphaned templates | Clean |
| Runtime static assets | 0 unreferenced served assets | Clean |
| npm dependencies | 0 unused | Clean |
| Python dependencies | 0 unused | Clean |

**Verdict:** No actionable dead runtime code found after cleanup.

---

## Changes Applied (2026-04-12)

### 1. Removed unused `import logging` + `logger` from 13 adapter files

Removed `import logging` and `logger = logging.getLogger(__name__)` from files that never called `logger.*`:

- `app/enrichment/adapters/abuseipdb.py`
- `app/enrichment/adapters/base.py`
- `app/enrichment/adapters/crtsh.py`
- `app/enrichment/adapters/greynoise.py`
- `app/enrichment/adapters/hashlookup.py`
- `app/enrichment/adapters/ip_api.py`
- `app/enrichment/adapters/malwarebazaar.py`
- `app/enrichment/adapters/otx.py`
- `app/enrichment/adapters/shodan.py`
- `app/enrichment/adapters/threatfox.py`
- `app/enrichment/adapters/threatminer.py`
- `app/enrichment/adapters/urlhaus.py`
- `app/enrichment/adapters/virustotal.py`

**Kept logger in:** `asn_cymru.py`, `dns_lookup.py`, `whois_lookup.py` (all use `logger.exception()`).

### 2. Removed unused `make_email_ioc()` test helper

- File: `tests/helpers.py`
- No test file imports or calls this function (all other `make_*_ioc` helpers have callers)

### 3. Removed unused `VerdictKey` type import

- File: `app/static/src/ts/modules/row-factory.test.ts`
- Imported but never used as a type annotation in the file

### 4. Fixed GreyNoise provider name mismatch (bug)

- File: `app/static/src/ts/modules/row-factory.ts`
- Changed `PROVIDER_CONTEXT_FIELDS` key from `"GreyNoise Community"` to `"GreyNoise"`
- Backend adapter (`greynoise.py`) sends `name = "GreyNoise"` — the old key never matched, so context fields (noise, riot, classification) were silently dropped

**Lines removed:** ~30 (imports + helper function)

---

## Known Non-Removable Dead Code

### Abstract method stubs (required by ABC)

These methods are never called at runtime (each adapter overrides `lookup()` directly) but are required by `BaseHTTPAdapter`'s `@abc.abstractmethod` declarations. Removing them would cause `TypeError: Can't instantiate abstract class`:

- `VTAdapter._build_url()` / `._parse_response()` — `virustotal.py`
- `ThreatMinerAdapter._build_url()` / `._parse_response()` — `threatminer.py`
- `CrtShAdapter._parse_response()` — `crtsh.py`

### Test-only public API methods (intentional)

These have zero production callers but are tested and part of their class's public API:

- `ProviderRegistry.provider_count_for_type()` — `registry.py` (convenience wrapper)
- `ConfigStore.all_provider_keys()` — `config_store.py` (settings iteration)
- `CacheStore.purge_expired()` — `store.py` (built for future periodic cleanup)

### Architectural scaffolding

- `cards.init()` — `cards.ts` (empty no-op, consistent module init pattern)

---

## Verified Live Runtime Surface

### TypeScript entrypoint and import chain

All 16 source files reachable from `main.ts`. Every exported function/type/constant imported by at least one consumer.

### Flask routes are framework entrypoints

Route handlers decorated with `@bp_api.route(...)` are live despite appearing "unused" in naive symbol scans.

### Templates and served assets

All templates referenced via `render_template()`, `{% include %}`, `{% extends %}`. All static assets referenced from `base.html`.

---

## Reproduction

```bash
# Python lint (unused imports/vars)
.venv/bin/ruff check --select F401,F841,F811 app/ tests/

# TypeScript type check
npx tsc --noEmit

# Cross-reference scan for unused exports
rg "export (function|const|type|interface)" app/static/src/ts/ --no-filename | \
  sed 's/.*export \(function\|const\|type\|interface\) //' | sed 's/[(<:].*//' | \
  while read sym; do rg -l "$sym" app/static/src/ts/ | wc -l; done

# Python function usage scan
rg "^def |^    def " app/ --no-filename | \
  sed 's/.*def //' | sed 's/(.*//' | \
  while read sym; do rg -l "$sym" app/ tests/ | wc -l; done
```
