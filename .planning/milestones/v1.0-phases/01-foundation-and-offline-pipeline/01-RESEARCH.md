# Phase 1: Foundation and Offline Pipeline - Research

**Researched:** 2026-02-21
**Domain:** Flask web app security scaffold + IOC extraction pipeline (Python/Flask)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

All implementation decisions were explicitly deferred to Claude for MVP velocity. No user-locked technology choices exist for Phase 1. The domain boundary is locked:

- Flask app delivering the complete offline IOC triage workflow
- Extract all IOCs (IPv4, IPv6, domain, URL, MD5, SHA1, SHA256, CVE)
- Normalize defanged patterns, classify by type, deduplicate
- Display results grouped by type
- Zero outbound network calls in offline mode
- Security scaffold (CSP, CSRF, host validation, input size cap, no subprocess/eval, autoescaping) established in Phase 1 and never retrofitted

### Claude's Discretion

**Results layout:**
- Collapsible accordion sections per IOC type with count badges (e.g., "IPv4 (12)")
- All sections expanded by default on first load
- Clean table inside each section: normalized IOC value, type classification, one-click copy button for refanged value
- Show original defanged form as a subtle secondary column where it differs from normalized

**Visual direction:**
- Dark theme — standard for security tooling, easier on analyst eyes during long sessions
- Minimal, clinical aesthetic — no gradients, no decoration, just data
- Monospace font for IOC values, system sans-serif for labels/UI
- Muted color palette with type-specific accent colors for IOC group headers (e.g., blue for IPs, orange for hashes, green for domains)

**Input experience:**
- Single large textarea with placeholder text showing example mixed IOC input (defanged examples)
- Offline/online toggle as a simple switch above the submit button, defaulting to offline
- Submit button labeled "Extract IOCs" (not "Submit" or "Analyze")
- Clear button to reset the textarea

