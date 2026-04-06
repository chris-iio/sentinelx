# Architecture

**Analysis Date:** 2026-04-06

## Pattern Overview

**Overall:** Layered pipeline architecture with offline extraction → online enrichment orchestration. SentinelX implements a meta-search engine for threat intelligence: extract indicators of compromise (IOCs) from free-form text, dispatch parallel enrichment queries to 14 threat intelligence providers, aggregate results, and render unified intelligence reports.

**Key Characteristics:**
- Offline IOC extraction pipeline (pure functions, no network)
- Online enrichment via provider adapter protocol (pluggable)
- Parallel ThreadPoolExecutor orchestration with per-provider rate limiting
- Immutable data models throughout (frozen dataclasses)
- Provider registry with configuration-aware dispatch
- Frontend polling orchestrator with verdict aggregation
- SQLite cache with TTL for enrichment results

## Layers

**Web Layer (Flask):**
- Purpose: HTTP request handling, template rendering, CSRF protection, rate limiting
- Location: `app/routes/`, `app/__init__.py`, `app/config.py`
- Contains: 6 route modules (analysis, detail, enrichment, history, settings, api) + security scaffold
- Depends on: Pipeline (IOC extraction), Enrichment (orchestrator/registry), History/Cache stores
- Used by: Browser/client

**Pipeline Layer (Extraction):**
- Purpose: Convert free-form analyst text into typed IOC objects (offline only)
- Location: `app/pipeline/`
- Contains: 
  - `extractor.py` - Uses iocextract + iocsearcher libraries, returns raw candidates
  - `normalizer.py` - Canonicalizes IOC strings (defanging, case normalization)
  - `classifier.py` - Regex-based type detection with strict precedence (9 types)
  - `models.py` - IOC and IOCType frozen dataclasses
- Depends on: None (pure functions, no Flask/network imports)
- Used by: Analysis routes, API routes

**Enrichment Layer (Provider Protocol):**
- Purpose: Define standardized interface for threat intelligence adapters
- Location: `app/enrichment/provider.py`
- Contains: `Provider` runtime-checkable Protocol (name, supported_types, requires_api_key, lookup(), is_configured())
- Depends on: IOC models, EnrichmentResult/Error models
- Used by: Registry, Orchestrator, all adapter implementations

**Registry Layer:**
- Purpose: Central registry of configured providers (dependency injection)
- Location: `app/enrichment/registry.py`, `app/enrichment/setup.py`
- Contains:
  - `ProviderRegistry` - stores providers by name, queries by type/configuration status
  - `build_registry()` - startup factory that instantiates all 14 providers
- Depends on: Provider protocol, ConfigStore
- Used by: Flask app factory, Analysis routes, API routes

**Orchestration Layer:**
- Purpose: Parallel enrichment dispatcher with rate-limit management and job tracking
- Location: `app/enrichment/orchestrator.py`
- Contains:
  - `EnrichmentOrchestrator` - ThreadPoolExecutor-based parallel lookup with per-provider Semaphores
  - Job status tracking in OrderedDict with LRU eviction
  - Backoff+retry logic for rate-limited (429) responses
- Depends on: Provider protocol, IOC models, CacheStore
- Used by: Route helpers, enrichment endpoints

**Configuration Layer:**
- Purpose: Read/write provider API keys and application settings
- Location: `app/enrichment/config_store.py`
- Contains: ConfigStore — INI-based multi-provider config at `~/.sentinelx/config.ini`
- Depends on: None
- Used by: Registry, Settings routes

**Cache Layer:**
- Purpose: SQLite-backed result caching with per-provider TTL
- Location: `app/cache/store.py`
- Contains: CacheStore — persistent cache at `~/.sentinelx/cache.db`; WAL mode + pragma optimizations
- Depends on: None
- Used by: Orchestrator (cache-check + cache-store in lookup pipeline)

**History Layer:**
- Purpose: Persist analysis sessions (IOCs, results, metadata)
- Location: `app/enrichment/history_store.py`
- Contains: HistoryStore — SQLite-backed session storage at `~/.sentinelx/history.db`
- Depends on: None
- Used by: Route helpers (saves after enrichment completes)

