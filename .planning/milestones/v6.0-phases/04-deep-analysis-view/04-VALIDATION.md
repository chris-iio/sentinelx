---
phase: 04
slug: deep-analysis-view
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | none — existing infrastructure |
| **Quick run command** | `python -m pytest tests/test_annotation_store.py tests/test_ioc_detail_routes.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_annotation_store.py tests/test_ioc_detail_routes.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | DEEP-01 | integration | `python -m pytest tests/test_ioc_detail_routes.py::test_detail_page_200 -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | DEEP-01 | integration | `python -m pytest tests/test_ioc_detail_routes.py::test_detail_page_empty_cache -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | DEEP-01 | integration | `python -m pytest tests/test_ioc_detail_routes.py::test_detail_page_with_results -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | DEEP-01 | integration | `python -m pytest tests/test_ioc_detail_routes.py::test_detail_url_ioc -x` | ❌ W0 | ⬜ pending |
| 04-01-05 | 01 | 1 | DEEP-01 | unit | `python -m pytest tests/test_cache_store.py::test_get_all_for_ioc -x` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | DEEP-02 | unit | `python -m pytest tests/test_annotation_store.py::test_init -x` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | DEEP-02 | unit | `python -m pytest tests/test_annotation_store.py::test_notes_round_trip -x` | ❌ W0 | ⬜ pending |
| 04-02-03 | 02 | 2 | DEEP-02 | integration | `python -m pytest tests/test_annotation_store.py::test_notes_survive_cache_clear -x` | ❌ W0 | ⬜ pending |
| 04-02-04 | 02 | 2 | DEEP-02 | integration | `python -m pytest tests/test_ioc_detail_routes.py::test_api_set_notes -x` | ❌ W0 | ⬜ pending |
| 04-02-05 | 02 | 2 | DEEP-02 | integration | `python -m pytest tests/test_ioc_detail_routes.py::test_api_notes_size_cap -x` | ❌ W0 | ⬜ pending |
| 04-02-06 | 02 | 2 | DEEP-03 | unit | `python -m pytest tests/test_annotation_store.py::test_tags_round_trip -x` | ❌ W0 | ⬜ pending |
| 04-02-07 | 02 | 2 | DEEP-03 | integration | `python -m pytest tests/test_ioc_detail_routes.py::test_api_add_tag -x` | ❌ W0 | ⬜ pending |
| 04-02-08 | 02 | 2 | DEEP-03 | integration | `python -m pytest tests/test_ioc_detail_routes.py::test_api_delete_tag -x` | ❌ W0 | ⬜ pending |
| 04-02-09 | 02 | 2 | DEEP-03 | unit | `python -m pytest tests/test_annotation_store.py::test_no_duplicate_tags -x` | ❌ W0 | ⬜ pending |
| 04-02-10 | 02 | 2 | DEEP-03 | integration | `python -m pytest tests/test_ioc_detail_routes.py::test_tags_on_results_page -x` | ❌ W0 | ⬜ pending |
| 04-02-11 | 02 | 2 | DEEP-04 | integration | `python -m pytest tests/test_ioc_detail_routes.py::test_graph_data_in_context -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_annotation_store.py` — stubs for DEEP-02, DEEP-03 (init, notes CRUD, tags CRUD, no-duplicates, survives cache clear)
- [ ] `tests/test_ioc_detail_routes.py` — stubs for DEEP-01 (route 200/empty/with-results, URL IOC), DEEP-02/03 API, DEEP-04 graph data
- [ ] Add `test_get_all_for_ioc` to existing `tests/test_cache_store.py`
- [ ] Add `<meta name="csrf-token">` to `app/templates/base.html`

*Existing infrastructure covers framework install — pytest already present.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SVG graph renders visually correct | DEEP-04 | Visual layout correctness not automatable | Open `/ioc/<type>/<value>` in browser, verify hub-and-spoke graph with colored verdict nodes |
| Filter bar shows tag pills | DEEP-03 | Dynamic UI interaction | Tag an IOC on detail page, navigate back, verify tag pill in filter bar |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
