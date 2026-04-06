# External Integrations

**Analysis Date:** 2026-04-06

## APIs & External Services

**Threat Intelligence Providers (14 total):**

1. **VirusTotal**
   - What: IP, domain, URL, hash enrichment — primary multi-purpose provider
   - SDK/Client: requests 2.32.5 (HTTP)
   - Auth: API key via `app/config.py` ConfigStore → `[virustotal]` INI section
   - Endpoint: `https://www.virustotal.com/api/v3` (allowlisted in SEC-16)
   - Adapter: `app/enrichment/adapters/virustotal.py`

2. **MalwareBazaar** (abuse.ch)
   - What: Hash-only malware sample database
   - SDK/Client: requests 2.32.5
   - Auth: API key via ConfigStore → `[providers]` section, key: `malwarebazaar`
   - Endpoint: `https://mb-api.abuse.ch`
   - Adapter: `app/enrichment/adapters/malwarebazaar.py`

3. **ThreatFox** (abuse.ch)
   - What: IP, domain, URL, hash — IOC sharing platform
   - SDK/Client: requests 2.32.5
   - Auth: API key via ConfigStore → `[providers]` section, key: `threatfox`
   - Endpoint: `https://threatfox-api.abuse.ch`
   - Adapter: `app/enrichment/adapters/threatfox.py`

4. **URLhaus** (abuse.ch)
   - What: URL, hash, IP, domain — malware distribution tracking
   - SDK/Client: requests 2.32.5
   - Auth: API key via ConfigStore → `[providers]` section, key: `urlhaus`
   - Endpoint: `https://urlhaus-api.abuse.ch`
   - Adapter: `app/enrichment/adapters/urlhaus.py`

5. **OTX AlienVault**
   - What: All IOC types including CVE — community threat intelligence
   - SDK/Client: requests 2.32.5
   - Auth: API key via ConfigStore → `[providers]` section, key: `otx`
   - Endpoint: `https://otx.alienvault.com`
   - Adapter: `app/enrichment/adapters/otx.py`

6. **GreyNoise Community**
   - What: IP-only internet scanner noise classification
   - SDK/Client: requests 2.32.5
   - Auth: API key via ConfigStore → `[providers]` section, key: `greynoise`
   - Endpoint: `https://api.greynoise.io/v3/community`
   - Adapter: `app/enrichment/adapters/greynoise.py`

7. **AbuseIPDB**
   - What: IP-only crowd-sourced abuse reporting
   - SDK/Client: requests 2.32.5
   - Auth: API key via ConfigStore → `[providers]` section, key: `abuseipdb`
   - Endpoint: `https://api.abuseipdb.com`
   - Adapter: `app/enrichment/adapters/abuseipdb.py`

8. **Shodan InternetDB** (zero-auth)
   - What: IP service enumeration, open port discovery
   - SDK/Client: requests 2.32.5
   - Auth: None (free tier, no API key required)
   - Endpoint: `https://internetdb.shodan.io`
   - Adapter: `app/enrichment/adapters/shodan.py`

9. **CIRCL Hashlookup** (zero-auth)
   - What: Hash lookup against NSRL known-good database
   - SDK/Client: requests 2.32.5
   - Auth: None (open API)
   - Endpoint: `https://hashlookup.circl.lu`
   - Adapter: `app/enrichment/adapters/hashlookup.py`

10. **IP Context / ipinfo.io** (zero-auth)
    - What: GeoIP, rDNS, and IP metadata
    - SDK/Client: requests 2.32.5
    - Auth: None (basic free tier)
    - Endpoint: `https://ipinfo.io`
    - Adapter: `app/enrichment/adapters/ip_api.py`

11. **DNS Records** (zero-auth)
    - What: Live DNS resolution and record lookup
    - SDK/Client: dnspython 2.8.0
    - Auth: None (system resolver)
    - Adapter: `app/enrichment/adapters/dns_lookup.py`

12. **Certificate Transparency / crt.sh** (zero-auth)
    - What: Historical certificate issuance and domain enumeration
    - SDK/Client: requests 2.32.5
    - Auth: None (public transparency logs)
    - Endpoint: `https://crt.sh`
    - Adapter: `app/enrichment/adapters/crtsh.py`

13. **ThreatMiner** (zero-auth)
    - What: Passive DNS, URL/sample relationships
    - SDK/Client: requests 2.32.5
    - Auth: None (free API)
    - Endpoint: `https://api.threatminer.org`
    - Adapter: `app/enrichment/adapters/threatminer.py`

