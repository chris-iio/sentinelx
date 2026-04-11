---
phase: 6
slug: models-parser-and-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (configured in pyproject.toml) |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_ssh_models.py tests/test_ssh_parser.py tests/test_config_store.py -x` |
| **Full suite command** | `pytest -m 'not e2e'` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_ssh_models.py tests/test_ssh_parser.py tests/test_config_store.py -x`
- **After every plan wave:** Run `pytest -m 'not e2e'`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | PARSE-01 | — | N/A | unit | `pytest tests/test_ssh_models.py::TestLoginEvent -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | PARSE-01 | — | N/A | unit | `pytest tests/test_ssh_models.py::TestParseSummary -x` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 1 | PARSE-01 | T-06-01 | Malformed lines don't crash parser | unit | `pytest tests/test_ssh_parser.py::TestParserAccepted -x` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 1 | PARSE-02 | — | N/A | unit | `pytest tests/test_ssh_parser.py::TestTimestampBSD -x` | ❌ W0 | ⬜ pending |
| 06-02-03 | 02 | 1 | PARSE-02 | — | N/A | unit | `pytest tests/test_ssh_parser.py::TestTimestampRFC3339 -x` | ❌ W0 | ⬜ pending |
| 06-02-04 | 02 | 1 | PARSE-02 | — | N/A | unit | `pytest tests/test_ssh_parser.py::TestYearRollover -x` | ❌ W0 | ⬜ pending |
| 06-02-05 | 02 | 1 | PARSE-03 | — | N/A | unit | `pytest tests/test_ssh_parser.py::TestSourceExtraction -x` | ❌ W0 | ⬜ pending |
| 06-02-06 | 02 | 1 | PARSE-04 | — | N/A | unit | `pytest tests/test_ssh_parser.py::TestSourceExtraction -x` | ❌ W0 | ⬜ pending |
| 06-02-07 | 02 | 1 | PARSE-04 | — | Invariant: source_ip/hostname mutually exclusive | unit | `pytest tests/test_ssh_models.py::TestLoginEventInvariant -x` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 2 | WEB-06 | T-06-05 | MAX_CONTENT_LENGTH=5MB (larger than 512KB) | unit | `pytest tests/test_routes.py -k "content_length" -x` | ❌ W0 | ⬜ pending |
| 06-03-02 | 03 | 2 | CFG-01 | — | N/A | unit | `pytest tests/test_config_store.py::TestSshSection -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_ssh_models.py` — stubs for PARSE-01 (LoginEvent), PARSE-04 (invariant), ParseSummary fields
- [ ] `tests/test_ssh_parser.py` — stubs for PARSE-01, PARSE-02, PARSE-03, PARSE-04 with comprehensive fixtures
- [ ] `tests/test_config_store.py` — extend with `TestSshSection` class (file exists; add new class)
- [ ] `tests/test_routes.py` — assert `MAX_CONTENT_LENGTH == 5 * 1024 * 1024` (file exists; add test)

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
