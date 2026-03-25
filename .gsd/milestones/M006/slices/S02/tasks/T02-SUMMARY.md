---
id: T02
parent: S02
milestone: M006
key_files:
  - requirements.txt
  - app/enrichment/setup.py
  - app/static/src/ts/modules/row-factory.ts
  - tests/test_registry_setup.py
key_decisions:
  - WHOIS provider registered in the zero-auth section (no API key needed, always configured) matching the DnsAdapter/CrtShAdapter pattern
  - WHOIS frontend context fields map raw_stats keys to display labels: registrar→Registrar, creation_date→Created, expiration_date→Expires, name_servers→NS (tags), org→Org
duration: ""
verification_result: passed
completed_at: 2026-03-25T11:42:48.707Z
blocker_discovered: false
---

# T02: Wire WhoisAdapter into registry as 15th provider, add WHOIS frontend context fields, update tests

**Wire WhoisAdapter into registry as 15th provider, add WHOIS frontend context fields, update tests**

## What Happened

Integrated the WhoisAdapter (created in T01) into the running system with four mechanical changes:

1. **requirements.txt**: Added `python-whois==0.9.6` dependency.
2. **app/enrichment/setup.py**: Imported WhoisAdapter and registered it as the 15th provider in the zero-auth section alongside DnsAdapter, CrtShAdapter, etc. Updated docstring to reflect 15 providers and list WHOIS in the zero-auth group.
3. **app/static/src/ts/modules/row-factory.ts**: Added 'WHOIS' to the CONTEXT_PROVIDERS set and added a WHOIS entry to PROVIDER_CONTEXT_FIELDS with fields: registrar (text), creation_date as 'Created' (text), expiration_date as 'Expires' (text), name_servers as 'NS' (tags), org (text). Also fixed a pre-existing duplicated code block at the end of the file that was causing a TypeScript compilation error.
4. **tests/test_registry_setup.py**: Updated `test_registry_has_fourteen_providers` to assert 15 providers. Added `test_registry_contains_whois` and `test_whois_is_always_configured` tests. The `get_provider_key` call count stays at 6 since WHOIS has no API key.

All verification passed: 33 registry tests, TypeScript typecheck clean, full suite 1035 tests (up from 1033).

## Verification

Three-stage verification from the task plan all passed:
1. `python3 -m pytest tests/test_registry_setup.py -v` — 33 passed including 2 new WHOIS tests
2. `make typecheck` — clean (tsc --noEmit, no errors)
3. `python3 -m pytest --tb=short -q` — 1035 passed (no regressions, +2 new tests)
Additionally verified `python3 -m pytest tests/test_whois_lookup.py -v` — all 56 T01 tests still pass.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/test_registry_setup.py -v` | 0 | ✅ pass | 100ms |
| 2 | `make typecheck` | 0 | ✅ pass | 70000ms |
| 3 | `python3 -m pytest --tb=short -q` | 0 | ✅ pass | 48280ms |
| 4 | `python3 -m pytest tests/test_whois_lookup.py -v` | 0 | ✅ pass | 60ms |


## Deviations

Fixed a pre-existing duplicated code block at the end of row-factory.ts (lines 563-573 were a duplicate of lines 553-562) that was causing TypeScript compilation errors. This was not caused by our edits but was already present in the file.

## Known Issues

None.

## Files Created/Modified

- `requirements.txt`
- `app/enrichment/setup.py`
- `app/static/src/ts/modules/row-factory.ts`
- `tests/test_registry_setup.py`
