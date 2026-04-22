# S03: Fast default proof loop and deterministic expensive lane

**Goal:** Make the repo's default proof loop fast and explicit, and keep the slower browser lane deterministic by preventing mocked online E2E tests from launching real background enrichment jobs.
**Demo:** A contributor can run a clearly documented fast verification lane for touched optimization work and a separate slower lane for deeper confidence, without accidental real backoff sleeps or ambiguous proof expectations.

## Must-Haves

- Add a named default verification lane that runs non-E2E pytest, Vitest, TypeScript typecheck, and the frontend build through one repo-native command surface.
- Add a separate deeper verification lane for browser evidence and document when contributors must run it for live enrichment/results-surface changes.
- Keep the expensive lane deterministic by ensuring mocked online E2E tests do not launch real background enrichment work or emit interpreter-shutdown executor noise.
- Preserve continuity coverage for R008, R009, R010, R019, and R040 while making proof expectations explicit.

## Threat Surface

- **Abuse**: The main regression risk is silently weakening the required proof bar by documenting a fast lane as sufficient for live enrichment changes, or accidentally letting test-only orchestration stubs leak into production paths.
- **Data exposure**: No new secrets or analyst data should be exposed; the E2E seam must stay test-only and preserve current security headers/CSRF behavior on the real Flask surface.
- **Input trust**: Analyst text still flows through the existing `/analyze` route and browser UI; the deterministic E2E seam must not bypass request validation or change the production polling contract.

## Requirement Impact

- **Requirements touched**: R008, R009, R010, R019, R040.
- **Re-verify**: non-E2E regression coverage, browser enrichment rendering, cursor-polling continuity, security-header continuity in E2E, and the absence of accidental real background-enrichment work in mocked online tests.
- **Decisions revisited**: D050, D052, D054.

## Proof Level

- This slice proves: integration
- Real runtime required: yes
- Human/UAT required: no

## Verification

- `make verify-fast` runs the default lane: `python3 -m pytest -q -m 'not e2e'`, `npx vitest run`, `npx tsc --noEmit`, and `make build`.
- `make verify-deep` runs the expensive browser lane: `python3 -m pytest -q tests/e2e`, including assertions in `tests/e2e/test_results_page.py` and `tests/e2e/test_url_e2e.py` that the mocked online path stays deterministic.
- `make verify` composes the fast and deep lanes so contributors have one unambiguous "full confidence" command.

## Observability / Diagnostics

- Runtime signals: named Make targets (`verify-fast`, `verify-deep`, `verify`) and deterministic mocked E2E job metadata/DOM assertions.
- Inspection surfaces: `Makefile`, `README.md`, `tests/e2e/conftest.py`, and browser assertions in `tests/e2e/test_results_page.py` / `tests/e2e/test_url_e2e.py`.
- Failure visibility: the expensive lane should fail via explicit Playwright/pytest assertions, not background-thread shutdown traces or accidental real enrichment side effects.
- Redaction constraints: keep provider keys, stored results, and analyst input handling unchanged; no secrets move into docs or client-visible test fixtures.

## Integration Closure

- Upstream surfaces consumed: S01's additive live polling contract, the existing pytest `e2e` marker in `pyproject.toml`, current frontend unit/typecheck/build commands, and the real Flask results-page rendering contract used by E2E.
- New wiring introduced in this slice: repo-native Make targets for fast/deep/full proof plus a test-only E2E fixture seam that returns deterministic online-mode job metadata without scheduling background enrichment work.
- What remains before the milestone is truly usable end-to-end: nothing for this seam once the named lanes are documented, the browser lane is deterministic, and both verification commands pass.

## Tasks

- [ ] **T01: Codify fast and deep verification lanes in the repo-native command surface** `est:0.5d`
  - Why: S03 only matters if contributors can tell which proof loop is routine, which one is deeper, and what each lane actually proves.
  - Files: `Makefile`, `README.md`
  - Do: Add `verify-fast`, `verify-deep`, and `verify` Make targets using the already-real commands in the repo; keep the default lane fast by excluding E2E pytest, keep the browser lane separate, and document exactly when optimization/live-enrichment work must run the deeper lane.
  - Verify: `make verify-fast`
  - Done when: `Makefile` exposes the named lanes, `README.md` explains their purpose and trigger conditions, and the default lane runs through one command.

- [ ] **T02: Stub online E2E orchestration so the deep lane stays deterministic** `est:0.75d`
  - Why: The expensive lane is currently slower than necessary and slightly noisy because mocked online browser tests still launch real background enrichment jobs.
  - Files: `tests/e2e/conftest.py`, `tests/e2e/test_results_page.py`, `tests/e2e/test_url_e2e.py`
  - Do: Patch the E2E live-server seam so mocked `/enrichment/status/**` tests get deterministic job ids/provider metadata without submitting real background work, add explicit assertions proving the mocked-online seam is active, and keep the real Flask/browser/security surface intact.
  - Verify: `make verify-deep`
  - Done when: the full E2E lane passes without interpreter-shutdown executor noise and the online mocked tests assert against deterministic lane behavior instead of implicitly trusting it.

## Files Likely Touched

- `Makefile`
- `README.md`
- `tests/e2e/conftest.py`
- `tests/e2e/test_results_page.py`
- `tests/e2e/test_url_e2e.py`
