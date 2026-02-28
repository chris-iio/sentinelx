# Dead Code Analysis Report

**Project:** SentinelX
**Date:** 2026-03-01
**Tools Used:** vulture 2.14 (Python), tsc --noEmit (TypeScript), ruff F401/F841 (imports/vars), manual cross-reference
**Test Baseline:** 224 unit/integration tests passing, 97% coverage

---

## Summary

| Category | Items Found | Severity |
|----------|-------------|----------|
| Python dead code (vulture) | 0 | Clean |
| TypeScript type errors | 0 | Clean |
| Unused Python imports (ruff) | 0 | Clean |
| Unused Python packages (requirements.txt) | 0 | Clean |
| Unused template partials | 0 | Clean |
| Unused static assets | 0 | Clean |
| TODO/FIXME annotations | 0 | Clean |
| Stale backup files | 2 files (5KB) | SAFE to delete |
| Untracked external directory | 1 (34MB) | SAFE to delete/ignore |
| Completed phase planning artifacts | 1 directory | SAFE to delete |
| Missing CSS definitions | 2 classes | CAUTION (functional gap) |
| Dev-only package in venv | 1 (pycryptodome) | SAFE to uninstall |
| Config deprecation warning | 1 (ruff pyproject.toml) | SAFE to fix |

**Verdict: Codebase is exceptionally clean.** Previous findings (v1.2 report) were all resolved.

---

## SAFE: Items to Clean Up

### 1. Stale Planning Backups (5.1KB total)
- `.planning/STATE.md.bak-2026-02-24T15-10-53` (2.5KB)
- `.planning/STATE.md.bak-2026-02-25T15-22-24` (2.6KB)

**Reason:** Old STATE.md backups from milestone transitions. Current STATE.md is authoritative.

### 2. Untracked External Directory (34MB)
- `everything-claude-code/` — separate project with its own `.git`, not part of SentinelX

**Action:** Delete or add to `.gitignore`.

### 3. Completed Phase 18 Artifacts (untracked)
- `.planning/phases/18-keyless-multi-source-ioc-enrichment/` (8 files: plans, summaries, context)

**Reason:** Phase 18 (v2.0) completed and shipped 2026-02-28. Artifacts are untracked.

### 4. Unused Dev Package
- `pycryptodome 3.23.0` installed in .venv but not in requirements.txt, not imported anywhere

**Action:** `pip uninstall pycryptodome`

### 5. Ruff Config Deprecation
- `pyproject.toml`: `select` under `[tool.ruff]` should be `[tool.ruff.lint]`

---

## CAUTION: Functional Gaps (Not Dead Code)

### 6. Missing `.alert-success` and `.alert-warning` CSS

Flask routes flash messages with categories `"success"` and `"warning"`, but only `.alert-error`
has a CSS definition. Success/warning messages render with base `.alert` styling only.

**Action:** Add CSS definitions in `input.css` following `.alert-error` pattern.

---

## False Positives Investigated (NOT Dead Code)

### TypeScript Forward Declarations (Phase 22 Scaffolding)

11 exports appear unused but are intentional scaffolding for the enrichment polling module:

| Export | File | Consumer |
|--------|------|----------|
| `IocType` | types/ioc.ts | Phase 22 |
| `IOC_PROVIDER_COUNTS` | types/ioc.ts | Phase 22 |
| `EnrichmentResultItem` | types/api.ts | Phase 22 |
| `EnrichmentErrorItem` | types/api.ts | Phase 22 |
| `EnrichmentItem` | types/api.ts | Phase 22 |
| `EnrichmentStatus` | types/api.ts | Phase 22 |
| `findCardForIoc` | modules/cards.ts | Phase 22 |
| `updateCardVerdict` | modules/cards.ts | Phase 22 |
| `updateDashboardCounts` | modules/cards.ts | Phase 22 |
| `sortCardsBySeverity` | modules/cards.ts | Phase 22 |
| `writeToClipboard` | modules/clipboard.ts | Phase 22 |

**Re-evaluate after phase 22 completes.**

### Flask Framework Entry Points
All Python functions flagged as single-file are Flask route handlers, error handlers, or factory
functions invoked by the framework — not dead code.

### screenshot.png
Referenced in `README.md` line 2.

---

## Previously Resolved (From v1.2 Report)

| Finding | Status |
|---------|--------|
| 7 unused `import pytest` in test files | Fixed |
| Unused `IOCType` import in test_routes.py | Fixed |
| Unused `csrf_app` variable in test_routes.py | Fixed |
| `TestConfig` class in config.py | Removed |
| `.btn-ghost` CSS class | Removed |

---

## Dependency Analysis — All Used

| Package | Import Count | Status |
|---------|-------------|--------|
| Flask 3.1.1 | 5 | Used |
| Flask-Limiter 4.1.1 | 2 | Used |
| Flask-WTF 1.2.2 | 1 | Used |
| iocextract 1.16.1 | 1 | Used |
| iocsearcher 2.7.2 | 1 | Used |
| python-dotenv 1.1.0 | 1 | Used |
| requests 2.32.5 | 7 | Used |
