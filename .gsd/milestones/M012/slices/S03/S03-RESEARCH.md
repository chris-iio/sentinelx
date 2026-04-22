# S03 Research — Fast default proof loop and deterministic expensive lane

## Summary

This slice is **targeted research**, not deep architecture work. SentinelX already has a natural verification split in the repo:

- **Fast/default lane:** Python tests excluding E2E, Vitest, TypeScript typecheck, and build
- **Expensive lane:** Playwright E2E, especially online-mode enrichment-surface coverage

The fast lane is already credible and cheap with existing commands; the expensive lane is the real problem. It is slow by design, but today it is also slightly noisy and less deterministic than it should be because online E2E helpers mock only `/enrichment/status/**` while the live Flask app still launches real background enrichment jobs through `_setup_orchestrator()`.

## Requirement Targeting

### Primary requirement ownership
- **R040** — existing test coverage remains a continuity safety net for refactoring-oriented work.

### Supporting continuity requirements this slice must preserve through proof-lane design
- **R008** — live analyst workflow behavior still needs an explicit deeper proof lane.
- **R009** — security posture must stay in the default/deep verification contract, not become optional.
- **R010** — debounced frontend behavior and polling efficiency need coverage in the right lane.
- **R014 / R015 / R018 / R019 / R020** — orchestrator concurrency, 429 backoff, semaphore behavior, cursor polling, and persistent sessions must remain proven without forcing every routine change through the full browser lane.

## Skill Notes

Two installed skills directly inform this slice:

- **`test` skill:** detect the project’s actual framework commands before proposing a new proof loop. That matters here because SentinelX has no package.json test scripts; the real command surface is `pytest`, `npx vitest run`, `npx tsc --noEmit`, and `make build`.
- **`verify-before-complete` skill:** evidence must be fresh and lane claims must map to real commands. For this slice, that means the lane contract should name exact commands, not vague labels like “quick checks” or “full confidence”.

## Implementation Landscape

### Command surface that already exists

- `pyproject.toml`
  - defines pytest marker `e2e`
  - this is the clean existing seam for splitting Python verification
- `Makefile`
  - current build/typecheck commands are `make build` and `npx tsc --noEmit`
  - there are **no** verification aggregation targets yet
- `vitest.config.ts`
  - TS unit tests are already isolated to `app/static/src/ts/**/*.test.ts`
- `package.json`
  - no `scripts.test`; adding npm wrapper commands is possible but not the most repo-native surface

### Files that matter for the expensive-lane determinism problem

- `tests/e2e/conftest.py`
  - starts a real Flask server with `create_app({... TESTING: False, WTF_CSRF_ENABLED: True ...})`
  - auto-marks E2E tests with `pytest.mark.e2e`
  - provides `setup_enrichment_route_mock(page, ...)`, which mocks only browser polling requests
- `tests/e2e/test_results_page.py`
  - `_navigate_online_with_mock()` registers the poll-route mock, then submits the real `/analyze` form in `online` mode
  - waits for `.ioc-summary-row`, proving the frontend consumed the mocked status payload
- `tests/e2e/test_url_e2e.py`
  - same pattern for URL-specific online enrichment tests
- `tests/e2e/pages/index_page.py`
  - `extract_iocs(..., mode="online")` just submits the real form; it does not stub backend job launch
- `app/routes/analysis.py`
  - online mode always calls `_setup_orchestrator(...)` if `registry.configured()` is non-empty
- `app/routes/_helpers.py`
  - `_setup_orchestrator()` creates a real `EnrichmentOrchestrator` and submits background work to module-level `_enrichment_pool`
- `app/enrichment/setup.py`
  - registers several **zero-auth providers** unconditionally (Hashlookup, IP Context, DNS, crt.sh, ThreatMiner, ASN Cymru, WHOIS)
  - therefore the E2E live app has configured providers even with no API keys

### Existing deterministic patterns worth preserving

- `tests/test_orchestrator.py`
  - backoff tests patch `app.enrichment.orchestrator.time.sleep`, so 429 behavior is already proven without real waiting
- `tests/e2e/pages/results_page.py`
  - `search()` waits 150ms after fill because `filter.ts` debounces at 100ms
  - good example of explicit async proof instead of flaky timing assumptions