**Adapter Layer (14 Providers):**
- Purpose: Implement Provider protocol for each threat intelligence source
- Location: `app/enrichment/adapters/`
- Contains: 14 adapter modules (virustotal, malwarebazaar, threatfox, shodan, urlhaus, otx, greynoise, abuseipdb, hashlookup, ip_api, dns_lookup, crtsh, threatminer, asn_cymru) + whois_lookup
- Depends on: Provider protocol, IOC models, http_safety module
- Used by: Registry (instantiated at startup)

**Frontend Layer (TypeScript/IIFE):**
- Purpose: Browser-based UI interactions (form, polling, rendering, filtering, export)
- Location: `app/static/src/ts/`
- Contains: 15+ modules organized by feature (enrichment, cards, filter, history, etc.); compiled to IIFE via esbuild
- Depends on: Backend API endpoints (/api/analyze, /api/status, /settings endpoints)
- Used by: Browser (HTML templates in `app/templates/`)

## Data Flow

**Offline Extraction Flow:**

1. Analyst pastes text in home page (`index.html`)
2. Form submission POST to `/analyze` with `mode=offline`
3. `run_pipeline(text)` in `extractor.py`:
   - Extract raw candidates (iocextract + iocsearcher)
   - Normalize each candidate (remove defanging, lowercase, trim)
   - Classify normalized string via regex patterns (precedence: CVE → SHA256 → SHA1 → MD5 → URL → IPv6 → IPv4 → Email → Domain)
   - Deduplicate by (type, value)
   - Return list of IOC dataclasses
4. Group IOCs by type (`group_by_type()`)
5. Render results.html template with IOC cards

**Online Enrichment Flow:**

1. User submits form with `mode=online`
2. `/analyze` route:
   - Extracts IOCs (same as offline)
   - Checks if registry has configured providers
   - Calls `_setup_orchestrator()` which:
     - Generates job_id (UUID)
     - Creates EnrichmentOrchestrator instance
     - Registers orchestrator in route-module-level `_orchestrators` OrderedDict
     - Submits `_run_enrichment_and_save()` to shared ThreadPoolExecutor
   - Returns job_id to template
3. Frontend polls `/api/status/<job_id>` via cursor-based fetch loop
4. Orchestrator.enrich_all() in background thread:
   - For each IOC × matching provider pair:
     - Check cache (TTL-aware)
     - If cache miss: acquire per-provider Semaphore, dispatch lookup via provider.lookup()
     - Retry once on 429 (rate-limit) with exponential backoff
     - Cache miss? Store result in CacheStore
     - Track result in job status dict
5. /api/status endpoint returns accumulated results + job state (running/done)
6. Frontend receives results, renders detail rows per IOC, sorts by verdict severity
7. After enrichment completes: history_store.save_analysis() persists session

**State Management:**

- `app.registry` — cached ProviderRegistry (built at startup, invalidated when settings saved)
- `app.cache_store` — singleton CacheStore (persistent SQLite)
- `app.history_store` — singleton HistoryStore (persistent SQLite)
- `_orchestrators` (route module state) — OrderedDict of job_id → EnrichmentOrchestrator (LRU eviction, max 200)
- Frontend module state — per-IOC dedup maps, polling timers, verdict caches (all ephemeral)

## Key Abstractions

**IOC (Indicator of Compromise):**
- Purpose: Immutable typed indicator with canonical + original forms
- Examples: `app/pipeline/models.py`
- Pattern: frozen dataclass with type: IOCType, value: str (canonical), raw_match: str (original)

**EnrichmentResult / EnrichmentError:**
- Purpose: Result type for provider lookups (success | error)
- Examples: `app/enrichment/models.py`
- Pattern: frozen dataclass; Either monad pattern (return EnrichmentResult | EnrichmentError)

**Provider Protocol:**
- Purpose: Pluggable adapter interface via structural typing
- Examples: `app/enrichment/provider.py`, `app/enrichment/adapters/virustotal.py`, etc.
- Pattern: @runtime_checkable Protocol with lookup(ioc) → EnrichmentResult | EnrichmentError

