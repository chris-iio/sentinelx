# Coding Conventions

**Analysis Date:** 2026-04-06

## Naming Patterns

**Files:**
- Python: `snake_case` (e.g., `test_orchestrator.py`, `extractor.py`, `base_adapter.py`)
- TypeScript: `kebab-case` for modules (e.g., `verdict-compute.ts`, `row-factory.ts`), lowercase with hyphens
- Test files: `test_*.py` for unit/integration tests (pytest convention)
- Fixture modules: `conftest.py` for pytest fixtures (module scope)

**Functions:**
- Python: `snake_case` (e.g., `enrich_all()`, `extract_iocs()`, `_make_pre_raise_hook()`)
- TypeScript: `camelCase` (e.g., `computeWorstVerdict()`, `updateCardVerdict()`, `findCopyButtonForIoc()`)
- Private functions: Prefix with underscore in both languages (e.g., `_parse_response()`, `_make_mock_adapter()`)

**Variables:**
- Python: `snake_case` for all variables (e.g., `max_workers`, `supported_types`, `detection_count`)
- TypeScript: `camelCase` for local variables and module state (e.g., `sortTimers`, `allResults`, `iocVerdicts`)
- Constants: `UPPER_SNAKE_CASE` for module-level constants (e.g., `_MALICIOUS_THRESHOLD`, `_BACKOFF_BASE`)

**Types:**
- Python: `PascalCase` for classes, frozen dataclasses (e.g., `EnrichmentResult`, `EnrichmentError`, `BaseHTTPAdapter`)
- TypeScript: `PascalCase` for interfaces, types (e.g., `EnrichmentResultItem`, `VerdictEntry`, `Page`)
- Module-level type aliases: Descriptive `PascalCase` (e.g., `VerdictKey`)

## Code Style

**Formatting:**
- **Python**: `ruff` formatter with `line-length = 100` (configured in `pyproject.toml`)
- **TypeScript**: `prettier` with esbuild (IIFE output for browser), strict `noEmit` compilation
- **Linting**: Ruff with rules ["E", "F", "W", "S", "B"] — security (S) and bugbear (B) enabled
- **Per-file exclusions**: Tests ignore E501 (line length) and S101 (assert usage)

**Imports:**
- Python: `from __future__ import annotations` at top of all modules for forward reference support
- TypeScript: ES2022 module syntax with `moduleResolution: "Bundler"`

## Import Organization

**Order (Python):**
1. `from __future__ import annotations` (always first if present)
2. Standard library (e.g., `import logging`, `from dataclasses import dataclass`)
3. Third-party libraries (e.g., `import requests`, `from flask import Blueprint`)
4. Local app imports (e.g., `from app.enrichment.models import EnrichmentResult`)
5. Blank line between groups

**Order (TypeScript):**
1. Type imports with `import type` (e.g., `import type { EnrichmentItem } from "../types/api"`)
2. Value imports (e.g., `import { computeWorstVerdict } from "./verdict-compute"`)
3. Relative imports grouped by depth

**Path Aliases:**
- None currently configured; use relative paths with `../` for sibling modules

## Error Handling

**Patterns (Python):**
- Explicit exception handling at library boundaries: try-catch blocks in `extract_iocs()` catch expected exceptions (ValueError, TypeError, AttributeError, UnicodeError) from `iocextract` and `iocsearcher` libraries
- Log warnings with context: `logger.warning("message", exc_info=True)` for unexpected errors (lines 69, 77 in `extractor.py`)
- Return error objects for application-level failures: `EnrichmentError(ioc=ioc, provider=self.name, error="message")` for provider lookup failures
- HTTP errors via `safe_request()` — adapters implement optional `_make_pre_raise_hook()` to convert HTTP status codes to verdicts (e.g., OTX adapter converts 404 to "no_data")
- Thread safety: Use `Lock()` for all mutations to shared `_jobs` dict in orchestrator (line 86: `self._lock = Lock()`)

**Patterns (TypeScript):**
- Try-catch in async operations (e.g., `fetch()` calls in polling loops)
- Return `null` or `undefined` for "not found" states (not throwing); nullable types force callers to handle absence
- DOM safety: Use `createElement()` + `textContent` exclusively; never `innerHTML` (SEC-08 enforcement)
- Graceful degradation: Silent return on missing DOM elements (e.g., `findCopyButtonForIoc()` returns `null` if button not found, caller checks before use)

## Logging

**Framework:** Python `logging` module (standard library)

