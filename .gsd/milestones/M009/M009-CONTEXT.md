# M009: Codebase Reduction

**Gathered:** 2026-03-29
**Status:** Ready for planning

## Project Description

SentinelX is a universal threat intelligence hub for SOC analysts. 15 enrichment provider adapters, 1,075 tests, ~26K total LOC across app/ and tests/. Eight milestones of feature work and cleanup have been completed. The codebase has structural duplication that prior cleanup milestones (M005, M007) didn't address — the adapter skeleton itself and the adapter test contract tests are the largest remaining surfaces.

## Why This Milestone

Prior milestones consolidated HTTP boilerplate into `safe_request()` (M007) and extracted test helpers (M007/S03), but the structural skeleton of each adapter — `__init__`, session setup, `supported_types` guard, `is_configured`, the `safe_request()` dispatch call, and the result-check boilerplate — is still repeated 12 times. Similarly, every adapter test file independently tests the same shared contract (protocol conformance, unsupported types, timeout, connection errors, SSL errors, allowed_hosts). This is the next layer of duplication to collapse.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Run the full test suite and see identical pass/fail behavior with fewer total tests (contract tests consolidated)
- Read any adapter file and see only provider-specific logic — no boilerplate
- See a measurably smaller codebase (LOC reduction in both app/ and tests/)

### Entry point / environment

- Entry point: `make test`, `make typecheck`, `make js`, `make css`
- Environment: local dev
- Live dependencies involved: none

## Completion Class

- Contract complete means: all tests pass, `make typecheck` clean, `make js` and `make css` build successfully
- Integration complete means: full test suite (unit + E2E) passes with zero behavior changes
- Operational complete means: none — no runtime behavior changes

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- All 1,075+ existing tests pass (count may decrease from consolidated tests, but zero failures)
- Net LOC reduction in both `app/` and `tests/`
- `make typecheck && make js && make css` all pass
- Same verdicts for same inputs — no adapter behavior regressions

## Risks and Unknowns

- ThreatMiner adapter has multi-endpoint lookup (3 endpoint types, domain merges 2 calls) — may not fit cleanly into a simple base class template
- VirusTotal has complex response parsing with endpoint map and base64 URL encoding — needs per-adapter flexibility in URL construction
- POST adapters (malwarebazaar, threatfox, urlhaus) pass different body formats (json_payload vs data) — base class must accommodate both
- Frontend function extraction: per KNOWLEDGE.md, `initExportButton` has closure dependencies on module-private `allResults` — may need state passed as parameter

## Existing Codebase / Prior Art

- `app/enrichment/http_safety.py` — `safe_request()` is the shared HTTP path all 12 HTTP adapters already use
- `app/enrichment/provider.py` — `Provider` protocol (structural typing, runtime_checkable) — the base class must still satisfy this
- `app/enrichment/adapters/*.py` — 15 adapters (12 HTTP, 2 DNS, 1 WHOIS)
- `app/enrichment/setup.py` — `build_registry()` constructs all adapters at startup
- `tests/helpers.py` — shared test factories (make_mock_response, make_*_ioc, mock_adapter_session)
- `app/static/src/ts/modules/enrichment.ts` — 582 LOC, contains functions duplicated in history.ts
- `app/static/src/ts/modules/history.ts` — 355 LOC, duplicates injectDetailLink, initExportButton, sortDetailRows
- `app/static/src/input.css` — 2,069 LOC, 8 milestones of accumulated CSS

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R041 — BaseHTTPAdapter absorbs shared adapter skeleton
- R042 — All 12 HTTP adapters migrated to BaseHTTPAdapter
- R043 — Non-HTTP adapters unchanged
- R044 — Shared parametrized test suite for adapter contract
- R045 — Per-adapter test files contain only verdict and parsing tests
- R046 — Dead CSS rules removed after audit
- R047 — Duplicated TypeScript functions extracted into shared module
- R048 — All existing tests pass with zero behavior changes
- R049 — Net LOC reduction across app/ and tests/

## Scope

### In Scope

- BaseHTTPAdapter abstract base class in `app/enrichment/adapters/base.py`
- Migration of all 12 HTTP adapters to subclass BaseHTTPAdapter
- Shared parametrized test suite for adapter protocol/error contract
- Removal of duplicate contract tests from per-adapter test files
- Dead CSS audit and removal
- Frontend TypeScript function dedup (enrichment.ts / history.ts)

### Out of Scope / Non-Goals

- No behavior changes to any adapter — same HTTP calls, same verdicts, same error handling
- No new features, providers, or UI changes
- No changes to non-HTTP adapters (dns_lookup, asn_cymru, whois_lookup) beyond including them in the shared contract test parametrization
- No changes to the Provider protocol itself

## Technical Constraints

- BaseHTTPAdapter must satisfy the existing `Provider` protocol (runtime_checkable isinstance check in ProviderRegistry)
- Adapter `__init__` signatures vary: some take `api_key + allowed_hosts`, others take only `allowed_hosts` — base class must handle both
- `setup.py` `build_registry()` constructs adapters with specific signatures — these constructor calls must still work
- Three adapters use POST (malwarebazaar, threatfox, urlhaus) with different body formats — base class must not assume GET-only
- ThreatMiner makes multiple API calls per lookup — base class `lookup()` template must allow override

## Integration Points

- `app/enrichment/setup.py` — constructor calls change if `__init__` signature changes
- `app/enrichment/orchestrator.py` — calls `adapter.lookup()` — no change expected
- `app/enrichment/provider.py` — Provider protocol must still be satisfied
- `tests/helpers.py` — `mock_adapter_session()` must work with base class

## Open Questions

- Whether ThreatMiner should subclass BaseHTTPAdapter with a fully overridden `lookup()`, or stay standalone — decide during S01 when the base class shape is clear
- Exact CSS dead-rule count — need to cross-reference at audit time
- Whether `initExportButton` can be extracted given its closure dependency on `allResults` — verify during S04
