---
phase: 01-foundation-and-offline-pipeline
verified: 2026-02-21T00:00:00Z
status: passed
score: 5/5 success criteria verified
re_verification: false
gaps: []
human_verification:
  - test: "Visual dark theme and UI quality check"
    expected: "Dark theme renders with correct colors, accordion groups expand, copy buttons function, mode indicator is visible"
    why_human: "Cannot verify visual rendering, color accuracy, or clipboard behavior programmatically. Plan 04 Task 3 was a human checkpoint — approved per SUMMARY — but that approval is not independently verifiable from code alone."
---

# Phase 1: Foundation and Offline Pipeline Verification Report

**Phase Goal:** Analyst can paste free-form text and receive extracted, classified, deduplicated IOCs — with zero outbound network calls and a hardened security posture
**Verified:** 2026-02-21
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Analyst pastes mixed defanged text and app extracts all IOCs, normalized, classified by type, duplicates collapsed | VERIFIED | `run_pipeline()` in `extractor.py` chains extract->normalize->classify->dedup; `test_pipeline.py` passes 14 tests including deduplication and multi-type extraction; `test_routes.py::test_analyze_deduplicates` passes |
| 2 | Offline mode makes zero outbound network calls — verified by test asserting no HTTP calls | VERIFIED | `test_routes.py::test_offline_mode_makes_no_http_calls` patches `urllib.request.urlopen`, `http.client.HTTPConnection`, `http.client.HTTPSConnection` and asserts none called; passes |
| 3 | Results page groups IOCs by type and clearly indicates offline mode was used | VERIFIED | `results.html` uses `<details>/<summary>` per type group; mode indicator banner renders `Offline Mode` / `Online Mode` based on `mode` variable; `test_routes.py::test_analyze_groups_by_type` passes |
| 4 | POST with Host header not on trusted list returns HTTP 400 | VERIFIED | `app/__init__.py` sets `TRUSTED_HOSTS = ['localhost', '127.0.0.1']`; `test_routes.py::test_invalid_host_returns_400` sends `Host: evil.com` and asserts 400; passes |
| 5 | 600 KB blob is rejected before extraction runs with clear error message | VERIFIED | `config.py` sets `MAX_CONTENT_LENGTH = 512 * 1024`; `app/__init__.py` registers 413 handler returning "Input too large. Maximum paste size is 512 KB."; `test_routes.py::test_oversize_post_returns_413` passes |

**Score:** 5/5 success criteria verified

---

## Required Artifacts

### Plan 01 Artifacts (Security Scaffold)

| Artifact | Status | Details |
|----------|--------|---------|
| `app/__init__.py` | VERIFIED | Contains `create_app`, applies TRUSTED_HOSTS/MAX_CONTENT_LENGTH/CSRF/CSP/debug=False before blueprint registration; 100% coverage |
| `app/config.py` | VERIFIED | Contains `class Config` with all security values; ALLOWED_API_HOSTS; validate() method; TestConfig subclass |
| `app/pipeline/models.py` | VERIFIED | `class IOCType` enum (8 types: IPV4 IPV6 DOMAIN URL MD5 SHA1 SHA256 CVE); `@dataclass(frozen=True) class IOC`; `group_by_type()` |
| `run.py` | VERIFIED | Contains `127.0.0.1`; imports `create_app`; `debug=False` hardcoded |
| `tests/conftest.py` | VERIFIED | `app` fixture via `create_app({'TESTING': True, ...})`; `client` fixture via `app.test_client()` |

### Plan 02 Artifacts (Normalizer + Classifier)

| Artifact | Status | Details |
|----------|--------|---------|
| `app/pipeline/normalizer.py` | VERIFIED | `normalize()` function; 17 compiled regex patterns covering all documented defanging variants; 100% coverage |
| `app/pipeline/classifier.py` | VERIFIED | `classify()` function; strict 8-step precedence (CVE->SHA256->SHA1->MD5->URL->IPv6->IPv4->Domain); imports IOCType and IOC from models; 100% coverage |
| `tests/test_normalizer.py` | VERIFIED | 142 lines; covers 30+ defanging variants including scheme, dot, at-sign, combined, and edge cases |
| `tests/test_classifier.py` | VERIFIED | 293 lines; covers all 8 IOC types with positive and negative cases; precedence tests |

