# Phase 2: Core Enrichment - Research

**Researched:** 2026-02-21
**Domain:** VirusTotal API v3 integration, parallel HTTP enrichment, Flask settings page, HTTP safety controls
**Confidence:** HIGH (VirusTotal API), HIGH (concurrency pattern), MEDIUM (incremental UI pattern)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Results presentation:**
- Minimal verdict display: one line per provider showing provider name, verdict (malicious/clean/unknown), and scan date
- Color-coded verdict badges: red for malicious, green for clean, gray for unknown/no-data
- Light summary count at IOC level: e.g., "1/1 malicious" — a tally, not a combined score
- Copy button on each IOC copies the IOC value plus enrichment summary in compact text format
- Add a full export button to export all IOCs + enrichment at once (clipboard or file)

**Error & loading states:**
- Dual loading indicators: global progress bar at top ("3/7 IOCs enriched") plus per-IOC spinners
- Auto-retry once on enrichment failure, then show error if still failing
- On API key invalid or rate-limited: warn the analyst before submitting ("API key issue detected — continue with offline only?") rather than blocking or silently degrading

**API key handling:**
- Settings page in the app where the analyst pastes their VT API key — no env var requirement
- When no API key is configured, online mode is visible but clicking it redirects to the settings page to add the key

### Claude's Discretion

- Enrichment results layout approach (inline under IOC vs side panel vs other) — pick what fits the existing accordion template
- Error display approach (inline badges, toasts, or combination)
- "No data" vs "Clean" visual distinction strategy
- IOC row visual state when flagged (subtle color accent or neutral)
- API key storage mechanism (config file vs .env vs other secure approach)
- API key validation behavior on save (test call vs accept as-is)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ENRC-01 | Application queries VirusTotal API v3 for IP, domain, URL, and hash IOC types and displays detection count, category, and last analysis date | VT API endpoints documented: GET /ip_addresses/{ip}, /domains/{domain}, /urls/{id}, /files/{hash}; response fields last_analysis_stats, last_analysis_date, categories confirmed |
| ENRC-04 | Application executes all provider queries in parallel per IOC (not sequentially) | ThreadPoolExecutor pattern with concurrent.futures confirmed as the correct approach for synchronous Flask; futures.as_completed() enables result streaming |
| ENRC-05 | Each enrichment result displays the provider name, lookup timestamp, and raw provider verdict with no transformation or score blending | last_analysis_stats gives raw counts per vendor category; no normalization needed — pass through directly |
| ENRC-06 | Provider failures return a clear error result per-provider without blocking other providers' results | Per-future exception handling pattern: each future.result() in try/except; failure produces EnrichmentError result, does not affect sibling futures |
| UI-03 | In online mode, enrichment queries fire after extraction and classification complete | Route branches on mode=="online"; pipeline runs first, then enrichment orchestrator called with IOC list |
| UI-05 | Visual loading indicator is displayed while enrichment API calls are in progress | Two viable patterns: (1) full-page enrichment via JavaScript polling a /status endpoint, (2) SSE streaming; polling is simpler given existing synchronous Flask stack |
| SEC-04 | All outbound HTTP requests enforce strict per-request timeouts (no indefinite hangs) | requests.get(..., timeout=(5, 30)) — connect timeout 5s, read timeout 30s — enforced on every call |
| SEC-05 | All outbound HTTP requests enforce a maximum response size limit (streaming + byte counting) | stream=True + iter_content() with byte counter + MAX_RESPONSE_BYTES limit; reject oversized responses mid-stream |
| SEC-06 | Outbound HTTP requests do not follow redirects unless explicitly justified per-provider | requests.get(..., allow_redirects=False) on all enrichment calls; VirusTotal API never requires redirect following |
| SEC-07 | Application never fetches, crawls, or makes HTTP requests to the IOC URL itself — only calls TI API endpoints | Enforced by ALLOWED_API_HOSTS allowlist (already scaffolded in Phase 1 config); URL lookups use base64-encoded identifier in VT endpoint path, never fetch the URL |
</phase_requirements>

