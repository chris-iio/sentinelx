---
estimated_steps: 23
estimated_files: 7
skills_used: []
---

# T01: Enrich docs/project-map.md with concrete file-path seams and ranked optimization priorities

The existing docs/project-map.md is high-level and lacks concrete file paths for each architecture seam and a ranked optimization priority list. This task reads the actual codebase modules and rewrites/enriches the project map so S02 has an identity-grounded, code-specific anchor rather than abstract categories.

## Why
S02 must select optimization targets grounded in SentinelX's identity. The current project map names seams without pointing to files or ranking them. Without this, S02 risks generic or misaligned optimization choices.

## Steps
1. Read key seam files to gather concrete evidence:
   - `app/routes/` — list all route modules and their surfaces
   - `app/enrichment/setup.py` — provider list and registration
   - `app/enrichment/registry.py` — ProviderRegistry structure
   - `app/enrichment/orchestrator.py` (or equivalent) — fan-out/retry logic
   - `app/pipeline/` — IOC extraction/normalization entry points
   - `app/static/src/ts/modules/` — TypeScript browser modules
   - `app/cache/store.py` — CacheStore structure
   - `tools/optimization_audit.py` — audit runner entry point
2. Map each architecture seam to its canonical file path(s).
3. Rewrite docs/project-map.md to add/update:
   - A **Architecture Seams** section with named seams, each having 1-3 canonical file paths and a one-line responsibility statement.
   - A **Ranked Optimization Priorities** section with at least 3 entries (ranked 1=highest), each naming the seam, the specific file(s), the optimization opportunity type (e.g. N+1 query, redundant work, unnecessary allocation), and what proof is needed.
   - Preserve all existing sections (What SentinelX Is Now, Who It Serves, Primary Analyst Loop, Core Runtime Shape, Non-Negotiable Guardrails).
4. Verify file structure with grep checks.

## Constraints
- Do NOT invent optimization findings — only name opportunities visible in the actual files read.
- Do NOT remove or contradict existing Non-Negotiable Guardrails.
- Keep the document analyst-readable: no more than ~100 lines total.

## Inputs

- `docs/project-map.md`
- `app/enrichment/setup.py`
- `app/enrichment/registry.py`
- `app/routes/`
- `app/pipeline/`
- `app/static/src/ts/modules/`
- `app/cache/store.py`
- `tools/optimization_audit.py`

## Expected Output

- `docs/project-map.md`

## Verification

grep -c '^## ' docs/project-map.md | awk '$1>=6{exit 0} {exit 1}' && grep -q 'app/enrichment\|app/routes\|app/pipeline' docs/project-map.md && grep -qi 'ranked\|optimization priorities\|priority' docs/project-map.md && ! grep -q 'TBD\|TODO' docs/project-map.md
