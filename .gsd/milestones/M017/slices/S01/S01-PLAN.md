# S01: Current-State Project Map

**Goal:** Produce a durable, code-grounded project map (docs/project-map.md) and a refreshed project summary (.gsd/PROJECT.md) that give any future agent — or optimization pass — a concrete identity anchor: what SentinelX is, who it serves, its primary analyst loop, its module-level architecture seams, and a ranked optimization priority list tied to actual file paths.
**Demo:** SentinelX has a separate project map plus refreshed project summary that explains what it is, who it serves, main analyst loop, architecture seams, and optimization priorities.

## Must-Haves

- docs/project-map.md exists and contains: (1) what/who/loop sections, (2) architecture seams with concrete file paths, (3) a ranked optimization priorities section with at least 3 named targets and their file references. .gsd/PROJECT.md is updated to reference the seam inventory and reflect M017 in-progress state. Both files are non-empty, section-complete, and have no TBD/TODO placeholders.

## Proof Level

- This slice proves: contract — document existence and structural completeness verified by grep/wc checks; no runtime required

## Integration Closure

Upstream: existing docs/project-map.md (partial), .gsd/PROJECT.md, app/ codebase, .gsd/REQUIREMENTS.md, .gsd/DECISIONS.md. Downstream: S02 consumes docs/project-map.md optimization priorities section as the identity-grounded audit input.

## Verification

- Run the task and slice verification checks for this slice.

## Tasks

- [ ] **T01: Enrich docs/project-map.md with concrete file-path seams and ranked optimization priorities** `est:45m`
  The existing docs/project-map.md is high-level and lacks concrete file paths for each architecture seam and a ranked optimization priority list. This task reads the actual codebase modules and rewrites/enriches the project map so S02 has an identity-grounded, code-specific anchor rather than abstract categories.
  - Files: `docs/project-map.md`, `app/enrichment/setup.py`, `app/enrichment/registry.py`, `app/pipeline/extractor.py`, `app/static/src/ts/modules/`, `app/cache/store.py`, `app/routes/`
  - Verify: grep -c '^## ' docs/project-map.md | awk '$1>=6{exit 0} {exit 1}' && grep -q 'app/enrichment\|app/routes\|app/pipeline' docs/project-map.md && grep -qi 'ranked\|optimization priorities\|priority' docs/project-map.md && ! grep -q 'TBD\|TODO' docs/project-map.md

- [ ] **T02: Refresh .gsd/PROJECT.md to align with enriched project map and current M017 state** `est:20m`
  After T01 enriches docs/project-map.md with concrete seam details and optimization priorities, this task updates .gsd/PROJECT.md to: (1) reference the enriched project map as the authoritative seam inventory, (2) add a brief **Seam Inventory** pointer section naming the canonical seams and their files, and (3) confirm M017 state reflects in-progress with project-map produced.
  - Files: `.gsd/PROJECT.md`, `docs/project-map.md`
  - Verify: grep -q 'project-map\|seam' .gsd/PROJECT.md && grep -q 'app/enrichment\|app/routes\|app/pipeline' .gsd/PROJECT.md && test -s .gsd/PROJECT.md

## Files Likely Touched

- docs/project-map.md
- app/enrichment/setup.py
- app/enrichment/registry.py
- app/pipeline/extractor.py
- app/static/src/ts/modules/
- app/cache/store.py
- app/routes/
- .gsd/PROJECT.md
