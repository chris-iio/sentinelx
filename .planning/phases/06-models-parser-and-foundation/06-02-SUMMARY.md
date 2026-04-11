---
phase: 06-models-parser-and-foundation
plan: 02
subsystem: config-infrastructure
tags: [config, ssh, upload-limit, tdd]
dependency_graph:
  requires: []
  provides: [ConfigStore.get_ssh_normal_hours, ConfigStore.set_ssh_normal_hours, MAX_CONTENT_LENGTH=5MB]
  affects: [app/enrichment/config_store.py, app/config.py, app/__init__.py]
tech_stack:
  added: []
  patterns: [configparser INI sections, TDD red-green]
key_files:
  created: []
  modified:
    - app/enrichment/config_store.py
    - app/config.py
    - app/__init__.py
    - tests/test_config_store.py
    - tests/test_routes.py
decisions:
  - SSH config uses _SSH_SECTION = "ssh" in existing config.ini (not a new file)
  - set_ssh_normal_hours delegates to _set_value() for automatic cache invalidation
  - 413 message updated from "paste" to "upload" to reflect new file upload use case
metrics:
  duration: ~8 minutes
  completed: 2026-04-12
  tasks_completed: 2
  files_modified: 5
---

# Phase 06 Plan 02: ConfigStore SSH Methods and MAX_CONTENT_LENGTH 5 MB Summary

SSH normal-hours config methods added to ConfigStore with [ssh] INI section, and MAX_CONTENT_LENGTH raised from 512 KB to 5 MB with 413 handler updated and regression test added.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add SSH normal-hours methods to ConfigStore | 737df3b | app/enrichment/config_store.py, tests/test_config_store.py |
| 2 | Increase MAX_CONTENT_LENGTH to 5 MB, update 413 handler, add regression test | 2a72f87 | app/config.py, app/__init__.py, tests/test_routes.py |

## What Was Built

**Task 1 — SSH normal-hours ConfigStore (TDD)**

Added three module-level constants and two methods to `app/enrichment/config_store.py`:
- `_SSH_SECTION = "ssh"`, `_SSH_NORMAL_HOURS_KEY = "normal_hours"`, `_SSH_NORMAL_HOURS_DEFAULT = "06:00-22:00"`
- `get_ssh_normal_hours()` — reads `[ssh]` section, returns `"06:00-22:00"` default when absent
- `set_ssh_normal_hours(hours_range)` — delegates to `_set_value()` for cache-safe writes

Added `TestSshSection` class (7 tests) to `tests/test_config_store.py` covering:
- Default returned when no config file exists
- Default returned when config exists but lacks `[ssh]` section
- set/get roundtrip
- Overwrite (latest value wins)
- Disk persistence (new instance reads back value)
- Coexistence with `[virustotal]`, `[providers]`, `[cache]` sections
- Default returned when `[ssh]` section exists but `normal_hours` key absent

TDD flow: 7 tests written first (RED: all fail with `AttributeError`), then constants + methods added (GREEN: all 23 pass).

**Task 2 — MAX_CONTENT_LENGTH 5 MB**

- `app/config.py`: `512 * 1024` → `5 * 1024 * 1024` with updated comment `# 5 MB — covers SSH auth.log uploads (SEC-12)`
- `app/__init__.py`: 413 handler updated from `"Maximum paste size is 512 KB."` to `"Maximum upload size is 5 MB."`
- `tests/test_routes.py`: Added `test_max_content_length_is_5mb()` asserting `Config.MAX_CONTENT_LENGTH == 5 * 1024 * 1024`

## Verification Results

```
python3 -c "from app.config import Config; assert Config.MAX_CONTENT_LENGTH == 5 * 1024 * 1024"  # OK
grep "Maximum upload size is 5 MB" app/__init__.py  # OK
python3 -m pytest tests/test_routes.py -k "content_length" -x -q   # 1 passed
python3 -m pytest tests/test_config_store.py -x -q                  # 23 passed
python3 -m pytest tests/ -x -q -m "not e2e"                         # 879 passed
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. Both changes are fully wired: ConfigStore methods read/write real config.ini, MAX_CONTENT_LENGTH is the live Flask limit.

## Threat Flags

No new threat surface introduced. MAX_CONTENT_LENGTH increase (T-06-05) and ConfigStore [ssh] section (T-06-04) were pre-registered in the plan's threat model and both accepted.

## Self-Check: PASSED

- `app/enrichment/config_store.py` — modified, contains `_SSH_SECTION`, `get_ssh_normal_hours`, `set_ssh_normal_hours`
- `app/config.py` — modified, contains `5 * 1024 * 1024`
- `app/__init__.py` — modified, contains `"Maximum upload size is 5 MB."`
- `tests/test_config_store.py` — modified, contains `TestSshSection`
- `tests/test_routes.py` — modified, contains `test_max_content_length_is_5mb`
- Commit `737df3b` — exists (Task 1)
- Commit `2a72f87` — exists (Task 2)
