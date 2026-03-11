---
phase: 01
slug: zero-auth-ip-intelligence-known-good
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + unittest.mock |
| **Config file** | pyproject.toml |
| **Quick run command** | `python3 -m pytest tests/test_ip_api.py tests/test_hashlookup.py -x -q` |
| **Full suite command** | `python3 -m pytest -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/test_ip_api.py tests/test_hashlookup.py tests/test_shodan.py tests/test_registry_setup.py -x -q`
- **After every plan wave:** Run `python3 -m pytest -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | EPROV-01 | unit | `python3 -m pytest tests/test_shodan.py -x -q` | ✅ | ⬜ pending |
| 01-02-01 | 02 | 1 | HINT-01 | unit | `python3 -m pytest tests/test_hashlookup.py -x -q` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | HINT-02 | type-check | `make typecheck` | ✅ | ⬜ pending |
| 01-02-03 | 02 | 1 | HINT-02 | visual | Browser smoke test | ❌ visual | ⬜ pending |
| 01-03-01 | 03 | 2 | IPINT-01 | unit | `python3 -m pytest tests/test_ip_api.py -x -q` | ❌ W0 | ⬜ pending |
| 01-03-02 | 03 | 2 | IPINT-02 | unit | `python3 -m pytest tests/test_ip_api.py::test_reverse_dns -x` | ❌ W0 | ⬜ pending |
| 01-03-03 | 03 | 2 | IPINT-03 | unit | `python3 -m pytest tests/test_ip_api.py::test_proxy_flags -x` | ❌ W0 | ⬜ pending |
| 01-03-04 | 03 | 2 | IPINT-01/02/03 | integration | `python3 -m pytest tests/test_registry_setup.py -x -q` | ✅ (update) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_ip_api.py` — stubs for IPINT-01, IPINT-02, IPINT-03
- [ ] `tests/test_hashlookup.py` — stubs for HINT-01
- [ ] Update `tests/test_registry_setup.py` — provider count assertion 8 → 10

*Existing infrastructure covers EPROV-01 and type-check requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Blue KNOWN GOOD badge visually distinct | HINT-02 | CSS visual styling | 1. Paste known NSRL hash (e.g. calc.exe MD5) 2. Verify blue badge in summary row 3. Verify "Known Good" filter chip works |
| IP Context row appears first, no badge | IPINT-01/02/03 | DOM layout + no-badge rendering | 1. Paste any public IP 2. Verify IP Context row at top of detail rows 3. Verify no verdict badge on IP Context row |
| CPEs and tags visible in Shodan card | EPROV-01 | Visual rendering of new fields | 1. Paste IP with known CPEs 2. Expand Shodan card 3. Verify CPE and tag pills rendered |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
