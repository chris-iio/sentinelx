# M008: 

## Vision
Decompose the monolithic routes.py (488 LOC) into focused Blueprint modules, then add a JSON REST API blueprint for programmatic IOC submission. The decomposition makes each route group independently testable and the API work a clean addition rather than more accretion onto the monolith.

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | Routes decomposition | medium | — | ✅ | routes.py deleted, replaced by app/routes/ package with 7 focused modules. All 1057 tests pass. No behavior changes. |
| S02 | REST API blueprint | low | S01 | ✅ | POST /api/analyze returns JSON with extracted IOCs. Online mode returns job_id for polling via GET /api/status/<job_id>. CSRF exempt, rate-limited. |