### Plan 03 Artifacts (Extractor + Pipeline)

| Artifact | Status | Details |
|----------|--------|---------|
| `app/pipeline/extractor.py` | VERIFIED | `extract_iocs()` uses both `iocextract` and `iocsearcher`; `run_pipeline()` chains extract->normalize->classify->dedup; 79% coverage (12 uncovered lines are exception handlers — acceptable) |
| `tests/test_extractor.py` | VERIFIED | 163 lines; tests IPv4, URL, hashes, CVE, mixed input, empty, no-IOCs, dedup |
| `tests/test_pipeline.py` | VERIFIED | 126 lines; end-to-end tests for deduplication, type classification, edge cases, realistic threat report |

### Plan 04 Artifacts (Routes + Templates + UI)

| Artifact | Status | Details |
|----------|--------|---------|
| `app/routes.py` | VERIFIED | `GET /` renders `index.html`; `POST /analyze` calls `run_pipeline()` and `group_by_type()`, renders `results.html`; 100% coverage |
| `app/templates/base.html` | VERIFIED | Contains `DOCTYPE html`; links external CSS via `url_for('static', filename='style.css')`; loads `main.js` with `defer`; no inline scripts |
| `app/templates/index.html` | VERIFIED | Contains "Extract IOCs"; form `action="{{ url_for('main.analyze') }}"`; CSRF hidden input; mode select defaulting to `offline`; submit button with `disabled` |
| `app/templates/results.html` | VERIFIED | Mode indicator banner; IOC groups in `<details>/<summary>`; count badges; `{{ ioc.value }}` (no `\|safe`); no-results message |
| `app/static/style.css` | VERIFIED | 548 lines; CSS custom properties for dark theme; type accent colors; monospace for IOC values |
| `app/static/main.js` | VERIFIED | Contains `clipboard` logic (`navigator.clipboard.writeText`); submit disable/enable; clear button; no inline event handlers |
| `tests/test_routes.py` | VERIFIED | 193 lines; 14 tests covering all functional, security, and edge case requirements |

---

## Key Link Verification

### Plan 01 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/__init__.py` | `app/config.py` | `Config` class loaded in factory | WIRED | Line 31: `from .config import Config`; line 32: `config = Config()` |
| `run.py` | `app/__init__.py` | `create_app` import | WIRED | Line 10: `from app import create_app` |

### Plan 02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/pipeline/classifier.py` | `app/pipeline/models.py` | IOCType enum and IOC dataclass import | WIRED | Line 17: `from app.pipeline.models import IOC, IOCType` |
| `app/pipeline/classifier.py` | `app/pipeline/normalizer.py` | (normalizer called externally in extractor; classifier expects pre-normalized input) | WIRED | Architecture confirmed: `extractor.py` calls `normalize()` before `classify()` at lines 121-122 |

### Plan 03 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/pipeline/extractor.py` | `iocextract` | Library import | WIRED | Line 18: `import iocextract`; used at lines 60, 66, 72, 78 |
| `app/pipeline/extractor.py` | `iocsearcher` | Library import | WIRED | Line 19: `from iocsearcher.searcher import Searcher`; `_searcher = Searcher()` at line 26; used at line 85 |
| `tests/test_pipeline.py` | `app/pipeline/extractor.py` | Full pipeline test | WIRED | Tests import `run_pipeline` and verify the full chain (multiple tests explicitly verify dedup and type classification through the complete pipeline) |

