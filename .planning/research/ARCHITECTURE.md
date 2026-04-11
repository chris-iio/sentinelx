# Architecture Patterns: SSH Log Anomaly Detection Integration

**Domain:** SSH auth.log parsing and behavioral anomaly detection added to SentinelX
**Researched:** 2026-04-12
**Confidence:** HIGH — based on direct codebase inspection of all affected files

---

## Integration Philosophy

SSH detection is a second vertical inside the same Flask shell. It shares the UI chrome,
security scaffold, and GeoIP infrastructure but does not touch the IOC enrichment pipeline
at all. Every change to existing files is additive. The only existing files that need
modification are three small additions: the app factory (2 lines), base.html (3 lines), and
main.ts (2 lines). Everything else is new.

---

## Recommended Architecture

### New File Layout

```
app/
  ssh/                           NEW package — parallel to enrichment/
    __init__.py
    models.py                    Frozen dataclasses: LoginEvent, AnomalyAlert
    parser.py                    Parse auth.log bytes → list[LoginEvent]
    detector.py                  list[LoginEvent] + geo_map → list[AnomalyAlert]
    geoip.py                     Thin HTTP wrapper around ipinfo.io (no ProviderRegistry)

  routes/
    ssh.py                       NEW — route module, registers bp_ssh Blueprint

app/templates/
  ssh/
    upload.html                  {% extends "base.html" %}
    results.html                 {% extends "base.html" %}

app/static/src/ts/modules/
  ssh.ts                         NEW — upload form validation + alert table interactions
```

### Existing Files Modified (additions only)

| File | Change | Lines Added |
|------|--------|-------------|
| `app/__init__.py` | `register_blueprint(bp_ssh)` | 2 |
| `app/templates/base.html` | SSH nav link in `<nav class="floating-settings">` | 3 |
| `app/static/src/ts/main.ts` | `import { init as initSsh }` + `initSsh()` | 2 |

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `ssh/models.py` | Immutable data types: `LoginEvent`, `AnomalyAlert` | Imported by parser, detector, routes |
| `ssh/parser.py` | Regex-based auth.log line parsing → `list[LoginEvent]` | `models.py` only |
| `ssh/geoip.py` | `lookup_country(ip, allowed_hosts) -> str \| None` via ipinfo.io | `http_safety.safe_request` |
| `ssh/detector.py` | Rule engine: per-user aggregation → `list[AnomalyAlert]` | `models.py` only (receives `geo_map` as parameter) |
| `routes/ssh.py` | Flask handlers: file validation, orchestrate ssh/ modules, render | `ssh/` package, `app.limiter` |
| `templates/ssh/upload.html` | Upload form with CSRF | `base.html` via `{% extends %}` |
| `templates/ssh/results.html` | Alert table render | `base.html` via `{% extends %}` |
| `ssh.ts` | File input validation, alert row interactions | DOM only — no enrichment modules |

---

## Data Flow

```
Analyst selects auth.log file in browser
  │
  ▼
POST /ssh/analyze  (multipart/form-data — CSRF token required, NOT exempt)
  │
  ├─ MAX_CONTENT_LENGTH guard (SEC-12) — rejects >512 KB before route handler
  │   See "File Size Constraint" section for guidance.
  │
  ▼
routes/ssh.py — validate file: present? extension .log/.txt? read as UTF-8 bytes?
  │
  ▼
ssh/parser.py — parse(content: str) → list[LoginEvent]
  Each LoginEvent: timestamp, username, source_ip, auth_result, raw_line
  │
  ▼
ssh/geoip.py — deduplicate IPs, call ipinfo.io for each unique IP
  Returns dict[ip_str → country_code]
  Typically 5–50 unique IPs → 5–50 HTTP calls (sequential is fine for v1.2)
  │
  ▼
ssh/detector.py — detect(events, geo_map, config) → list[AnomalyAlert]
  Builds per-user history in one in-memory pass
  Rules: new_ip, new_country, unusual_hours, impossible_travel
  │
  ▼
render_template("ssh/results.html", alerts=alerts, events=events, stats=stats)
  OR return jsonify(...)  for GET /api/ssh/analyze (if JSON API added)
```

---

## Data Models

```python
# app/ssh/models.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class LoginEvent:
    timestamp: datetime
    username: str
    source_ip: str
    auth_result: str   # "accepted" | "failed" | "invalid_user"
    raw_line: str

@dataclass(frozen=True)
class AnomalyAlert:
    rule: str           # "new_ip" | "new_country" | "unusual_hours" | "impossible_travel"
    severity: str       # "high" | "medium" | "low"
    username: str
    source_ip: str
    country_code: str | None
    timestamp: datetime
    detail: str         # human-readable explanation
    raw_line: str       # the triggering log line
```

