---
phase: 06-models-parser-and-foundation
plan: "01"
subsystem: ssh-models
tags: [dataclasses, models, ssh, frozen, tdd]
dependency_graph:
  requires: []
  provides:
    - app/ssh/models.py::LoginEvent
    - app/ssh/models.py::ParseSummary
  affects:
    - app/ssh/parser.py (Phase 6 Plan 02 — consumes LoginEvent)
    - Phase 7 GeoIP wrapper (consumes LoginEvent.source_ip)
    - Phase 8 detector (consumes LoginEvent, ParseSummary)
    - Phase 9 routes/UI (renders LoginEvent fields)
tech_stack:
  added:
    - app/ssh/ Python package (new top-level package mirroring app/enrichment/)
  patterns:
    - "@dataclass(frozen=True) — matches existing EnrichmentResult / IOC convention"
    - "from __future__ import annotations — PEP 563 deferred evaluation"
    - "str | None union fields — Python 3.10+ union syntax"
key_files:
  created:
    - app/ssh/__init__.py
    - app/ssh/models.py
    - tests/test_ssh_models.py
  modified: []
decisions:
  - "D-02 invariant is a parser responsibility, not model enforcement — LoginEvent is a plain data container"
  - "auth_method stored as raw string (not enum) to support future detection rules without schema changes"
  - "ParseSummary includes warning_count (per D-05 spec) alongside total/parsed/skipped"
metrics:
  duration_seconds: 103
  completed_date: "2026-04-11T22:50:50Z"
  tasks_completed: 1
  tasks_total: 1
  files_created: 3
  files_modified: 0
requirements_satisfied:
  - PARSE-01
  - PARSE-04
---

# Phase 6 Plan 01: SSH Models Summary

**One-liner:** LoginEvent and ParseSummary frozen dataclasses with 15 tests covering construction, immutability, D-02 invariant documentation, and field type semantics.

## What Was Built

### app/ssh/__init__.py
Package marker for the new `app/ssh/` top-level package, mirroring the `app/enrichment/` and `app/pipeline/` structure per D-10. Module docstring sets scope: models, parser, detector (Phase 8), routes (Phase 9).

### app/ssh/models.py
Two frozen dataclasses matching project convention:

**LoginEvent** — 7 fields per D-01:
- `username: str` — authenticated user
- `source_ip: str | None` — IPv4 or IPv6 address (None when hostname is set)
- `hostname: str | None` — resolved hostname when UseDNS enabled (None when source_ip is set)
- `timestamp: datetime` — parsed event time
- `auth_method: str` — stored as raw string ("password", "publickey", "keyboard-interactive/pam", etc.) per D-03
- `line_number: int` — 1-based line number for traceability per D-04
- `raw_line: str` — original unparsed log line per D-04

**ParseSummary** — 4 counter fields per D-05:
- `total_lines`, `parsed_count`, `skipped_count`, `warning_count`
- Invariant documented in docstring: `parsed_count + skipped_count + warning_count == total_lines`

### tests/test_ssh_models.py
15 unit tests across 3 test classes:
- `TestLoginEvent` (9 tests): construction with source_ip/hostname, IPv6, keyboard-interactive/pam, frozen enforcement, equality, field type assertions
- `TestParseSummary` (4 tests): construction, frozen enforcement, invariant assertion, all-zero edge case
- `TestLoginEventInvariant` (2 tests): documents that D-02 is a parser responsibility — model permits both-None and both-set to keep LoginEvent as a plain container

## Decisions Made

- **D-02 as parser contract, not model enforcement:** LoginEvent is a data container; raising in `__post_init__` would prevent the invariant from being tested at the parser layer and would break deserialization edge cases. The parser contract test (Plan 02) enforces exactly-one semantics.
- **auth_method as raw string:** An enum would lock the model to a fixed set of auth methods. Storing as plain string allows "keyboard-interactive/pam" and any future OpenSSH variants without a schema migration.
- **No imports from app.enrichment:** D-11 clean domain boundary maintained — SSH models are fully independent.

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries were introduced. The `raw_line` field's SEC-08 obligation (textContent-only rendering) is documented in the module docstring and the LoginEvent class docstring as required by T-06-01.

## Self-Check: PASSED

- app/ssh/__init__.py: FOUND
- app/ssh/models.py: FOUND
- tests/test_ssh_models.py: FOUND
- Commit 0c8c320: FOUND
- All 15 tests pass: VERIFIED
- `grep -c "@dataclass(frozen=True)" app/ssh/models.py` returns 2: VERIFIED
- No imports from app.enrichment: VERIFIED