## Summary

Phase 2 wires VirusTotal API v3 into the existing offline pipeline. The core technical work is: (1) a VT adapter that maps IOC types to the correct API endpoints and parses responses, (2) a parallel enrichment orchestrator using `concurrent.futures.ThreadPoolExecutor` (the correct choice for synchronous Flask), (3) a settings page for API key storage using Python's `configparser` with a gitignored config file (satisfying the user's "no env var requirement"), and (4) a JavaScript polling loop that drives the dual loading indicator UX without SSE or WebSocket complexity.

The VT API v3 exposes four clean GET endpoints that accept the IOC value directly in the path (IP, domain, hash) or as a base64-encoded URL identifier. All return a `data.attributes` JSON object containing `last_analysis_stats` (malicious/suspicious/harmless/undetected counts) and `last_analysis_date` (Unix timestamp). There is no normalization or score blending — the raw counts are the verdict display, exactly matching ENRC-05.

The critical HTTP safety controls (SEC-04 through SEC-07) are each a single `requests.get()` parameter: `timeout=`, `allow_redirects=False`, `stream=True` with byte counting. The existing `ALLOWED_API_HOSTS` allowlist scaffolded in Phase 1 needs only to be populated with `www.virustotal.com` and enforced at call time.

**Primary recommendation:** Build a thin `VTAdapter` class, a `EnrichmentOrchestrator` using `ThreadPoolExecutor`, a `ConfigStore` using `configparser`, and a `/settings` route. Keep all enrichment code in `app/enrichment/` separate from the existing `app/pipeline/` layer. Results are rendered incrementally via a JavaScript polling loop against a `/enrichment/status/{job_id}` endpoint backed by a thread-safe in-memory dict.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| requests | 2.32.5 (already installed) | HTTP calls to VT API | Already in requirements.txt; synchronous, well-understood, no new dependency |
| concurrent.futures | stdlib (Python 3.10+) | Parallel IOC enrichment | stdlib ThreadPoolExecutor is the idiomatic choice for I/O-bound parallelism in synchronous Flask; no new dependency |
| configparser | stdlib (Python 3.10+) | API key storage in config file | stdlib, no dependency, INI format is human-readable, gitignore-safe |
| base64 | stdlib | URL identifier encoding for VT | VT URL lookup requires base64url encoding without padding |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| threading.Lock | stdlib | Thread-safe job status dict | Needed when ThreadPoolExecutor workers write to shared dict while Flask thread reads it |
| uuid | stdlib | Job IDs for polling endpoint | Simple unique ID generation for enrichment job tracking |
| datetime / time | stdlib | Lookup timestamps, timeout tracking | Format last_analysis_date (Unix epoch) to human-readable strings |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ThreadPoolExecutor | asyncio + httpx | asyncio requires full Flask async migration (Quart) or run_in_executor nesting; ThreadPoolExecutor is simpler and correct for this scale |
| ThreadPoolExecutor | Celery + Redis | Celery is for persistent job queues across processes; this is an in-request enrichment that completes in <30s — massive overkill |
| configparser for key storage | python-dotenv / .env file | .env requires env var approach (user explicitly said no); configparser is more flexible for a settings UI |
| JavaScript polling | Flask SSE (flask-sse) | flask-sse requires Redis; polling is simpler and sufficient for a single-user local tool |
| JavaScript polling | WebSockets | Overkill for one-way, short-lived progress reporting |

**No new pip packages required.** All needed libraries are either already installed (`requests`) or in the Python 3.10 stdlib (`concurrent.futures`, `configparser`, `base64`, `uuid`, `threading`).

## Architecture Patterns

### Recommended Project Structure

