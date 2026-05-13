---
estimated_steps: 45
estimated_files: 5
skills_used: []
---

# T01: Write the final M017 closeout proof artifact

---
estimated_steps: 6
estimated_files: 5
skills_used:
  - write-docs
  - verify-before-complete
---

# T01: Write the final M017 closeout proof artifact

**Slice:** S05 — Final Integrated Proof + Durable Handoff
**Milestone:** M017

## Description

Create a durable, reader-friendly closeout artifact at `docs/m017-closeout-proof.md` that ties the project map, refreshed project summary, generated optimization audit, shipped S03/S04 optimizations, and requirements R084/R087/R088/R089 into one final proof package. This task should not change product code and should not hand-edit generated `.gsd` artifacts; it reads them as source evidence and writes a normal docs artifact future agents can inspect.

## Failure Modes

| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| Generated audit/project/requirements files | Stop and report the missing or inconsistent source; do not invent proof | N/A for file reads | Quote the inconsistency and defer to T02/T03 verification rather than claiming success |

## Negative Tests

- **Malformed inputs**: Treat missing headings, stale pending S04 language, or absent requirement IDs as blockers to closeout wording.
- **Error paths**: If source artifacts disagree with S03/S04 summaries, document the mismatch and do not mark R089 satisfied.
- **Boundary conditions**: Keep the artifact concise enough to be maintainable while including all four requirement IDs and both verification lanes.

## Steps

1. Inspect `docs/project-map.md`, `.gsd/PROJECT.md`, `.gsd/milestones/M017/M017-AUDIT.md`, `.gsd/REQUIREMENTS.md`, and the S03/S04 summaries already available to the executor.
2. Write `docs/m017-closeout-proof.md` with sections for current product identity, optimization outcomes, requirement coverage, verification plan/evidence placeholders, and handoff notes.
3. Explicitly map R084 to the project map, R087 to S03/S04 optimization proof, R088 to analyst-flow regression lanes, and R089 to final `make verify-fast`/`make verify-deep` evidence.
4. Include S03 incremental polling/status optimization and S04 frontend result-application severity-gate optimization as shipped outcomes, not future targets.
5. Include a short guardrail section stating that S05 should not introduce new product-code optimization unless verification exposes a real blocker that requires replanning.
6. Leave verification result fields as pending until T02/T03 produce fresh command evidence; do not fabricate durations, pass counts, or timestamps.

## Must-Haves

- [ ] `docs/m017-closeout-proof.md` exists and is non-empty.
- [ ] The artifact references R084, R087, R088, and R089.
- [ ] The artifact names both shipped optimization themes: incremental status/polling proof and result-application severity-gate proof.
- [ ] The artifact points to `make verify-fast` and `make verify-deep` as the final closeout lanes.

## Verification

- `test -s docs/m017-closeout-proof.md`
- `grep -Eq "R084|R087|R088|R089" docs/m017-closeout-proof.md`
- `grep -Ei "incremental|polling|status" docs/m017-closeout-proof.md`
- `grep -Ei "severity|result-application|recount|reorder" docs/m017-closeout-proof.md`

## Inputs

- `docs/project-map.md` — current product/codebase map from S01.
- `.gsd/PROJECT.md` — refreshed project summary from S01.
- `.gsd/milestones/M017/M017-AUDIT.md` — generated optimization audit with S03/S04 shipped outcomes.
- `.gsd/REQUIREMENTS.md` — requirement statuses and validation text for R084/R087/R088/R089.
- `.gsd/milestones/M017/slices/S04/S04-SUMMARY.md` — dependency summary with secondary optimization and verification evidence.

## Expected Output

- `docs/m017-closeout-proof.md` — final M017 proof and handoff artifact with pending verification slots for T02/T03.

## Inputs

- `docs/project-map.md`
- `.gsd/PROJECT.md`
- `.gsd/milestones/M017/M017-AUDIT.md`
- `.gsd/REQUIREMENTS.md`
- `.gsd/milestones/M017/slices/S04/S04-SUMMARY.md`

## Expected Output

- `docs/m017-closeout-proof.md`

## Verification

test -s docs/m017-closeout-proof.md && grep -Eq "R084|R087|R088|R089" docs/m017-closeout-proof.md && grep -Ei "incremental|polling|status" docs/m017-closeout-proof.md && grep -Ei "severity|result-application|recount|reorder" docs/m017-closeout-proof.md

## Observability Impact

No production signals change. The artifact improves operational handoff by giving future agents a single inspection file for M017 identity, shipped optimization proof, requirement coverage, and verification lanes.
