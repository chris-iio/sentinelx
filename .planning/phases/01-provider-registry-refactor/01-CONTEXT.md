# Phase 1: Provider Registry Refactor - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning
**Source:** PRD Express Path (docs/plans/2026-03-02-universal-threat-intel-hub.md)

<domain>
## Phase Boundary

Extract a formal provider protocol and registry so adding new providers requires zero changes to orchestrator or route code. This is the foundational refactoring phase for v4.0 — it converts SentinelX from hardcoded 3-provider wiring to a plugin-style registry architecture.

</domain>

<decisions>
## Implementation Decisions

### Provider Protocol (Task 24.1)
- Use `typing.Protocol` with `@runtime_checkable` for structural subtyping
- Protocol defines: `name: str`, `supported_types: set[IOCType] | frozenset[IOCType]`, `requires_api_key: bool`, `lookup(IOC) -> EnrichmentResult | EnrichmentError`, `is_configured() -> bool`
- All three existing adapters (VTAdapter, MBAdapter, TFAdapter) must satisfy the protocol via `isinstance()` check
- Add `name`, `requires_api_key`, and `is_configured()` attributes to existing adapters
- TDD: tests first using `isinstance(adapter, Provider)` assertions

### Provider Registry (Task 24.2)
- `ProviderRegistry` class with `register()`, `all()`, `configured()`, `providers_for_type(IOCType)`, `provider_count_for_type(IOCType)`
- Thread safety: populated once at app startup, read-only during request handling
- Duplicate registration raises `ValueError`
- `providers_for_type()` returns only configured providers that support the given IOC type

### ConfigStore Multi-Provider (Task 24.3)
- Expand existing ConfigStore with `[providers]` INI section
- New methods: `get_provider_key(name)`, `set_provider_key(name, key)`, `all_provider_keys()`
- Existing `get_vt_api_key()` / `set_vt_api_key()` remain backward-compatible
- Keys stored with lowercase provider identifiers (e.g., "greynoise", "otx")

### Route Wiring (Task 24.4)
- Create `app/enrichment/setup.py` with `build_registry(allowed_hosts, config_store)` — single place for all provider registration
- Replace hardcoded adapter imports/instantiation in routes.py with registry
- Online mode check: "at least one configured provider" instead of "VT key present"
- Existing route tests must still pass — may need mock updates from patching individual adapters to patching registry/setup

### Dynamic Provider Counts (Task 24.5)
- Pass `provider_counts` dict from backend to frontend via `data-provider-counts` template attribute
- Replace hardcoded `IOC_PROVIDER_COUNTS` in TypeScript with `getProviderCounts()` function that reads from DOM
- Legacy fallback to hardcoded values if data attribute missing
- Update `enrichment.ts` to call dynamic function instead of importing static constant

### Claude's Discretion
- Error handling details within Provider protocol implementations
- Internal organization of registry test fixtures
- Whether to add `__repr__` or other convenience methods to Registry
- TypeScript build verification approach

</decisions>

<specifics>
## Specific Ideas

- Provider protocol file: `app/enrichment/provider.py`
- Registry file: `app/enrichment/registry.py`
- Setup builder file: `app/enrichment/setup.py`
- Test files: `tests/test_provider_protocol.py`, `tests/test_provider_registry.py`, `tests/test_registry_setup.py`
- ConfigStore section name: `_PROVIDERS_SECTION = "providers"`
- VT adapter: `name = "VirusTotal"`, `requires_api_key = True`, `is_configured()` checks `self._api_key`
- MB adapter: `name = "MalwareBazaar"`, `requires_api_key = False`, `is_configured()` always True
- TF adapter: `name = "ThreatFox"`, `requires_api_key = False`, `is_configured()` always True
- TypeScript function: `getProviderCounts()` reads from `.page-results[data-provider-counts]`

</specifics>

<deferred>
## Deferred Ideas

- Settings page dynamic provider cards (Phase 4 scope)
- Individual provider adapter implementations (Phases 25-26)
- Results UX unified summary cards (Phase 4)
- Orchestrator refactoring to use registry directly (stretch — routes handle it for now)

</deferred>

---

*Phase: 01-provider-registry-refactor*
*Context gathered: 2026-03-02 via PRD Express Path*