```
app/
├── enrichment/             # New in Phase 2 — isolated from pipeline/
│   ├── __init__.py
│   ├── adapters/
│   │   ├── __init__.py
│   │   └── virustotal.py   # VTAdapter: maps IOCType → VT endpoint, parses response
│   ├── models.py           # EnrichmentResult, EnrichmentError dataclasses
│   ├── orchestrator.py     # EnrichmentOrchestrator: ThreadPoolExecutor + job tracking
│   └── config_store.py     # ConfigStore: configparser wrapper for API key persistence
├── pipeline/               # Unchanged from Phase 1
│   ├── classifier.py
│   ├── extractor.py
│   ├── models.py           # IOC, IOCType — used by enrichment layer
│   ├── normalizer.py
│   └── __init__.py
├── templates/
│   ├── base.html           # Update: settings nav link
│   ├── index.html          # Update: online mode redirect behavior
│   ├── results.html        # Update: enrichment display, loading indicators
│   └── settings.html       # New: API key entry form
├── static/
│   ├── main.js             # Update: polling loop, loading state, copy-with-enrichment
│   └── style.css           # Update: verdict badges, progress bar, spinner styles
├── routes.py               # Update: /analyze branches on mode; add /settings routes
├── config.py               # Update: ALLOWED_API_HOSTS += ["www.virustotal.com"]
└── __init__.py             # Unchanged
```

### Pattern 1: VT Adapter — IOCType to Endpoint Mapping

**What:** A stateless class that maps each `IOCType` to its VT API v3 endpoint, constructs the request, enforces all HTTP safety controls, and returns a typed result.

**When to use:** Called once per IOC from the orchestrator's thread pool workers.

```python
# Source: https://docs.virustotal.com/reference/overview
import base64
import time
import requests
from app.pipeline.models import IOC, IOCType
from app.enrichment.models import EnrichmentResult, EnrichmentError

VT_BASE = "https://www.virustotal.com/api/v3"
TIMEOUT = (5, 30)          # (connect, read) — SEC-04
MAX_RESPONSE_BYTES = 1 * 1024 * 1024  # 1 MB cap — SEC-05

ENDPOINT_MAP = {
    IOCType.IPV4:   lambda v: f"{VT_BASE}/ip_addresses/{v}",
    IOCType.IPV6:   lambda v: f"{VT_BASE}/ip_addresses/{v}",
    IOCType.DOMAIN: lambda v: f"{VT_BASE}/domains/{v}",
    IOCType.URL:    lambda v: f"{VT_BASE}/urls/{_url_id(v)}",
    IOCType.MD5:    lambda v: f"{VT_BASE}/files/{v}",
    IOCType.SHA1:   lambda v: f"{VT_BASE}/files/{v}",
    IOCType.SHA256: lambda v: f"{VT_BASE}/files/{v}",
    # CVE is NOT enriched by VT — orchestrator skips IOCType.CVE
}

def _url_id(url: str) -> str:
    """Base64url-encode URL without padding (VT URL identifier format)."""
    # Source: https://docs.virustotal.com/reference/url (base64 w/o padding)
    return base64.urlsafe_b64encode(url.encode()).decode().strip("=")

class VTAdapter:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._session = requests.Session()
        self._session.headers.update({"x-apikey": api_key, "Accept": "application/json"})

    def lookup(self, ioc: IOC) -> EnrichmentResult | EnrichmentError:
        if ioc.type not in ENDPOINT_MAP or ioc.type == IOCType.CVE:
            return EnrichmentError(ioc=ioc, provider="VirusTotal", error="Unsupported type")
        url = ENDPOINT_MAP[ioc.type](ioc.value)
        # SEC-06: no redirects; SEC-04: timeout; SEC-07: URL is VT endpoint, not IOC value
        try:
            resp = self._session.get(
                url, timeout=TIMEOUT, allow_redirects=False, stream=True
            )
            body = _read_limited(resp)  # SEC-05: byte cap
            resp.raise_for_status()
            return _parse_response(ioc, body)
        except requests.exceptions.Timeout:
            return EnrichmentError(ioc=ioc, provider="VirusTotal", error="Timeout")
        except requests.exceptions.HTTPError as e:
            return _map_http_error(ioc, e)
        except Exception as e:
            return EnrichmentError(ioc=ioc, provider="VirusTotal", error=str(e))

def _read_limited(resp) -> dict:
    """Read response with byte cap (SEC-05)."""
    import json
    chunks = []
    total = 0
    for chunk in resp.iter_content(chunk_size=8192):
        total += len(chunk)
        if total > MAX_RESPONSE_BYTES:
            raise ValueError("Response exceeded size limit")
        chunks.append(chunk)
    return json.loads(b"".join(chunks))
```

