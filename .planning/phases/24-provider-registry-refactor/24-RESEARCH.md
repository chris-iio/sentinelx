# Phase 24: Provider Registry Refactor - Research

**Researched:** 2026-03-02
**Domain:** Python typing.Protocol, plugin registry pattern, configparser multi-section, TypeScript DOM data attributes
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Provider Protocol (Task 24.1)
- Use `typing.Protocol` with `@runtime_checkable` for structural subtyping
- Protocol defines: `name: str`, `supported_types: set[IOCType] | frozenset[IOCType]`, `requires_api_key: bool`, `lookup(IOC) -> EnrichmentResult | EnrichmentError`, `is_configured() -> bool`
- All three existing adapters (VTAdapter, MBAdapter, TFAdapter) must satisfy the protocol via `isinstance()` check
- Add `name`, `requires_api_key`, and `is_configured()` attributes to existing adapters
- TDD: tests first using `isinstance(adapter, Provider)` assertions

#### Provider Registry (Task 24.2)
- `ProviderRegistry` class with `register()`, `all()`, `configured()`, `providers_for_type(IOCType)`, `provider_count_for_type(IOCType)`
- Thread safety: populated once at app startup, read-only during request handling
- Duplicate registration raises `ValueError`
- `providers_for_type()` returns only configured providers that support the given IOC type

#### ConfigStore Multi-Provider (Task 24.3)
- Expand existing ConfigStore with `[providers]` INI section
- New methods: `get_provider_key(name)`, `set_provider_key(name, key)`, `all_provider_keys()`
- Existing `get_vt_api_key()` / `set_vt_api_key()` remain backward-compatible
- Keys stored with lowercase provider identifiers (e.g., "greynoise", "otx")

#### Route Wiring (Task 24.4)
- Create `app/enrichment/setup.py` with `build_registry(allowed_hosts, config_store)` — single place for all provider registration
- Replace hardcoded adapter imports/instantiation in routes.py with registry
- Online mode check: "at least one configured provider" instead of "VT key present"
- Existing route tests must still pass — may need mock updates from patching individual adapters to patching registry/setup

#### Dynamic Provider Counts (Task 24.5)
- Pass `provider_counts` dict from backend to frontend via `data-provider-counts` template attribute
- Replace hardcoded `IOC_PROVIDER_COUNTS` in TypeScript with `getProviderCounts()` function that reads from DOM
- Legacy fallback to hardcoded values if data attribute missing
- Update `enrichment.ts` to call dynamic function instead of importing static constant

### Claude's Discretion
- Error handling details within Provider protocol implementations
- Internal organization of registry test fixtures
- Whether to add `__repr__` or other convenience methods to Registry
- TypeScript build verification approach

### Deferred Ideas (OUT OF SCOPE)
- Settings page dynamic provider cards (Phase 27 scope)
- Individual provider adapter implementations (Phases 25-26)
- Results UX unified summary cards (Phase 27)
- Orchestrator refactoring to use registry directly (stretch — routes handle it for now)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REG-01 | A `Provider` protocol exists with `name`, `supported_types`, `requires_api_key`, `lookup()`, and `is_configured()` — all three existing adapters satisfy it via `isinstance()` check | `typing.Protocol` + `@runtime_checkable` pattern; isinstance() works structurally at runtime |
| REG-02 | A `ProviderRegistry` class manages adapter registration and lookup by IOC type — adding a new provider requires only creating an adapter file and registering it in `setup.py` | Registry + setup.py wiring pattern; frozen after startup |
| REG-03 | The orchestrator queries the registry instead of hardcoding adapter lists — removing an adapter from registration makes it disappear from enrichment results | Registry's `providers_for_type()` replaces the hardcoded `adapters_list` in routes.py `analyze()` |
| REG-04 | ConfigStore supports multi-provider API key storage via `[providers]` INI section — each provider can independently store/retrieve its API key | configparser multi-section expansion; backward-compatible with existing `[virustotal]` section |
| REG-05 | The settings page dynamically renders provider cards based on registered providers — no template changes needed when adding providers (Note: ROADMAP states this; CONTEXT.md defers full settings card rendering to Phase 27; Task 24.5 covers dynamic provider counts for frontend) | `data-provider-counts` DOM attribute + `getProviderCounts()` TypeScript function |
</phase_requirements>