Both are frozen dataclasses — consistent with the project-wide immutability pattern
(`IOC`, `EnrichmentResult`, `EnrichmentError` are all frozen). `severity` is a string
rather than an enum to keep the models dependency-free; validate at construction time.

---

## GeoIP Reuse Without Coupling to the Enrichment Pipeline

`IPApiAdapter` in `app/enrichment/adapters/ip_api.py` is designed for the enrichment
pipeline: it accepts an `IOC`, returns an `EnrichmentResult`, and is registered in
`ProviderRegistry`. Do not use it directly in SSH. The coupling — IOC type guard,
`EnrichmentResult` schema, `CacheStore` key structure — is irrelevant and wrong for SSH.

Instead, create `ssh/geoip.py` as a standalone module that reuses only the safe HTTP layer:

```python
# app/ssh/geoip.py
"""GeoIP country lookup for SSH anomaly detection.

Uses ipinfo.io (already in ALLOWED_API_HOSTS). Reuses the safe_request()
path from http_safety for SSRF validation, timeout, byte cap, and exception
handling — without importing any enrichment models.
"""
from __future__ import annotations

import requests
from app.enrichment.http_safety import validate_endpoint, TIMEOUT, MAX_RESPONSE_BYTES

IPINFO_BASE = "https://ipinfo.io"


def lookup_country(ip: str, allowed_hosts: list[str]) -> str | None:
    """Return ISO-3166-1 alpha-2 country code for ip, or None on any error.

    Private/reserved IPs return None (ipinfo.io returns 404 for these).
    """
    url = f"{IPINFO_BASE}/{ip}/json"
    try:
        validate_endpoint(url, allowed_hosts)
        resp = requests.get(url, timeout=TIMEOUT, allow_redirects=False, stream=True)
        if resp.status_code == 404:
            return None   # private/reserved IP
        resp.raise_for_status()
        chunks, total = [], 0
        for chunk in resp.iter_content(chunk_size=8192):
            total += len(chunk)
            if total > MAX_RESPONSE_BYTES:
                return None
            chunks.append(chunk)
        import json
        body = json.loads(b"".join(chunks))
        return body.get("country") or None
    except Exception:
        return None  # never raise — absence of GeoIP is handled by detector
```

This approach reuses `validate_endpoint`, `TIMEOUT`, and `MAX_RESPONSE_BYTES` from
`http_safety` (the same constants used by every enrichment adapter) without importing
`EnrichmentError` or `IOC`. The `ipinfo.io` hostname is already in `ALLOWED_API_HOSTS`
in `app/config.py` — no allowlist change is needed.

**Caching GeoIP in SSH:** Do not use `CacheStore`. Its key schema is `(ioc_value, ioc_type,
provider)` — designed for enrichment. Instead, deduplicate IPs before calling `lookup_country`.
A log with 200 events from 5 unique IPs makes exactly 5 HTTP calls.

---

## In-Memory State for Per-User History

SSH detection is stateless per upload. The detector receives all `LoginEvent` objects from
one log file and builds per-user histories during a single in-memory pass. No cross-request
state is needed for v1.2.

```python
# app/ssh/detector.py (sketch)
from collections import defaultdict
from datetime import timezone

def detect(
    events: list[LoginEvent],
    geo_map: dict[str, str | None],   # ip → country_code | None
    normal_hours: tuple[int, int] = (6, 22),
) -> list[AnomalyAlert]:
    seen_ips:        dict[str, set[str]]      = defaultdict(set)
    seen_countries:  dict[str, set[str]]      = defaultdict(set)
    last_event:      dict[str, LoginEvent]    = {}
    alerts:          list[AnomalyAlert]       = []

    for event in sorted(events, key=lambda e: e.timestamp):
        user = event.username
        cc = geo_map.get(event.source_ip)

        # Rule evaluation — each emits zero or one AnomalyAlert
        ...

        seen_ips[user].add(event.source_ip)
        if cc:
            seen_countries[user].add(cc)
        last_event[user] = event

    return alerts
```

The `geo_map` is built by the route handler before calling `detect()`. The detector never
makes HTTP calls and is fully testable with no network access.

If a future milestone adds "upload multiple logs to build a baseline," the right approach is
a new `SshBaselineStore` (SQLite, same threading pattern as `CacheStore`) attached to the app
as `app.ssh_baseline_store` in `create_app()`. Do not bolt that onto `CacheStore`.

---

## Anomaly Detection Rules