- S01 compatibility wrappers (`tests/test_routes_helpers.py`, `tests/test_api_enrichment.py`, `tests/test_analysis_page.py`)
  - make plan-named backend checks callable without moving canonical ownership back out of `tests/test_routes.py` / `tests/test_api.py`

## Measurements

Fresh measurements in this worktree:

- `python3 -m pytest -q -m 'not e2e' --durations=20`
  - **952 passed, 113 deselected in 3.41s**
  - slowest non-E2E tests are ~0.02s–0.05s; no meaningful long tail
- `python3 -m pytest -q tests/e2e --durations=20`
  - **113 passed in 42.57s**
  - dominant cost is Playwright/browser interaction; top tests are ~1.4s–2.3s each
- `python3 -m pytest -q --durations=20`
  - **1065 passed in 44.80s**
  - almost all added wall time vs non-E2E comes from the browser suite
- `npx tsc --noEmit`
  - **0.72s**
- `npx vitest run`
  - **68 passed in 1.21s real time**
- `make build`
  - **1.36s**
- Combined likely fast/default lane:
  - `python3 -m pytest -q -m 'not e2e' && npx vitest run && npx tsc --noEmit && make build`
  - **6.08s real time**

## Findings

### 1) The repo already supports an honest fast lane

The split does **not** require new pytest markers or a new framework. `pyproject.toml` already marks browser tests as `e2e`, so the default Python lane can be `pytest -m 'not e2e'` immediately. Combined with existing Vitest/typecheck/build commands, the current fast lane is about 6 seconds and covers:

- backend/unit/integration Python behavior
- orchestrator/backoff logic (with patched sleeps)
- backend/frontend status-contract tests added in S01
- TS unit behavior
- type safety and bundle generation

### 2) The expensive lane is mostly Playwright, not Python generally

The gap between `pytest -m 'not e2e'` (3.41s) and full `pytest` (44.80s) is almost entirely the browser suite. That means the right separation is **fast lane vs browser lane**, not “small pytest vs large pytest”.

### 3) Real backoff sleeps are already avoided in the default lane

The risky backoff path lives in `app/enrichment/orchestrator.py`, but `tests/test_orchestrator.py` patches `app.enrichment.orchestrator.time.sleep` in the 429/backoff tests. The default Python lane therefore does **not** currently incur real 15s/30s backoff delays from those unit tests.

### 4) The current expensive lane is slower than necessary and slightly nondeterministic

Both `tests/e2e/test_results_page.py` and `tests/e2e/test_url_e2e.py` submit the real online form and only mock `/enrichment/status/**`. Because `app/enrichment/setup.py` always registers zero-auth providers, `app/routes/analysis.py` sees a non-empty configured registry and `_setup_orchestrator()` submits real background enrichment work.

Observed symptom during fresh runs:

- E2E-only and full-suite runs both ended with:
  - `RuntimeError: cannot schedule new futures after interpreter shutdown`
  - logged from `app/enrichment/orchestrator.py` via the background enrichment path

High-confidence code-path explanation:

- browser test submits `/analyze` in online mode
- Flask route calls `_setup_orchestrator()`
- helper submits background work to `_enrichment_pool`
- browser poll is mocked, so UI assertions pass without waiting for real backend enrichment
- at teardown/interpreter shutdown, in-flight background work can still try to schedule futures or continue logging

This does not fail the suite today, but it weakens the claim that the expensive lane is deterministic and self-explanatory.

### 5) The lane contract is currently implicit and scattered

Right now the commands exist but are not framed as:

- what every routine touched-area change should run
- what optimization work must run before claiming deeper confidence
- when the expensive lane is required
- what evidence each lane provides and what it does **not** provide

Without that contract, future work will keep oscillating between over-testing every small change and under-specifying proof.

## Recommendation

Plan this slice as **one lane-definition task plus one expensive-lane hygiene task**.

### Recommended shape

1. **Codify a default fast lane using existing commands**
   - likely surface: `Makefile` targets, because this repo already uses Make for build tooling and has no npm scripts to preserve
   - preferred contract:
     - Python fast: `python3 -m pytest -q -m 'not e2e'`
     - TS unit: `npx vitest run`
     - typecheck: `npx tsc --noEmit`
     - asset build: `make build`
   - aggregate target should be explicit and boring, e.g. a `verify-fast` / `proof-fast` style target

