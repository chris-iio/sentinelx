---
phase: 03-free-key-providers
plan: "03"
subsystem: provider-registry
tags: [registry, settings, multi-provider, routes, typescript]
dependency_graph:
  requires: [03-01, 03-02]
  provides: [all-8-providers-registered, multi-provider-settings-page]
  affects: [app/enrichment/setup.py, app/routes.py, app/templates/settings.html]
tech_stack:
  added: []
  patterns: [PROVIDER_INFO-metadata, per-provider-settings-loop, querySelectorAll-toggle]
key_files:
  created: []
  modified:
    - app/enrichment/setup.py
    - tests/test_registry_setup.py
    - app/routes.py
    - app/templates/settings.html
    - app/static/src/ts/modules/settings.ts
    - app/static/dist/main.js
    - tests/test_settings.py
decisions:
  - "PROVIDER_INFO defined in setup.py (not routes.py) — keeps provider metadata co-located with registration"
  - "settings_post routes virustotal to set_vt_api_key(), others to set_provider_key() — preserves backward compat"
  - "Template loops over providers list from route; no hardcoded provider names in HTML"
  - "settings.ts uses querySelectorAll('.settings-section') pattern — independent per-provider toggles"
  - "test_settings.py updated: old test_save_api_key preserved + provider_id=virustotal, 7 new tests added"
metrics:
  duration_seconds: 215
  completed_date: "2026-03-03"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 7
  tests_added: 11
  tests_total: 455
---

# Phase 03 Plan 03: Provider Registry + Settings Page Wiring Summary

All 4 new adapters (URLhaus, OTX, GreyNoise, AbuseIPDB) wired into build_registry() and settings page expanded to a 5-provider multi-form layout with per-provider key management and show/hide toggles.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Register all 4 new providers in setup.py and update registry tests | 2f2fec3 | setup.py, test_registry_setup.py |
| 2 | Multi-provider settings page (routes + template + TypeScript) | 9b35cf1 | routes.py, settings.html, settings.ts, main.js, test_settings.py |

## What Was Built

### Task 1: 8-Provider Registry

Updated `app/enrichment/setup.py` to import and register all 4 new adapters:

```python
urlhaus_key = config_store.get_provider_key("urlhaus") or ""
registry.register(URLhausAdapter(api_key=urlhaus_key, allowed_hosts=allowed_hosts))

otx_key = config_store.get_provider_key("otx") or ""
registry.register(OTXAdapter(api_key=otx_key, allowed_hosts=allowed_hosts))

gn_key = config_store.get_provider_key("greynoise") or ""
registry.register(GreyNoiseAdapter(api_key=gn_key, allowed_hosts=allowed_hosts))

abuseipdb_key = config_store.get_provider_key("abuseipdb") or ""
registry.register(AbuseIPDBAdapter(api_key=abuseipdb_key, allowed_hosts=allowed_hosts))
```

Added `PROVIDER_INFO` module-level constant — list of 5 dicts (id, name, requires_key, signup_url, description) for the 5 key-requiring providers. Public providers (MalwareBazaar, ThreatFox, Shodan) are omitted since they need no configuration.

Registry tests expanded from 11 to 18:
- `test_registry_has_eight_providers` (renamed from four)
- 4 new per-name tests (URLhaus, OTX AlienVault, GreyNoise, AbuseIPDB)
- `test_new_providers_unconfigured_without_keys`
- `test_new_provider_configured_with_key` (URLhaus with side_effect mock)
- `test_config_store_get_provider_key_called_for_each_new_provider` (asserts exactly 4 calls, correct names)

### Task 2: Multi-Provider Settings Page

`app/routes.py` `settings_get()` now loops over PROVIDER_INFO, calling `get_vt_api_key()` for virustotal and `get_provider_key(pid)` for all others. Returns `providers` list to template instead of `masked_key` scalar.

`settings_post()` accepts a `provider_id` hidden field, validates it against known provider IDs, and routes to `set_vt_api_key()` or `set_provider_key()` accordingly. Unknown provider_id flashes an error and does not save.

`settings.html` loops over `{% for provider in providers %}` — one `<section class="settings-section">` per provider with:
- Configured/Not configured status badge
- Provider description and signup link
- Hidden `provider_id` field per form
- Input with `id="api-key-{{ provider.id }}"` and `class="form-input--mono"`
- Toggle button with `data-role="toggle-key"`

`settings.ts` replaced single `getElementById` with `querySelectorAll('.settings-section')` forEach — each section wires its own toggle button to its own input independently.

`test_settings.py` updated with 7 new tests: all_five_providers, provider_id_fields, configured/not-configured badges, save for non-VT provider, unknown provider_id rejection, missing provider_id rejection.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_settings.py to match new multi-provider POST API**
- **Found during:** Task 2 verification
- **Issue:** Existing `test_save_api_key` and `test_save_api_key_follows_redirect` did not include `provider_id` in form data, causing them to fail (unknown provider → flash error, no save)
- **Fix:** Updated both tests to pass `provider_id=virustotal`; updated `test_save_api_key_follows_redirect` mock to stub `get_provider_key` (needed by new `settings_get` loop after redirect). Added `mock_instance.get_provider_key.return_value = None` to all GET-related mocks.
- **Files modified:** tests/test_settings.py
- **Commit:** 9b35cf1

## Verification Results

- `python3 -m pytest tests/ -x --ignore=tests/e2e` — 455 passed, 0 failed
- `make build` — CSS + JS compiled successfully
- `make typecheck` — tsc --noEmit clean

## Self-Check: PASSED

All files exist and all commits are present.
