---
estimated_steps: 31
estimated_files: 13
skills_used: []
---

# T01: Trim HTTP adapter docstrings and remove stale CSS comment

Trim duplicated SEC-control docstring text from 12 HTTP adapter files and remove a stale CSS comment. This is the entire slice — no code logic changes.

## Steps

1. For each of the 6 adapters that still have SEC bullet lists in module docstrings (abuseipdb, greynoise, malwarebazaar, threatfox, urlhaus, virustotal): replace the SEC-04/05/06/07/16 bullet list with a single line: `Delegates all HTTP safety controls to safe_request() in http_safety.py.`

2. For all 12 HTTP adapters: remove the `Thread safety:` paragraph from the **module** docstring. The class docstring already has one — there's no need for two. Keep the one in the class docstring.

3. For all 12 HTTP adapters: in the `lookup()` method docstring, replace the 2-3 line SSRF boilerplate (`Validates the X endpoint against the SSRF allowlist before any network call. Makes a GET/POST request with full safety controls and parses the response.`) with a single line: `Calls safe_request() and parses the response.`

4. In `app/static/src/input.css`, remove the stale comment at ~line 1300: `/* .chevron-toggle rules removed — standalone button replaced by .chevron-icon-wrapper inside summary row */`

5. Verify all 12 adapters import cleanly: `python3 -c "import app.enrichment.adapters.<name>"` for each.

6. Run `python3 -m pytest` to confirm all tests pass.

7. Run `wc -l app/enrichment/adapters/*.py | tail -1` to confirm LOC reduction.

8. Run `grep -c 'SEC-04\|SEC-05\|SEC-06\|SEC-07\|SEC-16' app/enrichment/adapters/*.py` to confirm all return 0.

## What to KEEP in each adapter

- API endpoint URLs and response format documentation
- Verdict thresholds / priority rules
- Response code semantics (what 200/404/429 mean for this specific API)
- Auth quirks (e.g., AbuseIPDB's capital 'Key' header)
- API-specific notes (e.g., VT's detection_stats type mapping)
- The `Args:` block with allowed_hosts/api_key descriptions
- The class-level `Thread safety:` line (keep exactly one)

## What to REMOVE

- SEC-04/05/06/07/16 bullet lists in module docstrings (6 adapters)
- `Thread safety:` paragraphs in module docstrings (all 12 — class docstring has it)
- SSRF boilerplate in lookup() docstrings (all 12)
- Any `Implements X enrichment ... with full HTTP safety controls matching the established adapter pattern:` intro that precedes the SEC bullet list
- The stale `.chevron-toggle` comment in input.css

## Must-Haves

- [ ] Zero SEC-04/05/06/07/16 references in adapter files
- [ ] Module docstrings have no `Thread safety:` paragraph (class docstring still has one)
- [ ] lookup() docstrings have no SSRF boilerplate
- [ ] Stale CSS comment removed
- [ ] All 1057 tests pass
- [ ] All 12 adapters import cleanly

## Inputs

- `app/enrichment/adapters/abuseipdb.py`
- `app/enrichment/adapters/crtsh.py`
- `app/enrichment/adapters/greynoise.py`
- `app/enrichment/adapters/hashlookup.py`
- `app/enrichment/adapters/ip_api.py`
- `app/enrichment/adapters/malwarebazaar.py`
- `app/enrichment/adapters/otx.py`
- `app/enrichment/adapters/shodan.py`
- `app/enrichment/adapters/threatfox.py`
- `app/enrichment/adapters/threatminer.py`
- `app/enrichment/adapters/urlhaus.py`
- `app/enrichment/adapters/virustotal.py`
- `app/static/src/input.css`

## Expected Output

- `app/enrichment/adapters/abuseipdb.py`
- `app/enrichment/adapters/crtsh.py`
- `app/enrichment/adapters/greynoise.py`
- `app/enrichment/adapters/hashlookup.py`
- `app/enrichment/adapters/ip_api.py`
- `app/enrichment/adapters/malwarebazaar.py`
- `app/enrichment/adapters/otx.py`
- `app/enrichment/adapters/shodan.py`
- `app/enrichment/adapters/threatfox.py`
- `app/enrichment/adapters/threatminer.py`
- `app/enrichment/adapters/urlhaus.py`
- `app/enrichment/adapters/virustotal.py`
- `app/static/src/input.css`

## Verification

python3 -m pytest && grep -c 'SEC-04\|SEC-05\|SEC-06\|SEC-07\|SEC-16' app/enrichment/adapters/*.py | grep -v ':0$' | wc -l | grep -q '^0$' && echo 'PASS: No SEC references remain'
