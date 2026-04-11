# Phase 6: Models, Parser, and Foundation - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

A correct, fully-tested SSH log parser exists and all blocking infrastructure changes are in place before any detection logic is written. This phase delivers: LoginEvent data model, auth.log parser with BSD syslog and RFC3339 timestamp support, ParseSummary for analyst feedback, ConfigStore `[ssh]` section for normal-hours window, and MAX_CONTENT_LENGTH increase to 5 MB.

</domain>

<decisions>
## Implementation Decisions

### LoginEvent model fields
- **D-01:** LoginEvent is a frozen dataclass with fields: username (str), source_ip (str | None), hostname (str | None), timestamp (datetime), auth_method (str — "password" or "publickey"), line_number (int), raw_line (str)
- **D-02:** source_ip and hostname are mutually exclusive optionals — exactly one is set per event. When hostname is present (UseDNS enabled), downstream GeoIP lookup is skipped for that event
- **D-03:** auth_method is stored explicitly, enabling future detection rules like "flag password auth from external IPs"
- **D-04:** raw_line and line_number provide full traceability back to the source file for debugging

### Parser error handling
- **D-05:** Parser returns a ParseSummary alongside the event list — includes total_lines, parsed_count, skipped_count at minimum. The UI (Phase 9) can display "Parsed 847 of 12,304 lines" for analyst confidence
- **D-06:** Lines that partially match SSH event patterns but fail to fully parse generate logger.warning() with line number and content — aids debugging without cluttering the analyst-facing summary
- **D-07:** Completely unrecognized lines (non-SSH syslog, blank lines, etc.) are silently skipped — counted in skipped_count but not logged individually

### Config section design
- **D-08:** Normal-hours window stored as single range string in `[ssh]` section: `normal_hours = 06:00-22:00`. Parser splits on dash, validates HH:MM format
- **D-09:** Default is 06:00-22:00 when the key is absent (CFG-01 requirement)

### Module organization
- **D-10:** SSH code lives in `app/ssh/` as a new top-level package, mirroring `app/enrichment/` and `app/pipeline/`. This package will contain models.py, parser.py, and in later phases detector.py (Phase 8) and routes (Phase 9)
- **D-11:** SSH models are in `app/ssh/models.py` — separate from enrichment models. Clean domain boundary: SSH models don't depend on enrichment models

### Claude's Discretion
- Auth method breadth: Whether to match only "Accepted password"/"Accepted publickey" (strict PARSE-01) or generically match "Accepted <method>" to capture keyboard-interactive, gssapi, etc. Claude will decide based on real-world auth.log patterns
- Future config keys: Whether to pre-wire constants or helper methods for anticipated Phase 8 config (e.g., travel_threshold_hours) or keep strictly to CFG-01 scope

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — PARSE-01 through PARSE-04, WEB-06, CFG-01 requirements with acceptance criteria

### Architecture and patterns
- `.planning/codebase/ARCHITECTURE.md` — Existing layered architecture, data flow patterns, frozen dataclass conventions
- `.planning/codebase/CONVENTIONS.md` — Naming patterns, error handling, import organization, immutability rules

### Existing infrastructure
- `app/enrichment/models.py` — Frozen dataclass pattern reference (EnrichmentResult, EnrichmentError)
- `app/enrichment/config_store.py` — ConfigStore with `_set_value()`, `_read_config()` for adding `[ssh]` section support
- `app/__init__.py` — App factory with MAX_CONTENT_LENGTH (currently 512KB → needs 5MB), blueprint registration pattern
- `app/config.py` — Config class with MAX_CONTENT_LENGTH constant

### Prior decisions
- `.planning/STATE.md` §Accumulated Context — GeoIP is ipinfo.io, detector receives geo_map, BSD year rollover handled in Phase 6

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ConfigStore._set_value()` / `_read_config()`: Already supports arbitrary INI sections — adding `[ssh]` section is a natural extension with get/set helper methods
- `@dataclass(frozen=True)` pattern: Well-established for EnrichmentResult, IOC — LoginEvent follows the same immutability convention
- `logging.getLogger(__name__)`: Module-level logger pattern used in every module — parser follows same convention

### Established Patterns
- **Frozen dataclasses** for all data models — LoginEvent and ParseSummary must be frozen
- **Union return types** for operations that may fail — parser could return `list[LoginEvent]` alongside `ParseSummary` (not raising exceptions)
- **Blueprint registration** in `create_app()` — SSH routes (Phase 9) will register as a new blueprint
- **Module docstrings** required on all Python modules with purpose, security notes

### Integration Points
- `app/__init__.py` create_app(): MAX_CONTENT_LENGTH must increase from 512KB to 5MB (WEB-06). The 413 error handler message also needs updating
- `app/config.py`: MAX_CONTENT_LENGTH constant definition
- `app/enrichment/config_store.py`: Add `get_ssh_normal_hours()` / `set_ssh_normal_hours()` helper methods (or generic section reader)
- Future (Phase 9): `app/ssh/routes.py` blueprint registered in create_app()

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User wants a rich LoginEvent model with full traceability (line numbers + raw lines), which suggests analyst debugging is a priority.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-models-parser-and-foundation*
*Context gathered: 2026-04-12*