---

## Summary

Phase 24 is a pure refactoring phase — no new user-visible features, no new providers. The goal is to convert SentinelX's hardcoded 3-adapter wiring into a plugin-style architecture so that Phases 25-26 can add new providers by dropping in one file and one registration line.

The technical domain is well-understood Python: `typing.Protocol` with `@runtime_checkable` is the idiomatic way to define structural interfaces in Python 3.8+ without forcing inheritance. The existing codebase already uses frozen dataclasses, configparser, and thread-safe patterns — all consistent with what Phase 24 requires. The key risk is test suite compatibility: 12 route tests currently mock `app.routes.VTAdapter`, `app.routes.MBAdapter`, and `app.routes.TFAdapter` individually; after the refactor they will need to mock `app.enrichment.setup.build_registry` instead.

The TypeScript half (Task 24.5) is a targeted change: replace the hardcoded `IOC_PROVIDER_COUNTS` constant in `types/ioc.ts` with a runtime function that reads a `data-provider-counts` JSON attribute from the `.page-results` DOM element. This keeps provider count data flowing from backend to frontend dynamically. The esbuild pipeline requires no changes — this is purely a TypeScript module edit.

**Primary recommendation:** Implement tasks in strict order (24.1 → 24.2 → 24.3 → 24.4 → 24.5) since each depends on the previous. Run the full pytest suite after each task to catch regressions immediately. The route test updates in Task 24.4 are the highest-complexity step.

---

## Standard Stack

### Core (already in project)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `typing.Protocol` | Python 3.8+ stdlib | Structural subtyping for Provider interface | No inheritance required; `isinstance()` works with `@runtime_checkable` |
| `typing.runtime_checkable` | Python 3.8+ stdlib | Enables `isinstance(obj, Protocol)` checks at runtime | Required for TDD test assertions |
| `configparser` | Python stdlib | INI-format multi-section config storage | Already used in ConfigStore; adding a `[providers]` section requires no new imports |
| `pytest` | Already installed | Test framework for all unit tests | Already in use with 224 tests |
| `unittest.mock` | Python stdlib | Mocking for route tests | Already used extensively in `test_routes.py` |

### Supporting (already in project)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `from __future__ import annotations` | Python 3.10 | Postponed annotation evaluation | All new Python files in this project use it |
| `frozenset` | Python builtin | Immutable set for `supported_types` | TFAdapter already uses it; Protocol must accept both `set` and `frozenset` |

### No New Dependencies

This phase requires zero new pip packages. All patterns use Python stdlib and existing project dependencies.

**No installation required** — all tooling is already present.

---

## Architecture Patterns

### Recommended File Structure

```
app/enrichment/
├── provider.py          # NEW: Provider Protocol definition
├── registry.py          # NEW: ProviderRegistry class
├── setup.py             # NEW: build_registry() factory function
├── config_store.py      # MODIFIED: add [providers] section methods
├── orchestrator.py      # UNCHANGED: already accepts adapters list
├── models.py            # UNCHANGED
├── http_safety.py       # UNCHANGED
└── adapters/
    ├── virustotal.py    # MODIFIED: add name, requires_api_key, is_configured()
    ├── malwarebazaar.py # MODIFIED: add name, requires_api_key, is_configured()
    └── threatfox.py     # MODIFIED: add name, requires_api_key, is_configured()

app/routes.py            # MODIFIED: use build_registry() instead of hardcoded adapters

app/static/src/ts/
├── types/ioc.ts         # MODIFIED: replace IOC_PROVIDER_COUNTS with getProviderCounts()
└── modules/enrichment.ts # MODIFIED: call getProviderCounts() instead of IOC_PROVIDER_COUNTS

app/templates/results.html  # MODIFIED: add data-provider-counts attribute

tests/
├── test_provider_protocol.py   # NEW
├── test_provider_registry.py   # NEW
├── test_registry_setup.py      # NEW
├── test_config_store.py        # MODIFIED: add multi-provider key tests
└── test_routes.py              # MODIFIED: update mocks to use build_registry
```