**ProviderRegistry:**
- Purpose: Central registry with configuration-aware queries
- Examples: `app/enrichment/registry.py`
- Pattern: Dict-based registry with filter methods (all(), configured(), providers_for_type())

**EnrichmentOrchestrator:**
- Purpose: Parallel enrichment dispatcher with rate-limit management
- Examples: `app/enrichment/orchestrator.py`
- Pattern: ThreadPoolExecutor + per-provider Semaphores + job status tracking (OrderedDict with LRU eviction)

**CacheStore:**
- Purpose: Persistent enrichment result cache with TTL
- Examples: `app/cache/store.py`
- Pattern: SQLite wrapper with thread-safe Lock + WAL mode + PRAGMA optimizations

## Entry Points

**Web Server:**
- Location: `app/__init__.py` create_app()
- Triggers: Flask application factory (called from a WSGI server or test runner)
- Responsibilities: Security scaffold (CSP, CSRF, rate limiting), singleton setup (registry, cache, history), blueprint registration

**Analysis Route:**
- Location: `app/routes/analysis.py` /analyze
- Triggers: Form submission from index.html
- Responsibilities: Pipeline execution, orchestrator setup (online mode), result rendering

**API Analyze Endpoint:**
- Location: `app/routes/api.py` POST /api/analyze
- Triggers: JSON POST from frontend or programmatic client
- Responsibilities: Validate JSON, run pipeline, optional orchestrator setup, return structured JSON

**Enrichment Status Endpoint:**
- Location: `app/routes/enrichment.py` /api/status/<job_id>
- Triggers: Frontend polling loop (enrichment.ts)
- Responsibilities: Retrieve job status from orchestrator, serialize results, return cursor-based response

**Frontend Initialization:**
- Location: `app/static/src/ts/main.ts`
- Triggers: DOMContentLoaded event
- Responsibilities: Initialize all feature modules in order (form, clipboard, cards, filter, enrichment, history, settings, ui, graph)

## Error Handling

**Strategy:** Comprehensive error handling at each layer — explicit exception catching with logging, user-friendly messages in UI.

**Patterns:**

- **Pipeline errors** (extractor): Catch TypeError/ValueError/AttributeError per extraction method, log warning, continue (silent discard of malformed candidates)
- **Provider errors** (adapter): Catch requests.exceptions, return EnrichmentError dataclass (never raise)
- **Rate-limit errors** (orchestrator): Catch 429 status, exponential backoff with jitter, retry up to 2 extra times
- **Route errors** (Flask): Try/except with logging; return user-friendly error messages
- **Database errors** (cache/history): Catch sqlite3.Error, log warning, allow graceful degradation (enrichment proceeds without cache)

## Cross-Cutting Concerns

**Logging:** Standard Python logging module (app-scoped loggers via `logging.getLogger(__name__)`) — errors logged with exc_info=True for full tracebacks.

**Validation:** 
- Input validation at system boundaries (Flask routes check form/JSON fields)
- Type checking via frozen dataclasses (IOC, EnrichmentResult, etc.)
- Provider configuration validation in ProviderRegistry (is_configured() method)

**Authentication:** 
- Provider API keys via ConfigStore (read from INI file)
- Per-provider key validation in adapter is_configured() method
- Session integrity via SECRET_KEY + CSRF tokens

**Rate Limiting:**
- Per-route limits via Flask-Limiter (`@limiter.limit("X per minute")`)
- Per-provider concurrency via Semaphores in EnrichmentOrchestrator
- Exponential backoff with jitter for 429 responses

**Security:**
- OWASP CSRF via Flask-WTF CSRFProtect (all POST endpoints except /api/)
- Content Security Policy (default-src 'self') via after_request hook
- Input size cap (MAX_CONTENT_LENGTH 512 KB)
- SSRF prevention via ALLOWED_API_HOSTS allowlist
- XSS prevention via Jinja2 autoescaping + createElement (no innerHTML)
- Debug mode hardcoded to False (SEC-15)

---

*Architecture analysis: 2026-04-06*