### Pattern 2: Parallel Enrichment Orchestrator

**What:** Submits one future per IOC to a thread pool, collects results as they complete, updates a shared job-status dict for polling.

**When to use:** Called by the `/analyze` route when `mode == "online"`.

```python
# Source: https://docs.python.org/3/library/concurrent.futures.html
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

class EnrichmentOrchestrator:
    def __init__(self, adapter: VTAdapter, max_workers: int = 10) -> None:
        self._adapter = adapter
        self._max_workers = max_workers
        self._jobs: dict[str, dict] = {}  # job_id → status
        self._lock = Lock()

    def enrich_all(self, job_id: str, iocs: list[IOC]) -> None:
        """Fire enrichment for all IOCs in parallel. Updates job status dict."""
        enrichable = [i for i in iocs if i.type in ENDPOINT_MAP]
        total = len(enrichable)
        with self._lock:
            self._jobs[job_id] = {"total": total, "done": 0, "results": [], "complete": False}

        def _do_lookup(ioc: IOC):
            result = self._adapter.lookup(ioc)
            # Auto-retry once on failure (per user decision)
            if isinstance(result, EnrichmentError):
                result = self._adapter.lookup(ioc)
            return result

        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            futures = {pool.submit(_do_lookup, ioc): ioc for ioc in enrichable}
            for future in as_completed(futures):
                result = future.result()  # safe: exceptions caught in lookup()
                with self._lock:
                    self._jobs[job_id]["results"].append(result)
                    self._jobs[job_id]["done"] += 1
        with self._lock:
            self._jobs[job_id]["complete"] = True
```

### Pattern 3: API Key Config Store

**What:** Reads and writes the VT API key to a gitignored INI config file using Python's stdlib `configparser`. Satisfies the user decision: "Settings page in the app where the analyst pastes their VT API key — no env var requirement."

**When to use:** Settings page save; VT adapter initialization.

```python
# Source: https://docs.python.org/3/library/configparser.html
import configparser
import os
from pathlib import Path

CONFIG_PATH = Path.home() / ".sentinelx" / "config.ini"
# Alternative: Path(__file__).parent.parent / "instance" / "config.ini"
# Use ~/.sentinelx/ to keep outside repo tree — never accidentally committed

class ConfigStore:
    def get_vt_api_key(self) -> str | None:
        cfg = configparser.ConfigParser()
        cfg.read(CONFIG_PATH)
        return cfg.get("virustotal", "api_key", fallback=None) or None

    def set_vt_api_key(self, key: str) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        cfg = configparser.ConfigParser()
        cfg.read(CONFIG_PATH)
        if "virustotal" not in cfg:
            cfg["virustotal"] = {}
        cfg["virustotal"]["api_key"] = key
        with open(CONFIG_PATH, "w") as f:
            cfg.write(f)
```

Key: store config in `~/.sentinelx/config.ini` (outside repo tree). This is never accidentally committed. No gitignore entry needed.

### Pattern 4: JavaScript Polling for Incremental Results

**What:** The `/analyze` POST (online mode) kicks off enrichment in a background thread, returns immediately with a `job_id`. The browser polls `/enrichment/status/{job_id}` every 750ms, updating the progress bar and individual IOC rows as results arrive.

**When to use:** This is the simplest pattern that satisfies the loading indicator requirement (UI-05) without SSE infrastructure.

