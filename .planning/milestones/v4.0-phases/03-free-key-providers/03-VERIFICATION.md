---
phase: 03-free-key-providers
verified: 2026-03-03T12:30:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
---

# Phase 03: Free-Key Providers — Verification Report

**Phase Goal:** Implement 4 free-key provider adapters (URLhaus, OTX AlienVault, GreyNoise, AbuseIPDB), register all in the provider registry, and expand the settings page for multi-provider API key management.
**Verified:** 2026-03-03T12:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | URLhaus adapter enriches URL, hash, IP, and domain IOCs via abuse.ch POST API | VERIFIED | `URLhausAdapter` in `app/enrichment/adapters/urlhaus.py`; `_ENDPOINT_MAP` routes URL/IPV4/IPV6/DOMAIN/MD5/SHA256 to correct endpoints; 33 tests in `test_urlhaus.py` (465 lines), all passing |
| 2 | OTX adapter enriches all IOC types including CVE via OTX v1 GET API | VERIFIED | `OTXAdapter` in `app/enrichment/adapters/otx.py`; `supported_types = frozenset(IOCType)` covers all 8 types; `_OTX_TYPE_MAP` maps CVE to "cve" path; 42 tests (593 lines), all passing |
| 3 | GreyNoise adapter enriches IP IOCs using riot/noise/classification verdict logic | VERIFIED | `GreyNoiseAdapter` in `app/enrichment/adapters/greynoise.py`; `_parse_response` implements priority: riot -> clean, classification=malicious -> malicious, noise -> suspicious, else -> no_data; 29 tests (424 lines), all passing |
| 4 | AbuseIPDB adapter enriches IP IOCs using abuseConfidenceScore thresholds | VERIFIED | `AbuseIPDBAdapter` in `app/enrichment/adapters/abuseipdb.py`; thresholds >=75 malicious, >=25 suspicious, >0 reports clean, else no_data; 429 pre-check before `raise_for_status`; 33 tests (491 lines), all passing |
| 5 | All 4 adapters satisfy the Provider protocol (isinstance check passes) | VERIFIED | Each test file contains a `TestXxxProtocol` class with explicit `isinstance(adapter, Provider)` assertion; all pass |
| 6 | All 4 adapters use SSRF validation, timeouts, size cap, and no-redirect controls | VERIFIED | Each adapter calls `validate_endpoint()` before network call, uses `TIMEOUT=(5,30)`, `stream=True`, `allow_redirects=False`, `read_limited()` for response — confirmed in all 4 adapter files |
| 7 | Unconfigured adapters (empty API key) report is_configured() == False | VERIFIED | All 4 adapters: `is_configured() -> bool(self._api_key)`; confirmed in `test_new_providers_unconfigured_without_keys` in `test_registry_setup.py` |
| 8 | All 8 providers register through build_registry() — no hardcoded provider lists outside setup.py | VERIFIED | `app/enrichment/setup.py` registers all 8 providers in sequence; `test_registry_has_eight_providers` asserts `len(registry.all()) == 8`; no other file contains provider list |
| 9 | Settings page dynamically renders a form per key-requiring provider with status indicators | VERIFIED | `settings.html` uses `{% for provider in providers %}` loop producing one `<section class="settings-section">` per provider; shows Configured/Not configured badges; 5 provider sections confirmed |
| 10 | Saving a provider key via the settings page stores it in ConfigStore and shows 'Configured' on reload | VERIFIED | `settings_post()` accepts `provider_id` field, validates against known IDs, routes VT to `set_vt_api_key()` and others to `set_provider_key(pid)`; `test_save_provider_key_for_urlhaus` and `test_save_vt_api_key` both pass |

**Score:** 10/10 truths verified

---

### Required Artifacts

All checked at three levels: exists (L1), substantive (L2), wired (L3).

