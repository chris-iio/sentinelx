# Phase 6: Models, Parser, and Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-12
**Phase:** 06-models-parser-and-foundation
**Areas discussed:** LoginEvent model fields, Parser error handling, Config section design, Module organization

---

## LoginEvent Model Fields

### Auth method capture

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, store auth method | LoginEvent gets auth_method field ('password' or 'publickey'). Future-proofs for rules like 'flag password auth from external IPs'. | ✓ |
| No, just parse it to match | Use patterns to identify lines but don't store the method. Minimal model. | |
| You decide | Claude picks based on codebase patterns. | |

**User's choice:** Yes, store auth method
**Notes:** Enables future detection rules based on auth method.

### Hostname vs IP representation (PARSE-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Boolean is_hostname flag | source_ip: str + is_hostname: bool. Simple, explicit. | |
| Optional IP + optional hostname | source_ip: str | None + hostname: str | None. Exactly one set. More precise. | ✓ |
| Single field, always string | source: str. Downstream checks via regex/ipaddress. Minimal model. | |

**User's choice:** Optional IP + optional hostname
**Notes:** More precise type representation — exactly one field set per event.

### Debug information

| Option | Description | Selected |
|--------|-------------|----------|
| Line number only | line_number: int. Enough to trace back without memory bloat. | |
| Both line number and raw line | line_number: int + raw_line: str. Full traceability but doubles memory per event. | ✓ |
| Neither — keep model clean | No debug fields. Parser logs with context; model stays minimal. | |

**User's choice:** Both line number and raw line
**Notes:** Full traceability prioritized over memory efficiency.

---

## Parser Error Handling

### Malformed line handling

| Option | Description | Selected |
|--------|-------------|----------|
| Skip + collect summary | Silent skip, return parse summary with counts. No per-line warnings. | |
| Skip + log warnings | Skip and log each unrecognized line. Noisy for large files. | |
| Skip + summary + warnings | Both: structured summary AND warnings for partial SSH match failures. | ✓ |

**User's choice:** Skip + summary + warnings
**Notes:** Summary for analyst confidence, warnings for debugging edge cases.

### Auth method breadth

| Option | Description | Selected |
|--------|-------------|----------|
| Only password + publickey | Strict PARSE-01 match. Simple. | |
| Any 'Accepted' method | Generic match captures keyboard-interactive, gssapi, etc. | |
| You decide | Claude picks based on real-world auth.log patterns. | ✓ |

**User's choice:** You decide (Claude's discretion)
**Notes:** None.

---

## Config Section Design

### Time format

| Option | Description | Selected |
|--------|-------------|----------|
| Single range string | normal_hours = 06:00-22:00. One key, compact. | ✓ |
| Two separate keys | normal_hours_start = 06:00 and normal_hours_end = 22:00. Explicit. | |
| You decide | Claude picks based on ConfigStore patterns. | |

**User's choice:** Single range string
**Notes:** Compact format, familiar to sysadmins.

### Future config keys

| Option | Description | Selected |
|--------|-------------|----------|
| Only normal hours for now | Just CFG-01. YAGNI. | |
| Reserve known keys | Placeholder constants for travel_threshold_hours, max_file_size_mb. | |
| You decide | Claude judges based on practicality. | ✓ |

**User's choice:** You decide (Claude's discretion)
**Notes:** None.

---

## Module Organization

### Code location

| Option | Description | Selected |
|--------|-------------|----------|
| app/ssh/ package | New top-level package alongside enrichment/ and pipeline/. | ✓ |
| app/enrichment/ssh/ subpackage | Nested under enrichment. Blurs domain model. | |
| Flat modules in app/ | No new package, just files. May get messy. | |

**User's choice:** app/ssh/ package
**Notes:** Mirrors existing package pattern, clean separation.

### Models file location

| Option | Description | Selected |
|--------|-------------|----------|
| Own file: app/ssh/models.py | SSH-specific models file. Clean domain boundary. | ✓ |
| Shared: app/models.py | Unified models module. Blurs boundaries. | |
| You decide | Claude picks based on patterns. | |

**User's choice:** Own file: app/ssh/models.py
**Notes:** SSH models don't depend on enrichment models — separate domain.

---

## Claude's Discretion

- Auth method breadth (password+publickey only vs generic "Accepted" match)
- Future config key pre-wiring for Phase 8

## Deferred Ideas

None — discussion stayed within phase scope.