### Pattern 1: `@runtime_checkable` Protocol

**What:** Defines a structural interface. Any class with the right attributes and methods is considered to implement it — no explicit inheritance needed.

**When to use:** When you want `isinstance()` checks to work against the protocol at runtime (required for TDD assertions).

**Critical limitation:** `@runtime_checkable` only checks for method/attribute *presence*, not *signature*. `isinstance(obj, Provider)` returns `True` if `obj` has attributes named `name`, `supported_types`, `requires_api_key`, `lookup`, and `is_configured` — but does NOT verify their types or call signatures. This is a known Python limitation.

```python
# Source: Python docs - https://docs.python.org/3/library/typing.html#typing.runtime_checkable
from __future__ import annotations
from typing import Protocol, runtime_checkable
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType


@runtime_checkable
class Provider(Protocol):
    """Protocol that all enrichment provider adapters must satisfy."""

    name: str
    supported_types: set[IOCType] | frozenset[IOCType]
    requires_api_key: bool

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError: ...
    def is_configured(self) -> bool: ...
```

**isinstance() works because of @runtime_checkable:**
```python
from app.enrichment.provider import Provider
from app.enrichment.adapters.virustotal import VTAdapter

adapter = VTAdapter(api_key="key", allowed_hosts=[])
assert isinstance(adapter, Provider)  # True — structural match
```

### Pattern 2: Provider Registry (Simple Dictionary Registry)

**What:** A class that holds a dict of `name -> adapter`, provides type-filtered lookup, and enforces duplicate prevention.

**When to use:** When the set of plugins is known at startup and read-only during request handling (no concurrency concerns for registration).

```python
# app/enrichment/registry.py
from __future__ import annotations
from app.enrichment.provider import Provider
from app.pipeline.models import IOCType


class ProviderRegistry:
    """Registry of enrichment provider adapters.

    Populated once at app startup via register(). Read-only during request handling.
    Thread safety: assumes registration completes before any request is served.
    """

    def __init__(self) -> None:
        self._providers: dict[str, Provider] = {}

    def register(self, provider: Provider) -> None:
        """Register a provider. Raises ValueError on duplicate name."""
        if provider.name in self._providers:
            raise ValueError(f"Provider '{provider.name}' already registered")
        self._providers[provider.name] = provider

    def all(self) -> list[Provider]:
        """Return all registered providers."""
        return list(self._providers.values())

    def configured(self) -> list[Provider]:
        """Return only providers where is_configured() is True."""
        return [p for p in self._providers.values() if p.is_configured()]

    def providers_for_type(self, ioc_type: IOCType) -> list[Provider]:
        """Return configured providers that support the given IOC type."""
        return [
            p for p in self._providers.values()
            if p.is_configured() and ioc_type in p.supported_types
        ]

    def provider_count_for_type(self, ioc_type: IOCType) -> int:
        """Return count of configured providers for the given IOC type."""
        return len(self.providers_for_type(ioc_type))
```

### Pattern 3: Setup Factory Function

**What:** A single `build_registry()` function that creates all adapters and registers them. This is the only place provider registration happens.

**When to use:** Called once at request time in `routes.py` — not at module import time (Flask app context required for `ALLOWED_API_HOSTS`).