**Error and empty states:**
- No IOCs found: friendly message "No IOCs detected in the pasted text" with a hint about supported types
- Size limit exceeded: rejection message before extraction with the size limit stated
- Empty input: disable submit button when textarea is empty
- Validation errors: inline, not modal

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EXTR-01 | User can paste free-form text (single IOC, SIEM alert snippet, email headers/body, threat report) into a single large input field | Flask route with textarea form; MAX_CONTENT_LENGTH guards the route boundary |
| EXTR-02 | Application extracts all IOCs from pasted text, supporting IPv4, IPv6, domain, URL, MD5, SHA1, SHA256, and CVE types | `iocextract` handles IPv4, URL, hash types; `iocsearcher` adds CVE and fills accuracy gaps; combined coverage is complete |
| EXTR-03 | Application normalizes common defanging patterns (hxxp, hxxps, [.], {.}, (.), [dot], _dot_, [@], [at], [://]) before classification | `iocextract` handles most defanging natively; custom normalization layer fills edge cases; test corpus of 30+ variants required |
| EXTR-04 | Application classifies each extracted IOC by type using deterministic logic (no ML, no heuristics) | Regex precedence ordering on normalized strings; strict type detection with no ambiguous fallback |
| EXTR-05 | Application deduplicates extracted IOCs before enrichment (same normalized value = one lookup) | Hash-based dedup on normalized value before classification output is returned |
| UI-01 | Single-page web interface with a large text input field, a submit button, and a visible offline/online mode toggle | Flask GET `/` renders `index.html` with textarea, toggle, and submit button |
| UI-02 | In offline mode, only extraction, normalization, and classification are performed — zero outbound network calls | Offline/online fork happens AFTER classification; enrichment step is not reached in offline mode; verified by test asserting no HTTP calls |
| UI-04 | Results page groups extracted IOCs by type (IPv4, IPv6, domain, URL, hash, CVE) | Jinja2 template iterates over IOC groups by type; type-specific CSS accent colors from CONTEXT.md |
| UI-07 | UI visually indicates whether the current submission used offline or online mode | Mode passed to template context; persistent banner or badge in results view |
| SEC-01 | Application binds to 127.0.0.1 only by default | `app.run(host='127.0.0.1')` in `run.py`; never `0.0.0.0` |
| SEC-02 | API keys are read exclusively from environment variables, never from config files, CLI args, or query parameters | `Config` class reads `os.environ` at init; `python-dotenv` for dev convenience only |
| SEC-03 | Application fails fast at startup with a clear error if required API keys are missing (when online mode is configured) | `Config.__init__` validates env vars; raises `ValueError` at startup for missing keys |
| SEC-08 | All IOC strings and API response fields are HTML-escaped before rendering (Jinja2 autoescaping, no |safe on untrusted data) | Jinja2 autoescaping enabled by default for `.html` templates; no `\|safe` on any untrusted data — enforced by discipline and grep-check |
| SEC-09 | Content Security Policy header blocks inline scripts (default-src 'self'; script-src 'self') | Set via `after_request` hook in app factory (or flask-talisman); CSP value is `"default-src 'self'; script-src 'self'"` |
| SEC-10 | CSRF protection is enabled on all POST endpoints | Flask-WTF `CSRFProtect(app)` initialized in app factory; `{{ csrf_token() }}` in all forms |
| SEC-11 | Host header validation rejects requests from unexpected origins (TRUSTED_HOSTS for DNS rebinding prevention) | Flask's built-in `TRUSTED_HOSTS = ['localhost', '127.0.0.1']` config raises `SecurityError` → HTTP 400 |
| SEC-12 | Input size is capped (MAX_CONTENT_LENGTH) to prevent ReDoS and memory exhaustion | `app.config['MAX_CONTENT_LENGTH'] = 512 * 1024` (512 KB); Flask returns 413 automatically on oversize |
| SEC-13 | No subprocess calls, no shell execution, no eval/exec anywhere in the codebase | Architecture enforces pure Python paths; verified by `bandit -r app/` (`bandit` flags B602, B603, B604) |
| SEC-14 | No persistent storage of raw pasted text blobs | Pipeline is stateless per request; no database, no file writes, no session storage of paste text |
| SEC-15 | Debug mode is hardcoded to False in all non-development entry points | `app.debug = False` in production app factory; asserted in unit test |
| SEC-16 | Outbound API calls only target hostnames on an explicit allowlist (SSRF prevention) | In Phase 1, zero outbound calls occur; allowlist enforcement structure is established in `config.py` for Phase 2 use |

</phase_requirements>

---

## Summary

Phase 1 builds a running Flask application that receives pasted text, extracts and classifies IOCs, deduplicates them, and displays results grouped by type — with all outbound calls disabled and a hardened security posture in place. The offline pipeline (Extractor → Normalizer → Classifier) is implemented as pure functions entirely independent of Flask, making it trivially testable without a request context. Security defenses (TRUSTED_HOSTS, CSRF, CSP, MAX_CONTENT_LENGTH, debug lockdown) are established in the app factory before any route logic is written, not retrofitted later.

The dominant risk in this phase is not feature complexity but security misconfiguration. All five critical pitfalls documented in PITFALLS.md have Phase 1 prevention steps: DNS rebinding requires `TRUSTED_HOSTS` in the app factory; XSS requires Jinja2 autoescape discipline and CSP headers; API key leakage requires debug lockdown and startup validation; ReDoS requires `MAX_CONTENT_LENGTH` before extraction runs; and the SSRF allowlist structure (not enforcement yet — no outbound calls in Phase 1) must be established in `config.py` now so Phase 2 cannot be written without it.

**Primary recommendation:** Build Config + models first, then the pure extraction pipeline, then wire to Flask routes with all security configuration in the app factory. The UI can be minimal HTML — no JavaScript frameworks required for Phase 1. Accordion/copy UX is progressive enhancement on top of server-rendered HTML.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12+ | Runtime | Active security support through 2028; Flask 3.1 supports 3.9+; 3.12 gives better error messages |
| Flask | 3.1.3 | Web framework | Lightest viable option; Jinja2 autoescape on by default for `.html` templates; no ORM/auth surface |
| Jinja2 | 3.1.x (bundled) | HTML templating | Ships with Flask; autoescape enabled by default — IOC strings render safe with `{{ var }}` |
| Flask-WTF | 1.2.2 | CSRF protection | `CSRFProtect(app)` protects all POST endpoints; single call; released October 2024 |
| python-dotenv | 1.2.1 | `.env` loading for dev | `load_dotenv()` populates `os.environ`; `.env` excluded from git |

### IOC Extraction

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| iocextract | 1.16.1 | Primary IOC extraction | Battle-tested defanging (hxxp, [.], {.}); supports IPv4, URL, hashes, email, YARA; InQuest Labs |
| iocsearcher | 2.7.2 | CVE + supplementary types | Adds CVE identifiers, MITRE ATT&CK, 40+ types; released December 2025; more accurate than iocextract on 11/13 shared types per peer-reviewed comparison |

### Development Tools

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| ruff | 0.15.2 | Linter + formatter | Replaces flake8, black, isort; includes Bandit security rules (`-S` flag); released February 2026 |
| bandit | current | Security static analysis | Run separately for full security report; flags B602, B603, B604 (subprocess/eval) |
| pytest | 8.x | Test runner | Standard; table-driven tests |
| pytest-flask | current | Flask test fixtures | Provides `client` fixture for route testing |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Flask 3.1 | FastAPI | FastAPI requires async-first + Pydantic; sync-by-default is simpler for offline-only Phase 1 |
| Flask 3.1 | Django | ORM, admin, migrations are irrelevant for no-persistence tool; adds unaudited attack surface |
| iocextract + iocsearcher | Custom regex only | iocextract encodes years of defang pattern research; custom regex is a known pitfall (ReDoS, missed variants) |
| iocextract + iocsearcher | iocsearcher only | iocextract has broader ecosystem adoption for URL/hash extraction; iocsearcher supplements, not replaces |
| flask-talisman | Manual `after_request` headers | flask-talisman (1.1.0, August 2023) is low-activity; apache/superset actively recommends against it. Manual `after_request` is more maintainable and has zero external dependency. Prefer manual headers for Phase 1. |

**Installation:**
```bash
python3.12 -m venv .venv
source .venv/bin/activate

# Core framework
pip install Flask==3.1.3 Flask-WTF==1.2.2

# IOC extraction
pip install iocextract==1.16.1 iocsearcher==2.7.2

# Dev environment
pip install python-dotenv==1.2.1

# Dev tools
pip install pytest pytest-flask ruff bandit
```

---

## Architecture Patterns

### Recommended Project Structure

```
sentinelx/
├── app/
│   ├── __init__.py          # create_app() factory; security headers; CSRF; TRUSTED_HOSTS
│   ├── routes.py            # Blueprint: GET /, POST /analyze
│   ├── config.py            # Config class: reads env vars, validates at startup
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── extractor.py     # extract_iocs(text: str) -> list[RawMatch]
│   │   ├── normalizer.py    # normalize(raw: str) -> str (refanging)
│   │   ├── classifier.py    # classify(normalized: str, raw: str) -> IOC
│   │   └── models.py        # IOCType enum; IOC frozen dataclass
│   └── templates/
│       ├── base.html        # Layout: no inline JS; dark theme CSS vars
│       ├── index.html       # Paste form + mode toggle + submit
│       └── results.html     # IOC groups with accordion; mode indicator
├── tests/
│   ├── test_extractor.py    # Unit: 30+ defanging variants corpus
│   ├── test_normalizer.py   # Unit: all normalization patterns
│   ├── test_classifier.py   # Unit: type detection per IOC type
│   └── test_routes.py       # Integration: offline flow, 413 on oversize, 400 on bad Host
├── run.py                   # Entry: create_app() + app.run(host='127.0.0.1', debug=False)
├── requirements.txt
└── .env.example             # Documents required env vars; never commit .env
```

### Pattern 1: Application Factory with Security Config

**What:** `create_app()` creates the Flask instance, registers blueprints, and sets all security configuration in one place before any route runs.

**When to use:** Always — enables proper test isolation (`create_app({'TESTING': True})`), prevents circular imports, and ensures security headers are not accidentally omitted from any response.

**Example:**
```python
# app/__init__.py
# Source: https://flask.palletsprojects.com/en/stable/patterns/appfactories/
def create_app(config_override=None):
    app = Flask(__name__)

    # Security configuration — established first, before any routes
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    app.config['TRUSTED_HOSTS'] = ['localhost', '127.0.0.1']
    app.config['MAX_CONTENT_LENGTH'] = 512 * 1024  # 512 KB hard cap
    app.config['WTF_CSRF_ENABLED'] = True
    app.debug = False  # Hardcoded; never from env in production entry point

    if config_override:
        app.config.update(config_override)

    from flask_wtf.csrf import CSRFProtect
    CSRFProtect(app)

    from .routes import bp
    app.register_blueprint(bp)

    @app.after_request
    def set_security_headers(response):
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    return app
```

### Pattern 2: Pipeline as Pure Functions

**What:** The IOC extraction pipeline (extract → normalize → classify) is implemented as pure functions taking strings and returning typed dataclasses. No Flask context, no side effects, no HTTP calls ever cross this boundary.

**When to use:** Always — this is the core safety invariant. Pure functions are trivially testable, cannot accidentally make network calls, and make offline/online the fork in the route handler rather than in business logic.

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
    raw_match: str    # original string from input, for display in "original" column
```

```python
# app/pipeline/extractor.py
import iocextract
from iocsearcher.searcher import Searcher

_searcher = Searcher()  # Create once; reuse for all calls (per iocsearcher docs)

def extract_iocs(text: str) -> list[dict]:
    """Extract raw IOC candidates from free-form text. No side effects."""
    results = []
    # iocextract for URLs, IPs, hashes
    for url in iocextract.extract_urls(text, refang=True):
        results.append({'raw': url, 'type_hint': 'url'})
    # iocsearcher for CVEs and supplementary types
    iocs = _searcher.search_data(text)
    for ioc_type, values in iocs.items():
        for val in values:
            results.append({'raw': val, 'type_hint': ioc_type})
    return results
```

### Pattern 3: Flask TRUSTED_HOSTS for DNS Rebinding Prevention

**What:** Flask's built-in `TRUSTED_HOSTS` config validates the `Host` header on every request and raises a `SecurityError` (returned as HTTP 400) for unrecognized host values.

**When to use:** Always for localhost-only tools. DNS rebinding attacks (see CVE-2025-49596, CVSS 9.4 on Anthropic MCP Inspector, 2025) can access localhost servers via a malicious site if this is not configured.

**Configuration:**
```python
app.config['TRUSTED_HOSTS'] = ['localhost', '127.0.0.1']
```

**Verification test:**
```python
def test_untrusted_host_returns_400(client):
    response = client.post(
        '/analyze',
        data={'text': 'test', 'csrf_token': get_csrf_token(client)},
        headers={'Host': 'evil.com'}
    )
    assert response.status_code == 400
```

**Note:** Flask sets `TRUSTED_HOSTS = None` by default, meaning all hosts are accepted. This MUST be set explicitly in the app factory.

### Pattern 4: MAX_CONTENT_LENGTH Before Extraction

**What:** Flask's `MAX_CONTENT_LENGTH` config cap causes Flask to return HTTP 413 automatically before the route handler is ever called. This prevents ReDoS and memory exhaustion from large paste blobs.

**Why this order matters:** The cap must reject the request before `extract_iocs()` is called. Setting the limit in the route handler (after reading the body) is too late.

**Configuration:**
```python
app.config['MAX_CONTENT_LENGTH'] = 512 * 1024  # 512 KB
```

**What Flask returns:** `413 Request Entity Too Large` with a default Werkzeug error page. Override with `@app.errorhandler(413)` for a user-friendly message.

**Success criterion verification:** POST a 600 KB body — Flask returns 413 before the route function executes.

### Pattern 5: CSRF with Flask-WTF

**What:** `CSRFProtect(app)` validates a CSRF token on every POST request. The token is generated per-session and must be included in every form.

**Why CSRF matters for localhost:** An adversary's website can initiate POST requests to `http://localhost:5000/analyze` from the analyst's browser via DNS rebinding or direct origin attacks. CSRF tokens prevent this even if `TRUSTED_HOSTS` is bypassed.

**Setup:**
```python
# app/__init__.py
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    csrf.init_app(app)
    ...
```

**Template:**
```html
<!-- index.html -->
<form method="post" action="/analyze">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
    <textarea name="text" ...></textarea>
    <button type="submit">Extract IOCs</button>
</form>
```

### Pattern 6: Security Headers via after_request (not flask-talisman)

**Recommendation:** Use manual `after_request` headers, NOT flask-talisman.

**Rationale:** flask-talisman (last release August 2023, GoogleCloudPlatform repo inactive, wntrblm fork active but small) has been identified by apache/superset and others as a maintenance concern. Manual `after_request` headers are:
- Zero external dependency
- Fully explicit and auditable
- Trivially tested with `curl -I`
- Not subject to flask-talisman's HTTPS-enforcement default (which conflicts with localhost HTTP development)

**Required headers for Phase 1:**
```python
@app.after_request
def set_security_headers(response):
    # SEC-09: Block inline scripts; only allow same-origin resources
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'"
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    # Prevent referrer leakage
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response
```

### Anti-Patterns to Avoid

- **`| safe` on IOC values:** IOC strings are untrusted user input. `{{ ioc.value | safe }}` enables XSS via crafted paste. Use `{{ ioc.value }}` always.
- **Monolithic route handler:** All extraction logic in the route function makes it untestable without a Flask context. Keep the pipeline in `pipeline/` as pure functions.
- **Reading `DEBUG` from environment:** `app.debug = os.getenv('DEBUG', 'false').lower() == 'true'` can be manipulated. Hardcode `app.debug = False` in production entry points.
- **Setting `MAX_CONTENT_LENGTH` only in the route:** By the time the route runs, the body has already been read. The config must be set in the app factory.
- **Skipping TRUSTED_HOSTS:** Flask default is `None` (accept all). Must be explicitly set to `['localhost', '127.0.0.1']`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| IOC extraction from defanged text | Custom regex patterns for all defanging variants | `iocextract` + `iocsearcher` | iocextract encodes years of defang research; ReDoS risk in naive regex is documented and easy to introduce |
| CSRF token generation and validation | Custom token store in session | `Flask-WTF CSRFProtect` | Session-based timing-safe comparison, token rotation; hand-rolled versions are vulnerable to timing attacks |
| Defanging normalization for all variants | Regex that covers hxxp, [.], {.}, [dot], [at], etc. | `iocextract`'s built-in refanging + custom layer for edge cases | The documented defanging variants alone span 10+ patterns; undocumented analyst inventions cannot be enumerated |
| IOC deduplication | Complex set operations with type + value | `frozenset` or `dict` keyed on `(IOCType, normalized_value)` | Straightforward but must use normalized value, not raw match — a common error |
| HTML escaping | Manual string replacement of `<`, `>`, `&` | Jinja2 autoescaping (enabled by default) | Jinja2 handles all 5 HTML special chars including edge cases in attribute contexts; custom implementations miss cases |

**Key insight:** The security-sensitive parts (CSRF, escaping) have well-audited library implementations with known correct behavior. The domain-specific parts (IOC extraction) have libraries that encode years of pattern research. Hand-rolling either category in Phase 1 is a correctness risk, not a shortcut.

---

## Common Pitfalls

### Pitfall 1: TRUSTED_HOSTS Not Set (DNS Rebinding)

**What goes wrong:** Flask's default is `TRUSTED_HOSTS = None`, which accepts any Host header. A malicious website can use DNS rebinding to make the analyst's browser submit requests to `http://localhost:5000/` with arbitrary data. CVE-2025-49596 (Anthropic MCP Inspector, CVSS 9.4, 2025) demonstrates this exact attack class against a localhost tool.

**Why it happens:** Developers assume "localhost-only = safe from external." Flask does not configure this by default.

**How to avoid:** Set `app.config['TRUSTED_HOSTS'] = ['localhost', '127.0.0.1']` in the app factory. Add an integration test: POST with `Host: evil.com` returns 400.

**Warning signs:** No `TRUSTED_HOSTS` in app factory. No test asserting 400 for invalid Host.

### Pitfall 2: |safe on IOC Values (XSS)

**What goes wrong:** An IOC value containing `<script>alert(1)</script>` or `javascript:...` executes in the analyst's browser. Since this is localhost, the analyst's machine is the target.

**Why it happens:** Developers use `| safe` to avoid Jinja2 escaping on values that "look like plain text." IOC strings containing `<`, `>`, or `&` (especially URLs and CVE descriptions) trigger this.

**How to avoid:** Never use `| safe`, `Markup()`, or `render_template_string()` on any IOC value or API response field. Always `{{ var }}`. Set CSP `default-src 'self'` as second layer.

**Warning signs:** Any `| safe` in templates. Missing CSP header. URL-type IOCs rendered as `<a href="{{ ioc.value }}">` without scheme check.

### Pitfall 3: MAX_CONTENT_LENGTH Not Set Before Extraction (ReDoS)

**What goes wrong:** An adversary embeds a crafted 2 MB paste containing carefully structured text that triggers catastrophic backtracking in IOC extraction regex. The Flask worker hangs for minutes.

**Why it happens:** Developers think about input validation inside the route handler, not before it. By the time the handler reads the body, it's already in memory.

**How to avoid:** Set `app.config['MAX_CONTENT_LENGTH'] = 512 * 1024` in the app factory. Flask's Werkzeug rejects oversize bodies before the route handler runs, returning 413. Verify: POST 600 KB → 413, not timeout.

**Warning signs:** `MAX_CONTENT_LENGTH` absent from app factory. No test asserting 413 on oversize POST.

### Pitfall 4: Debug Mode Leaks API Keys

**What goes wrong:** Flask's Werkzeug interactive debugger renders full Python stack traces in the browser, including all local variables — including any API key that was loaded from `os.environ`. In Phase 1, there are no API keys yet, but the pattern is established here.

**Why it happens:** `app.run(debug=True)` is the first thing every Flask tutorial shows. Developers enable it for development and never change it.

**How to avoid:** Hardcode `app.debug = False` in `create_app()`. Never read `DEBUG` from env in the production entry point. Add a unit test: `assert app.debug is False`.

**Warning signs:** `debug=True` anywhere except `run.py` dev block. `DEBUG` read from env without explicit production override.

### Pitfall 5: Partial Defanging Misses Edge Cases

**What goes wrong:** iocextract handles the common patterns but misses analyst-invented variants: `hXXp://` (mixed case), `https[://]`, dots between octets with spaces, Unicode lookalike dots. An IOC is silently dropped — the analyst doesn't know.

**Why it happens:** Libraries are built against documented defanging patterns. Analysts invent new ones.

**How to avoid:** Build a test corpus of 30+ defanging variants before writing classifier tests. iocextract + iocsearcher together cover more than either alone, but custom normalization is still needed for edge cases. Display "could not classify" items to analysts.

**Warning signs:** Extraction tested only against clean IOC formats. No "unclassified" output shown to analyst.

---

## Code Examples

### App Factory with Full Security Config

```python
# app/__init__.py
# Sources: https://flask.palletsprojects.com/en/stable/patterns/appfactories/
#          https://flask.palletsprojects.com/en/stable/config/
import os
import secrets
from flask import Flask
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()

def create_app(config_override=None):
    app = Flask(__name__)

    # Security scaffold — all established before routes registered
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    app.config['TRUSTED_HOSTS'] = ['localhost', '127.0.0.1']
    app.config['MAX_CONTENT_LENGTH'] = 512 * 1024  # Reject >512 KB before route runs
    app.debug = False  # Hardcoded; never from env

    if config_override:
        app.config.update(config_override)

    csrf.init_app(app)

    from .routes import bp
    app.register_blueprint(bp)

    @app.after_request
    def set_security_headers(response):
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return 'Input too large. Maximum paste size is 512 KB.', 413

    return app
```

### IOC Models (Immutable Typed Dataclasses)

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
    value: str       # canonical (refanged) form — used for display and dedup key
    raw_match: str   # original string from input, shown in "original" column

def group_by_type(iocs: list['IOC']) -> dict[IOCType, list['IOC']]:
    """Group deduplicated IOC list by type for template rendering."""
    result: dict[IOCType, list['IOC']] = {}
    for ioc in iocs:
        result.setdefault(ioc.type, []).append(ioc)
    return result
```

### Route Handler (Offline Mode)

```python
# app/routes.py
from flask import Blueprint, render_template, request, current_app
from .pipeline.extractor import extract_iocs
from .pipeline.normalizer import normalize
from .pipeline.classifier import classify
from .pipeline.models import IOC, group_by_type

bp = Blueprint('main', __name__)

@bp.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@bp.route('/analyze', methods=['POST'])
def analyze():
    text = request.form.get('text', '')
    mode = request.form.get('mode', 'offline')

    # Input validation happens here (after MAX_CONTENT_LENGTH guard in config)
    if not text.strip():
        return render_template('index.html', error='No input provided.')

    # Pipeline: pure functions, no Flask context, no HTTP calls
    raw_matches = extract_iocs(text)
    iocs_seen: dict[tuple, IOC] = {}
    for match in raw_matches:
        normalized_value = normalize(match['raw'])
        ioc = classify(normalized_value, match['raw'])
        if ioc is not None:
            key = (ioc.type, ioc.value)
            if key not in iocs_seen:
                iocs_seen[key] = ioc

    deduped = list(iocs_seen.values())
    grouped = group_by_type(deduped)

    # Offline mode: stop here. No enrichment.
    return render_template(
        'results.html',
        grouped=grouped,
        mode=mode,
        total_count=len(deduped),
    )
```

### Test: Security Properties

```python
# tests/test_routes.py
def test_oversize_post_returns_413(client):
    """MAX_CONTENT_LENGTH rejects large pastes before extraction runs."""
    large_payload = 'a' * (600 * 1024)  # 600 KB > 512 KB limit
    response = client.post('/analyze', data={'text': large_payload})
    assert response.status_code == 413

def test_invalid_host_returns_400(client):
    """TRUSTED_HOSTS rejects requests with unexpected Host header."""
    response = client.get('/', headers={'Host': 'evil.example.com'})
    assert response.status_code == 400

def test_debug_mode_is_false(app):
    """Debug mode must never be enabled in production app factory."""
    assert app.debug is False

def test_security_headers_present(client):
    """Security headers are set on all responses."""
    response = client.get('/')
    assert 'default-src' in response.headers.get('Content-Security-Policy', '')
    assert response.headers.get('X-Content-Type-Options') == 'nosniff'
    assert response.headers.get('X-Frame-Options') == 'SAMEORIGIN'

def test_offline_mode_makes_no_http_calls(client, mocker):
    """Offline mode must make zero outbound network calls."""
    mock_request = mocker.patch('httpx.get')
    mock_request2 = mocker.patch('httpx.post')
    client.post('/analyze', data={
        'text': 'hxxp://example[.]com 192.168.1.1',
        'mode': 'offline',
        'csrf_token': get_csrf_token(client)
    })
    mock_request.assert_not_called()
    mock_request2.assert_not_called()
```

### Defanging Normalization Reference

```python
# app/pipeline/normalizer.py
import re

# Ordered by precedence — apply all, left to right
DEFANG_PATTERNS = [
    (r'hxxps?://', lambda m: m.group(0).replace('hxxp', 'http')),    # hxxp/hxxps
    (r'\[:\]//|\[://\]|\[:/\]', '://'),                              # [:]// [://] [:/]
    (r'\[\.\]|\(\.\)|\{\.\}', '.'),                                   # [.] (.) {.}
    (r'\[dot\]|\(dot\)|\{dot\}|_dot_', '.', re.IGNORECASE),          # [dot] etc.
    (r'\[@\]|\[at\]|\(@\)', '@', re.IGNORECASE),                     # [@] [at] (@)
]

def normalize(text: str) -> str:
    """Refang a single defanged IOC string. Returns canonical form."""
    result = text
    for pattern, replacement, *flags in DEFANG_PATTERNS:
        flag = flags[0] if flags else 0
        if callable(replacement):
            result = re.sub(pattern, replacement, result, flags=flag | re.IGNORECASE)
        else:
            result = re.sub(pattern, replacement, result, flags=flag)
    return result
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `requests` for all HTTP | `httpx` for async API calls | 2022+ | Not relevant for Phase 1 (no outbound calls), but must not use `requests` when Phase 2 adds enrichment |
| flask-talisman for security headers | Manual `after_request` + Flask's `TRUSTED_HOSTS` | 2023 (talisman maintenance dropped) | Removes external dependency; more explicit; avoid flask-talisman |
| `ioc-fanger` for normalization | `iocextract` (native defanging) + custom layer | 2022 (ioc-fanger went inactive) | Never use ioc-fanger; iocextract handles defanging natively |
| `cyobstract` for extraction | `iocsearcher` (December 2025 release) | 2024+ | Never use cyobstract; iocsearcher is actively maintained and more accurate |
| Flask debug mode detection from env | Hardcoded `app.debug = False` | Flask security guidance current | Debug mode via env can be manipulated; hardcode it |

**Deprecated/outdated:**
- `ioc-fanger`: Inactive since September 2022, no Python 3.10+ support. Use iocextract's built-in refanging.
- `cyobstract`: Unmaintained for years. Use iocsearcher.
- `flask-talisman`: Low activity (August 2023 last release); apache/superset recommends against it. Use manual `after_request` headers.
- `requests` for outbound calls: Not relevant Phase 1 (no outbound), but avoid in Phase 2. Use httpx.

---

## Open Questions

1. **iocextract + iocsearcher API overlap and deduplication**
   - What we know: Both libraries return IOC candidates; some types overlap (URLs, IPs, hashes)
   - What's unclear: Whether running both in sequence produces duplicates that need dedup across libraries, or whether the pipeline's per-`(type, value)` dedup handles this cleanly
   - Recommendation: Build the extractor to collect from both libraries into a single list, then let the pipeline's dedup step (keyed on normalized value + type) collapse duplicates. Test with a paste that triggers both libraries on the same IOC.

2. **iocsearcher's `Searcher` object initialization cost**
   - What we know: iocsearcher docs say "create once, reuse" — the object parses all regexps at init time
   - What's unclear: Whether module-level instantiation works correctly with Flask's app factory pattern and test isolation
   - Recommendation: Instantiate `_searcher = Searcher()` at module level in `extractor.py` (not inside the function); verify tests don't share state between them since Searcher is stateless after init.

3. **Dark theme without a CSS framework**
   - What we know: CONTEXT.md specifies dark theme, monospace IOC fonts, type-specific accent colors, no gradients or decoration
   - What's unclear: Whether vanilla CSS variables are sufficient or if a minimal framework (e.g., `water.css`, `sakura.css`) would accelerate development
   - Recommendation: Use plain CSS with custom properties for the color palette. Phase 1 is MVP — no CSS framework needed. Accordion via `<details>/<summary>` HTML elements requires zero JavaScript and zero dependencies.

4. **Copy-to-clipboard in Phase 1 with CSP `script-src 'self'`**
   - What we know: CONTEXT.md specifies a copy button per IOC; CSP blocks inline scripts
   - What's unclear: Whether clipboard copy requires JavaScript from an external CDN (blocked by CSP) or can be done with a self-hosted minimal script
   - Recommendation: Use the Clipboard API (`navigator.clipboard.writeText()`) in a small self-hosted `static/main.js` file. CSP `script-src 'self'` allows this. No inline `onclick` attributes — attach event listeners from the external script file. This is consistent with `SEC-09`.

---

## Build Order for Phase 1

This ordering is critical: security config precedes all other code.

```
Step 1: Project scaffold
  - pyproject.toml, requirements.txt, .gitignore, .env.example
  - Virtual environment setup

Step 2: app/__init__.py (create_app factory)
  - TRUSTED_HOSTS, MAX_CONTENT_LENGTH, SECRET_KEY
  - CSRFProtect initialization
  - after_request security headers
  - errorhandler(413)
  - DEBUG = False hardcoded

Step 3: app/pipeline/models.py
  - IOCType enum
  - IOC frozen dataclass
  - group_by_type() utility

Step 4: app/pipeline/normalizer.py + tests/test_normalizer.py
  - 30+ defanging patterns as test corpus FIRST
  - Implementation to pass tests
  - Edge cases: mixed case, bracket variants, Unicode

Step 5: app/pipeline/extractor.py + tests/test_extractor.py
  - iocextract + iocsearcher integration
  - Test against real defanged IOC corpus

Step 6: app/pipeline/classifier.py + tests/test_classifier.py
  - Deterministic type detection
  - Precedence ordering (URL > domain > IPv4 > IPv6 > hash > CVE)
  - Deduplication logic

Step 7: app/routes.py + tests/test_routes.py
  - GET / → index.html
  - POST /analyze → offline pipeline → results.html
  - Security property tests (413, 400 bad host, debug=False, no HTTP calls)

Step 8: Templates
  - base.html (dark theme CSS, no inline scripts)
  - index.html (textarea, offline/online toggle, submit, clear)
  - results.html (accordion by IOC type, mode indicator, copy buttons)

Step 9: run.py
  - create_app() + app.run(host='127.0.0.1', port=5000, debug=False)

Step 10: Verification
  - pytest -v (all tests pass)
  - curl -I http://localhost:5000/ (verify security headers)
  - curl -H "Host: evil.com" http://localhost:5000/ (verify 400)
  - POST 600 KB blob (verify 413)
  - Manual paste of defanged IOC block (verify extraction + grouping)
```

---

## Sources

### Primary (HIGH confidence)
- https://flask.palletsprojects.com/en/stable/config/ — Flask 3.1 TRUSTED_HOSTS, MAX_CONTENT_LENGTH, SECRET_KEY, DEBUG docs
- https://flask.palletsprojects.com/en/stable/patterns/appfactories/ — Application factory pattern
- https://flask.palletsprojects.com/en/stable/web-security/ — Security recommendations
- https://flask-wtf.readthedocs.io/en/1.2.x/csrf/ — CSRFProtect setup, token in templates
- https://pypi.org/project/iocsearcher/ — version 2.7.2, December 2025, CVE support verified
- https://pypi.org/project/iocextract/ — version 1.16.1, September 2023, Python 3 compatible
- https://pypi.org/project/Flask-WTF/ — version 1.2.2, October 2024

### Secondary (MEDIUM confidence)
- https://github.com/InQuest/iocextract — Last confirmed release September 2023; 278 commits; GPLv2 license
- https://github.com/malicialab/iocsearcher — MIT license; iocsearcher API: `Searcher().search_data(text)`
- https://github.com/apache/superset/discussions/31764 — flask-talisman maintenance concerns; recommends alternatives
- https://github.com/wntrblm/flask-talisman — Active fork of GoogleCloudPlatform/flask-talisman; 110 commits
- https://www.oligo.security/blog/critical-rce-vulnerability-in-anthropic-mcp-inspector-cve-2025-49596 — CVE-2025-49596 DNS rebinding + RCE against localhost tool; CVSS 9.4
- https://www.sourcery.ai/vulnerabilities/python-flask-security-audit-host-header-injection-python — Flask host header injection vulnerability DB

### Tertiary (LOW confidence)
- WebSearch result: iocextract labeled "Inactive" on Snyk health analysis — single source, not cross-verified with official repo; treat as flag to verify early in implementation
- Defanging edge case patterns beyond documented variants — practitioner observation; validate with test corpus during implementation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Flask 3.1, Flask-WTF 1.2.2, iocextract 1.16.1, iocsearcher 2.7.2 all verified against PyPI official pages; versions current as of February 2026
- Architecture: HIGH — Application factory, TRUSTED_HOSTS, MAX_CONTENT_LENGTH patterns verified against Flask 3.1 official docs
- Security patterns: HIGH — TRUSTED_HOSTS raises 400 confirmed; CSP via after_request is Flask-documented; CSRF via Flask-WTF confirmed; CVE-2025-49596 DNS rebinding reference is authoritative
- IOC extraction accuracy: MEDIUM — iocextract + iocsearcher combination is research-validated but edge case coverage requires a real-world defanging corpus during implementation
- flask-talisman decision: MEDIUM — maintenance concerns sourced from community discussion (apache/superset), not official deprecation notice; `after_request` alternative is LOW risk

**Research date:** 2026-02-21
**Valid until:** 2026-04-21 (stable stack; 60 days reasonable; iocsearcher is actively maintained so check for point releases before implementation)

**Open concern from STATE.md addressed:**
- `iocextract` Flask 3.1 compatibility: iocextract is a pure text-processing library with no Flask dependency. It uses the `regex` package. Compatibility concern is about Python 3.12, not Flask version. The `regex` package is actively maintained and Python 3.12 compatible. The concern is noted but LOW risk — iocextract makes no Flask or web calls.
- `flask-talisman` Flask 3.1 compatibility: Resolved by recommending `after_request` headers instead. flask-talisman dependency is eliminated from Phase 1.