2. **Codify a separate deeper browser lane**
   - likely surface: another Make target and contributor-facing docs in `README.md`
   - should explicitly say this is the analyst-workflow lane and is slower by design
   - candidate command: `python3 -m pytest -q tests/e2e`
   - if the slice wants one “everything” target, it should compose fast + browser rather than re-explaining each command everywhere

3. **Make the expensive lane deterministic enough to trust**
   - highest-leverage seam is `tests/e2e/conftest.py` plus the online helper paths in `tests/e2e/test_results_page.py` and `tests/e2e/test_url_e2e.py`
   - goal: keep the real browser/UI path, but stop launching real background enrichment jobs when the test is already supplying a canned status payload
   - preferred direction: patch or replace `_setup_orchestrator()` for the E2E live server session so online-mode UI tests still get a job id and provider metadata without real background submission
   - avoid touching core app behavior unless the fixture-level patch cannot provide the required shape

### Why this order

The lane contract is the slice’s main deliverable. But if the expensive lane keeps printing interpreter-shutdown traces, the docs/targets will still feel ambiguous. Tighten the E2E helper/session seam in the same slice so “fast” and “deep” both mean something precise.

## Natural Task Seams

### Task seam 1 — verification contract + command surface
Files likely touched:
- `Makefile`
- `README.md`
- possibly a small repo-local doc if README is intentionally slim

Deliverable:
- named fast/deep verification targets with exact commands
- written guidance on when each lane is required

### Task seam 2 — deterministic online E2E helper path
Files likely touched:
- `tests/e2e/conftest.py`
- `tests/e2e/test_results_page.py`
- `tests/e2e/test_url_e2e.py`
- possibly `tests/e2e/pages/index_page.py`
- only if necessary: a very small seam in `app/routes/analysis.py` or `app/routes/_helpers.py`

Deliverable:
- online E2E enrichment-surface tests no longer start uncontrolled real background enrichment when they are already using mocked status responses
- expensive lane stops emitting misleading shutdown noise

## Risks / Unknowns

- I did **not** fully instrument the E2E shutdown race beyond code-path reasoning plus repeated observed logs. The likely root cause is strong, but planner/executor should confirm with one focused reproduction before changing fixture behavior.
- `README.md` in this repo is not currently the active command surface for testing; if the user prefers a thinner README, a small project-local contributor note may be better. The command target itself still belongs in `Makefile`.
- The slice should resist inventing more granularity than needed (for example, “medium” lanes or many file-scoped wrappers). The current evidence supports **fast vs deep**, nothing fancier.

## Verification Plan

### For the fast-lane contract
Run fresh after any command-surface change:

- `python3 -m pytest -q -m 'not e2e'`
- `npx vitest run`
- `npx tsc --noEmit`
- `make build`

Optional aggregate proof if a new Make target is added:

- `make verify-fast` (or whatever name lands)

### For the expensive-lane contract
Run fresh after E2E helper changes:

- `python3 -m pytest -q tests/e2e`

Success bar:
- browser tests still pass
- no new outbound-provider dependence is introduced
- interpreter-shutdown enrichment trace is gone, or at minimum reduced to a clearly understood and documented residual if total elimination proves impractical

### For final slice-level proof
If the slice lands both target definitions and E2E determinism cleanup, the strongest proof is:

- fast lane aggregate target (or the four underlying commands)
- `python3 -m pytest -q tests/e2e`

## Skill Discovery (suggest)

Installed skills already cover most of this slice:
- `test`
- `verify-before-complete`

External skills that looked relevant but are **not required** for this slice:
- `currents-dev/playwright-best-practices-skill@playwright-best-practices` — highest-signal external Playwright skill found (`npx skills add currents-dev/playwright-best-practices-skill@playwright-best-practices`)
- `microsoft/playwright-cli@playwright-cli` — potentially useful if future browser-proof work expands beyond the current pytest/Playwright setup (`npx skills add microsoft/playwright-cli@playwright-cli`)

Flask-specific external skills exist, but the repo’s current Flask work here is simple and the installed `test` skill is already the better fit for this slice.