| Artifact | Provides | L1 Exists | L2 Substantive | L3 Wired | Status |
|----------|----------|-----------|----------------|----------|--------|
| `app/enrichment/adapters/urlhaus.py` | URLhausAdapter class | YES | 213 lines, class URLhausAdapter, _ENDPOINT_MAP, _parse_response | Imported in setup.py | VERIFIED |
| `tests/test_urlhaus.py` | URLhaus adapter tests | YES | 465 lines, 33 tests across 4 test classes | Run by pytest | VERIFIED |
| `app/enrichment/adapters/otx.py` | OTXAdapter class | YES | 211 lines, class OTXAdapter, _OTX_TYPE_MAP, _parse_response | Imported in setup.py | VERIFIED |
| `tests/test_otx.py` | OTX adapter tests | YES | 593 lines, 42 tests across 5 test classes | Run by pytest | VERIFIED |
| `app/enrichment/adapters/greynoise.py` | GreyNoiseAdapter class | YES | 215 lines, class GreyNoiseAdapter, _parse_response | Imported in setup.py | VERIFIED |
| `tests/test_greynoise.py` | GreyNoise adapter tests | YES | 424 lines, 29 tests across 4 test classes | Run by pytest | VERIFIED |
| `app/enrichment/adapters/abuseipdb.py` | AbuseIPDBAdapter class | YES | 212 lines, class AbuseIPDBAdapter, _parse_response | Imported in setup.py | VERIFIED |
| `tests/test_abuseipdb.py` | AbuseIPDB adapter tests | YES | 491 lines, 33 tests across 4 test classes | Run by pytest | VERIFIED |
| `app/enrichment/setup.py` | build_registry with all 8 providers + PROVIDER_INFO | YES | 116 lines, PROVIDER_INFO list (5 entries), build_registry registers 8 providers | Imported in routes.py | VERIFIED |
| `tests/test_registry_setup.py` | Registry setup tests for 8 providers | YES | Contains test_registry_has_eight_providers and 4 per-name tests | Run by pytest | VERIFIED |
| `app/routes.py` | Multi-provider settings GET/POST routes | YES | settings_get() loops PROVIDER_INFO, settings_post() accepts provider_id | Wired as Flask blueprint | VERIFIED |
| `app/templates/settings.html` | Multi-provider settings template | YES | 75 lines, {% for provider in providers %} loop, Configured/Not configured badges, data-role="toggle-key" | Rendered by settings_get() | VERIFIED |
| `app/static/src/ts/modules/settings.ts` | Per-provider show/hide toggle | YES | 37 lines, querySelectorAll('.settings-section') forEach pattern | Compiled into dist/main.js | VERIFIED |
| `app/static/dist/main.js` | Compiled JS bundle | YES | Contains D() function with querySelectorAll and toggle-key logic | Loaded by base.html | VERIFIED |

---

### Key Link Verification

#### Plan 01 Key Links

| From | To | Via | Status | Evidence |
|------|----|-----|--------|----------|
| `app/enrichment/adapters/urlhaus.py` | `app/enrichment/http_safety.py` | `from app.enrichment.http_safety import` | WIRED | Line 36: `from app.enrichment.http_safety import TIMEOUT, read_limited, validate_endpoint` |
| `app/enrichment/adapters/otx.py` | `app/enrichment/http_safety.py` | `from app.enrichment.http_safety import` | WIRED | Line 40: `from app.enrichment.http_safety import TIMEOUT, read_limited, validate_endpoint` |
| `app/config.py` | urlhaus-api.abuse.ch in ALLOWED_API_HOSTS | `urlhaus-api.abuse.ch` | WIRED | Line 47: `"urlhaus-api.abuse.ch",    # Phase 03-01: URLhaus (free-key)` |
| `app/config.py` | otx.alienvault.com in ALLOWED_API_HOSTS | `otx.alienvault.com` | WIRED | Line 48: `"otx.alienvault.com",      # Phase 03-01: OTX AlienVault (free-key)` |

#### Plan 02 Key Links

