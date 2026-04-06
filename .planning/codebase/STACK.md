# Technology Stack

**Analysis Date:** 2026-04-06

## Languages

**Primary:**
- Python 3.10+ - Backend application logic, threat intelligence adapters, API orchestration
- TypeScript 5.8+ - Frontend application logic, DOM manipulation, module initialization

**Secondary:**
- HTML5 - Templates (Jinja2), security-hardened with autoescaping
- CSS3 - Tailwind CSS for styling via standalone CLI

## Runtime

**Environment:**
- CPython 3.10+ (standard Python runtime)
- Node.js (TypeScript/JavaScript tooling only — no Node.js in production)
- Standalone CLI tools for build (no npm dependencies in production code)

**Package Manager:**
- pip - Python dependency management
- Lockfile: `requirements.txt` pinned versions, no external lockfile format needed

## Frameworks

**Core:**
- Flask 3.1.1 - Web framework, HTTP routing, template rendering (Jinja2), application factory pattern
- Flask-WTF 1.2.2 - CSRF protection via form tokens (SEC-10)
- Flask-Limiter 4.1.1 - Rate limiting with in-memory storage (SEC-21)

**Testing:**
- pytest - Python unit and integration test runner (configured in `pyproject.toml`)
- Vitest 3.1.0 - TypeScript/JavaScript test runner with coverage
- jsdom 26.1.0 - DOM simulation for browser-free JavaScript testing

**Build/Dev:**
- esbuild 0.27.3 - TypeScript bundler (IIFE output, no external source maps in production)
- Tailwind CSS 3.4.17 - Standalone CLI (v3.4.17) for CSS generation
- TypeScript 6.0.2 - Type checking (via `npx tsc --noEmit`, no emit)
- Ruff 0.x - Python linting and formatting (configured in `pyproject.toml`)

## Key Dependencies

**Critical:**
- requests 2.32.5 - HTTP client for all outbound API calls to threat intelligence providers (central security point)
- iocextract 1.16.1 - IOC extraction from raw text input (IP, domain, URL, hash parsing)
- iocsearcher 2.7.2 - IOC type detection and classification

**Infrastructure:**
- python-dotenv 1.1.0 - Load `.env` files for development (never in production, file in .gitignore)
- dnspython 2.8.0 - DNS resolution for zero-auth DNS Records provider adapter
- python-whois 0.9.6 - WHOIS lookup for domain registration data (zero-auth provider)

## Configuration

**Environment:**
- Reads from environment variables via `python-dotenv` for development
- `.env` file present (in .gitignore) for local API keys during development
- `.env.example` documents required variables
- Config validation at startup (see `app/config.py`)

**Build:**
- `Makefile` orchestrates build (CSS + JS)
- `tsconfig.json` - TypeScript compiler options (target es2022, strict mode)
- `tsconfig.test.json` - Extends base tsconfig with vitest globals for test files
- `pyproject.toml` - Python project metadata, Ruff linting rules, pytest markers

**Storage Configuration:**
- SQLite database at `~/.sentinelx/cache.db` (user home directory, outside repo)
- INI config file at `~/.sentinelx/config.ini` (persists API keys with 0o600 permissions)
- Both created on-demand with directory creation (mode 0o700)

## Platform Requirements

**Development:**
- Python 3.10+ with pip
- Node.js (for esbuild/TypeScript tooling)
- Standalone binaries downloaded by Makefile: Tailwind CLI, esbuild
- Linux x64 platform target (configured in Makefile: `PLATFORM := linux-x64`)

**Production:**
- Python 3.10+ runtime (Flask WSGI app)
- localhost binding only (`127.0.0.1:5000`) — not network-exposed by default
- SQLite (embedded, no external database required)
- INI-format config file for API keys (read-only after initial setup)
- No external dependencies beyond `requirements.txt` packages

---

*Stack analysis: 2026-04-06*