```python
# app/enrichment/setup.py
from __future__ import annotations
from app.enrichment.config_store import ConfigStore
from app.enrichment.registry import ProviderRegistry
from app.enrichment.adapters.virustotal import VTAdapter
from app.enrichment.adapters.malwarebazaar import MBAdapter
from app.enrichment.adapters.threatfox import TFAdapter


def build_registry(allowed_hosts: list[str], config_store: ConfigStore) -> ProviderRegistry:
    """Build and return a fully populated ProviderRegistry.

    This is the ONLY place providers are registered. Adding a new provider
    requires: (1) create adapter file, (2) add one register() call here.
    """
    registry = ProviderRegistry()
    vt_key = config_store.get_vt_api_key()
    registry.register(VTAdapter(api_key=vt_key or "", allowed_hosts=allowed_hosts))
    registry.register(MBAdapter(allowed_hosts=allowed_hosts))
    registry.register(TFAdapter(allowed_hosts=allowed_hosts))
    return registry
```

### Pattern 4: ConfigStore Multi-Section Expansion

**What:** Add a `[providers]` section alongside the existing `[virustotal]` section. Keys are lowercase provider names (e.g., `"greynoise"`, `"otx"`).

**When to use:** When storing API keys for providers that are identified by name, not hard-typed.

```python
# Additions to app/enrichment/config_store.py
_PROVIDERS_SECTION = "providers"


def get_provider_key(self, name: str) -> str | None:
    """Read API key for a named provider (lowercase name, e.g., 'greynoise')."""
    cfg = configparser.ConfigParser()
    cfg.read(self._config_path)
    value = cfg.get(_PROVIDERS_SECTION, name.lower(), fallback=None)
    return value or None

def set_provider_key(self, name: str, key: str) -> None:
    """Write API key for a named provider."""
    self._config_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    cfg = configparser.ConfigParser()
    cfg.read(self._config_path)
    if _PROVIDERS_SECTION not in cfg:
        cfg[_PROVIDERS_SECTION] = {}
    cfg[_PROVIDERS_SECTION][name.lower()] = key
    fd = os.open(str(self._config_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        cfg.write(fh)

def all_provider_keys(self) -> dict[str, str]:
    """Return all provider keys from [providers] section."""
    cfg = configparser.ConfigParser()
    cfg.read(self._config_path)
    if _PROVIDERS_SECTION not in cfg:
        return {}
    return dict(cfg[_PROVIDERS_SECTION])
```

### Pattern 5: Dynamic Provider Counts via DOM Data Attribute

**What:** Backend computes per-type provider counts from the registry and serializes them to a JSON string in a `data-provider-counts` attribute on `.page-results`. TypeScript reads this at runtime.

**When to use:** When the provider count changes dynamically (new providers added) and must flow from backend to frontend without hardcoding.

**Backend (routes.py `analyze()`):**
```python
import json
from app.enrichment.models import IOCType

# After building the registry:
provider_counts = {
    ioc_type.value: registry.provider_count_for_type(ioc_type)
    for ioc_type in IOCType
    if ioc_type != IOCType.CVE  # CVE has no providers currently
}
template_extras["provider_counts"] = json.dumps(provider_counts)
```

**Template (results.html):**
```html
<div class="page-results"
  {% if mode == "online" and job_id %}
    data-job-id="{{ job_id }}"
    data-mode="{{ mode }}"
    data-provider-counts="{{ provider_counts | tojson | forceescape }}"
  {% else %}
    data-mode="{{ mode }}"
  {% endif %}>
```

**TypeScript (types/ioc.ts):**
```typescript
// Replace IOC_PROVIDER_COUNTS constant with a function
export function getProviderCounts(): Record<string, number> {
  const el = document.querySelector<HTMLElement>(".page-results");
  if (!el) return defaultProviderCounts;
  const raw = el.getAttribute("data-provider-counts");
  if (!raw) return defaultProviderCounts;
  try {
    return JSON.parse(raw) as Record<string, number>;
  } catch {
    return defaultProviderCounts;
  }
}

// Keep as fallback
const defaultProviderCounts: Record<IocType, number> = {
  ipv4: 2, ipv6: 2, domain: 2, url: 2, md5: 3, sha1: 3, sha256: 3,
} as const;
```

