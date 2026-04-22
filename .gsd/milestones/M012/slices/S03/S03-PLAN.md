# S03: Fast default proof loop and deterministic expensive lane

**Goal:** Make the repo's default proof loop fast and explicit, and keep the slower browser lane deterministic by preventing mocked online E2E tests from launching real background enrichment jobs.
**Demo:** A contributor can run a clearly documented fast verification lane for touched optimization work and a separate slower lane for deeper confidence, without accidental real backoff sleeps or ambiguous proof expectations.

## Must-Haves

- Add a named default verification lane that runs non-E2E pytest, Vitest, TypeScript typecheck, and the frontend build through one repo-native command surface.
- Add a separate deeper verification lane for browser evidence and document when contributors must run it for live enrichment/results-surface changes.
- Keep the expensive lane deterministic by ensuring mocked online E2E tests do not launch real background enrichment work or emit interpreter-shutdown executor noise.
- Preserve continuity coverage for R008, R009, R010, R019, and R040 while making proof expectations explicit.

## Proof Level

- This slice proves: - This slice proves: integration
- Real runtime required: yes (for the browser lane)
- Human/UAT required: no

## Integration Closure

Makefile targets, contributor-facing documentation, and the E2E live-server fixture agree on one fast default lane and one slower browser lane; online mocked browser tests still exercise the real Flask + browser surface while bypassing uncontrolled background job submission.

## Verification

- Named verification targets make the expected proof lane visible in contributor workflows, and a deterministic mocked browser seam turns expensive-lane failures into direct test/assertion output instead of background-thread shutdown noise.

## Tasks

- [x] **T01: Codify fast and deep verification lanes in the repo-native command surface** `est:0.5d`
  Add explicit Make targets for the fast/default lane and the deeper browser lane, then document when each lane is required so optimization work has unambiguous proof expectations tied to existing commands rather than ad-hoc tribal knowledge.
  - Files: `Makefile`, `README.md`
  - Verify: make verify-fast

- [x] **T02: Stub online E2E orchestration so the deep lane stays deterministic** `est:0.75d`
  Patch the E2E live-server/test helper seam so online tests that already mock `/enrichment/status/**` stop launching real background enrichment jobs, then add browser assertions proving the deterministic seam is active and run the full expensive lane without shutdown-noise ambiguity.
  - Files: `tests/e2e/conftest.py`, `tests/e2e/test_results_page.py`, `tests/e2e/test_url_e2e.py`
  - Verify: make verify-deep

## Files Likely Touched

- Makefile
- README.md
- tests/e2e/conftest.py
- tests/e2e/test_results_page.py
- tests/e2e/test_url_e2e.py