```javascript
// main.js — polling loop
function pollEnrichment(jobId, totalIocs) {
    var progressBar = document.getElementById('enrich-progress');
    var interval = setInterval(function() {
        fetch('/enrichment/status/' + jobId)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                // Update global progress bar: "3/7 IOCs enriched"
                updateProgressBar(progressBar, data.done, data.total);
                // Update individual IOC rows with newly arrived results
                data.results.forEach(renderEnrichmentResult);
                if (data.complete) {
                    clearInterval(interval);
                    progressBar.classList.add('complete');
                }
            });
    }, 750);
}
```

### Anti-Patterns to Avoid

- **Building URL from IOC value as request target (SEC-07):** Never `requests.get(ioc.value)`. Always use `ENDPOINT_MAP[ioc.type](ioc.value)` which constructs the VT API endpoint path with the IOC as path parameter.
- **Global requests.Session across threads:** Create one session per adapter instance. Sessions are not thread-safe for concurrent use without locking.
- **Blocking Flask response during enrichment:** Enrichment must run in a background thread, not in the request handler. The route returns `job_id` immediately.
- **Bare `future.result()` without exception handling:** The orchestrator's `lookup()` is exception-safe, but the outer orchestrator itself must also guard against unexpected exceptions.
- **Storing enrichment results in Flask `g` or `session`:** These are request-scoped. Use the in-memory job dict (module-level on the orchestrator) or Flask's application context.
- **Following redirects on enrichment calls (SEC-06):** VirusTotal API never redirects legitimate lookups. A redirect is a signal of misconfiguration or attack.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parallel HTTP calls | Manual thread list + join | `concurrent.futures.ThreadPoolExecutor` | stdlib, handles worker lifecycle, exception propagation, timeout |
| Response size limiting | Custom buffered reads | `stream=True` + `iter_content(8192)` + byte counter | Proven pattern; iter_content respects chunk boundaries |
| Redirect prevention | Custom redirect checker | `allow_redirects=False` parameter | Single parameter; custom solution is fragile |
| API key storage | Custom encryption or database | `configparser` to `~/.sentinelx/config.ini` | stdlib, proven, human-readable; overkill to encrypt a local analyst tool key |
| URL base64 encoding | Custom encoding | `base64.urlsafe_b64encode(...).strip("=")` | One-liner using stdlib |

**Key insight:** All HTTP safety controls are single `requests.get()` parameters. There is nothing complex to build — the complexity is in not forgetting them.

## Common Pitfalls

### Pitfall 1: VT 404 is Not an Error — It Means "No Data"

**What goes wrong:** Treating HTTP 404 from VT as an enrichment failure error. 404 means "VirusTotal has never seen this IOC" — which is meaningful information, not an error.

**Why it happens:** Standard HTTP error handling raises on 4xx. VT 404 is semantically different.

**How to avoid:** Check `status_code == 404` before `raise_for_status()`. Return an `EnrichmentResult` with `verdict="no_data"` (not an `EnrichmentError`).

**Warning signs:** All enrichment results for new/private IOCs show as errors rather than "No data".

### Pitfall 2: URL IOC Lookup Identity Confusion

**What goes wrong:** Sending the URL value as a direct path segment (`/urls/https://evil.com/path`) — which breaks due to slashes and fails URL-path parsing.

**Why it happens:** IP and domain lookups use the value directly. URL lookups require base64url encoding.

**How to avoid:** Use `_url_id(url)` which applies `base64.urlsafe_b64encode(url.encode()).decode().strip("=")`. Verified against VT docs.

**Warning signs:** All URL lookups return 404 or 400.

### Pitfall 3: requests.Session Thread Safety

**What goes wrong:** Sharing a single `requests.Session` instance across all ThreadPoolExecutor worker threads leads to race conditions on connection pool and header state.

**Why it happens:** `requests.Session` maintains internal state (cookies, adapters) that is not documented as thread-safe for concurrent use.

**How to avoid:** Create one `VTAdapter` instance per enrichment call, or create a new `Session` inside each worker thread. The simplest correct approach: create the Session in `VTAdapter.__init__()` and instantiate one adapter per enrichment job (not one globally).

**Warning signs:** Intermittent connection errors or corrupted headers under parallel load.