### Anti-Patterns to Avoid

- **Registering at module import time:** Do not call `register()` at the top level of adapter modules. Flask app context (`ALLOWED_API_HOSTS`) is not available at import time. Registration must happen inside `build_registry()`.
- **Sharing a registry instance across requests as a module global:** The registry is built per-request in the `analyze()` route. Do not store it as a module-level variable (would require locks, complicates testing, and leaks state across requests).
- **isinstance() for type annotation enforcement:** `@runtime_checkable` only checks attribute names, not signatures. Do not rely on `isinstance(x, Provider)` to prove `lookup()` returns the right type — that is mypy/pyright's job.
- **Mutating supported_types at runtime:** `supported_types` is read at registration time by `providers_for_type()`. If it were mutable, the registry cache would be stale. Keep it as a class attribute or frozen set.
- **Jinja2 `| safe` on provider_counts:** The `data-provider-counts` attribute value comes from `json.dumps()` of internal data (IOC type names → int). It is safe-ish but should still use `| forceescape` to prevent HTML attribute injection if names ever become user-controlled.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structural interfaces | Inheritance hierarchy | `typing.Protocol` | No coupling; adapters stay independent; stdlib since Python 3.8 |
| Runtime isinstance checks | Custom `hasattr` duck-typing | `@runtime_checkable` Protocol | Standard, well-understood, PEP 544 compliant |
| INI config multi-section | Custom file format | `configparser` sections | Already in use; `cfg[section][key]` is all that's needed |
| Provider count computation | Hardcoded dict in TypeScript | Backend computation from registry | Stays in sync automatically as providers are added/removed |

**Key insight:** The complexity is in understanding what `@runtime_checkable` does and does NOT guarantee. It checks attribute *presence* only. Type accuracy is mypy/pyright's job, not isinstance()'s job.

---

## Common Pitfalls

### Pitfall 1: runtime_checkable Only Checks Attribute Names

**What goes wrong:** A class with `name = 5` (int) and `lookup = "not a method"` (str) would still pass `isinstance(obj, Provider)` if the names exist.

**Why it happens:** PEP 544 specifies runtime checks only verify structural membership by name presence, not type or signature.

**How to avoid:** TDD tests should call `adapter.lookup(ioc)` and assert the return type, not just check `isinstance`. The isinstance check proves the adapter "claims" to implement the protocol; calling the method proves it actually works.

**Warning signs:** Tests that only check `isinstance()` without calling `lookup()` give false confidence.

### Pitfall 2: Route Test Mock Targets Must Change

**What goes wrong:** Existing route tests patch `app.routes.VTAdapter`, `app.routes.MBAdapter`, `app.routes.TFAdapter`. After Task 24.4 removes those imports from routes.py, patching them will silently have no effect.

**Why it happens:** `unittest.mock.patch` patches the name *where it's looked up*. After routes.py imports only `build_registry` from `app.enrichment.setup`, the adapter classes are no longer in `app.routes` namespace.

**How to avoid:** Tests that previously patched individual adapters should instead patch `app.enrichment.setup.build_registry` and return a mock registry. Or patch at the adapter module level (`app.enrichment.adapters.virustotal.VTAdapter`).

**Warning signs:** Tests that patch `app.routes.VTAdapter` but the patch has no visible effect on test behavior.

### Pitfall 3: VTAdapter.is_configured() Must Handle Empty String

**What goes wrong:** `build_registry()` passes `api_key=vt_key or ""` when no key is set. `is_configured()` must treat `""` (empty string) as not configured, same as `None`.

**Why it happens:** `bool("")` is `False`, so `return bool(self._api_key)` handles both `None` and `""` correctly — but only if the adapter stores the key before calling `is_configured()`.

**How to avoid:** `VTAdapter.is_configured()` returns `bool(self._api_key)`. Since empty string is falsy in Python, this works. Write a test that confirms `VTAdapter(api_key="", ...).is_configured()` returns `False`.

