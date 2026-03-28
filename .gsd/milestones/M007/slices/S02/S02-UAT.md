# S02: Docstring trimming & dead CSS — UAT

**Milestone:** M007
**Written:** 2026-03-28T02:12:52.013Z

# S02 UAT: Docstring Trimming & Dead CSS

## Preconditions
- All 12 HTTP adapter .py files present in `app/enrichment/adapters/`
- `app/static/src/input.css` present
- Python 3.10+ available
- pytest installed with project dependencies

## Test Cases

### TC-1: Zero SEC control references in adapter files
**Steps:**
1. Run: `grep -c 'SEC-04\|SEC-05\|SEC-06\|SEC-07\|SEC-16' app/enrichment/adapters/*.py`
**Expected:** All 15 .py files show `:0`. No adapter file contains SEC-04, SEC-05, SEC-06, SEC-07, or SEC-16 references.

### TC-2: Module-level Thread safety paragraphs removed
**Steps:**
1. For each of the 12 HTTP adapters, extract text before the `class` definition.
2. Check for "Thread safety" in that region.
**Expected:** Zero matches. No module docstring contains a Thread safety paragraph.

### TC-3: Class-level Thread safety preserved
**Steps:**
1. For each of the 12 HTTP adapters, extract text after the `class` definition.
2. Check for "Thread safety" in class docstrings.
**Expected:** 10 adapters (all except otx.py and urlhaus.py) have exactly 1 "Thread safety" line in their class docstring.

### TC-4: lookup() SSRF boilerplate removed
**Steps:**
1. Run: `grep -n 'Validates the.*SSRF\|safety controls and parses\|full safety controls' app/enrichment/adapters/*.py`
**Expected:** Zero matches. No adapter lookup() docstring contains SSRF/safety-controls boilerplate.

### TC-5: lookup() has delegation reference
**Steps:**
1. Run: `grep -l 'safe_request()' app/enrichment/adapters/*.py`
**Expected:** All 12 HTTP adapters contain a reference to `safe_request()` in their lookup() docstring.

### TC-6: Stale CSS comment removed
**Steps:**
1. Run: `grep -c 'chevron-toggle' app/static/src/input.css`
**Expected:** Returns `0`. The stale `.chevron-toggle rules removed` comment is gone.

### TC-7: All adapters import cleanly
**Steps:**
1. Run: `for f in abuseipdb crtsh greynoise hashlookup ip_api malwarebazaar otx shodan threatfox threatminer urlhaus virustotal; do python3 -c "import app.enrichment.adapters.$f"; done`
**Expected:** All 12 imports succeed with exit code 0, no SyntaxError or IndentationError.

### TC-8: Full test suite passes
**Steps:**
1. Run: `python3 -m pytest --tb=short -q`
**Expected:** 1057 tests pass, 0 failures, 0 errors.

### TC-9: API-specific documentation preserved
**Steps:**
1. Spot-check `abuseipdb.py` for: endpoint URL, capital 'Key' header note, confidence score threshold.
2. Spot-check `virustotal.py` for: detection_stats type mapping, response code semantics.
3. Spot-check `ip_api.py` for: ipinfo.io endpoint URL, 404 handling for private IPs.
**Expected:** All API-specific details remain in adapter docstrings — only cross-cutting boilerplate was removed.

### Edge Cases

### EC-1: Non-HTTP adapters unaffected
**Steps:**
1. Check `app/enrichment/adapters/dns_lookup.py`, `asn_cymru.py`, `whois_lookup.py` for unchanged content.
**Expected:** DNS/ASN/WHOIS adapters have no SEC references and were not modified by this slice.