### Pitfall 4: Enrichment Blocks Flask Request Thread

**What goes wrong:** Calling `orchestrator.enrich_all()` directly in the route handler blocks the Flask development server (single-threaded by default) until all enrichment completes.

**Why it happens:** Flask's development server is single-threaded; `enrich_all()` blocks the calling thread.

**How to avoid:** Submit enrichment as a background thread immediately after getting the `job_id`. The route returns a redirect or partial page with the `job_id` for polling. Use `threading.Thread(target=orchestrator.enrich_all, args=(job_id, iocs), daemon=True).start()`.

**Warning signs:** Browser hangs on POST /analyze for the full enrichment duration.

### Pitfall 5: CVE Type Sent to VirusTotal

**What goes wrong:** Sending CVE IOCs to VT `GET /files/CVE-2025-12345` — VT does not have a CVE endpoint. The request returns 404 or malformed response.

**Why it happens:** Iterating over all `iocs` without filtering by type.

**How to avoid:** `ENDPOINT_MAP` only contains the four VT-supported types. The orchestrator filters: `enrichable = [i for i in iocs if i.type in ENDPOINT_MAP]`.

**Warning signs:** All CVE IOCs show as VT errors.

### Pitfall 6: API Key Validation on Settings Save

**What goes wrong:** Making a live VT API call to validate the key on the settings save endpoint — this (a) adds latency, (b) consumes quota, and (c) ties settings save to VT availability.

**Why it happens:** "Validate on save" seems like good UX but has hidden costs.

**How to avoid:** Per Claude's Discretion, recommend "accept as-is" on save. The first enrichment attempt reveals an invalid key via `WrongCredentialsError (401)`, which triggers the pre-submit warning flow.

**Warning signs:** Settings saves are slow or fail when VT is unreachable.

### Pitfall 7: Rate Limiting (4 requests/minute on free VT key)

**What goes wrong:** Submitting a paste with 20 IOCs fires 20 parallel VT calls, hitting the 4 req/min public API rate limit almost immediately, causing `QuotaExceededError (429)` for most results.

**Why it happens:** The public VT key is rate-limited to 4 req/min (500/day). Parallel execution sends all requests at once.

**How to avoid:** Two strategies: (a) set `max_workers=4` in ThreadPoolExecutor to naturally throttle to ~4 concurrent requests, or (b) detect 429 in the error handler and surface it clearly per-provider with the pre-submit warning (per user decision). The user decision already covers this: "On rate-limited: warn the analyst before submitting."

**How to detect the rate limit before submission:** Make one lightweight probe call (e.g., check API key validity) and surface warnings proactively.

**Warning signs:** Most enrichment results come back as `QuotaExceededError`.

## Code Examples

Verified patterns from official sources:

### VT Response Structure (all IOC types)

```json
{
  "data": {
    "type": "ip_address",
    "id": "1.2.3.4",
    "attributes": {
      "last_analysis_stats": {
        "malicious": 5,
        "suspicious": 0,
        "harmless": 60,
        "undetected": 8,
        "timeout": 0
      },
      "last_analysis_date": 1700000000,
      "categories": {
        "Forcepoint ThreatSeeker": "malicious sites",
        "BitDefender": "malware"
      }
    }
  }
}
```

### Parsing VT Response into EnrichmentResult