**Warning signs:** Online mode fails for the empty-string API key case (redirects to settings, which is correct behavior, but should be traced to `is_configured()` returning False).

### Pitfall 4: providers_for_type() Must Filter to Configured Providers Only

**What goes wrong:** If `providers_for_type()` returns ALL providers that support a type (including unconfigured ones), then a VT adapter with no key would be included, and its lookup would fail at API call time with an auth error.

**Why it happens:** Forgetting the `is_configured()` filter — returning all providers that match `ioc_type in p.supported_types` without the configured check.

**How to avoid:** The spec is explicit: `providers_for_type()` returns only configured providers that support the given IOC type. Both conditions must hold: `p.is_configured() AND ioc_type in p.supported_types`.

**Warning signs:** EnrichmentError results with "Authentication error" even when no VT key is expected.

### Pitfall 5: enrichable_count Calculation Must Use Registry

**What goes wrong:** After route refactor, the `enrichable_count` calculation (line 146-149 in current routes.py) still iterates over a local `adapters_list`. This list must be replaced with `registry.providers_for_type(ioc.type)`.

**Why it happens:** The `enrichable_count` calculation is a secondary code path that's easy to miss when refactoring the primary adapter instantiation.

**How to avoid:** After building the registry, compute `enrichable_count` using the registry:
```python
enrichable_count = sum(
    len(registry.providers_for_type(ioc.type))
    for ioc in iocs
)
```

**Warning signs:** `enrichable_count` is 0 or wrong after refactor, causing incorrect progress bar max.

### Pitfall 6: JSON Serialization of provider_counts in Template

**What goes wrong:** Jinja2's `| tojson` filter produces a string like `{"ipv4": 2, ...}`. If placed directly in an HTML attribute without escaping, characters like `"` will break the attribute boundary.

**Why it happens:** HTML attributes use double quotes; JSON also uses double quotes.

**How to avoid:** Use `| tojson | forceescape` in the Jinja2 template, or use single-quoted attribute syntax. Flask's built-in `tojson` filter already escapes `<`, `>`, `&` but not attribute-breaking `"` unless combined with `forceescape` or HTML encoding.

**Alternative:** Use `json.dumps()` on the backend and pass the result through `flask.escape()` before injecting into the template — or rely on Jinja2 autoescaping by passing the raw dict as a template variable and using `{{ provider_counts | tojson }}` inside the attribute (autoescaping will HTML-encode the quotes).

**Warning signs:** Browser fails to parse `data-provider-counts` attribute; JavaScript `JSON.parse()` throws.

### Pitfall 7: TypeScript getProviderCounts() Fallback Path

**What goes wrong:** `getProviderCounts()` is called from `updatePendingIndicator()` which runs during enrichment polling. If the DOM element is missing or the attribute is malformed, returning `undefined` or throwing will break the entire polling loop.

**Why it happens:** TypeScript's strict null checking won't catch runtime JSON.parse errors.

**How to avoid:** Always return `defaultProviderCounts` on any failure path (null element, missing attribute, JSON parse error). The fallback keeps the old hardcoded behavior, which is safe.

**Warning signs:** Progress indicator freezes or shows incorrect "N pending" count during enrichment.

---

## Code Examples

### Provider Protocol (complete)

```python
# app/enrichment/provider.py
# Source: Python docs typing.Protocol (https://docs.python.org/3/library/typing.html#typing.runtime_checkable)
from __future__ import annotations
from typing import Protocol, runtime_checkable
from app.enrichment.models import EnrichmentError, EnrichmentResult
from app.pipeline.models import IOC, IOCType


@runtime_checkable
class Provider(Protocol):
    """Protocol that all enrichment provider adapters must satisfy.

    Uses structural subtyping — adapters do not need to inherit from this class.
    @runtime_checkable enables isinstance(adapter, Provider) checks.

    Note: isinstance() only checks attribute name presence, not types or signatures.
    """

    name: str
    supported_types: set[IOCType] | frozenset[IOCType]
    requires_api_key: bool

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError: ...
    def is_configured(self) -> bool: ...
```

