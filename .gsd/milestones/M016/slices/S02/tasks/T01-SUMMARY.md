---
id: T01
parent: S02
milestone: M016
key_files:
  - tests/test_emailrep_registry_settings.py
  - app/enrichment/setup.py
key_decisions:
  - Provider key lookup failures are treated as missing keys during registry composition, leaving key-required providers unconfigured instead of aborting startup.
duration: 
verification_result: passed
completed_at: 2026-05-09T16:42:21.326Z
blocker_discovered: false
---

# T01: Added EmailRep registry/settings contract tests and hardened provider-key reads so EmailRep stays unconfigured when its key lookup fails.

**Added EmailRep registry/settings contract tests and hardened provider-key reads so EmailRep stays unconfigured when its key lookup fails.**

## What Happened

Created `tests/test_emailrep_registry_settings.py` to pin the EmailRep settings metadata, SSRF allowlist host, EmailRep-only IOC type boundary, missing/empty key behavior, and exact configured email-provider count when an EmailRep key is present. The tests exercise `build_registry()` and `ProviderRegistry.providers_for_type()` / `provider_count_for_type()` directly with mocked `ConfigStore` responses and no live network calls. The focused red case covered `ConfigStore.get_provider_key("emailrep")` raising an exception. `_get_provider_key_or_empty()` in `app/enrichment/setup.py` routes key-required provider composition through a fail-closed missing-key behavior, preserving the single registration path while treating local provider-key read failures as unconfigured providers.

## Verification

Focused tests and required task command passed. `python3 -m pytest tests/test_emailrep_registry_settings.py -q` passed with 14 tests. `python3 -m pytest tests/test_emailrep_registry_settings.py tests/test_registry_setup.py tests/test_adapter_contract.py -q` passed as part of fresh slice verification with 235 tests. LSP diagnostics in the original task run reported no issues for `app/enrichment/setup.py` or `tests/test_emailrep_registry_settings.py`.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/test_emailrep_registry_settings.py tests/test_registry_setup.py tests/test_adapter_contract.py -q` | 0 | ✅ pass (235 passed in 0.34s) | 340ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `tests/test_emailrep_registry_settings.py`
- `app/enrichment/setup.py`
