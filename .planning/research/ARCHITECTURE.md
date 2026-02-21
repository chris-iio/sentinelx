# Architecture Research

**Domain:** Security-focused local IOC triage web application (Flask/Python)
**Researched:** 2026-02-21
**Confidence:** HIGH — patterns verified against Flask official docs, Python stdlib docs, and security tool community references

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Browser (localhost only)                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  Paste Input + Mode Toggle (offline/online) + Submit Button   │  │
│  └─────────────────────────────┬──────────────────────────────────┘  │
│                                │ POST /analyze                        │
└────────────────────────────────┼─────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                     Flask Application Layer                          │
│  ┌──────────────┐  ┌──────────────────────────────────────────────┐  │
│  │  Route:      │  │           IOC Pipeline                        │  │
│  │  GET  /      │  │                                               │  │
│  │  POST /      │  │  Input → Extractor → Normalizer → Classifier  │  │
│  │    analyze   │  │                          ↓                    │  │
│  └──────────────┘  │                    [offline stops here]       │  │
│                    │                          ↓                    │  │
│                    │                    Enricher (online only)     │  │
│                    │                          ↓                    │  │
│                    │                    Result Renderer            │  │
│                    └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                 ↓ (online mode only)
┌─────────────────────────────────────────────────────────────────────┐
│                     External API Layer                               │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐            │
│  │  VirusTotal   │  │  AbuseIPDB    │  │  Shodan / N   │            │
│  │  Adapter      │  │  Adapter      │  │  Adapter      │            │
│  └───────────────┘  └───────────────┘  └───────────────┘            │
│  (All calls: strict timeouts, max response size, no redirects)       │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Flask Routes | Receive POST, validate input length/content-type, dispatch to pipeline | Single Blueprint, `routes.py` |
| IOC Extractor | Find candidate IOC strings in free-form text using regex patterns | `iocextract` library + custom patterns |
| Normalizer | Refang defanged IOCs (hxxp, [.], {.}, etc.) to canonical form | `iocextract` refang + custom defang patterns |
| Classifier | Deterministically assign type label (IPv4, IPv6, domain, URL, hash, CVE) | Regex with precedence ordering |
| Enricher Orchestrator | Fan-out parallel API calls for each IOC; collect results with timeouts | `concurrent.futures.ThreadPoolExecutor` |
| Provider Adapters | One class per API provider: construct request, parse response, return typed result | Per-provider module in `enrichers/` |
| Config Reader | Read API keys from environment; validate presence at startup; expose read-only | `os.environ` + startup checks |
| HTML Renderer | Render Jinja2 templates; never use `|safe` on untrusted data | Jinja2 autoescaping (default on) |
| Security Headers | Add CSP, X-Content-Type-Options, X-Frame-Options to all responses | Flask `after_request` hook or Flask-Talisman |

## Recommended Project Structure

```
sentinelx/
├── app/
│   ├── __init__.py          # Application factory: create_app()
│   ├── routes.py            # Single blueprint: GET /, POST /analyze
│   ├── config.py            # Config class: reads env vars, validates at startup
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── extractor.py     # IOC string extraction from free-form text
│   │   ├── normalizer.py    # Defang reversal, canonical form
│   │   ├── classifier.py    # Type assignment: IPv4/domain/hash/CVE etc.
│   │   └── models.py        # IOC dataclass: type, value, raw_match
│   ├── enrichers/
│   │   ├── __init__.py      # EnricherResult dataclass; run_all() orchestrator
│   │   ├── base.py          # Abstract BaseEnricher: lookup(ioc) → EnricherResult
│   │   ├── virustotal.py    # VirusTotal adapter
│   │   ├── abuseipdb.py     # AbuseIPDB adapter (if selected)
│   │   └── [provider].py   # Additional provider adapters
│   └── templates/
│       ├── base.html        # Layout: CSP meta tag, no inline JS
│       ├── index.html       # Paste form + mode toggle
│       └── results.html     # Results grouped by IOC type, source-attributed
├── tests/
│   ├── test_extractor.py
│   ├── test_normalizer.py
│   ├── test_classifier.py
│   ├── test_enrichers.py    # Mocked HTTP — never call real APIs in tests
│   └── test_routes.py
├── run.py                   # Entry point: create_app() + app.run(host='127.0.0.1')
├── requirements.txt
└── .env.example             # Document required env vars; never commit .env
```

### Structure Rationale

- **`app/pipeline/`:** The extraction pipeline is independent of Flask — it can be tested without a request context. Isolating it here enforces that boundary.
- **`app/enrichers/`:** Each provider is its own file. Adding or removing a provider means adding or deleting one file and registering it in `__init__.py`. No changes elsewhere.
- **`app/config.py`:** Centralizes all environment variable reads. If a key is missing, fail loudly at startup — not during a request. Analysts get a clear error, not a silent enrichment gap.
- **`tests/`:** Flat, one file per module. Enricher tests use mocked HTTP responses — real API calls are forbidden in the test suite.

