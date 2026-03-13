---
phase: 03
slug: passive-dns-pivoting
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, no new install needed) |
| **Config file** | None at project root — run via `python -m pytest` |
| **Quick run command** | `python -m pytest tests/test_threatminer.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_threatminer.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | DINT-03 | unit | `python -m pytest tests/test_threatminer.py::TestProviderProtocol -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | DINT-03 | unit | `python -m pytest tests/test_threatminer.py::TestIPLookup -x` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | DINT-03 | unit | `python -m pytest tests/test_threatminer.py::TestDomainLookup -x` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | DINT-03 | unit | `python -m pytest tests/test_threatminer.py::TestHashLookup -x` | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 1 | DINT-03 | unit | `python -m pytest tests/test_threatminer.py::TestNoDataHandling -x` | ❌ W0 | ⬜ pending |
| 03-01-06 | 01 | 1 | DINT-03 | unit | `python -m pytest tests/test_threatminer.py::TestHTTPErrors -x` | ❌ W0 | ⬜ pending |
| 03-01-07 | 01 | 1 | DINT-03 | unit | `python -m pytest tests/test_threatminer.py::TestHTTPSafetyControls -x` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | DINT-03 | unit | `python -m pytest tests/test_registry_setup.py -x` | ✅ (update) | ⬜ pending |
| 03-02-02 | 02 | 2 | DINT-03 | unit | `python -m pytest tests/test_security_audit.py -x` | ✅ (update) | ⬜ pending |
| 03-02-03 | 02 | 2 | DINT-03 | manual | Visual verify in browser | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_threatminer.py` — stubs for DINT-03 (adapter protocol, IP/domain/hash lookups, no_data handling, HTTP errors, safety controls)
- [ ] Update `tests/test_registry_setup.py` — bump provider count, add ThreatMiner assertion
- [ ] Update `tests/test_security_audit.py` — add `"api.threatminer.org"` to expected ALLOWED_API_HOSTS

*Existing infrastructure covers all framework needs — no new install required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Frontend renders passive_dns and samples context fields | DINT-03 | Visual rendering in browser | Run app, enrich a domain IOC, verify ThreatMiner card shows passive DNS entries and related samples |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
