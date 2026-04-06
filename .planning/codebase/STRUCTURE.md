# Codebase Structure

**Analysis Date:** 2026-04-06

## Directory Layout

```
sentinelx/
├── app/                           # Flask application code
│   ├── __init__.py                # Application factory (create_app)
│   ├── config.py                  # Configuration + environment validation
│   ├── routes/                    # HTTP route handlers
│   │   ├── __init__.py            # Blueprint registration
│   │   ├── analysis.py            # POST /analyze, GET /
│   │   ├── api.py                 # POST /api/analyze, GET /api/status/<job_id>
│   │   ├── detail.py              # GET /ioc/<type>/<value>
│   │   ├── enrichment.py          # GET /enrichment_status/<job_id>
│   │   ├── history.py             # GET /history, POST /history/delete
│   │   ├── settings.py            # GET /settings, POST /settings
│   │   └── _helpers.py            # Shared orchestrator setup + serializers
│   ├── pipeline/                  # IOC extraction pipeline (offline, pure)
│   │   ├── __init__.py            # Package marker
│   │   ├── models.py              # IOC, IOCType dataclasses
│   │   ├── extractor.py           # Entry: extract_iocs(), run_pipeline()
│   │   ├── normalizer.py          # Canonicalize strings
│   │   └── classifier.py          # Type detection via regex precedence
│   ├── enrichment/                # Threat intelligence provider layer
│   │   ├── __init__.py            # Package marker
│   │   ├── provider.py            # Provider Protocol definition
│   │   ├── registry.py            # ProviderRegistry — central registry
│   │   ├── setup.py               # build_registry() factory + PROVIDER_INFO
│   │   ├── orchestrator.py        # EnrichmentOrchestrator — parallel dispatch
│   │   ├── models.py              # EnrichmentResult, EnrichmentError dataclasses
│   │   ├── config_store.py        # ConfigStore — INI-based settings at ~/.sentinelx/config.ini
│   │   ├── history_store.py       # HistoryStore — session storage at ~/.sentinelx/history.db
│   │   ├── http_safety.py         # SSRF prevention (allowed_hosts validation)
│   │   └── adapters/              # 14 provider adapter implementations
│   │       ├── virustotal.py      # VirusTotal adapter
│   │       ├── malwarebazaar.py   # MalwareBazaar adapter
│   │       ├── threatfox.py       # ThreatFox adapter
│   │       ├── shodan.py          # Shodan InternetDB adapter (zero-auth)
│   │       ├── urlhaus.py         # URLhaus adapter
│   │       ├── otx.py             # OTX AlienVault adapter
│   │       ├── greynoise.py       # GreyNoise Community adapter
│   │       ├── abuseipdb.py       # AbuseIPDB adapter
│   │       ├── hashlookup.py      # CIRCL Hashlookup adapter (zero-auth)
│   │       ├── ip_api.py          # ipinfo.io adapter (zero-auth)
│   │       ├── dns_lookup.py      # DNS Records adapter (zero-auth)
│   │       ├── crtsh.py           # crt.sh adapter (zero-auth)
│   │       ├── threatminer.py     # ThreatMiner adapter (zero-auth)
│   │       ├── asn_cymru.py       # Team Cymru ASN adapter (zero-auth)
│   │       └── whois_lookup.py    # WHOIS adapter (zero-auth)
│   ├── cache/                     # Enrichment result cache
│   │   ├── __init__.py            # Package marker
│   │   └── store.py               # CacheStore — SQLite at ~/.sentinelx/cache.db
│   ├── templates/                 # Jinja2 HTML templates
│   │   ├── base.html              # Base layout (header, nav, footer)
│   │   ├── index.html             # Home page (paste form)
│   │   ├── results.html           # Analysis results page (grouped IOC cards)
│   │   ├── ioc_detail.html        # IOC detail page (tabbed provider results)
│   │   ├── history.html           # Analysis history page
│   │   └── settings.html          # Settings page (API key configuration)
│   └── static/                    # Frontend assets
│       ├── src/                   # TypeScript source
│       │   └── ts/                # TypeScript modules
│       │       ├── main.ts        # Entry point — initializes all modules
│       │       ├── types/
│       │       │   ├── api.ts     # API response types (EnrichmentItem, EnrichmentStatus)
│       │       │   └── ioc.ts     # IOC type definitions
│       │       ├── utils/
│       │       │   └── dom.ts     # DOM utilities (attr, findElements)
│       │       └── modules/       # Feature modules
│       │           ├── enrichment.ts      # Polling loop + progress tracking (928 LOC)
│       │           ├── row-factory.ts     # DOM row constructors for results display
│       │           ├── verdict-compute.ts # Verdict aggregation logic
│       │           ├── cards.ts           # IOC card UI
│       │           ├── filter.ts          # Result filtering
│       │           ├── history.ts         # History page interactions
│       │           ├── settings.ts        # Settings page interactions
│       │           ├── clipboard.ts       # Copy-to-clipboard functionality
│       │           ├── form.ts            # Form submission handling
│       │           ├── export.ts          # Result export (CSV, JSON)
│       │           ├── graph.ts           # Relationship graph visualization
│       │           ├── shared-rendering.ts # Shared DOM rendering utilities
│       │           └── ui.ts              # Generic UI interactions
│       ├── css/                   # Tailwind CSS (compiled)
│       │   └── output.css         # Compiled Tailwind styles
│       ├── fonts/                 # Font files
│       └── dist/                  # Compiled JavaScript (esbuild output, gitignored)
│
├── tests/                         # Test suite (757+ tests)
│   ├── conftest.py                # Pytest fixtures (Flask app, test db, config)
│   ├── helpers.py                 # Test helper functions
│   ├── test_pipeline.py           # Pipeline extraction tests
│   ├── test_classifier.py         # IOC classification tests
│   ├── test_normalizer.py         # Normalization tests
│   ├── test_extractor.py          # Extractor integration tests
│   ├── test_*.py                  # Provider adapter tests (virustotal, malwarebazaar, etc.)
│   ├── test_provider_registry.py  # Registry tests
│   ├── test_orchestrator.py       # Orchestrator concurrency + retry tests
│   ├── test_api.py                # API endpoint tests
│   ├── test_cache_store.py        # Cache store tests
│   ├── test_history_store.py      # History store tests
│   ├── test_config_store.py       # Config store tests
│   ├── test_security_audit.py     # Security checks
│   ├── test_adapter_contract.py   # Provider protocol compliance tests
│   ├── test_history_routes.py     # History route tests
│   ├── test_ioc_detail_routes.py  # Detail page route tests
│   ├── e2e/                       # Playwright end-to-end tests (91 tests)
│   │   ├── conftest.py            # E2E fixtures (browser, base URL)
│   │   ├── pages/
│   │   │   ├── index_page.py      # Home page object
│   │   │   ├── results_page.py    # Results page object (20+ selectors)
│   │   │   └── settings_page.py   # Settings page object
│   │   ├── test_homepage.py       # Home page interactions
│   │   ├── test_results_page.py   # Results rendering + interactions
│   │   ├── test_extraction.py     # IOC extraction E2E
│   │   ├── test_url_e2e.py        # URL enrichment E2E
│   │   ├── test_navigation.py     # Page navigation E2E
│   │   ├── test_settings.py       # Settings E2E
│   │   ├── test_ui_controls.py    # UI interaction E2E
│   │   └── test_copy_buttons.py   # Copy button functionality E2E
│
├── Makefile                       # Build automation
│   # Key targets: make build, make js, make css, make typecheck, make test, make test-e2e
│
├── pyproject.toml                 # Python project config (pytest, black, mypy, etc.)
├── tsconfig.json                  # TypeScript configuration
├── esbuild.config.js              # esbuild configuration (IIFE output)
├── Dockerfile                     # Container image definition
├── .gitignore                     # Git ignore rules
├── README.md                      # Project overview
│
├── .planning/                     # Planning documents (generated by GSD)
│   ├── PROJECT.md                 # Master project doc
│   ├── MILESTONES.md              # Shipped milestone history
│   ├── ROADMAP.md                 # v1.1 phase breakdown
│   └── codebase/                  # Codebase analysis (this directory)
│       ├── ARCHITECTURE.md        # Layers, patterns, data flow
│       ├── STRUCTURE.md           # File organization, naming conventions
│       ├── CONVENTIONS.md         # Code style, naming patterns
│       ├── TESTING.md             # Test framework, patterns
│       ├── STACK.md               # Technology stack
│       ├── INTEGRATIONS.md        # External services
│       └── CONCERNS.md            # Technical debt, known issues
│
└── docs/                          # Reference documentation
    ├── plans/                     # Detailed phase/feature implementation plans
    ├── SECURITY.md                # Security design notes
    └── API.md                     # API endpoint documentation
```

