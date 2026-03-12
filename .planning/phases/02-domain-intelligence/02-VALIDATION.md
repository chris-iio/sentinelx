---
phase: 02
slug: domain-intelligence
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, no config file) |
| **Config file** | none — see existing conftest.py |
| **Quick run command** | `python -m pytest tests/test_dns_lookup.py tests/test_crtsh.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_dns_lookup.py tests/test_crtsh.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | DINT-01 | unit | `python -m pytest tests/test_dns_lookup.py -x -q` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | DINT-01 | unit | `python -m pytest tests/test_dns_lookup.py -x -q` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | DINT-02 | unit | `python -m pytest tests/test_crtsh.py -x -q` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | DINT-02 | unit | `python -m pytest tests/test_crtsh.py -x -q` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | DINT-01, DINT-02 | integration | `python -m pytest tests/test_registry_setup.py -x -q` | ✅ | ⬜ pending |
| 02-03-02 | 03 | 2 | DINT-01, DINT-02 | visual | manual | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_dns_lookup.py` — stubs for DINT-01 (DnsAdapter unit tests, mocked via `unittest.mock.patch("dns.resolver.Resolver")`)
- [ ] `tests/test_crtsh.py` — stubs for DINT-02 (CrtShAdapter unit tests, mocked via `unittest.mock.patch("requests.get")`)

*Existing test infrastructure (pytest, conftest.py, mock patterns) covers scaffolding needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| DNS records display in domain result card | DINT-01 | Visual rendering | Submit a domain IOC, verify A/MX/NS/TXT rows appear |
| Cert transparency history display in domain result card | DINT-02 | Visual rendering | Submit a domain IOC, verify cert count/date range/subdomains appear |
| Domain cards work with no API keys | DINT-01, DINT-02 | Config-dependent | Clear all API keys, submit domain, verify DNS+CT data still appears |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
