---
phase: 1
slug: contracts-and-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + Playwright (E2E) |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/ -m "not e2e" -x -q` |
| **Full suite command** | `pytest tests/ -m e2e --tb=short` |
| **Estimated runtime** | ~60 seconds (E2E suite) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -m "not e2e" -x -q`
- **After every plan wave:** Run `pytest tests/ -m e2e --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| BASELINE | 01 | 1 | (none) | smoke | `pytest tests/ -m e2e --tb=short` | ✅ (existing suite) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

Phase 1 produces documentation only. No new test infrastructure is needed.
The existing 91 E2E tests are the enforcement mechanism.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CSS catalog completeness | SC-1 | Requires human review that all E2E selectors are catalogued | Compare `CSS-CONTRACTS.md` entries against `grep -r 'page.locator\|page.query_selector' tests/e2e/` |
| Template comment accuracy | SC-2 | Requires human review of inline comments | Read `_ioc_card.html` and verify data-attribute comments match actual consumers |
| Information density criteria clarity | SC-3 | Requires human judgement on criteria quality | Read criteria and confirm they are specific and testable |
| CSS layer ownership rule clarity | SC-4 | Requires human judgement on rule quality | Read `input.css` header comment and confirm it is unambiguous |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