**Patterns:**
- Module-level logger: `logger = logging.getLogger(__name__)` in every module
- Log at appropriate levels:
  - `logger.warning()`: Expected error conditions (library exceptions, 404 not found)
  - `logger.info()`: Major state changes (job started, job complete)
  - `logger.debug()`: Detailed flow information (for debugging)
- Include context: `exc_info=True` when logging caught exceptions

**JavaScript/TypeScript:**
- No `console.log()` in production code (enforced by post-tool hooks)
- Use proper logging if needed (currently inline logging minimal)

## Comments

**When to Comment:**
- **Module docstrings (required):** Every Python module has `"""Docstring at top"""` explaining purpose, design decisions, and security notes
- **Class docstrings (required):** Every class has docstring with purpose, attributes, and usage notes
- **Function docstrings (required):** Functions explain Args, Returns, and notable behavior
- **Complex logic (when needed):** Inline comments explain "why" not "what" (e.g., semaphore placement in orchestrator — see lines 12-14 of `orchestrator.py`)
- **Security notes:** Flagged as "Security:" or "CRITICAL:" in docstrings (e.g., OTX type map handling)
- **Constants:** Define threshold constants with comments explaining their purpose (e.g., `_MALICIOUS_THRESHOLD = 5  # pulse_info.count >= this`)

**JSDoc/TSDoc:**
- TypeScript: Use `/** ... */` block comments for functions and types (e.g., `verdict-compute.test.ts` helper functions)
- Document type parameters and return types explicitly
- Use `@param` and `@returns` tags for clarity

## Function Design

**Size:**
- Python: Typical 20-50 lines; max ~100 for complex template methods (e.g., `BaseHTTPAdapter.lookup()`)
- TypeScript: Typical 30-80 lines; debounced wrappers and event handlers may exceed this

**Parameters:**
- Python: Use keyword-only arguments where sensible (e.g., `__init__(self, allowed_hosts, *, api_key: str = "")` in adapters)
- TypeScript: Optional parameters with defaults (e.g., `attr(el: Element, name: string, fallback = "")`)

**Return Values:**
- Python: Return dataclass instances for structured results; return `EnrichmentResult | EnrichmentError` union types for operations that may fail
- TypeScript: Return `T | null` for potentially missing values; use discriminated unions for multi-branch results (e.g., `EnrichmentResultItem | EnrichmentErrorItem`)

## Module Design

**Exports (Python):**
- Adapters and core services are imported by name: `from app.enrichment.adapters.otx import OTXAdapter`
- Factories and helpers live in dedicated modules: `helpers.py` for test helpers, `_helpers.py` for route helpers
- Configuration is accessed through module-level instances (e.g., `CONFIG_STORE = ConfigStore()`)

**Exports (TypeScript):**
- Modules export named functions/types: `export function computeWorstVerdict()`, `export interface VerdictEntry`
- Module state is private: Use `const` for module-level maps (e.g., `const sortTimers: Map<string, ...> = new Map()`)

**Barrel Files:**
- `tests/e2e/pages/__init__.py` re-exports page classes for cleaner imports: `from tests.e2e.pages import IndexPage, ResultsPage`
- TypeScript modules do not use barrel files; import from specific modules

## Immutability

**Python:**
- Dataclasses are frozen: `@dataclass(frozen=True)` for `EnrichmentResult`, `EnrichmentError` (line 13, 36 in `models.py`)
- Dict/list operations create new objects: `orchestrator._jobs = OrderedDict()` (not mutated in-place)

**TypeScript:**
- Spread operator for immutable updates: `{ ...user, name }`
- No in-place mutations of DOM-bound state; re-render instead

## Security-Relevant Patterns

**SSRF Prevention (SEC-16):**
- HTTP adapters require `allowed_hosts` allowlist: `BaseHTTPAdapter.__init__(self, allowed_hosts: list[str], *, api_key: str = "")`
- All adapters instantiate with specific host allowlists passed from setup

**DOM Safety (SEC-08):**
- No `innerHTML` usage: `attr()` utility returns safe string values, DOM built via `createElement() + textContent`
- CSS.escape() for attribute selectors: `'.copy-btn[data-value="' + CSS.escape(iocValue) + '"]'` in enrichment.ts line 86

**Input Validation:**
- JSON API validates required fields: `text` is required and non-empty (lines 53-55 in `api.py`)
- Mode validation: whitelist check against `_VALID_MODES = {"offline", "online"}`

---

*Convention analysis: 2026-04-06*