### Adapter Additions (VTAdapter example)

```python
# Inside VTAdapter class body, add as class attributes + method:
name = "VirusTotal"
requires_api_key = True

def is_configured(self) -> bool:
    """Return True if a non-empty API key is stored."""
    return bool(self._api_key)
```

```python
# MBAdapter and TFAdapter (no key needed):
name = "MalwareBazaar"  # or "ThreatFox"
requires_api_key = False

def is_configured(self) -> bool:
    return True  # No API key needed — always available
```

### Routes Refactor Pattern

```python
# BEFORE (routes.py analyze()):
vt_adapter = VTAdapter(api_key=api_key, allowed_hosts=allowed_hosts)
mb_adapter = MBAdapter(allowed_hosts=allowed_hosts)
tf_adapter = TFAdapter(allowed_hosts=allowed_hosts)
adapters_list = [vt_adapter, mb_adapter, tf_adapter]
orchestrator = EnrichmentOrchestrator(adapters=adapters_list)

# AFTER:
from app.enrichment.setup import build_registry

registry = build_registry(allowed_hosts=allowed_hosts, config_store=config_store)
if not registry.configured():
    flash("Please configure at least one provider API key before using online mode", "warning")
    return redirect(url_for("main.settings_get"))

adapters_list = registry.all()  # Pass all providers to orchestrator
orchestrator = EnrichmentOrchestrator(adapters=adapters_list)
enrichable_count = sum(len(registry.providers_for_type(ioc.type)) for ioc in iocs)
```

### Route Test Update Pattern

```python
# BEFORE (patching individual adapters in test_routes.py):
with (
    patch("app.routes.ConfigStore") as MockStore,
    patch("app.routes.VTAdapter") as MockVTAdapter,
    patch("app.routes.MBAdapter") as MockMBAdapter,
    patch("app.routes.TFAdapter") as MockTFAdapter,
    patch("app.routes.EnrichmentOrchestrator") as MockOrchestrator,
    ...
):

# AFTER (patching build_registry):
with (
    patch("app.routes.build_registry") as mock_build_registry,
    patch("app.routes.EnrichmentOrchestrator") as MockOrchestrator,
    patch("app.routes.Thread") as MockThread,
):
    mock_registry = MagicMock()
    mock_registry.configured.return_value = [MagicMock()]  # non-empty = online OK
    mock_registry.all.return_value = [MagicMock()]
    mock_registry.providers_for_type.return_value = [MagicMock(), MagicMock()]
    mock_build_registry.return_value = mock_registry
    ...
```

### TypeScript getProviderCounts()