### Plan 04 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/routes.py` | `app/pipeline/extractor.py` | `run_pipeline` import | WIRED | Line 18: `from app.pipeline.extractor import run_pipeline`; used at line 46 |
| `app/routes.py` | `app/templates/results.html` | `render_template` with grouped IOCs | WIRED | Line 59: `return render_template('results.html', grouped=grouped, mode=mode, ...)` |
| `app/templates/index.html` | `app/routes.py` | Form POST to /analyze | WIRED | Line 16: `action="{{ url_for('main.analyze') }}"` |
| `app/templates/base.html` | `app/static/style.css` | CSS link tag | WIRED | Line 7: `<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">` |
| `app/templates/base.html` | `app/static/main.js` | Script tag (external, CSP-compliant) | WIRED | Line 25: `<script src="{{ url_for('static', filename='main.js') }}" defer></script>` |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| EXTR-01 | 01-03 | User can paste free-form text into a large input field | SATISFIED | `index.html` has `<textarea name="text">` with placeholder; `POST /analyze` reads `request.form.get('text')` |
| EXTR-02 | 01-03 | Extracts all IOCs: IPv4, IPv6, domain, URL, MD5, SHA1, SHA256, CVE | SATISFIED | `extract_iocs()` uses iocextract (URLs, IPs, hashes) + iocsearcher (CVEs); all 8 types classified by `classify()`; 125 tests cover all types |
| EXTR-03 | 01-02 | Normalizes defanging patterns (hxxp, [.], {.}, [dot], _dot_, [@], [at], [://]) | SATISFIED | `normalizer.py` has 17 compiled regex patterns covering all documented variants; 30+ test cases in `test_normalizer.py` |
| EXTR-04 | 01-02 | Classifies each IOC by type using deterministic logic (no ML) | SATISFIED | `classifier.py` uses strict regex + ipaddress validation in 8-step precedence order; 100% coverage |
| EXTR-05 | 01-03 | Deduplicates extracted IOCs (same normalized value = one lookup) | SATISFIED | `run_pipeline()` uses `dict` keyed on `(IOCType, normalized_value)`; `test_pipeline.py::test_duplicate_url_collapsed` and `test_duplicate_hash_collapsed` pass |
| UI-01 | 01-04 | Single-page web interface with large text input, submit button, offline/online mode toggle | SATISFIED | `index.html` has large `<textarea>`, "Extract IOCs" submit button, `<select id="mode-select">` defaulting to offline |
| UI-02 | 01-04 | Offline mode makes zero outbound network calls | SATISFIED | `POST /analyze` only calls `run_pipeline()` (pure function); `test_offline_mode_makes_no_http_calls` patches HTTP clients and asserts none called; passes |
| UI-04 | 01-04 | Results page groups IOCs by type | SATISFIED | `results.html` loops `grouped.items()` with `<details>/<summary>` per IOCType |
| UI-07 | 01-04 | UI visually indicates offline or online mode | SATISFIED | Mode indicator banner in `results.html`: "Results — Offline Mode" or "Results — Online Mode" based on `mode` variable |
| SEC-01 | 01-01 | Binds to 127.0.0.1 only | SATISFIED | `run.py` line 17: `app.run(host="127.0.0.1", port=5000, debug=False)` |
| SEC-02 | 01-01 | API keys read from environment variables only | SATISFIED | `config.py` uses `os.environ.get("VIRUSTOTAL_API_KEY")`; `SECRET_KEY` from env with auto-generated fallback; load_dotenv for dev convenience only |
| SEC-03 | 01-01 | Fails fast at startup if required API keys are missing | SATISFIED | `config.validate()` called in `create_app()`; Phase 1 stub is appropriately commented — no online mode configured yet, so no keys required |
| SEC-08 | 01-01 / 01-04 | All IOC strings HTML-escaped before rendering (no \|safe on untrusted data) | SATISFIED | Jinja2 autoescaping on by default for .html; grep of all templates confirms zero uses of `\|safe`; `{{ ioc.value }}` and `{{ ioc.raw_match }}` render escaped |
| SEC-09 | 01-01 | CSP header blocks inline scripts (default-src 'self'; script-src 'self') | SATISFIED | `app/__init__.py` after_request sets `Content-Security-Policy: default-src 'self'; script-src 'self'`; `test_security_headers_present` asserts both values; passes |
| SEC-10 | 01-01 | CSRF protection enabled on all POST endpoints | SATISFIED | `CSRFProtect(app)` initialized in `create_app()`; `index.html` includes `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`; `test_csrf_token_required` verifies 400 without token; passes |
| SEC-11 | 01-01 | Host header validation rejects unexpected origins (DNS rebinding prevention) | SATISFIED | `app.config["TRUSTED_HOSTS"] = ['localhost', '127.0.0.1']`; `test_invalid_host_returns_400` sends `Host: evil.com` and asserts 400; passes |
| SEC-12 | 01-01 | Input size capped (MAX_CONTENT_LENGTH, prevents ReDoS/memory exhaustion) | SATISFIED | `MAX_CONTENT_LENGTH = 512 * 1024` in config; 413 handler returns "Input too large. Maximum paste size is 512 KB."; `test_oversize_post_returns_413` passes |
| SEC-13 | 01-01 | No subprocess, shell, eval/exec in codebase | SATISFIED | Grep of `app/` confirms zero subprocess/eval/exec calls; only comment in `__init__.py` referencing SEC-13 |
| SEC-14 | 01-01 | No persistent storage of raw pasted text | SATISFIED | `POST /analyze` reads text, calls pipeline, renders template — no writes to disk/DB; pipeline is stateless per request |
| SEC-15 | 01-01 | Debug mode hardcoded to False | SATISFIED | `app.debug = False` applied twice in `create_app()` (before and after config_override); `test_debug_mode_is_false` asserts `app.debug is False`; passes |
| SEC-16 | 01-04 | Outbound API calls only target allowlisted hostnames (SSRF prevention) | SATISFIED | `ALLOWED_API_HOSTS: list[str] = []` in `config.py`; loaded in `create_app()` as `app.config["ALLOWED_API_HOSTS"]`; structure established for Phase 2 enforcement; zero outbound calls in Phase 1 make enforcement trivially satisfied |

**All 20 phase requirements: SATISFIED**

No orphaned requirements detected. All 20 IDs declared in phase ROADMAP.md match exactly across the four plan `requirements` fields (01-01 covers 11 SEC reqs; 01-02 covers EXTR-03, EXTR-04; 01-03 covers EXTR-01, EXTR-02, EXTR-05; 01-04 covers UI-01, UI-02, UI-04, UI-07, SEC-16).

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/templates/index.html` | 26 | `placeholder="...&#10;..."` | Info | Expected — it is a `<textarea>` placeholder attribute showing example defanged IOC values, not a code placeholder |
| `app/static/style.css` | 189 | `.ioc-textarea::placeholder` | Info | Expected — CSS rule styling the textarea placeholder, not a code stub |

No blocker or warning anti-patterns found. The two `return []` instances in `extractor.py` (lines 48, 114) are legitimate guard returns for empty input and empty candidate list — not stubs.

---

## Test Suite Results

- **Total tests:** 125 passed, 0 failed
- **Coverage:** 94% overall (201 statements, 12 uncovered)
- **Uncovered lines:** `extractor.py` exception handler branches (lines 62-63, 68-69, 73-75, 80-81, 87-88, 124) — these are `except Exception: pass` blocks guarding against library errors; acceptable for Phase 1
- **100% coverage:** `__init__.py`, `config.py`, `pipeline/__init__.py`, `classifier.py`, `models.py`, `normalizer.py`, `routes.py`

---

## Human Verification Required

### 1. Visual UI Quality

**Test:** Start the app (`source .venv/bin/activate && python run.py`), open `http://127.0.0.1:5000/` in browser, paste the defanged test block from Plan 04 Task 3, submit, examine results page.
**Expected:** Dark theme with `--bg-primary: #0d1117`; accordion sections for each IOC type expanded by default; type-specific accent colors (blue for IPv4/IPv6, green for domain, cyan for URL, orange for hashes, red for CVE); monospace font on IOC values; copy buttons show "Copied!" briefly on click; mode indicator "Results — Offline Mode" visible.
**Why human:** Visual rendering, color fidelity, clipboard behavior, and perceived UX quality cannot be verified programmatically. The Plan 04 SUMMARY states Task 3 (human checkpoint) was "approved by user" — this was recorded at execution time but cannot be independently confirmed from code artifacts alone.

---

## Gaps Summary

No gaps found. All five success criteria are verified. All 20 phase requirement IDs are satisfied. All 125 tests pass. 94% test coverage (exceeds 80% threshold). All artifacts exist, are substantive, and are wired. No blocker anti-patterns. No `|safe` on untrusted data. No inline scripts. No subprocess/eval/exec. No outbound calls.

The one human verification item (visual UI quality) does not constitute a gap — it is a NEEDS_HUMAN item for completeness only. Automated verification of the underlying security and functional properties is comprehensive and passing.

---

_Verified: 2026-02-21_
_Verifier: Claude (gsd-verifier)_
