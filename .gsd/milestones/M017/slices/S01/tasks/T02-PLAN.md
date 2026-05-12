---
estimated_steps: 15
estimated_files: 2
skills_used: []
---

# T02: Refresh .gsd/PROJECT.md to align with enriched project map and current M017 state

After T01 enriches docs/project-map.md with concrete seam details and optimization priorities, this task updates .gsd/PROJECT.md to: (1) reference the enriched project map as the authoritative seam inventory, (2) add a brief **Seam Inventory** pointer section naming the canonical seams and their files, and (3) confirm M017 state reflects in-progress with project-map produced.

## Why
.gsd/PROJECT.md is the first thing future planning agents read. It must accurately reflect what has been produced and where to find the seam inventory, so S02 and later slices don't need to re-derive it.

## Steps
1. Read updated docs/project-map.md (T01 output).
2. Read current .gsd/PROJECT.md.
3. Update .gsd/PROJECT.md:
   - In **Current State**: note that docs/project-map.md now includes concrete architecture seams and ranked optimization priorities (produced by M017/S01).
   - Add or update a **Seam Inventory** section (or pointer) naming the 4-5 canonical seams with their file paths, matching T01 output.
   - Confirm Milestone Sequence entry for M017 reflects current state.
4. Verify with grep checks.

## Constraints
- Do NOT delete existing sections in PROJECT.md.
- Keep changes minimal and additive — update only what is stale or missing.
- .gsd/ files are not committed to git (managed externally).

## Inputs

- `docs/project-map.md`
- `.gsd/PROJECT.md`

## Expected Output

- `.gsd/PROJECT.md`

## Verification

grep -q 'project-map\|seam' .gsd/PROJECT.md && grep -q 'app/enrichment\|app/routes\|app/pipeline' .gsd/PROJECT.md && test -s .gsd/PROJECT.md
