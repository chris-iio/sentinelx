# M011: Lean & Fast

**Gathered:** 2026-04-04
**Status:** Ready for planning

## Project Description

SentinelX is a universal threat intelligence hub for SOC analysts. It extracts, normalizes, classifies, and enriches IOCs against 15 providers in parallel. After 10 milestones the codebase is 24K lines (9.3K app, 14.9K tests) with 1061 tests and a mature adapter architecture (BaseHTTPAdapter + contract tests). The codebase is functionally complete — this milestone is purely about reduction and speed.

## Why This Milestone

10 milestones of iterative development accumulated:
- **Verbose adapter docstrings:** 1,176 lines of docstrings in 16 adapter files (42% of adapter code). Module-level and class-level docstrings repeat API endpoint URLs, HTTP status code tables, verdict priority lists, and parameter walkthroughs that the code itself expresses.
- **Granular per-field tests:** ~72 one-assertion-per-field tests (test_raw_stats_has_asn_key, test_detection_count_always_zero, etc.) across 7 adapter test files. Each is ~5-8 lines for a single assert. Can be collapsed into single response-shape tests.
- **Dead CSS:** 2,006 lines in input.css accumulated over 10 milestones. Some classes (e.g. settings-provider-card) appear to have no template references.
- **Slow orchestrator tests:** 7 tests account for ~6.2s of the 9s unit suite due to time.sleep-based timing.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Run the same app with identical behavior — no visible changes
- Navigate adapter files ~40% faster (less scrolling past docstrings)
- Get test results in ~3-4s instead of ~9s for unit tests

### Entry point / environment

- Entry point: `pytest` and code editor
- Environment: local dev
- Live dependencies involved: none

## Completion Class

- Contract complete means: all tests pass, LOC reduction ≥ 1,000, unit tests < 5s
- Integration complete means: `make typecheck`, `make js`, `make css` all clean
- Operational complete means: none

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- All tests pass (count may decrease from consolidation)
- Net LOC reduction ≥ 1,000 across app/ and tests/
- Unit test suite runs in < 5s
- Zero behavior changes — same verdicts, same UI, same enrichment flow

## Risks and Unknowns

- **Docstring trim may remove genuinely useful edge case documentation** — Mitigate by keeping any gotcha that would surprise a reader (e.g. ThreatMiner always returns HTTP 200, python-whois datetime polymorphism).
- **Test consolidation may hide coverage gaps** — When collapsing 8 single-field asserts into 1 multi-assert test, a failure message becomes less specific. Mitigate by using descriptive assert messages.
- **Dead CSS audit false positives** — Classes referenced only via JS string construction (e.g. `verdict-badge--${verdict}`) won't appear in a literal grep. Must account for dynamic class patterns.

## Existing Codebase / Prior Art

- `app/enrichment/adapters/*.py` — 16 adapter files, 2,816 total lines, 1,176 docstring lines
- `app/enrichment/adapters/base.py` — BaseHTTPAdapter (161 lines) — docstring here is the canonical reference, per-adapter docs should defer to it
- `tests/test_adapter_contract.py` — 13 parametrized contract tests covering protocol conformance (588 lines)
- `tests/test_orchestrator.py` — 27 tests, 839 lines, 7 slow tests using time.sleep timing
- `app/static/src/input.css` — 2,006 lines of Tailwind + custom CSS
- `tests/helpers.py` — shared test factories (make_mock_response, make_ipv4_ioc, etc.)

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R056 — Adapter docstring trim (M011/S01)
- R057 — Per-adapter test consolidation (M011/S02)
- R058 — Dead CSS removal (M011/S03)
- R059 — Orchestrator test speedup (M011/S03)
- R060 — All tests pass, zero behavior changes (M011/all)

## Scope

### In Scope

- Trim adapter module and class docstrings to one-liner + edge cases
- Consolidate granular per-field test assertions into response-shape tests
- Full dead CSS audit and removal
- Rewrite orchestrator sleep-based tests with synchronization primitives
- Verify all tests pass and builds clean

### Out of Scope / Non-Goals

- New features or UI changes
- Adapter logic changes
- Test framework changes
- Architecture changes
- row-factory.ts PROVIDER_CONTEXT_FIELDS compression (84 lines, not worth a slice)

## Technical Constraints

- Docstring trim must preserve genuinely non-obvious gotchas (see KNOWLEDGE.md entries)
- CSS audit must account for dynamic class construction in TypeScript (e.g. `verdict-badge--${verdict}`, `filter-pill--${type}`)
- Tailwind safelist in tailwind.config.js must be checked — some classes exist only there
- Test consolidation must maintain same assertion coverage — every field still asserted, just grouped

## Integration Points

- None — this is entirely internal refactoring

## Open Questions

- None — scope is well-defined from investigation
