---
phase: 24-provider-registry-refactor
plan: 01
subsystem: api
tags: [python, protocol, typing, registry, configparser, tdd]

# Dependency graph
requires: []
provides:
  - Provider protocol (typing.Protocol, @runtime_checkable) at app/enrichment/provider.py
  - ProviderRegistry class with register/all/configured/providers_for_type at app/enrichment/registry.py
  - ConfigStore multi-provider key storage via [providers] INI section
  - Protocol conformance (name, requires_api_key, is_configured) on VTAdapter, MBAdapter, TFAdapter
affects:
  - 24-02 (wires registry into routes and frontend)
  - 25-shodan (new provider will implement Provider protocol)
  - 26-free-key-providers (new providers will implement Provider protocol)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - typing.Protocol with @runtime_checkable for structural adapter conformance
    - Central registry pattern for plugin-style provider registration
    - configparser [providers] section for multi-provider key storage

key-files:
  created:
    - app/enrichment/provider.py
    - app/enrichment/registry.py
    - tests/test_provider_protocol.py
    - tests/test_provider_registry.py
  modified:
    - app/enrichment/adapters/virustotal.py
    - app/enrichment/adapters/malwarebazaar.py
    - app/enrichment/adapters/threatfox.py
    - app/enrichment/config_store.py
    - tests/test_config_store.py

key-decisions:
  - "Used @runtime_checkable Protocol so isinstance(adapter, Provider) works without explicit subclassing"
  - "Registry stores providers by name (dict[str, Provider]) — O(1) duplicate detection via ValueError"
  - "providers_for_type() combines is_configured() + supported_types filter in one step"
  - "ConfigStore uses separate [providers] INI section — does not conflict with existing [virustotal] section"
  - "Provider names stored lowercase in [providers] section — case-insensitive retrieval by design"

patterns-established:
  - "Provider protocol: name, supported_types, requires_api_key class attrs + lookup() + is_configured() methods"
  - "is_configured() pattern: True always for public providers, bool(self._api_key) for key-required providers"
  - "Registry lookup pattern: providers_for_type() as the primary method for orchestrator queries"

requirements-completed: [REG-01, REG-02, REG-04]

# Metrics
duration: 4min
completed: 2026-03-02
---

# Phase 24 Plan 01: Provider Protocol + Registry Summary

**@runtime_checkable Provider protocol, ProviderRegistry with type/config filtering, and ConfigStore expanded to multi-provider [providers] INI section — all three adapters conform via isinstance()**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-02T11:30:45Z
- **Completed:** 2026-03-02T11:34:51Z
- **Tasks:** 2
- **Files modified:** 9 (4 created, 5 modified)

## Accomplishments

- Provider protocol defined with @runtime_checkable — all 3 adapters pass isinstance(adapter, Provider) without subclassing
- ProviderRegistry built with register/all/configured/providers_for_type/provider_count_for_type — duplicate detection via ValueError
- ConfigStore expanded with get_provider_key/set_provider_key/all_provider_keys using new [providers] INI section — fully backward compatible with existing [virustotal] section
- 25 new tests added (15 protocol + 10 multi-provider config) plus 18 registry tests, all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Provider Protocol + Adapter Conformance** - `775bc29` (feat)
2. **Task 2: ProviderRegistry + ConfigStore Multi-Provider** - `a407af3` (feat)

_Note: Both tasks implemented with TDD (RED then GREEN pattern)_

## Files Created/Modified

- `app/enrichment/provider.py` - @runtime_checkable Provider Protocol definition
- `app/enrichment/registry.py` - ProviderRegistry with register/filter/query methods
- `app/enrichment/adapters/virustotal.py` - Added name, requires_api_key, is_configured()
- `app/enrichment/adapters/malwarebazaar.py` - Added name, requires_api_key, is_configured()
- `app/enrichment/adapters/threatfox.py` - Added name, requires_api_key, is_configured()
- `app/enrichment/config_store.py` - Added _PROVIDERS_SECTION, get/set_provider_key, all_provider_keys
- `tests/test_provider_protocol.py` - 15 protocol conformance tests
- `tests/test_provider_registry.py` - 18 registry behavior tests
- `tests/test_config_store.py` - 10 new multi-provider tests in TestConfigStoreMultiProvider

## Decisions Made

- @runtime_checkable chosen so isinstance() works without requiring explicit inheritance — structural typing means any adapter with the right shape qualifies
- Registry dict keyed by provider name enables O(1) duplicate detection and O(1) provider lookup
- VTAdapter.is_configured() uses bool(self._api_key) — empty string returns False, any non-empty string returns True
- [providers] INI section kept separate from [virustotal] to avoid backward-compat breaks and keep clean separation of concerns

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

9 pre-existing E2E test failures (Playwright) observed during full suite run — unrelated to this plan. Documented in MEMORY.md as known issues requiring VT API key. All 267 non-E2E tests pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Provider protocol and registry are ready — Plan 02 can wire them into routes and setup.py
- All three existing adapters conform to Provider protocol without any route changes (backward compatible)
- ConfigStore ready for Plan 02 to read keys and pass to adapters during registry construction

---
*Phase: 24-provider-registry-refactor*
*Completed: 2026-03-02*