| Rule | Trigger | Severity | Notes |
|------|---------|----------|-------|
| `new_ip` | IP not seen before for this user in this log | low | Suppress if only one login total (everything is "new") |
| `new_country` | Country not seen before for this user | medium | Skip if GeoIP unavailable for this IP |
| `unusual_hours` | Login outside configurable window (default 06–22) | low | Use server-local time from log timestamp |
| `impossible_travel` | Two logins from different countries within physically impossible timespan | high | Requires lat/lon from ipinfo.io `loc` field; 500 km/h threshold |

`impossible_travel` requires the `loc` field from ipinfo.io (e.g. `"37.3382,-121.8863"`).
Extend `geoip.py` to return a small struct `(country_code, lat, lon)` rather than just a
country code — this costs nothing extra since the full response is already fetched.

---

## Blueprint Registration

```python
# app/__init__.py — inside create_app(), after existing bp/bp_api registration
from .routes.ssh import bp_ssh
app.register_blueprint(bp_ssh)
```

```python
# app/routes/ssh.py
from flask import Blueprint, current_app, render_template, request
from app import limiter

bp_ssh = Blueprint("ssh", __name__, url_prefix="/ssh")

@bp_ssh.route("/", methods=["GET"])
@limiter.limit("60 per minute")
def upload_form():
    return render_template("ssh/upload.html")

@bp_ssh.route("/analyze", methods=["POST"])
@limiter.limit("5 per minute")
def analyze():
    # validate, parse, geoip, detect, render
    ...
```

Route names: `url_for('ssh.upload_form')`, `url_for('ssh.analyze')`.
`bp_ssh` is NOT CSRF-exempt — file upload is a state-changing POST. The CSRF meta tag in
`base.html` is already wired; browser forms include the token automatically via Flask-WTF.

---

## Template Inheritance

SSH templates extend `base.html` with no changes to `base.html` itself except the nav link:

```html
{# templates/ssh/upload.html #}
{% extends "base.html" %}
{% block content %}
  <section class="site-section">
    {# File upload form — CSRF token included automatically via Flask-WTF #}
    <form method="post" enctype="multipart/form-data" action="{{ url_for('ssh.analyze') }}">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      ...
    </form>
  </section>
{% endblock %}
```

`base.html` provides: nav chrome, CSP meta, CSRF meta, font preloads, `style.css`, `main.js`.
The single surgical addition to `base.html` is one nav link:

```html
{# base.html — add inside <nav class="floating-settings"> #}
<a href="{{ url_for('ssh.upload_form') }}"
   class="nav-link nav-link--icon"
   aria-label="SSH Analysis">
  {{ icon("shield-check", class="nav-icon nav-icon--lg") }}
</a>
```

Verify the icon slug exists in `app/templates/macros/icons.html` before using it. Do not
introduce a new icon unless it is already in the Heroicon set used by the project.

---

## TypeScript Module

```typescript
// app/static/src/ts/modules/ssh.ts
export function init(): void {
  // 1. File input: validate extension + warn on size before submit
  // 2. Alert table: copy-to-clipboard on alert rows (follow clipboard.ts pattern)
  // 3. Alert table: severity filter (optional — pure CSS class toggle is enough for v1.2)
}
```

Register in `main.ts`:
```typescript
import { init as initSsh } from "./modules/ssh";
// in init(): initSsh();
```

SSH analysis is synchronous — parse + detect runs inside the POST handler, no background
jobs or polling. Do not wire `ssh.ts` to the enrichment polling machinery in `enrichment.ts`.

---

## File Size Constraint

The existing `MAX_CONTENT_LENGTH` of 512 KB applies globally and is enforced before any
route handler runs (SEC-12). Flask has no per-route content-length override. Options:

1. **Recommended for v1.2:** Keep the 512 KB limit and document it. A trimmed auth.log
   covering 24–48 hours of typical server activity is under 512 KB. Display the limit
   clearly on the upload form so analysts know to trim the file if needed.

2. **If analysts need larger files:** Raise `MAX_CONTENT_LENGTH` globally to e.g. 2 MB.
   This relaxes the guard for all routes, not just SSH. Document the security tradeoff
   (POST body size limit affects the IOC paste endpoint too).

Option 1 is consistent with "single-shot triage tool" scope and avoids a security regression.

---

## Security Posture

| Concern | Mitigation |
|---------|-----------|
| File upload injection | Validate extension; read as text only; never execute content; no subprocess |
| Path traversal | In-memory processing only; filename not used after content is read |
| Large file DoS | Existing 512 KB `MAX_CONTENT_LENGTH` guard |
| GeoIP SSRF | `validate_endpoint()` + `TIMEOUT` + byte cap reused from `http_safety`; `ipinfo.io` already in allowlist |
| Auth.log leaking to client | Render only structured fields; `raw_line` on `AnomalyAlert` goes through `{{ var }}` autoescaping, never `\| safe` |
| CSRF on upload | `bp_ssh` is NOT CSRF-exempt; CSRF token required on form POST |
| XSS from log content | Jinja2 autoescaping ON for `.html` templates; all log-derived fields rendered via `{{ var }}` |
| innerHTML in `ssh.ts` | Follow SEC-08 — `createElement` + `textContent` only, no `innerHTML` |

