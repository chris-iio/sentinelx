# S05 Research — Validation evidence closure

## Summary

S05 is a **targeted artifact-closure slice**, not a new product/code slice.

The current M012 code and tests already cover most of the continuity story; the remaining failure is in the **closeout stitching**:

- `.gsd/milestones/M012/M012-VALIDATION.md` is **missing**.
- Slice-local assessment coverage is incomplete:
  - `S01-ASSESSMENT.md` — missing
  - `S02-ASSESSMENT.md` — missing
  - `S03-ASSESSMENT.md` — missing
  - `S04-ASSESSMENT.md` — present
- `S04-ASSESSMENT.md` already documents the exact validation gaps the first pass found: **R020 lacks explicit milestone-level proof, R009/R014/R015/R018 are only partially evidenced in slice summaries, only S04 has a slice-local assessment artifact, and the S04 routes/helpers ↔ persistence boundary is not tied into a concrete milestone closeout handoff**.

The important surprise is that `.gsd/REQUIREMENTS.md` already contains much of the missing milestone-level proof text:

- `R009` proof is already written at `.gsd/REQUIREMENTS.md` around the M012 traceability rows.
- `R014`, `R015`, `R018`, `R020`, and `R022` already have explicit proof rows.
- `R008`, `R010`, `R019`, and `R040` are already clearly advanced/validated in the M012 slice summaries.

So S05 should **prefer artifact creation + fresh evidence capture + canonical validation write** over any app/test refactor. The current auto-mode failure is file-based: the expected validation artifact was not written. The last task in this slice must call `gsd_validate_milestone` so `.gsd/milestones/M012/M012-VALIDATION.md` exists on disk.

## Requirements This Slice Owns / Supports

### Primary closure targets

S05 owns milestone-closeout proof for the roadmap continuity set:

- `R008` — analyst workflow continuity
- `R009` — CSP / CSRF / textContent-only DOM / SSRF allowlist / host validation continuity
- `R010` — polling/sort/render efficiency continuity
- `R014` — per-provider concurrency preserved
- `R015` — 429 backoff preserved
- `R018` — semaphore/backoff/snapshot invariants preserved
- `R019` — `?since=` cursor contract preserved
- `R020` — persistent adapter `requests.Session` usage preserved
- `R022` — WAL-backed cache/history design preserved unless disproven
- `R040` — test/verification safety net remains explicit and current

### Milestone acceptance support

S05 also has to make the milestone closeout auditable against the roadmap and context:

- success criteria from `.gsd/milestones/M012/M012-ROADMAP.md`
- final integrated acceptance from `.gsd/milestones/M012/M012-CONTEXT.md`
- slice delivery / assessment coverage / cross-slice integration / verification classes required by the validation flow

## Skill Notes

Installed skills that matter here:

- **`verify-before-complete`** — do not claim the milestone validates until fresh evidence exists in this slice and `gsd_validate_milestone` has actually written the milestone validation artifact.
- **`write-docs`** — this slice is mostly evidence synthesis for a fresh reader. Optimize for auditable, file-backed explanations rather than ad-hoc commentary.
- **`test`** — useful only for keeping the proof surface to repo-native commands that already exist (`pytest`, `make verify-fast`, optional `make verify-deep`).

## Skill Discovery (suggest)

No additional skill is required to finish S05, but two external skills were the most relevant direct matches for the existing stack if future work wants deeper framework-specific help:

- **Pytest:** `npx skills add github/awesome-copilot@pytest-coverage`
- **Flask:** `npx skills add aj-geddes/useful-ai-prompts@flask-api-development`

Neither looks necessary for this slice because the work is primarily GSD artifact closure using already-established local Flask/pytest patterns.

## Implementation Landscape

### 1) Artifact inventory and current gaps

Files that already exist and should be treated as the evidence spine:

