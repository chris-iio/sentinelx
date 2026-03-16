---
phase: 3
slug: visual-redesign
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + playwright-pytest (E2E) |
| **Config file** | `tests/e2e/conftest.py` |
| **Quick run command** | `make typecheck && make js-dev` |
| **Full suite command** | `pytest tests/ -m e2e --tb=short` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every CSS change:** `make css` then browser reload
- **After every TS change:** `make typecheck && make js-dev`
- **After every task commit:** `pytest tests/ -m e2e --tb=short -q` — confirm 89/91 baseline
- **After every plan wave:** `pytest tests/ -m e2e --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green + manual browser verification
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | VIS-01 | CSS visual | `make css` + manual browser review | ✅ (manual) | ⬜ pending |
| 03-01-02 | 01 | 1 | VIS-02 | typecheck + build + E2E | `make typecheck && make js-dev && pytest tests/ -m e2e --tb=short -q` | ✅ | ⬜ pending |
| 03-01-03 | 01 | 1 | VIS-03 | typecheck + build + E2E | `make typecheck && make js-dev && pytest tests/ -m e2e --tb=short -q` | ✅ | ⬜ pending |
| 03-01-04 | 01 | 1 | GRP-02 | typecheck + build + E2E | `make typecheck && make js-dev && pytest tests/ -m e2e --tb=short -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/e2e/test_visual_redesign.py` — covers VIS-03 (section headers after enrichment) and GRP-02 (no-data collapse/expand); requires online-mode fixture
- [ ] Online-mode E2E fixture — mock enrichment server or recorded responses

*Note: VIS-01 is CSS-only (manual visual review). VIS-02 breaks no existing selector and is visible in DOM after enrichment.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Verdict badge size prominence | VIS-01 | No pixel/screenshot comparison in Playwright suite | After `make css`, load results page, verify `.verdict-label` is visually larger than `.verdict-badge` |
| Micro-bar visual proportions | VIS-02 | Color proportions need visual check | After enrichment, verify bar segments match verdict distribution |
| Section headers visible | VIS-03 | Online-mode required | Run enrichment, verify "Reputation" and "Infrastructure Context" labels appear |
| No-data collapse/expand | GRP-02 | Online-mode required | Run enrichment, verify no-data providers collapsed, count summary shown, expand works |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