14. **ASN Intel / Team Cymru** (zero-auth)
    - What: ASN, BGP, network context via DNS mapping
    - SDK/Client: dnspython 2.8.0
    - Auth: None (DNS-based lookups)
    - Adapter: `app/enrichment/adapters/asn_cymru.py`

15. **WHOIS Lookup** (zero-auth)
    - What: Domain registration data and contact info
    - SDK/Client: python-whois 0.9.6
    - Auth: None (public WHOIS)
    - Adapter: `app/enrichment/adapters/whois_lookup.py`

## Data Storage

**Databases:**
- SQLite 3.x (embedded)
  - Connection: `~/.sentinelx/cache.db` (user home directory)
  - Client: sqlite3 (Python stdlib)
  - Purpose: Enrichment result caching with TTL, thread-safe via WAL journal mode
  - Schema: Single table `enrichment_cache` (ioc_value, ioc_type, provider, result_json, cached_at)
  - Configuration: WAL mode, PRAGMA tuning for concurrency (see `app/cache/store.py`)

**File Storage:**
- Local filesystem only
  - `.sentinelx/` directory in user home (created with 0o700 permissions)
  - `config.ini` - API key configuration (0o600 permissions, owner-only read)
  - `cache.db` - SQLite enrichment cache
  - No cloud storage or external blob services

**Caching:**
- SQLite-backed with application-level TTL (configurable, default 24 hours)
- No Redis, Memcached, or external cache layers
- In-memory Flask-Limiter for rate limiting (non-persistent, single-process only)

## Authentication & Identity

**Auth Provider:**
- Custom (application-level API key storage)
  - No OAuth, OpenID, SAML, or third-party identity providers
  - API keys for each threat intelligence provider stored in `~/.sentinelx/config.ini`
  - Settings page allows analysts to configure keys without environment variables (user-facing security preference)
  - ConfigStore class handles read/write with file permissions (SEC-17)

**Session Management:**
- Flask session cookies (CSRF-protected)
- SECRET_KEY auto-generated if not in environment (warning logged)
- SameSite=Lax for CSRF defense-in-depth (SEC-19)

## Monitoring & Observability

**Error Tracking:**
- None detected (no Sentry, DataDog, or external error tracking)
- Logging via Python stdlib `logging` module to console/stderr

**Logs:**
- Python `logging` module with per-module loggers
- Logged to stdout/stderr (no file-based or external aggregation)
- Request/response errors logged at adapter level

## CI/CD & Deployment

**Hosting:**
- Local development: Flask development server (`127.0.0.1:5000`)
- Production: WSGI-compatible application (run.py entry point)
- No containerization (Docker/Kubernetes) detected
- No cloud platform integration (AWS, GCP, Azure)

**CI Pipeline:**
- None detected (no GitHub Actions, GitLab CI, Jenkins, or CircleCI configuration)
- Manual testing and deployment

## Environment Configuration

**Required env vars:**
- `SECRET_KEY` - Flask session/CSRF key (auto-generated if not set, production should set explicitly)
- Provider API keys can be set via `.env` during development (see `.env.example`)

**Secrets location:**
- `.env` file (in .gitignore, never committed) for development convenience
- `~/.sentinelx/config.ini` for persistent per-user configuration
- All secrets written with 0o600 (owner-only) file permissions (SEC-17)

**SSRF Allowlist:**
- All outbound API calls validated against `ALLOWED_API_HOSTS` in `app/config.py` (SEC-16)
- Prevents unauthorized outbound requests to internal/private networks
- Validation enforced in `app/enrichment/http_safety.py::validate_endpoint()`

## Request/Response Security

**HTTP Settings:**
- Timeout: (5 second connect, 30 second read) on all requests (SEC-04)
- Streaming responses with 1 MB byte cap to prevent memory exhaustion (SEC-05)
- Content-Length validation before processing

**Headers:**
- Content Security Policy: self-only for all resource types (SEC-09)
- X-Content-Type-Options: nosniff
- X-Frame-Options: SAMEORIGIN
- Referrer-Policy: no-referrer
- Permissions-Policy: camera, microphone, geolocation, payment disabled

## Webhooks & Callbacks

**Incoming:**
- None detected (stateless analyst query processing, no event subscriptions)

**Outgoing:**
- None detected (read-only enrichment, no callback or notification webhooks to external services)

---

*Integration audit: 2026-04-06*