## Architectural Patterns

### Pattern 1: Application Factory

**What:** `create_app()` function creates and configures the Flask instance rather than creating it at module level. Blueprint registration, config loading, and security header hooks all happen inside the factory.

**When to use:** Always — even for small apps. Enables proper testing (create test app with different config), and prevents circular import problems.

**Trade-offs:** Slightly more boilerplate than a single-file app; worth it for testability and maintainability.

**Example:**
```python
# app/__init__.py
def create_app(config_override=None):
    app = Flask(__name__)
    app.config.from_object(Config())  # reads env vars, validates at init
    if config_override:
        app.config.update(config_override)

    from .routes import bp
    app.register_blueprint(bp)

    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        return response

    return app
```

### Pattern 2: Pipeline as Pure Functions

**What:** The IOC extraction pipeline (extract → normalize → classify) is implemented as pure functions that take strings and return dataclasses. No Flask context, no side effects, no HTTP calls.

**When to use:** Always — this is the core safety invariant. Pure functions are trivially testable and cannot accidentally make network calls.

**Trade-offs:** Requires passing data explicitly (no global state), which is the correct behavior anyway.

**Example:**
```python
# app/pipeline/models.py
from dataclasses import dataclass
from enum import Enum

class IOCType(Enum):
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    DOMAIN = "domain"
    URL = "url"
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    CVE = "cve"

@dataclass(frozen=True)
class IOC:
    type: IOCType
    value: str        # canonical (refanged) form
    raw_match: str    # original string from input, for display
```

### Pattern 3: Provider Adapter with Abstract Base

**What:** Each threat intelligence provider implements a `BaseEnricher` abstract class with a single `lookup(ioc: IOC) -> EnricherResult` method. The orchestrator treats all providers uniformly.

**When to use:** Whenever you have multiple external providers that return similar data. New providers require only a new file implementing the interface.

**Trade-offs:** Minor abstraction overhead; pays off when adding the second or third provider.

**Example:**
```python
# app/enrichers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from ..pipeline.models import IOC

@dataclass(frozen=True)
class EnricherResult:
    provider: str
    ioc_value: str
    verdict: str           # raw provider verdict, no interpretation
    raw_response: dict     # sanitized subset of API response
    queried_at: datetime
    error: Optional[str] = None  # set if lookup failed

class BaseEnricher(ABC):
    @abstractmethod
    def lookup(self, ioc: IOC) -> EnricherResult:
        ...

    def supports(self, ioc_type) -> bool:
        """Override to restrict which IOC types this enricher handles."""
        return True
```

### Pattern 4: Parallel Enrichment with ThreadPoolExecutor

**What:** Fan out all enricher lookups for all IOCs concurrently using `concurrent.futures.ThreadPoolExecutor`. Each future has an independent timeout. Results are collected as they complete; failures are captured as error results, not exceptions.

**When to use:** Parallel API enrichment where each call is I/O-bound and independent. ThreadPoolExecutor is preferred over asyncio here because Flask routes are synchronous, and the `requests`/`httpx` synchronous clients are simpler to reason about than async variants in a sync Flask context.

**Trade-offs:** Threads carry overhead vs. asyncio; for ~5-10 concurrent API calls per triage request, thread overhead is negligible. Asyncio would require Flask async support or a different event loop model that adds complexity for minimal gain at this scale.

**Example:**
```python
# app/enrichers/__init__.py
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import logging

MAX_ENRICHER_WORKERS = 10
PER_ENRICHER_TIMEOUT_SECONDS = 10

def run_all(iocs, enrichers, mode):
    if mode == "offline":
        return []

    results = []
    with ThreadPoolExecutor(max_workers=MAX_ENRICHER_WORKERS) as executor:
        futures = {
            executor.submit(enricher.lookup, ioc): (enricher, ioc)
            for ioc in iocs
            for enricher in enrichers
            if enricher.supports(ioc.type)
        }
        for future in as_completed(futures, timeout=30):
            enricher, ioc = futures[future]
            try:
                results.append(future.result(timeout=PER_ENRICHER_TIMEOUT_SECONDS))
            except TimeoutError:
                results.append(EnricherResult(
                    provider=type(enricher).__name__,
                    ioc_value=ioc.value,
                    verdict="timeout",
                    raw_response={},
                    queried_at=datetime.utcnow(),
                    error="Request timed out"
                ))
            except Exception as exc:
                logging.error("Enricher failed: %s", exc)
                results.append(EnricherResult(..., error=str(exc)))
    return results
```