## Directory Purposes

**app/:** Flask application code. All request handling, provider registry, enrichment orchestration, and data persistence logic.

**app/routes/:** HTTP request handlers organized by feature. Each module attaches @bp.route() decorators to a shared Blueprint. Routes are grouped by concern: analysis (extraction), api (JSON endpoints), detail (IOC detail pages), enrichment (polling), history (session management), settings (configuration).

**app/pipeline/:** Pure offline IOC extraction. No Flask imports, no network calls, no state. Entry point is run_pipeline() which chains extraction → normalization → classification → deduplication.

**app/enrichment/:** Provider protocol definition, registry, orchestration, and adapter implementations. All 14 provider adapters inherit this directory structure. Registry is the single source of truth for available providers. Orchestrator dispatches parallel lookups with per-provider rate limiting.

**app/enrichment/adapters/:** One file per provider. Each adapter implements the Provider protocol (lookup(), is_configured(), supported_types, requires_api_key). To add a provider: create adapters/new_provider.py, then add one register() call in setup.py.

**app/cache/:** Persistent SQLite cache for enrichment results. Single CacheStore instance lives at app.cache_store. Key: (ioc_value, ioc_type, provider); value: JSON-serialized enrichment result with TTL.

**app/templates/:** Jinja2 HTML templates. Each template corresponds to a route. Templates import CSS from static/css/ and JS from static/dist/. Security: Jinja2 autoescaping enabled by default; no unsafe filters used.

