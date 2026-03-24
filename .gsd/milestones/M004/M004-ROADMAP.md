# M004: Refactor & Optimize

**Vision:** Full-stack code consolidation — finish the M002 adapter hardening that didn't land on main, tighten routes and frontend, DRY up tests. No new features. Every test still passes.

## Success Criteria

- All 924+ tests pass with zero regressions after every slice
- No HTTP adapter contains inline `validate_endpoint`/`read_limited`/`requests.get`/`requests.post` — all use `safe_request()`
- Each HTTP adapter reduced by ~40% LOC — only URL construction, headers, response parsing, verdict logic remain
- Per-provider `requests.Session` injected and used for connection pooling
- `analyze()` reads `current_app.registry`, not `build_registry()` per request
- TypeScript strict mode clean, dead code removed
- CSS dead rules pruned, E2E tests confirm no visual regressions
- Adapter test files use shared fixtures, repetitive patterns extracted

## Key Risks / Unknowns

- Adapter-specific edge cases must survive `safe_request()` extraction — VT's `_map_http_error()`, ThreatMiner's body-level 404, AbuseIPDB's 429 pre-check
- Test mock migration from `patch("requests.get")` to `patch("requests.request")` across all adapter test files — URL assertion index shifts

## Proof Strategy

- Adapter edge cases → retire in S01 by proving all 924+ tests pass after converting each adapter, with specific attention to VT, ThreatMiner, and AbuseIPDB test suites
- Test mock migration → retire in S01 by converting mocks alongside each adapter conversion and running tests after each

## Verification Classes

- Contract verification: pytest full suite (924+ tests), TypeScript typecheck (`npx tsc --noEmit`), grep-based assertions for `safe_request` adoption
- Integration verification: E2E tests (Playwright) confirm enrichment flow and UI rendering
- Operational verification: none
- UAT / human verification: visual spot-check that results page and detail page render correctly after CSS cleanup

## Milestone Definition of Done

This milestone is complete only when all are true:

- All 924+ tests pass with zero regressions
- 12 HTTP adapters use `safe_request()` with per-provider `requests.Session`
- `analyze()` reads cached registry from `current_app.registry`
- Routes file is decomposed — no 90-line monolithic functions
- TypeScript strict-mode clean, no dead exports, no dead code
- CSS audited — dead rules removed, E2E tests confirm no visual regressions
- Adapter test files use shared fixtures where repetition was extracted
- Success criteria re-checked against running app

## Requirement Coverage

- Covers: R018, R019, R020, R021, R022, R023, R024, R025
- Partially covers: none
- Leaves for later: R010, R011
- Orphan risks: none

## Slices

- [x] **S01: Adapter HTTP consolidation + session pooling** `risk:high` `depends:[]`
  > After this: All 12 HTTP adapters use `safe_request()` with per-provider `Session`. Each adapter is ~40% shorter. 924+ tests pass.

- [x] **S02: Registry caching + routes decomposition** `risk:medium` `depends:[S01]`
  > After this: `analyze()` reads cached registry. Routes file is shorter and decomposed. Settings POST rebuilds registry. All tests pass.

- [x] **S03: Frontend tightening — TypeScript + CSS audit** `risk:low` `depends:[]`
  > After this: Dead code removed from TS modules. Dead CSS rules pruned. TypeScript strict-mode clean. E2E tests confirm no visual regressions.

- [x] **S04: Test DRY-up — shared adapter fixtures** `risk:low` `depends:[S01]`
  > After this: Shared test helpers extract repetitive mock/assert patterns. All tests still pass. Test files are shorter.

## Boundary Map

### S01 → S02

Produces:
- `http_safety.py` → `safe_request(method, url, session, headers, no_data_on_404, json)` — shared HTTP helper
- Each adapter → `self._session: requests.Session` attribute, used via `safe_request(session=self._session)`
- `setup.py` → `requests.Session()` created per adapter during registration
- All adapters use `from app.enrichment.http_safety import safe_request` (no more `validate_endpoint`, `read_limited`, `TIMEOUT` imports)

Consumes:
- nothing (first slice)

### S01 → S04

Produces:
- Adapter test mocks now use `patch("requests.request")` instead of `patch("requests.get")`
- URL assertion index: `call_args.args[1]` (not `args[0]`)
- `safe_request()` always passes `json=None` explicitly — test assertions must use `not call_kwargs.get("json")`

Consumes:
- nothing (first slice)

### S02 → (terminal)

Produces:
- `app.registry` cached on `create_app()` — `current_app.registry` available in request context
- `settings_post()` rebuilds registry on key change
- `analyze()` decomposed into helpers

Consumes from S01:
- Adapters accept `session` parameter — registry construction in `setup.py` creates Sessions

### S03 → (terminal, independent)

Produces:
- Tighter TypeScript modules — fewer exports, less dead code
- Smaller `input.css` — dead rules removed

Consumes:
- nothing (independent of S01/S02)

### S04 → (terminal)

Produces:
- `tests/conftest.py` or `tests/helpers.py` — shared adapter test fixtures and mock helpers
- Shorter adapter test files using shared patterns

Consumes from S01:
- New mock pattern (`patch("requests.request")`, arg index shifts) — fixtures must use the post-S01 mock pattern
