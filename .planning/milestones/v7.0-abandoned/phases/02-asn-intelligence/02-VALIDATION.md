---
phase: 02
slug: asn-intelligence
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest tests/test_asn_cymru.py -x` |
| **Full suite command** | `pytest tests/ -m 'not e2e'` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_asn_cymru.py -x`
- **After every plan wave:** Run `pytest tests/ -m 'not e2e'`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | ASN-01 | unit | `pytest tests/test_asn_cymru.py -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | ASN-01 | unit | `pytest tests/test_asn_cymru.py -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | ASN-01 | unit | `pytest tests/test_asn_cymru.py::test_nxdomain` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | ASN-01 | unit | `pytest tests/test_registry_setup.py -x` | ✅ partial | ⬜ pending |
| 02-01-05 | 01 | 2 | ASN-01 | integration | `pytest tests/test_asn_cymru.py tests/test_registry_setup.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_asn_cymru.py` — stubs for ASN-01 (adapter unit tests: IPv4 lookup, IPv6 query, NXDOMAIN handling, configuration checks)
- [ ] Update `tests/test_registry_setup.py` — change count from 13 to 14, add "ASN Intel" presence test, add always-configured test

*Existing infrastructure covers test framework and fixtures.*

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
