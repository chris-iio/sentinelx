---
phase: 2
slug: typescript-module-extractions
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + playwright-pytest (E2E) |
| **Config file** | `tests/e2e/conftest.py` |
| **Quick run command** | `tsc --noEmit && make js-dev` |
| **Full suite command** | `pytest tests/ -m e2e --tb=short` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `tsc --noEmit && make js-dev`
- **After every plan wave:** Run `pytest tests/ -m e2e --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | (none) | typecheck + build | `tsc --noEmit && make js-dev` | ✅ | ⬜ pending |
| 02-01-02 | 01 | 1 | (none) | typecheck + build | `tsc --noEmit && make js-dev` | ✅ | ⬜ pending |
| 02-01-03 | 01 | 1 | (none) | typecheck + build + E2E | `tsc --noEmit && make js-dev && pytest tests/ -m e2e --tb=short` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test files needed.

The E2E suite (91 tests) validates behavioral identity. TypeScript strict mode validates type safety. esbuild validates bundle compilation.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