**app/static/src/ts/:** TypeScript source (pre-build). Compiled via esbuild to IIFE in static/dist/main.js. Organized by feature: modules/ for business logic (enrichment, filtering, export), types/ for API/IOC types, utils/ for DOM helpers.

**tests/:** Pytest-based unit and integration tests (757+). Tests follow file-per-module pattern: test_classifier.py tests classifier.py, test_virustotal.py tests adapters/virustotal.py. Fixtures in conftest.py provide Flask app, test database, mock config.

**tests/e2e/:** Playwright end-to-end tests (91 tests). Page object models (pages/) separate test logic from selectors. Tests exercise full user flows: extraction, enrichment polling, filtering, export.

## Key File Locations

**Entry Points:**
- `app/__init__.py` create_app() — Flask application factory
- `app/routes/__init__.py` — Blueprint registration
- `app/routes/analysis.py` — POST /analyze (main enrichment entry point)
- `app/routes/api.py` — POST /api/analyze (JSON API)
- `app/static/src/ts/main.ts` — Frontend initialization (DOMContentLoaded)

**Configuration:**
- `app/config.py` — Flask Config class + env var reading
- `app/enrichment/config_store.py` — Provider API keys (INI file at ~/.sentinelx/config.ini)
- `pyproject.toml` — Python project config, dependencies, test settings

**Core Logic:**
- `app/pipeline/extractor.py` — run_pipeline() entry point for IOC extraction
- `app/pipeline/classifier.py` — Type detection via regex precedence
- `app/enrichment/registry.py` — Provider registry + lookup queries
- `app/enrichment/orchestrator.py` — Parallel enrichment with rate limiting
- `app/enrichment/setup.py` — Registry initialization (14 providers)
- `app/enrichment/adapters/virustotal.py` — Example provider adapter

