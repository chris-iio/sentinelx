# M007: Dead Code & Boilerplate Reduction

**Gathered:** 2026-03-27
**Status:** Ready for planning

## Project Description

SentinelX is a universal threat intelligence hub for SOC analysts — 15 enrichment providers, 1043 tests, 6 completed milestones. This milestone is a pure cleanup pass: eliminate dead code, consolidate duplicated HTTP boilerplate across adapters, trim bloated docstrings, and standardize test helpers.

## Why This Milestone

M005 planned `safe_request()` consolidation but the work never landed — the function doesn't exist in `http_safety.py` and all 12 HTTP adapters still inline identical ~25-line HTTP + exception chains. Adapter files are 40-46% docstrings, with SEC control descriptions copied verbatim in every file. Dead CSS from M001 persists. 23 of 33 test files don't use the shared test helpers that already exist.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Run `python3 -m pytest` and see all tests pass with fewer total LOC
- Read any adapter file and find only adapter-specific logic — no duplicated HTTP plumbing

### Entry point / environment

- Entry point: `python3 -m pytest` / `make build` / `wc -l`
- Environment: local dev
- Live dependencies involved: none

## Completion Class

- Contract complete means: all tests pass, `safe_request()` exists, grep confirms zero inline HTTP boilerplate in adapters
- Integration complete means: no behavior changes — same HTTP calls, same verdicts, same error handling
- Operational complete means: none (pure refactor)

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- All 1043+ tests pass
- `grep -c 'validate_endpoint\|read_limited\|requests.exceptions' app/enrichment/adapters/*.py` returns 0 for all HTTP adapters (consolidated into safe_request)
- Measurable net LOC reduction via `wc -l`

## Risks and Unknowns

- safe_request() must handle all 12 adapter variations (GET/POST, 404 pre-check, per-request headers, auth headers on session) — the M005 KNOWLEDGE.md entries document the API shape decisions
- Adapter tests that mock `adapter._session.get` must still work after migration — safe_request() must use session.get/post internally, not session.request()

## Existing Codebase / Prior Art

- `app/enrichment/http_safety.py` — existing SSRF validation and byte-limited reader (65 lines). safe_request() goes here.
- `app/enrichment/adapters/shodan.py` — representative HTTP adapter pattern (200 lines, 42% docstring)
- `tests/helpers.py` — existing shared mock factories (67 lines, used by 10/33 test files)
- `.gsd/KNOWLEDGE.md` — M005 entries document safe_request() API decisions (D039, D040, D041) and known gotchas

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- R026 — safe_request() in http_safety.py (reattempt — M005 never landed)
- R027 — All 12 HTTP adapters use safe_request() (reattempt)
- R036 — Shared safe_request() consolidation
- R037 — Adapter docstring trimming
- R038 — Dead CSS removal
- R039 — Test DRY-up with shared helpers
- R040 — All tests pass, zero behavior changes

## Scope

### In Scope

- Extract safe_request() into http_safety.py
- Migrate all 12 HTTP adapters to use safe_request()
- Trim adapter docstrings — remove duplicated SEC control text
- Remove dead CSS (consensus-badge, confirmed dead selectors)
- Migrate test files to use shared tests/helpers.py factories

### Out of Scope / Non-Goals

- New features or capabilities
- New adapters or providers
- Routes decomposition (routes.py is 488 lines but functional)
- Frontend refactoring beyond dead CSS removal
- Test coverage expansion (only DRY-up existing tests)

## Technical Constraints

- safe_request() must use session.get()/session.post() via getattr dispatch, NOT session.request() — existing test mocks depend on this (KNOWLEDGE.md)
- SSLError handler must appear before ConnectionError handler in the exception chain (D035 — correctness constraint, not style)
- DNS adapters (dns_lookup, asn_cymru) and WHOIS adapter are excluded from safe_request() — they don't use HTTP

## Integration Points

- None — pure internal refactor

## Open Questions

- None