```python
# Source: VT API v3 reference + example JSON structure
import datetime

def _parse_response(ioc: IOC, body: dict) -> EnrichmentResult:
    attrs = body["data"]["attributes"]
    stats = attrs.get("last_analysis_stats", {})
    last_analysis_date = attrs.get("last_analysis_date")
    ts = (
        datetime.datetime.fromtimestamp(last_analysis_date, tz=datetime.timezone.utc).isoformat()
        if last_analysis_date
        else None
    )
    malicious = stats.get("malicious", 0)
    total = sum(stats.values()) - stats.get("timeout", 0) - stats.get("type-unsupported", 0)
    if malicious > 0:
        verdict = "malicious"
    elif total == 0:
        verdict = "no_data"
    else:
        verdict = "clean"
    return EnrichmentResult(
        ioc=ioc,
        provider="VirusTotal",
        verdict=verdict,
        detection_count=malicious,
        total_engines=total,
        scan_date=ts,
        raw_stats=stats,
    )

def _map_http_error(ioc: IOC, err) -> EnrichmentResult | EnrichmentError:
    if err.response is not None and err.response.status_code == 404:
        # 404 = VT has no record; not an error
        return EnrichmentResult(ioc=ioc, provider="VirusTotal", verdict="no_data",
                                detection_count=0, total_engines=0, scan_date=None, raw_stats={})
    code = err.response.status_code if err.response is not None else "unknown"
    if code == 429:
        return EnrichmentError(ioc=ioc, provider="VirusTotal", error="Rate limit exceeded (429)")
    if code in (401, 403):
        return EnrichmentError(ioc=ioc, provider="VirusTotal", error=f"Authentication error ({code})")
    return EnrichmentError(ioc=ioc, provider="VirusTotal", error=f"HTTP {code}")
```

### EnrichmentResult and EnrichmentError Models

```python
from dataclasses import dataclass, field
from app.pipeline.models import IOC

@dataclass(frozen=True)
class EnrichmentResult:
    ioc: IOC
    provider: str
    verdict: str           # "malicious" | "clean" | "no_data"
    detection_count: int
    total_engines: int
    scan_date: str | None  # ISO8601 string or None
    raw_stats: dict        # last_analysis_stats passthrough

@dataclass(frozen=True)
class EnrichmentError:
    ioc: IOC
    provider: str
    error: str             # human-readable error message
```

### Enforcing SEC-16 ALLOWED_API_HOSTS

```python
# app/enrichment/adapters/virustotal.py
from urllib.parse import urlparse
from flask import current_app

def _validate_endpoint(url: str) -> None:
    """Raise if endpoint hostname is not on the SSRF allowlist (SEC-16)."""
    parsed = urlparse(url)
    allowed = current_app.config.get("ALLOWED_API_HOSTS", [])
    if parsed.hostname not in allowed:
        raise ValueError(f"Endpoint hostname {parsed.hostname!r} not in ALLOWED_API_HOSTS")

# In config.py, add: ALLOWED_API_HOSTS: list[str] = ["www.virustotal.com"]
```

### Polling Endpoint