**Testing:**
- `tests/conftest.py` — Pytest fixtures (Flask app, test config)
- `tests/test_classifier.py` — Pipeline classification tests
- `tests/test_orchestrator.py` — Concurrency + retry logic tests
- `tests/e2e/conftest.py` — Playwright fixtures
- `tests/e2e/pages/results_page.py` — Results page object (hard-coded selectors)

## Naming Conventions

**Files:**
- `models.py` — frozen dataclasses (IOC, EnrichmentResult, etc.)
- `store.py` — persistence layer (CacheStore, HistoryStore)
- `routes.py` or `{feature}.py` — HTTP handlers
- `adapters/{provider}.py` — Provider implementations (lowercase name matching config key)
- `test_{module}.py` — Test file for module.py

**Directories:**
- `modules/` — Named per feature (enrichment, cards, filter)
- `types/` — TypeScript type definitions
- `adapters/` — Provider adapter implementations
- `e2e/` — End-to-end tests + page objects

**Classes:**
- `{Service}` — Service classes (CacheStore, HistoryStore, ConfigStore)
- `{Adapter}` — Provider adapters (VTAdapter, MBAdapter)
- `{Type}` — Data models (IOC, EnrichmentResult, EnrichmentError)
- camelCase — Functions (run_pipeline, classify, group_by_type)

**Functions:**
- camelCase for all Python/TypeScript functions
- `_private_function` for internal module functions
- `init()` for module initialization (frontend modules)

## Where to Add New Code

**New Threat Intelligence Provider:**
1. Create `app/enrichment/adapters/{provider_name}.py` implementing Provider protocol
2. Add one register() call in `app/enrichment/setup.py` build_registry()
3. Add entry to PROVIDER_INFO in setup.py if requires_api_key=True
4. Add test file `tests/test_{provider_name}.py`
5. Update app/config.py ALLOWED_API_HOSTS if new domain

**New IOC Type:**
1. Add enum value to IOCType in `app/pipeline/models.py`
2. Add classification logic in `app/pipeline/classifier.py` (update precedence if needed)
3. Add test cases in `tests/test_classifier.py`
4. Update adapter supported_types as needed

**New Feature (UI interaction):**
1. Create `app/static/src/ts/modules/{feature}.ts` with init() export
2. Import + call init() in `app/static/src/ts/main.ts`
3. Add type definitions to `app/static/src/ts/types/` as needed
4. Create test file `tests/e2e/test_{feature}.py` with page object if needed

**New Route/Endpoint:**
1. Create `app/routes/{feature}.py` with @bp.route() decorators
2. Import routes in `app/routes/__init__.py`
3. Add template in `app/templates/{feature}.html` if HTML response
4. Add test file `tests/test_{feature}_routes.py`
5. Update API documentation in docs/API.md

**Database Schema Change:**
1. For cache: modify _CREATE_TABLE in `app/cache/store.py`, add migration logic
2. For history: modify schema in `app/enrichment/history_store.py`
3. Add test case to verify schema + migration

**Shared Utilities:**
- Helper functions for DOM manipulation → `app/static/src/ts/utils/dom.ts`
- Shared rendering logic → `app/static/src/ts/modules/shared-rendering.ts`
- Python utilities → New file in appropriate layer (pipeline/, enrichment/, cache/)

## Special Directories

**app/static/dist/:** Generated — esbuild output. Contains compiled main.js + source maps. Gitignored. Rebuild with `make js`.

**~/.sentinelx/:** Runtime — User config + data directory. Contains:
- config.ini — Provider API keys (user-created via /settings page)
- cache.db — SQLite enrichment cache
- history.db — SQLite analysis history
- Not committed to git (user-specific secrets)

**tests/e2e/pages/:** Page object models for Playwright tests. Each page encapsulates selectors (data-* attributes) and interactions. Used to centralize CSS selector maintenance.

---

*Structure analysis: 2026-04-06*