| From | To | Via | Status | Evidence |
|------|----|-----|--------|----------|
| `app/enrichment/adapters/greynoise.py` | `app/enrichment/http_safety.py` | `from app.enrichment.http_safety import` | WIRED | Line 35: `from app.enrichment.http_safety import TIMEOUT, read_limited, validate_endpoint` |
| `app/enrichment/adapters/abuseipdb.py` | `app/enrichment/http_safety.py` | `from app.enrichment.http_safety import` | WIRED | Line 38: `from app.enrichment.http_safety import TIMEOUT, read_limited, validate_endpoint` |
| `app/config.py` | api.greynoise.io in ALLOWED_API_HOSTS | `api.greynoise.io` | WIRED | Line 49: `"api.greynoise.io",        # Phase 03-02: GreyNoise Community (free-key)` |
| `app/config.py` | api.abuseipdb.com in ALLOWED_API_HOSTS | `api.abuseipdb.com` | WIRED | Line 50: `"api.abuseipdb.com",       # Phase 03-02: AbuseIPDB (free-key)` |

#### Plan 03 Key Links

| From | To | Via | Status | Evidence |
|------|----|-----|--------|----------|
| `app/enrichment/setup.py` | `app/enrichment/adapters/urlhaus.py` | `from app.enrichment.adapters.urlhaus import` | WIRED | Line 20: `from app.enrichment.adapters.urlhaus import URLhausAdapter` |
| `app/enrichment/setup.py` | `app/enrichment/adapters/otx.py` | `from app.enrichment.adapters.otx import` | WIRED | Line 17: `from app.enrichment.adapters.otx import OTXAdapter` |
| `app/enrichment/setup.py` | `app/enrichment/adapters/greynoise.py` | `from app.enrichment.adapters.greynoise import` | WIRED | Line 15: `from app.enrichment.adapters.greynoise import GreyNoiseAdapter` |
| `app/enrichment/setup.py` | `app/enrichment/adapters/abuseipdb.py` | `from app.enrichment.adapters.abuseipdb import` | WIRED | Line 14: `from app.enrichment.adapters.abuseipdb import AbuseIPDBAdapter` |
| `app/routes.py` | `app/enrichment/setup.py` | `from app.enrichment.setup import.*PROVIDER_INFO` | WIRED | Line 32: `from app.enrichment.setup import PROVIDER_INFO, build_registry` |
| `app/templates/settings.html` | `app/routes.py` | `for provider in providers` | WIRED | Line 14: `{% for provider in providers %}` — providers list passed from settings_get() |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| URL-01 | 03-01-PLAN | URLhaus adapter enriches URL, hash, IP, and domain IOCs using the abuse.ch v1 API | SATISFIED | `URLhausAdapter` implements POST to /v1/url/, /v1/host/, /v1/payload/; supported_types includes URL, IPV4, IPV6, DOMAIN, MD5, SHA256; 33 tests pass |
| OTX-01 | 03-01-PLAN | OTX AlienVault adapter enriches all IOC types including CVE using the OTX v1 API | SATISFIED | `OTXAdapter` uses `frozenset(IOCType)` covering all 8 types; `_OTX_TYPE_MAP` maps CVE -> "cve"; pulse-count verdict thresholds >=5/>=1/else; 42 tests pass |
| GREY-01 | 03-02-PLAN | GreyNoise Community adapter enriches IP IOCs using the GreyNoise v3 community API | SATISFIED | `GreyNoiseAdapter` hits `/v3/community/{ip}`; riot/noise/classification priority verdict; 404 returns no_data; 29 tests pass |
| ABUSE-01 | 03-02-PLAN | AbuseIPDB adapter enriches IP IOCs using the AbuseIPDB v2 API | SATISFIED | `AbuseIPDBAdapter` hits `/api/v2/check?ipAddress={ip}&maxAgeInDays=90`; score threshold verdicts; 429 pre-handling; 33 tests pass |
| MULTI-01 | 03-03-PLAN | All four providers register through the same registry pattern with no hardcoded lists | SATISFIED | `build_registry()` in setup.py is the single registration point; no hardcoded provider lists anywhere else; `test_registry_has_eight_providers` asserts len == 8 |
| MULTI-02 | 03-03-PLAN | Unconfigured providers (no API key) are gracefully skipped without errors | SATISFIED | `is_configured()` returns `bool(self._api_key)` for all 4 adapters; `registry.providers_for_type()` filters out unconfigured adapters; `test_new_providers_unconfigured_without_keys` verifies this explicitly |