---

## Build Order (Phase Dependencies)

The dependency graph is a strict DAG. Build bottom-up.

```
Phase 1 — Models + Parser (zero external dependencies)
  app/ssh/__init__.py          (empty, package marker)
  app/ssh/models.py            (frozen dataclasses only)
  app/ssh/parser.py            (regex + models import)
  tests/unit/test_ssh_parser.py

Phase 2 — GeoIP Wrapper (depends on http_safety — already exists)
  app/ssh/geoip.py             (imports validate_endpoint, TIMEOUT, MAX_RESPONSE_BYTES)
  tests/unit/test_ssh_geoip.py (mock requests.get)

Phase 3 — Detector (depends on models; geoip decoupled via geo_map parameter)
  app/ssh/detector.py          (pure function: events + geo_map → alerts)
  tests/unit/test_ssh_detector.py  (no network, pass geo_map dict directly)

Phase 4 — Routes + Templates (depends on all ssh/ modules)
  app/routes/ssh.py            (register bp_ssh, orchestrate phases 1-3)
  app/templates/ssh/upload.html
  app/templates/ssh/results.html
  app/__init__.py              (+2 lines: import bp_ssh, register_blueprint)
  app/templates/base.html      (+3 lines: nav link)
  tests/unit/test_ssh_routes.py

Phase 5 — TypeScript (depends on templates existing)
  app/static/src/ts/modules/ssh.ts
  app/static/src/ts/main.ts   (+2 lines: import + initSsh())
  make js-dev
```

Key dependency insight: the detector accepts `geo_map: dict[str, str | None]` as a
parameter rather than calling `geoip.lookup_country` directly. This means Phase 3
(detector) can be built and fully tested before Phase 2 (GeoIP) is complete. The route
handler in Phase 4 is the only place that wires them together.

---

## What Does Not Change

The following existing components are untouched by this feature:

| Component | Reason |
|-----------|--------|
| `app/enrichment/` (all 20+ files) | SSH does not use the enrichment pipeline |
| `app/pipeline/` (extractor, classifier, normalizer) | SSH has its own parser |
| `app/cache/store.py` | SSH is stateless per upload; no cache needed |
| `app/routes/__init__.py` | `bp` and `bp_api` blueprints unchanged |
| `app/enrichment/adapters/ip_api.py` | GeoIP reused via `http_safety` constants, not via adapter class |
| `app/config.py` | `ipinfo.io` already in `ALLOWED_API_HOSTS`; no change required |
| All existing templates (9 files) | SSH templates are new files in `templates/ssh/` |
| All existing TS modules (14 files) | `ssh.ts` is additive; `main.ts` gets 2 lines |
| Existing test suite (757 unit + 91 E2E) | No existing test should need modification |

---

## Sources

All findings are from direct file inspection (no training data relied upon):

- `app/__init__.py` — blueprint registration pattern, singleton stores, security scaffold
- `app/config.py` — `ALLOWED_API_HOSTS` (ipinfo.io already present), `MAX_CONTENT_LENGTH`
- `app/enrichment/http_safety.py` — `safe_request`, `validate_endpoint`, `TIMEOUT`, `MAX_RESPONSE_BYTES`
- `app/enrichment/adapters/ip_api.py` — ipinfo.io response shape, `loc` field availability
- `app/enrichment/adapters/base.py` — `BaseHTTPAdapter` pattern (informational, not reused in SSH)
- `app/enrichment/models.py` — frozen dataclass pattern
- `app/pipeline/models.py` — `IOC` frozen dataclass, confirming project-wide convention
- `app/cache/store.py` — CacheStore key schema `(ioc_value, ioc_type, provider)`
- `app/routes/__init__.py` — blueprint structure (`bp` + `bp_api`)
- `app/routes/_helpers.py` — in-memory orchestrator state, `_MAX_ORCHESTRATORS` LRU pattern
- `app/routes/api.py` — `bp_api = Blueprint("api", ..., url_prefix="/api")` pattern
- `app/routes/analysis.py` — route handler structure, `limiter.limit` usage
- `app/templates/base.html` — nav chrome, CSRF meta tag, `{% block content %}`
- `app/static/src/ts/main.ts` — module init registration pattern
