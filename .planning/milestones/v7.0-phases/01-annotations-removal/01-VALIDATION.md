---
phase: 01
slug: annotations-removal
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pytest.ini` |
| **Quick run command** | `pytest tests/test_ioc_detail_routes.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_ioc_detail_routes.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | CLEAN-01 | smoke | `python -c "from app import create_app; create_app()"` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | CLEAN-02 | integration | `pytest tests/test_ioc_detail_routes.py::TestAnnotationRoutes404 -x` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | CLEAN-01 | integration | `pytest tests/test_ioc_detail_routes.py -x -q` | ✅ (rewrite) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_ioc_detail_routes.py::TestAnnotationRoutes404` — new test class asserting annotation routes return 404 (covers CLEAN-02)
- [ ] Smoke test assertion confirming `create_app()` succeeds without import errors (covers CLEAN-01 startup criterion)
- [ ] Negative assertions: detail page HTML contains no `detail-annotations`, `ioc-notes`, `tag-input` strings (covers CLEAN-01 UI criterion)
- [ ] Negative assertion: results page HTML contains no `data-tags` attribute (covers CLEAN-01 UI criterion)

*Existing infrastructure covers test framework — no new dependencies needed.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