```typescript
// types/ioc.ts — replace IOC_PROVIDER_COUNTS export with:

const _defaultProviderCounts: Record<IocType, number> = {
  ipv4: 2, ipv6: 2, domain: 2, url: 2, md5: 3, sha1: 3, sha256: 3,
} as const;

/**
 * Returns provider counts per IOC type, reading from DOM if available.
 * Falls back to hardcoded defaults if attribute is missing or malformed.
 */
export function getProviderCounts(): Record<string, number> {
  const el = document.querySelector<HTMLElement>(".page-results");
  if (el === null) return _defaultProviderCounts;
  const raw = el.getAttribute("data-provider-counts");
  if (raw === null) return _defaultProviderCounts;
  try {
    return JSON.parse(raw) as Record<string, number>;
  } catch {
    return _defaultProviderCounts;
  }
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded adapter list in `routes.py` | `build_registry()` + `ProviderRegistry` | Phase 24 | Adding providers requires zero changes to routes.py |
| `if not api_key:` redirect to settings | `if not registry.configured():` redirect | Phase 24 | Redirect triggers if ANY required provider is unconfigured |
| Hardcoded `IOC_PROVIDER_COUNTS` in TypeScript | `getProviderCounts()` reading DOM | Phase 24 | Counts update automatically as backend adds providers |
| Single `[virustotal]` INI section | Multi-section with `[providers]` section | Phase 24 | Per-provider key storage without INI format changes |

**Deprecated/outdated after Phase 24:**
- Direct imports of `VTAdapter`, `MBAdapter`, `TFAdapter` in `routes.py` — replaced by `build_registry`
- `if not api_key:` check using `config_store.get_vt_api_key()` — replaced by `registry.configured()`
- `IOC_PROVIDER_COUNTS` as a static TypeScript constant — replaced by `getProviderCounts()`

---

## Open Questions

1. **Should build_registry() be called once at app startup or per-request?**
   - What we know: Current code instantiates adapters inside `analyze()` per-request. The registry reads from ConfigStore (file I/O) each time.
   - What's unclear: Whether file I/O per request is acceptable vs. caching the registry at startup.
   - Recommendation: Per-request is safest for correctness (picks up config changes without restart) and matches the existing pattern. Performance impact is negligible for a local tool. The CONTEXT.md says "populated once at app startup, read-only during request handling" — this means build once in `create_app()` and pass via `app.config` or Flask `g`. Either approach works; per-request is simpler for now and the deferred decision notes this is acceptable.

2. **How should the online mode redirect condition change?**
   - What we know: Currently redirects if `not api_key` (VT key missing). After refactor, it should redirect if `not registry.configured()`.
   - What's unclear: Should it redirect only if ALL providers are unconfigured, or only required-key providers?
   - Recommendation: Use `not registry.configured()` which returns True if any provider passes `is_configured()`. Since MB and TF are always configured, `registry.configured()` will always be non-empty — this means online mode will ALWAYS be allowed after the refactor. This changes behavior: previously, a missing VT key redirected to settings; after refactor, it won't. The CONTEXT.md says "at least one configured provider" which confirms this is intentional.

3. **Does `provider_counts` need to be passed in offline mode?**
   - What we know: `IOC_PROVIDER_COUNTS` is only used in `updatePendingIndicator()` which runs during enrichment polling — online mode only.
   - What's unclear: Should `data-provider-counts` be added to the template for offline mode renders too?
   - Recommendation: Only pass `provider_counts` in online mode (same guard as `job_id`). The TypeScript fallback handles the missing attribute case for offline renders.

---

## Sources

### Primary (HIGH confidence)

- Python 3.10 stdlib — `typing.Protocol`, `typing.runtime_checkable`, `configparser` — verified against codebase in use (pyproject.toml requires Python 3.10)
- Codebase direct inspection — `app/routes.py`, `app/enrichment/adapters/*.py`, `app/enrichment/config_store.py`, `app/enrichment/orchestrator.py`, `tests/test_routes.py`, `app/static/src/ts/types/ioc.ts`, `app/static/src/ts/modules/enrichment.ts`
- `.planning/phases/24-provider-registry-refactor/24-CONTEXT.md` — locked decisions
- `docs/plans/2026-03-02-universal-threat-intel-hub.md` — detailed task specifications with code

### Secondary (MEDIUM confidence)

- PEP 544 (Protocols for Structural Subtyping) — `@runtime_checkable` semantics verified from Python official docs
- `docs/plans/2026-03-02-universal-threat-intel-hub-design.md` — design rationale and provider matrix

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are already in the project; no new dependencies
- Architecture: HIGH — all patterns are directly specified in CONTEXT.md and the implementation plan; code examples verified against existing adapter structure
- Pitfalls: HIGH — identified from direct code inspection of test_routes.py mock targets, existing adapter patterns, and TypeScript module dependencies
- Open questions: MEDIUM — behavioral questions about registry.configured() and offline mode that the planner must make explicit in task steps

**Research date:** 2026-03-02
**Valid until:** 2026-04-02 (stable stdlib patterns; 30-day horizon)
