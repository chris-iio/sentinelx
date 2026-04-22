---
estimated_steps: 4
estimated_files: 2
skills_used:
  - write-docs
  - verify-before-complete
---

# T02: Write the ranked persistence/helper keep-change assessment for M012


Turn the S04 evidence into a durable assessment and decision record. Use the research findings, the new helper/settings diagnostics surface, and fresh verification output to rank what SentinelX should do now, do next, later, and leave alone. Keep the conclusion explicit: preserve the WAL-backed stores and full-fidelity history replay unless new measurement disproves the current evidence.

## Steps

1. Re-read `S04-RESEARCH.md`, the M012 context/roadmap, and the final T01 outputs so the assessment cites real code seams instead of generic optimization advice.
2. Write `.gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md` with explicit **Do now**, **Do next**, **Later**, and **Leave alone** sections, plus a short requirement-impact note covering R022, R040, R008, and R019.
3. Append the planning/execution conclusion to `.gsd/DECISIONS.md`, capturing that S04 keeps the WAL stores as-is and treats helper-layer diagnostics/measurement as the only justified near-term follow-through.
4. Verify the assessment file exists, is non-empty, and contains the ranked sections so milestone closeout has a durable handoff artifact.

## Must-Haves

- [ ] The assessment names specific files/seams (`app/cache/store.py`, `app/enrichment/history_store.py`, `app/routes/_helpers.py`, and the new diagnostics surface) rather than generic “persistence” prose.
- [ ] The ranking clearly distinguishes **Do now**, **Do next**, **Later**, and **Leave alone** with proof-backed rationale.
- [ ] The written decision explicitly preserves WAL-mode cache/history behavior and the full-results history replay path unless future measurement says otherwise.
- [ ] The assessment calls out that `_get_enrichment_status()` `?since=` behavior and `HistoryStore.save_analysis()` continuity were intentionally left alone in this slice.

## Verification

- `test -s .gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md && rg -n "^## (Do now|Do next|Later|Leave alone)" .gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md`
- `rg -n "WAL|helper|persistence|history replay" .gsd/DECISIONS.md`

## Inputs

- `.gsd/milestones/M012/slices/S04/S04-RESEARCH.md` — evidence summary and recommendation baseline for the slice.
- `.gsd/milestones/M012/M012-CONTEXT.md` — milestone-level framing for optimization proof and ranked next work.
- `.gsd/milestones/M012/M012-ROADMAP.md` — roadmap promise this slice must close truthfully.
- `app/routes/_helpers.py` — final helper seam shape after T01.
- `app/routes/settings.py` — final inspection surface used as the slice’s shipped quick win.
- `.gsd/DECISIONS.md` — existing decision log that needs the S04 keep/change conclusion appended.

## Expected Output

- `.gsd/milestones/M012/slices/S04/S04-ASSESSMENT.md` — ranked persistence/helper next-work decision with proof-backed recommendations.
- `.gsd/DECISIONS.md` — appended S04 decision capturing the keep/change stance.
