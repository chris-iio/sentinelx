# M010: 

## Vision
Eliminate route layer duplication (orchestrator setup, status endpoints), remove dead imports/exports, and relocate Recent Analyses from the home page to a dedicated /history page. Leave the codebase lean and focused before the next feature milestone.

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | Route Duplication & Dead Code Cleanup | medium | — | ✅ | After this: analysis.py and api.py share a single orchestrator setup helper; status endpoints consolidated; dead imports/exports removed; all tests pass. |
| S02 | Recent Analyses → Dedicated /history Page | low | S01 | ⬜ | After this: home page shows only the paste form; /history lists recent analyses with links to detail pages. |
