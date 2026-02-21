# Stack Research

**Domain:** Security-focused local IOC triage web application (Python + Flask)
**Researched:** 2026-02-21
**Confidence:** MEDIUM-HIGH (core stack HIGH, secondary TI providers MEDIUM)

---

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12+ | Runtime | 3.12 has active security support through 2028; Flask 3.1 supports 3.9+; 3.12 gives asyncio improvements and better error messages |
| Flask | 3.1.3 | Web framework | Lightest viable web framework for a single-page local tool; full control over request/response cycle; no ORM or auth machinery to audit around; Jinja2 autoescape is on by default for .html templates |
| Jinja2 | 3.1.x (bundled with Flask) | HTML templating | Ships with Flask; autoescape enabled by default for .html — IOC strings and API response data never need `\|safe`; use `{{ var }}` everywhere |

### IOC Extraction and Normalization

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| iocextract | 1.16.1 | Primary IOC extraction from free-form text | Handles defanged variants natively (hxxp, [.], {.}); supports IPv4, IPv6 (partial), URLs, MD5/SHA1/SHA256/SHA512, email, YARA; maintained by InQuest Labs; returns iterators for low memory overhead |
| iocsearcher | 2.7.2 | Supplementary IOC extraction (41 indicator types) | More accurate than iocextract on 11 of 13 shared indicator types per peer-reviewed comparison; adds CVE identifiers, MITRE ATT&CK, cryptocurrency addresses; released December 2025, actively maintained |

**Decision:** Use `iocextract` as the primary extraction layer (battle-tested, broad ecosystem adoption) and `iocsearcher` for CVE and supplementary types. Do not use `ioc-fanger` (last released Sept 2022, inactive) or `cyobstract` (unmaintained). Write custom normalization for edge cases rather than adding an inactive library.

### Threat Intelligence API Clients

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| vt-py | 0.22.0 | VirusTotal API v3 client | Official client from VirusTotal; async-native; supports files, URLs, domains, IPs; released October 2025; Apache 2.0 licensed |
| greynoise | 3.0.1 | GreyNoise API client | Official client maintained by GreyNoise Intelligence; released June 2025; free community tier available; provides context on mass-scanning IPs (critical for analyst triage) |

**Note on AbuseIPDB:** No official Python client library is maintained. The third-party `abuseipdb` PyPI package is inactive (last release > 12 months). Implement AbuseIPDB queries directly with `httpx` against their REST API — the API is simple enough to call without a wrapper (single endpoint, JSON response). This avoids an unmaintained dependency.

**Note on Shodan:** Shodan has an official `shodan` Python client but the API requires a paid subscription for non-trivial use. Treat as optional/future. Do not include in MVP.

### Async HTTP Client

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| httpx | 0.28.1 | Parallel outbound API calls to threat intelligence providers | Supports both async (`asyncio.gather`) and sync; strict timeout configuration via `httpx.Timeout`; no automatic redirect following (configurable); HTTP/2 support; actively developed (1.0.0 pre-release in progress). aiohttp is faster at extreme concurrency (1000+ connections) but async-only and adds complexity; for 3-5 parallel TI API calls, httpx is the correct choice |

**Do not use:** `requests` — synchronous only, no native async; forces thread pooling or `concurrent.futures` for parallel calls. The parallel API query requirement rules it out.

