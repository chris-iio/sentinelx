# M004: Refactor & Optimize

**Gathered:** 2026-03-24
**Status:** Ready for planning

## Project Description

SentinelX is a threat intelligence hub for SOC analysts — paste text, extract IOCs, enrich against 14 providers in parallel. Three milestones shipped: results page redesign (M001), results page rework (M002), system efficiency & completeness (M003). The codebase is ~4,923 LOC Python, ~2,459 LOC TypeScript, ~635 LOC templates, 924 tests on main.

## Why This Milestone

The M002 adapter hardening plan (safe_request extraction, session pooling, cached registry) was designed and validated in a worktree but the code on main still has every adapter inlining HTTP boilerplate — `validate_endpoint()` → `requests.get()` → `read_limited()` repeated 12 times. The `analyze()` route still calls `build_registry()` per request instead of reading a cached registry. After three milestones of feature work, the codebase needs structural consolidation before adding more capabilities.

This is a "finish it properly" milestone — no new features, no new providers. Clean the code, consolidate the patterns, tighten the stack.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Use SentinelX exactly as before — all existing functionality preserved
- Observe faster enrichment due to connection pooling and cached registry (behavioral improvement)

### Entry point / environment

- Entry point: `python run.py` / browser at localhost:5000
- Environment: local dev
- Live dependencies involved: none (all changes are internal refactoring)

## Completion Class

- Contract complete means: 924+ tests pass, adapter LOC reduced ~40%, no inline HTTP boilerplate
- Integration complete means: E2E tests pass — enrichment flow works end-to-end
- Operational complete means: none — no new operational surface

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- All 924+ tests pass with zero regressions after every slice
- No adapter file contains inline `validate_endpoint`/`read_limited`/`requests.get`/`requests.post` calls
- `analyze()` reads `current_app.registry`, not `build_registry()` per request
- TypeScript strict mode clean, no dead exports
- E2E tests pass — no visual regressions from CSS cleanup

## Risks and Unknowns

- **Adapter-specific edge cases** — VT has `_map_http_error()` for 429/401/403 mapping, ThreatMiner uses body-level `status_code == "404"` (HTTP always returns 200), AbuseIPDB pre-checks 429 before `raise_for_status()`. These must all be preserved through the `safe_request()` extraction.
- **Test mock migration** — Tests currently mock `requests.get`/`requests.post`. After switching to `safe_request()` which uses `requests.request()`, mocks must change to `patch("requests.request")`. URL assertion indexes shift (arg[0] → arg[1]).
- **CSS dead rule detection** — No automated tool to detect dead CSS against Jinja templates + TypeScript DOM creation. Manual audit required.

## Existing Codebase / Prior Art

- `app/enrichment/http_safety.py` — Already has `validate_endpoint()` and `read_limited()`. `safe_request()` will be added here.
- `app/enrichment/adapters/*.py` — 12 HTTP adapters, each ~170-350 LOC with ~25-35 lines of identical HTTP boilerplate
- `app/enrichment/setup.py` — Adapter registration factory. Session creation will be added here.
- `app/routes.py` — 373 LOC, monolithic `analyze()` at 90 lines
- `app/enrichment/orchestrator.py` — 297 LOC, already has per-provider semaphores and 429 backoff
- `app/static/src/ts/modules/enrichment.ts` — 576 LOC, largest TS module
- `app/static/src/ts/modules/row-factory.ts` — 561 LOC
- `app/static/src/input.css` — 1,902 lines

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R018 — Adapter HTTP boilerplate extraction (primary target)
- R019 — Per-provider session pooling
- R020 — Registry caching in hot path
- R021 — Routes decomposition
- R022 — TypeScript tightening
- R023 — CSS dead rule cleanup
- R024 — Test DRY-up
- R025 — Zero regression constraint

## Scope

### In Scope

- `safe_request()` extraction into `http_safety.py`
- Per-provider `requests.Session` creation and injection
- Registry caching in `create_app()` with rebuild on settings POST
- `analyze()` decomposition and routes cleanup
- TypeScript dead code removal and module tightening
- CSS dead rule audit and pruning
- Adapter test fixture extraction and DRY-up
- Redundant SEC-XX docstring removal from adapters

### Out of Scope / Non-Goals

- New providers or IOC types
- New UI features or pages
- Template changes beyond what CSS cleanup requires
- Orchestrator architectural changes (semaphore model, backoff logic stays as-is)
- Profiling or benchmarking (deferred: R010)

## Technical Constraints

- Python 3.10+ (match/case not available — 3.10 minimum, not 3.11)
- All 12 HTTP adapters use the Provider Protocol — no base class. `safe_request()` is a shared function, not a method.
- `requests.Session` is thread-safe for concurrent reads but not concurrent writes — per-provider sessions with per-provider semaphores are safe
- Test mocks will need to change from `patch("requests.get")` to `patch("requests.request")` per KNOWLEDGE.md
- URL assertion indexes shift: `call_args.args[0]` → `call_args.args[1]` per KNOWLEDGE.md

## Integration Points

- None — purely internal refactoring. No external service changes.

## Open Questions

- None — scope is well-defined from prior M002 planning and current codebase investigation.