All 6 phase requirements are SATISFIED. No orphaned requirements detected.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/templates/settings.html` | 53 | `placeholder="Paste your {{ provider.name }} API key here"` | INFO | HTML `placeholder` attribute — this is correct usage of the HTML attribute, not a code placeholder stub |

No code stubs, empty implementations, or incomplete handlers found. The single "placeholder" occurrence is a legitimate HTML form input placeholder attribute.

---

### Human Verification Required

#### 1. Settings Page Visual Layout

**Test:** Navigate to `/settings` with a configured VirusTotal key and unconfigured URLhaus. Inspect the page.
**Expected:** 5 provider sections appear in order (VirusTotal, URLhaus, OTX AlienVault, GreyNoise, AbuseIPDB). VirusTotal shows "Configured" badge with dot indicator. URLhaus shows "Not configured" badge. Each provider displays its description and signup link.
**Why human:** CSS badge rendering, visual hierarchy, and color indicators cannot be verified by grep.

#### 2. Show/Hide Toggle Independence

**Test:** On the settings page, click "Show" for URLhaus and then "Show" for OTX without touching VirusTotal.
**Expected:** Each toggle controls only its own provider's input independently. VirusTotal input type remains "password" while URLhaus and OTX inputs switch to "text".
**Why human:** DOM event isolation across dynamically generated elements requires live browser interaction to verify.

#### 3. Key Save Round-Trip

**Test:** Paste a test API key into the URLhaus form and click "Save API Key". Check that on reload the key shows as masked (asterisks) and badge changes to "Configured".
**Expected:** Flash message "API key saved for urlhaus." appears, page reloads, badge becomes "Configured", input shows masked key.
**Why human:** Requires live ConfigStore write to `~/.sentinelx/config.ini` and Flask session state for flash messages.

---

### Test Suite Results

- `tests/test_urlhaus.py`: 33 tests, all PASSED
- `tests/test_otx.py`: 42 tests, all PASSED
- `tests/test_greynoise.py`: 29 tests, all PASSED
- `tests/test_abuseipdb.py`: 33 tests, all PASSED
- `tests/test_registry_setup.py`: 18 tests, all PASSED (including `test_registry_has_eight_providers`)
- `tests/test_settings.py`: 19 tests, all PASSED (including multi-provider and provider_id validation tests)
- **Full suite (excluding E2E):** 455 tests, 455 PASSED, 0 FAILED
- `make typecheck`: tsc --noEmit CLEAN (no type errors)

---

## Summary

Phase 03 goal is fully achieved. All 4 free-key provider adapters (URLhaus, OTX AlienVault, GreyNoise, AbuseIPDB) are implemented, tested, and wired into the live registry. The settings page has been expanded from a single VT form to a dynamic 5-provider multi-form layout. All 6 requirement IDs (URL-01, OTX-01, GREY-01, ABUSE-01, MULTI-01, MULTI-02) are satisfied by verifiable code.

Key implementation quality notes:
- Each adapter strictly follows the Provider protocol (runtime_checkable isinstance passes)
- Every adapter imports and uses the shared http_safety module — SSRF, timeouts, size caps, and no-redirects are consistently applied
- ALLOWED_API_HOSTS in app/config.py contains all 4 new hostnames
- build_registry() is the single source of truth — no provider lists exist elsewhere
- The settings template is fully data-driven from PROVIDER_INFO; adding a new provider requires only a new entry in setup.py

---

_Verified: 2026-03-03T12:30:00Z_
_Verifier: Claude (gsd-verifier)_