```python
# app/routes.py (addition)
import json

@bp.route("/enrichment/status/<job_id>")
def enrichment_status(job_id):
    """Return current enrichment job status as JSON for polling."""
    status = orchestrator.get_status(job_id)
    if status is None:
        return {"error": "job not found"}, 404
    # Serialize results for JSON transport
    return {
        "total": status["total"],
        "done": status["done"],
        "complete": status["complete"],
        "results": [_serialize_result(r) for r in status["results"]],
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| VT API v2 (md5 hash only, XML responses) | VT API v3 (all types, JSON, consistent /api/v3/ prefix) | VT v3 GA ~2019, v2 deprecated | All new code targets v3; v2 docs are misleading if found |
| Celery for in-request parallel calls | concurrent.futures.ThreadPoolExecutor | Python 3.2+ | No Redis/broker needed for lightweight per-request parallelism |
| Global requests.Session | Per-adapter Session (or session-per-thread) | requests 2.x | Thread safety is not guaranteed; per-instance is correct |

**Deprecated/outdated:**
- VT API v2 docs: Outdated; v2 used `/vtapi/v2/` prefix, XML or JSON, different endpoint structure. All current work uses `/api/v3/`.
- flask-sse: Requires Redis pub/sub backend. Not appropriate for a single-user local tool with no persistent broker.

## Open Questions

1. **API key validation on settings save — test call vs accept-as-is**
   - What we know: User left this to Claude's discretion. Making a live call on save consumes quota and ties save to VT availability.
   - What's unclear: Whether the analyst expects immediate feedback that the key works.
   - Recommendation: Accept-as-is on save. The first enrichment run will surface `WrongCredentialsError (401)` with a clear pre-submit warning per the user's error handling decision. Document this in the settings page UI.

2. **In-memory job store cleanup — memory leak risk**
   - What we know: Each enrichment run creates a job entry in a module-level dict. Entries are never cleaned up.
   - What's unclear: Whether this is a real concern for a single-user local tool with short sessions.
   - Recommendation: Add a simple LRU eviction with `maxsize=100` jobs, or expire jobs after 10 minutes using a timestamp. Use `collections.OrderedDict` for simple LRU.

3. **Results page: full-page POST vs redirect-after-POST with polling**
   - What we know: The current `/analyze` route renders `results.html` directly from the POST response. Adding polling requires either (a) changing the flow to POST → redirect to `/results/{job_id}` or (b) injecting a `job_id` into the existing results.html and starting the poll from JS.
   - What's unclear: Which approach fits better with the existing `<details>/<summary>` accordion template.
   - Recommendation: Inject `job_id` into `results.html` as a `data-job-id` attribute on the page body, keep the extraction results in the existing table structure, and add enrichment columns per-row that start as spinners. Avoids changing the POST → render flow.

4. **Max workers for ThreadPoolExecutor vs VT rate limit**
   - What we know: Public VT key = 4 req/min. Parallel execution can hit this immediately with >4 IOCs.
   - What's unclear: Whether `max_workers=4` is sufficient throttling or whether explicit rate-limiting logic is needed.
   - Recommendation: Set `max_workers=4` as a conservative default. Add a `VT_MAX_WORKERS` config key so it's adjustable. Document that free key users should expect 429 on large pastes and point to the pre-submit warning flow.

## Sources

### Primary (HIGH confidence)

- https://docs.virustotal.com/reference/overview — VT API v3 overview, authentication, endpoint structure
- https://docs.virustotal.com/reference/ip-info — IP address endpoint, response fields
- https://docs.virustotal.com/reference/domain-info — Domain endpoint, response fields
- https://docs.virustotal.com/reference/url-info — URL endpoint, base64 identifier
- https://docs.virustotal.com/reference/file-info — File/hash endpoint, response fields
- https://docs.virustotal.com/reference/errors — Error codes: 404 NotFoundError, 429 QuotaExceeded, 401 WrongCredentials
- https://docs.python.org/3/library/concurrent.futures.html — ThreadPoolExecutor, as_completed
- https://docs.python.org/3/library/configparser.html — ConfigParser INI file API
- https://docs.python-requests.org/en/latest/ — allow_redirects, timeout, stream, iter_content

### Secondary (MEDIUM confidence)

- https://docs.virustotal.com/reference/public-vs-premium-api — Rate limits: 4 req/min, 500 req/day (public key)
- VT URL encoding verified: `base64.urlsafe_b64encode(url.encode()).decode().strip("=")` — confirmed in VT docs and multiple SOC blog posts
- https://flask.palletsprojects.com/en/stable/patterns/javascript/ — Flask JavaScript/fetch integration patterns

### Tertiary (LOW confidence — needs validation)

- requests.Session thread safety: documented as "not thread-safe" in community sources and multiple GitHub issues; official docs do not explicitly state this — treat as LOW until tested under concurrent load
- `max_workers=4` as VT rate limit throttle: logical deduction (4 concurrent = ~4 req/interval), not explicitly documented by VT

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are stdlib or already installed; no ambiguity about which tools to use
- Architecture: HIGH — VT API endpoints and response structure are official-documented; parallel pattern is well-established
- Pitfalls: HIGH — VT 404 semantics, URL base64 encoding, CVE exclusion all verified against official docs; thread safety and rate limiting are community-verified
- Incremental UI pattern: MEDIUM — polling pattern is verified in Flask docs; specific implementation details (job store cleanup, redirect-after-POST vs inject) remain as open questions

**Research date:** 2026-02-21
**Valid until:** 2026-04-21 (stable VT API; 60-day estimate)