### Caching

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| cachetools | 7.0.1 | In-memory TTL cache for API responses | Pure Python, zero external dependencies, TTLCache evicts stale entries automatically; `threading.RLock` makes it thread-safe; released February 2026; no Redis/Memcached/SQLite required for a single-user local tool. TTL of 1 hour for most providers (VirusTotal scans don't change minute-to-minute) |

**Do not use:** `Flask-Caching` with a file or Redis backend — unnecessary complexity for a local tool. Do not persist raw API responses to disk — out of scope per PROJECT.md ("No persistent storage of raw pasted blobs"). In-memory TTL cache is sufficient.

### Output Sanitization

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| MarkupSafe | 2.1.x (bundled with Flask) | Escape untrusted strings in templates | Ships with Flask/Jinja2; `Markup.escape()` converts `<`, `>`, `&`, `"`, `'` to HTML entities; use at the Python layer when building structured data before it reaches templates |
| bleach | 6.3.0 | Allowlist-based HTML sanitization | Use only if rendering any HTML from API responses (unlikely); for plain-text IOC display, Jinja2 autoescape is sufficient and bleach is not needed. Do NOT use the `\|safe` Jinja2 filter on any user input or API response data |

**Decision:** For this project, Jinja2 autoescape + never using `\|safe` on untrusted data is sufficient. `bleach` is in the dependency list only if a future feature requires rendering API-provided HTML content. Keep it out of v1.

### Security Headers

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| flask-talisman | 1.1.0 | HTTP security headers (CSP, HSTS, etc.) | Adds Content-Security-Policy, X-Frame-Options, X-Content-Type-Options in one extension; localhost-only tool still benefits from CSP to block injected scripts from IOC content. Note: project is low-activity but stable, last release August 2023 |

**CSP configuration for this project:** Since this is a local tool with no external CDN resources, set CSP to `default-src 'self'`. This blocks any injected script from an IOC string that makes it into the page despite Jinja2 escaping.

### Forms and CSRF

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Flask-WTF | 1.2.2 | CSRF protection | Even for a localhost-only tool, CSRF matters if analyst has other browser tabs open. Single-call `CSRFProtect(app)` adds token validation to all POST endpoints; released October 2024 |

**Note:** For a localhost-only tool, CSRF is a defense-in-depth measure. Enable it. The overhead is a single hidden field per form.

### Environment Variable Management

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| python-dotenv | 1.2.1 | Load API keys from `.env` file during development | Standard approach for 12-factor app config; `load_dotenv()` populates `os.environ`; `.env` excluded from git via `.gitignore`. Released October 2025 |

**At runtime:** Production use should set environment variables directly (systemd unit, shell profile) rather than relying on `.env`. `python-dotenv` is a development convenience, not a secret manager.

### Development Tools

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| ruff | 0.15.2 | Linter + formatter (replaces flake8, black, isort) | Includes Bandit security rules (S-prefix); 10-100x faster than alternatives; single config in `pyproject.toml`; released February 2026 |
| bandit | current | Security-focused static analysis | Run separately for security scan even if using ruff — `ruff --select S` covers most Bandit rules but standalone `bandit` gives full output format suitable for CI |
| pytest | 8.x | Test runner | Standard; use `pytest-flask` plugin for Flask test client fixtures |
| pytest-flask | current | Flask testing fixtures | Provides `client` fixture; integrates with Flask test client |
| mypy | current | Static type checking | Optional but recommended for untrusted-input code paths |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Web framework | Flask 3.1 | FastAPI | FastAPI requires async-first architecture and adds Pydantic dependency; for a local tool with 1-2 analysts, Flask's sync-by-default model with async httpx calls is simpler and sufficient |
| Web framework | Flask 3.1 | Django | Django brings ORM, admin, migrations — all irrelevant for a no-persistence local tool; overkill adds attack surface |
| IOC extraction | iocextract + iocsearcher | regex-only custom solution | iocextract encodes years of defang pattern research; writing equivalent regex is a pitfall, not a shortcut |
| IOC extraction | iocextract + iocsearcher | ioc-fanger | Last released September 2022, no Python 3.10+ classifier testing; inactive per Snyk health analysis |
| Async HTTP | httpx | aiohttp | aiohttp is async-only; httpx gives both sync (for tests, simple paths) and async (for parallel API calls) in one library; simpler mental model |
| Async HTTP | httpx | requests + concurrent.futures | requests is synchronous; threading workarounds are messier and slower than native async |
| Caching | cachetools TTLCache | Redis | Redis is an external process dependency — absurd for a single-user local tool; TTLCache is in-process and zero-config |
| Caching | cachetools TTLCache | Flask-Caching | Flask-Caching wraps backends; cachetools is more direct for application-level function caching; fewer layers |
| Caching | cachetools TTLCache | diskcache | diskcache persists to disk; PROJECT.md prohibits persistent storage of raw blobs; in-memory TTL is sufficient |
| Security headers | flask-talisman | Manual response headers | flask-talisman is battle-tested and handles nonce generation for CSP; manual headers risk misconfiguration |
| AbuseIPDB | Direct httpx calls | abuseipdb PyPI package | PyPI package is inactive (no release in 12+ months); direct API call is 10 lines and avoids the dead dependency |

---

## Installation

```bash
# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Core web framework
pip install Flask==3.1.3 Flask-WTF==1.2.2 flask-talisman==1.1.0

# IOC extraction and normalization
pip install iocextract==1.16.1 iocsearcher==2.7.2

# Threat intelligence API clients
pip install vt-py==0.22.0 greynoise==3.0.1

# Async HTTP client (for parallel TI API calls and direct AbuseIPDB calls)
pip install httpx==0.28.1

# In-memory TTL cache
pip install cachetools==7.0.1

# Environment variable management
pip install python-dotenv==1.2.1

# Dev dependencies
pip install pytest pytest-flask mypy ruff bandit
```

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `ioc-fanger` | Inactive since September 2022; no Python 3.10+ support classification; Snyk health: inactive | iocextract (handles defanging natively) |
| `cyobstract` | Unmaintained; not updated for years | iocsearcher (actively maintained, more accurate) |
| `requests` for API calls | Synchronous only; cannot do parallel TI queries without `concurrent.futures` workaround | `httpx` with asyncio |
| `aiohttp` | Async-only; adds complexity for minimal gain at 3-5 concurrent connections | `httpx` (async + sync in one library) |
| `diskcache` or SQLite for caching | Persistent storage violates PROJECT.md constraint ("No persistent storage of raw pasted blobs") | `cachetools.TTLCache` (in-memory, auto-evicts) |
| `\|safe` Jinja2 filter on untrusted data | Bypasses autoescape; IOC strings and API responses MUST never be marked safe | `{{ var }}` (autoescape) always; never `{{ var \| safe }}` |
| `subprocess` / `shell=True` | Explicitly prohibited in PROJECT.md; no shell execution in deterministic code paths | Python-native parsing libraries only |
| `eval` / `exec` | Same prohibition; enables code injection via crafted IOC input | Never |
| `abuseipdb` PyPI package | Inactive (no release in 12+ months); unmaintained wrapper | Direct `httpx` call to AbuseIPDB REST API |
| Debug mode in production | `app.run(debug=True)` exposes interactive debugger; RCE risk | `debug=False`, bind to `127.0.0.1` only |
| Redis / Memcached | External process dependency for a localhost-only single-user tool | `cachetools.TTLCache` |
| `bleach` v5 or earlier | Requires `html5lib` and is deprecated as of 2023; bleach 6.x is the only safe version if needed | `bleach==6.3.0` (if HTML rendering required) or Jinja2 autoescape (preferred) |

---

## Stack Patterns by Variant

**Offline mode (extraction + classification only):**
- Flask route handles form POST
- Call `iocextract` + `iocsearcher` synchronously — no async needed
- Return rendered template with classified IOCs
- Zero outbound network calls

**Online mode (parallel TI enrichment):**
- Flask route spawns `asyncio.run()` or uses a background task
- `httpx.AsyncClient` with `asyncio.gather()` fires all provider queries in parallel
- Per-provider timeout: 10 seconds connect, 15 seconds read (never block on slow APIs)
- `max_redirects=0` — no redirect following on outbound requests (PROJECT.md requirement)
- Results cached in `cachetools.TTLCache` keyed by `(provider, ioc_value)` with TTL=3600s
- HTML rendered with Jinja2; all IOC strings and API data passed as plain variables (no `\|safe`)

**API key management:**
- Read from `os.environ.get("VT_API_KEY")` etc. at startup
- Fail fast with clear error if required key is missing: `raise ValueError("VT_API_KEY not set")`
- Never log the key value; never render it in any template

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Flask 3.1.3 | Python 3.9-3.13 | Dropped Python 3.8 in Flask 3.1.0 |
| httpx 0.28.1 | Python 3.8-3.12 | Pre-release 1.0.0 targets Python 3.9+ |
| vt-py 0.22.0 | Python 3.7+ | Uses async/await; compatible with Python 3.12 asyncio |
| greynoise 3.0.1 | Python 3.8+ | Major version bump (3.0.0) in June 2025 — breaking changes from 2.x |
| iocsearcher 2.7.2 | Python 3.x | Check Python version requirement before install |
| cachetools 7.0.1 | Python 3.x | Not thread-safe by default — wrap with `threading.RLock` |
| flask-talisman 1.1.0 | Flask 2.x, 3.x | Low activity but no known Flask 3.1 incompatibilities |

---

## Sources

- PyPI/iocextract — version 1.16.1, Python 3 compatible: https://pypi.org/project/iocextract/ (MEDIUM confidence — last PyPI release Sept 2023)
- PyPI/iocsearcher — version 2.7.2, released December 2025: https://pypi.org/project/iocsearcher/ (HIGH confidence — recently verified)
- PyPI/vt-py — version 0.22.0, released October 2025: https://pypi.org/project/vt-py/ (HIGH confidence)
- PyPI/greynoise — version 3.0.1, released June 2025: https://pypi.org/project/greynoise/ (HIGH confidence)
- PyPI/httpx — version 0.28.1, released December 2024: https://pypi.org/project/httpx/ (HIGH confidence)
- PyPI/cachetools — version 7.0.1, released February 2026: https://pypi.org/project/cachetools/ (HIGH confidence)
- PyPI/flask-talisman — version 1.1.0, released August 2023: https://pypi.org/project/flask-talisman/ (MEDIUM confidence — low activity)
- PyPI/Flask-WTF — version 1.2.2, released October 2024: https://pypi.org/project/Flask-WTF/ (HIGH confidence)
- PyPI/python-dotenv — version 1.2.1, released October 2025: https://pypi.org/project/python-dotenv/ (HIGH confidence)
- PyPI/bleach — version 6.3.0, released October 2025: https://pypi.org/project/bleach/ (HIGH confidence — deprecated status noted but still maintained)
- PyPI/ruff — version 0.15.2, released February 2026: https://pypi.org/project/ruff/ (HIGH confidence)
- Flask security docs: https://flask.palletsprojects.com/en/stable/web-security/ (HIGH confidence)
- ioc-fanger inactive status: https://snyk.io/advisor/python/ioc-fanger (MEDIUM confidence)
- cachetools thread safety note: https://cachetools.readthedocs.io/ (HIGH confidence)
- httpx async support: https://www.python-httpx.org/async/ (HIGH confidence)
- iocsearcher vs iocextract accuracy comparison: ScienceDirect peer-reviewed paper (MEDIUM confidence — paper-based claim)
- Flask 3.1.3 release February 2026: https://pypi.org/project/Flask/ (HIGH confidence)

---

*Stack research for: oneshot-ioc — local IOC triage web application*
*Researched: 2026-02-21*