### Pattern 5: Defense-in-Depth HTML Rendering

**What:** Jinja2 autoescaping (enabled by default for `.html` templates) is the first layer. A second layer is never using `|safe` on any data that passed through user input or API responses. A third layer is setting CSP headers that prevent inline script execution.

**When to use:** All templates that display IOC values or API response data.

**Trade-offs:** Slightly more template discipline required (can't shortcut with `|safe`); eliminates an entire class of XSS vulnerabilities.

**Key rule:** The only values that may be passed through `markupsafe.Markup()` or `|safe` are strings constructed entirely by application code, never strings that touched user input or external API responses.

## Data Flow

### Request Flow

```
Analyst pastes text → POST /analyze
        ↓
    [Route] validate input (max length, content-type)
        ↓
    [Extractor] regex scan → raw IOC candidate strings
        ↓
    [Normalizer] refang → canonical value strings
        ↓
    [Classifier] regex precedence → IOC(type, value, raw_match) list
        ↓
    [offline?] ──YES──→ render results without enrichment data
        ↓ NO
    [Enricher Orchestrator] fan-out parallel lookups
        ↓
    [Provider Adapters] HTTP calls (strict timeout, max size, no redirect)
        ↓
    [Enricher Orchestrator] collect results + errors
        ↓
    [Route] render results.html with IOC list + EnricherResult list
        ↓
    Browser receives HTML — Jinja2 autoescaping applied throughout
```

### Key Data Flow Rules

1. **Input crosses the trust boundary exactly once** — at the route handler. After extraction and classification, all data flows as typed dataclasses, not raw strings.
2. **Enrichment results are never trusted** — API response fields are treated as untrusted strings and rendered through Jinja2 autoescaping, never marked safe.
3. **No data persists** — the pipeline is stateless per request. No database writes, no session storage of raw text blobs.
4. **Offline/online is a pre-enrichment fork** — the pipeline always runs extraction + classification. The enrichment step is conditionally skipped, not removed from the flow.

### Security Boundaries

```
┌─────────────────────────────────────────────────┐
│  UNTRUSTED ZONE                                  │
│  - Raw paste text (user input)                   │
│  - API response bodies (external provider data)  │
│  - IOC values (could be crafted adversarially)   │
└──────────────────┬──────────────────────────────┘
                   │ crosses boundary via
                   │ [validation + typed dataclasses]
┌──────────────────▼──────────────────────────────┐
│  TRUSTED ZONE                                    │
│  - IOC(type, value) after classification         │
│  - EnricherResult fields (but rendered escaped)  │
│  - Application-generated template literals       │
└─────────────────────────────────────────────────┘
```

**Sanitization happens at two points:**
1. Input length/format validation in the route handler before pipeline entry
2. Jinja2 autoescaping at HTML render time for all displayed values

## Anti-Patterns

### Anti-Pattern 1: Monolithic Route Handler

**What people do:** Put extraction, classification, enrichment, and rendering all inside the route function in a single file.

**Why it's wrong:** Untestable without a live Flask server. Makes offline/online mode a conditional inside business logic. Cannot unit-test extraction without HTTP setup.

**Do this instead:** Route handlers call pipeline functions. Pipeline functions know nothing about Flask. Enrichers know nothing about the pipeline internals. Each layer is independently testable.

### Anti-Pattern 2: `|safe` on IOC Strings

**What people do:** Use `{{ ioc.value | safe }}` in templates to avoid encoding IOC values that contain characters like `<`, `>`, or `&`.

**Why it's wrong:** IOC values are untrusted user input. An adversary who can craft the pasted text can inject script tags. IOC values also include domains/URLs that may contain characters that Jinja2 needs to escape for safe display.

**Do this instead:** Always render IOC values through Jinja2's default autoescaping (`{{ ioc.value }}`). The escaped output is correct for display in HTML.

### Anti-Pattern 3: Blocking the Route Thread on Sequential API Calls

**What people do:** Call enrichers one-at-a-time in a for-loop within the Flask route handler.

**Why it's wrong:** If each provider takes 2-3 seconds and there are 5 providers, triage of a single IOC takes 10-15 seconds. For a block of 20 IOCs, this becomes unbearable.

**Do this instead:** `concurrent.futures.ThreadPoolExecutor` with all enricher+IOC combinations submitted at once. The total enrichment time approaches the slowest single call, not the sum of all calls.

### Anti-Pattern 4: Trusting API Response Structure

**What people do:** Access `response.json()['data']['attributes']['last_analysis_stats']` directly without checking if keys exist.

**Why it's wrong:** API schemas change, providers return errors in unexpected shapes, and network issues can produce partial responses. Uncaught `KeyError` crashes the enricher and can surface internal details in the UI.

**Do this instead:** Each provider adapter uses `.get()` with safe defaults, wraps the entire call in try/except, and returns an `EnricherResult` with `error` set on failure. The orchestrator never fails due to a single provider's misbehavior.

### Anti-Pattern 5: Global HTTP Client Configuration

**What people do:** Create a global `requests.Session` or `httpx.Client` without timeouts and reuse it across enrichers.

**Why it's wrong:** Without explicit timeouts, a hung provider can block a thread indefinitely. Without max response size limits, a malformed API response can exhaust memory.

**Do this instead:** Each enricher creates its client with explicit `timeout=httpx.Timeout(10.0)`. For response size, stream the response and abort if `content-length` exceeds the limit or if bytes read exceed the limit during streaming.

## Integration Points

### External Services

| Service | Integration Pattern | Key Constraints |
|---------|---------------------|-----------------|
| VirusTotal API v3 | REST/JSON via httpx with API key header | 10s timeout, 1MB max response, no redirects |
| AbuseIPDB API v2 | REST/JSON via httpx with API key header | 10s timeout, 512KB max response, no redirects |
| Additional providers | Same adapter pattern, same constraints | Must implement `BaseEnricher.lookup()` |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Route → Pipeline | Function call, raw string in, `list[IOC]` out | No Flask context crosses this boundary |
| Pipeline → Enrichers | Function call, `list[IOC]` in, `list[EnricherResult]` out | Enrichers may not call pipeline functions |
| Enrichers → External APIs | HTTP via httpx, structured response parsing | All failures must be caught, never propagate as exceptions to route |
| Route → Templates | Jinja2 `render_template()` with typed context dict | Never pass raw strings that came from user input as `|safe` |
| Config → All | `current_app.config` inside request context | Keys validated at startup; missing key = startup failure, not runtime error |

## Scaling Considerations

This is a localhost-only single-analyst tool. Scaling is not a design goal. However, for completeness:

| Scale | Architecture Adjustment |
|-------|--------------------------|
| 1 analyst (target) | Flask dev server, localhost binding — correct design |
| Small team (internal jump box) | Gunicorn with 2-4 workers; add rate limiting per-IP |
| Multi-user (out of scope) | Would require authentication, per-session isolation, async task queue (Celery) — not this project |

**First bottleneck if misused:** Thread pool saturation under concurrent analyst sessions. Default `ThreadPoolExecutor` workers of `min(32, cpu_count + 4)` handles small team use. Rate limiting prevents abuse.

## Build Order Implications

Based on component dependencies, the correct build sequence is:

1. **Config + models** — foundational types and config validation used by everything else
2. **Extractor + Normalizer** — core pipeline, pure functions, no external dependencies
3. **Classifier** — depends on extractor output types
4. **Routes (offline)** — wire pipeline to Flask, establish full request flow without enrichment
5. **BaseEnricher + one provider adapter (VirusTotal)** — enrichment layer
6. **Parallel orchestrator** — fan-out; must have at least one working adapter to test
7. **Additional provider adapters** — additive, each independently testable
8. **Security hardening** — CSP headers, response size limits, input length caps; validate the whole system

This ordering means offline mode is fully functional and testable before any network code is written. The enrichment layer can be developed and tested against mock HTTP responses without needing live API keys.

## Sources

- Flask Application Factory pattern: https://flask.palletsprojects.com/en/stable/patterns/appfactories/ (HIGH confidence — official Flask 3.1 docs)
- Flask Blueprints: https://flask.palletsprojects.com/en/stable/blueprints/ (HIGH confidence — official Flask 3.1 docs)
- Flask XSS/Security guidance: https://flask.palletsprojects.com/en/stable/web-security/ (HIGH confidence — official Flask 3.1 docs)
- bleach.clean() documentation: https://bleach.readthedocs.io/en/latest/clean.html (HIGH confidence — official bleach docs, version 6.3.0)
- httpx resource limits: https://www.python-httpx.org/advanced/resource-limits/ (HIGH confidence — official httpx docs)
- httpx timeouts: https://www.python-httpx.org/advanced/timeouts/ (HIGH confidence — official httpx docs)
- iocextract library: https://github.com/InQuest/iocextract (MEDIUM confidence — GitHub README, widely used in security tooling)
- concurrent.futures documentation: https://docs.python.org/3/library/concurrent.futures.html (HIGH confidence — Python 3.14 stdlib docs)
- Jinja2 autoescaping/XSS prevention: https://semgrep.dev/docs/cheat-sheets/flask-xss (MEDIUM confidence — verified against Flask official docs)
- python-dotenv: https://pypi.org/project/python-dotenv/ (HIGH confidence — PyPI official page)

---
*Architecture research for: Security-focused local IOC triage Flask application*
*Researched: 2026-02-21*
