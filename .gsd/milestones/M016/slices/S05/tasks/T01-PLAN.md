---
estimated_steps: 13
estimated_files: 2
skills_used: []
---

# T01: Reconcile M016 context and requirement ownership

Expected executor skills: `write-docs`, `verify-before-complete`.

Why: validation cannot be trusted while `.gsd/milestones/M016/M016-CONTEXT.md` still describes a superseded Minimal Useful Product Hardening milestone and `.gsd/REQUIREMENTS.md` leaves R083 looking like an active M016 blocker. This task repairs the planning ledger before any pass/fail validation claim.

Do:
1. Rewrite the M016 context artifact through the existing GSD artifact path if available, or by careful direct edit if no context-update tool is present, so it reflects the actual roadmap: EmailRep adapter, settings/registry integration, safe compact UI rendering, and mocked Online E2E proof.
2. Preserve explicit out-of-scope boundaries: raw EML parsing, header-authentication phishing triage, multiple email reputation providers, live EmailRep smoke tests, and diagnostic log export.
3. Update the R083 notes/ownership in `.gsd/REQUIREMENTS.md` so it is clearly future M018 work per D075/D076, not an M016 requirement to implement or validate.
4. Add a compact requirement coverage section in context naming R008, R009, and R011 as continuity/security/E2E support for M016.
5. Do not modify completed S01-S04 summaries, roadmap checkboxes, or code unless this reconciliation uncovers a concrete proof gap.

Threat Surface (Q3): no runtime auth/data surface is changed; artifact text must still avoid secrets and raw EmailRep keys.
Requirement Impact (Q4): touches R008, R009, R011 as supporting validated requirements and R083 as explicitly descoped/future-owned; decisions D075 and D076 apply.
Failure Modes (Q5): if requirement editing is partial, milestone validation may continue to report ledger drift; if R083 is removed instead of scoped, future diagnostic-export work loses traceability.
Negative Tests (Q7): verify the stale title is gone, EmailRep scope is present, and R083 still exists with M018 ownership.
Done when: context and requirement ledger tell one coherent story and the verification command passes.

## Inputs

- `.gsd/milestones/M016/M016-CONTEXT.md`
- `.gsd/milestones/M016/M016-ROADMAP.md`
- `.gsd/milestones/M016/slices/S04/S04-SUMMARY.md`
- `.gsd/REQUIREMENTS.md`
- `.gsd/DECISIONS.md`

## Expected Output

- `.gsd/milestones/M016/M016-CONTEXT.md`
- `.gsd/REQUIREMENTS.md`

## Verification

python3 - <<'PY'
from pathlib import Path
ctx = Path('.gsd/milestones/M016/M016-CONTEXT.md').read_text()
req = Path('.gsd/REQUIREMENTS.md').read_text()
assert 'Email Reputation Depth' in ctx, 'M016 context must name operative Email Reputation Depth scope'
assert 'EmailRep' in ctx and 'mocked Online' in ctx, 'M016 context must include EmailRep mocked Online proof scope'
assert 'Minimal Useful Product Hardening' not in ctx.splitlines()[0], 'M016 title must no longer advertise stale minimal-product scope'
assert 'R083' in req and 'M018' in req, 'R083 must remain recorded and point at the future M018 diagnostic export scope'
print('context/requirement reconciliation checks passed')
PY

## Observability Impact

Improves closeout diagnostics by making the canonical context and requirement ledger explain why R083 is not part of M016 validation and where to inspect the future owning milestone.