- `.gsd/milestones/M012/M012-ROADMAP.md` — milestone success criteria, slice list, boundary map, S05 definition
- `.gsd/milestones/M012/M012-CONTEXT.md` — final integrated acceptance + verification classes
- `.gsd/milestones/M012/slices/S01/S01-SUMMARY.md` — live terminal-state contract + analyst-visible failure handling
- `.gsd/milestones/M012/slices/S02/S02-SUMMARY.md` — shared live/history result-application seam + parity/non-polling evidence
- `.gsd/milestones/M012/slices/S03/S03-SUMMARY.md` — `make verify-fast` / `make verify-deep` lane contract + deterministic mocked-online E2E seam
- `.gsd/milestones/M012/slices/S04/S04-SUMMARY.md` — helper diagnostics + persistence keep decision
- `.gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md` — explicit statement of the first validation gaps and the need for a remediation closure slice
- `.gsd/REQUIREMENTS.md` — already contains explicit M012 proof rows for `R009`, `R014`, `R015`, `R018`, `R020`, `R022`
- `.gsd/DECISIONS.md` — contains M012 planning decisions `D050`, `D051`, `D053`, `D055`, and the S04 keep/change conclusion `D056`

Files currently missing and likely needed for a clean validation pass:

- `.gsd/milestones/M012/M012-VALIDATION.md` — **missing** (must be rendered by `gsd_validate_milestone`)
- `.gsd/milestones/M012/slices/S01/S01-ASSESSMENT.md` — missing
- `.gsd/milestones/M012/slices/S02/S02-ASSESSMENT.md` — missing
- `.gsd/milestones/M012/slices/S03/S03-ASSESSMENT.md` — missing

Planner implication:

- The safest closure path is **artifact-first**: add the missing slice assessment coverage (or file-backed omission equivalents) and then render the milestone validation.
- Relying on prose-only omission rationale inside the final validation doc is riskier because the current MV02 prompt is artifact-oriented.

### 2) Existing proof surfaces by requirement

#### `R009` — security posture continuity

Use these files as the evidence base:

- `app/__init__.py` — CSP header, `CSRFProtect`, `TRUSTED_HOSTS`, `ALLOWED_API_HOSTS`
- `app/templates/base.html` — CSRF meta token
- `tests/test_api.py` — API CSRF exemption vs browser POST still requiring CSRF
- `tests/test_http_safety.py` — SSRF allowlist rejection and safe request path
- `app/static/src/ts/modules/shared-rendering.ts`, `app/static/src/ts/modules/row-factory.ts`, `app/static/src/ts/modules/enrichment.ts` — createElement/textContent path instead of unsafe HTML
- `.gsd/REQUIREMENTS.md` — already has a compact milestone-level proof row for R009

Planner implication:

- S05 probably does **not** need new code or new tests for R009.
- It needs to **pull the existing proof into milestone validation** so reviewer-style validation no longer sees it as “only partially evidenced in slice summaries.”

#### `R014`, `R015`, `R018` — orchestrator continuity

Use these files:

- `tests/test_orchestrator.py` — explicit sections for per-provider semaphore, 429 backoff, semaphore release during sleep, snapshot status semantics, `_cached_markers` locking
- `app/enrichment/orchestrator.py` — current implementation matches those invariants
- `.gsd/REQUIREMENTS.md` — already has concise proof rows for each requirement

Planner implication:

- The cleanest fresh proof is a focused rerun of `tests/test_orchestrator.py`.
- Validation text should cite this test surface directly instead of depending only on old M003/M004 claims.

#### `R019` — cursor-based polling continuity

Use these files:

- `tests/test_api.py` — `?since=` cursor filtering and `next_since`
- `tests/test_routes.py` / compatibility wrappers if needed
- `app/static/src/ts/modules/enrichment.test.ts` — live poll continuity and `next_since` progression
- `app/routes/_helpers.py` and `app/static/src/ts/modules/enrichment.ts`

Planner implication:

- This is already well represented in S01/S02; a small fresh proof command plus explicit validation writeup should be enough.

#### `R020` — persistent `requests.Session` usage

Use these files:

- `app/enrichment/adapters/base.py` — canonical `self._session = requests.Session()` path
- `tests/test_http_safety.py` — session-based safe request path
- `tests/test_adapter_contract.py` — adapter contract and allowed-host coverage
- `.gsd/REQUIREMENTS.md` — already has a proof row for R020

Planner implication:

- This was the most explicit gap called out by `S04-ASSESSMENT.md`: there was no milestone-level proof, even though the requirement ledger already contains one.
- S05 should surface this in the milestone validation doc; structural code changes are not indicated.

#### `R022` — WAL-backed persistence continuity

Use these files:

- `app/cache/store.py`
- `app/enrichment/history_store.py`
- `tests/test_cache_store.py`
- `tests/test_history_store.py`
- `tests/test_history_routes.py`
- `tests/test_settings.py`
- `.gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md`
- `.gsd/DECISIONS.md` entry `D056`

Planner implication:

- S04 already did the keep/change work. S05 only needs to tie that result into the milestone validation narrative so the ranked action-plan success criterion is obviously satisfied.

#### `R040` — proof loop continuity

Use these files:

- `Makefile` — `verify-fast`, `verify-deep`, `verify`
- `README.md` — contributor guidance on when each lane is required
- `.gsd/milestones/M012/slices/S03/S03-SUMMARY.md` — fresh lane evidence
- `.gsd/milestones/M012/slices/S04/S04-SUMMARY.md` — later `make verify-fast` proof after S04 changes

Planner implication:

- The latest fast-lane numbers are in S04, while deep-lane proof is in S03.
- The validator should use a consistent story: S03 established the lane split and deep-lane seam; S04 re-proved the fast lane after later changes.

### 3) Slice assessment coverage pattern

Older milestones in this repo do have slice-local `S##-ASSESSMENT.md` files (for example under `M001` and `M002`). M012 currently only has `S04-ASSESSMENT.md`.

That makes the most straightforward closure pattern:

- create brief `S01-ASSESSMENT.md`, `S02-ASSESSMENT.md`, and `S03-ASSESSMENT.md`
- each one can be small and formulaic: roadmap confirmed, no slice-order changes, no new remediation beyond what S05 is already addressing, note what downstream slice consumed
- use `gsd_summary_save` with `artifact_type: "ASSESSMENT"`

This is safer than trying to argue MV02 away without files.

### 4) Canonical milestone validation write path

The final milestone artifact must be rendered by **`gsd_validate_milestone`**, not manually written.

Planner implication:

- S05 should stage all evidence and prose first, then call `gsd_validate_milestone` last.
- The tool fields map cleanly to the required sections:
  - `successCriteriaChecklist`
  - `sliceDeliveryAudit`
  - `crossSliceIntegration`
  - `requirementCoverage`
  - `verificationClasses`
  - `verdictRationale`
  - optional `remediationPlan`
- The current auto-mode failure is not resolved until that tool writes `.gsd/milestones/M012/M012-VALIDATION.md`.

## Natural Seams for Tasking

### Seam 1 — Close missing slice assessment artifacts first

Best first task:

- create `S01-ASSESSMENT.md`, `S02-ASSESSMENT.md`, `S03-ASSESSMENT.md` (or explicit omitted-equivalent assessment artifacts)

Why first:

- It clears the obvious MV02 artifact gap immediately.
- It is low-risk, uses only existing summaries/UAT, and does not depend on rerunning the whole test suite first.
- It gives the final validator a complete slice artifact inventory.

### Seam 2 — Re-run focused proof for the requirements called out as partial

Recommended focused commands rather than one giant opaque batch:

- `python3 -m pytest tests/test_orchestrator.py -q` → `R014`, `R015`, `R018`
- `python3 -m pytest tests/test_api.py tests/test_routes.py tests/test_http_safety.py -q` → `R009`, `R019`, plus API/browser security boundaries
- `python3 -m pytest tests/test_cache_store.py tests/test_history_store.py tests/test_history_routes.py tests/test_settings.py -q` → `R022` and S04 persistence/helper closure
- structural checks for `R020` if needed:
  - `rg -n "self\._session = requests\.Session\(" app/enrichment/adapters`
  - `python3 -m pytest tests/test_adapter_contract.py tests/test_http_safety.py -q`
- `make verify-fast` → fresh `R040` / broad non-E2E safety-net proof

Optional escalation:

- `make verify-deep` only if the executor wants fresh current-message browser/live-flow proof rather than citing the already-fresh S03 deep-lane evidence. Because S05 is artifact-only, this is a judgment call, not an automatic requirement.

### Seam 3 — Synthesize milestone validation last

Final task:

- use roadmap + context + summaries + assessments + focused fresh command output to build the validation payload
- call `gsd_validate_milestone`
- verify `M012-VALIDATION.md` exists and is non-empty

## Recommendation

### Recommended slice outcome

Treat S05 as a **milestone-closeout evidence slice**, not a code-change slice.

Concretely:

1. **Create the missing slice assessment coverage** for S01–S03.
2. **Capture fresh focused proof** for the requirements the first validation flagged as partial (`R009`, `R014`, `R015`, `R018`, `R020`, `R022`, `R040`).
3. **Use the already-written requirement ledger rows** in `.gsd/REQUIREMENTS.md` as the milestone proof index rather than rediscovering those arguments from scratch.
4. **Render the canonical milestone validation file** with `gsd_validate_milestone`.

### What not to do

- Do not reopen app/frontend/backend implementation unless a fresh verification run actually fails.
- Do not manually write `M012-VALIDATION.md`.
- Do not rely only on slice summaries for the requirements already distilled in `.gsd/REQUIREMENTS.md`; use the ledger to make the milestone validation coherent.

## Risks / Unknowns

- The first validation failure was largely about **artifact shape**, not implementation breakage. If S05 skips the artifact work and only reruns tests, validation can still fail.
- `.gsd/REQUIREMENTS.md` already has the right proof rows, but a reviewer that looks only at M012 slice summaries can still conclude the evidence is partial. S05 has to bridge that gap explicitly in the milestone validation prose.
- The fast-lane counts changed between S03 and S04. The final validation writeup should use one consistent narrative instead of mixing stale counts.
- If the executor chooses omission prose instead of creating `S01`–`S03` assessment files, MV02 may still flag missing assessment artifacts.

## Verification

Use these as the proof floor for S05 execution:

- Artifact coverage:
  - `test -s .gsd/milestones/M012/slices/S01/S01-ASSESSMENT.md`
  - `test -s .gsd/milestones/M012/slices/S02/S02-ASSESSMENT.md`
  - `test -s .gsd/milestones/M012/slices/S03/S03-ASSESSMENT.md`
- Focused requirement proof:
  - `python3 -m pytest tests/test_orchestrator.py -q`
  - `python3 -m pytest tests/test_api.py tests/test_routes.py tests/test_http_safety.py -q`
  - `python3 -m pytest tests/test_cache_store.py tests/test_history_store.py tests/test_history_routes.py tests/test_settings.py -q`
  - optional: `python3 -m pytest tests/test_adapter_contract.py tests/test_http_safety.py -q`
- Broad safety-net proof:
  - `make verify-fast`
- Optional browser proof if the executor wants current-message end-to-end evidence:
  - `make verify-deep`
- Final artifact existence check:
  - `test -s .gsd/milestones/M012/M012-VALIDATION.md`

The final success condition for this slice is not just passing tests; it is **a present, canonical milestone validation artifact on disk** plus enough structured evidence that `gsd_validate_milestone` can return `pass` instead of another remediation round.