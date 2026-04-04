# S01: Adapter Docstring Trim

**Goal:** All 16 adapter files (15 non-base + base untouched) have one-liner + edge-case-only docstrings; ~1,000 lines removed; all 1,061 tests pass unchanged.
**Demo:** After this: After this: all 16 adapter files have one-liner + edge-case-only docstrings; ~650 lines removed; all tests pass unchanged.

## Tasks
- [x] **T01: Trimmed 416 lines of verbose docstrings from 4 high-gotcha adapter files, preserving edge-case info as inline comments** — Trim docstrings in the 4 adapter files that have genuinely non-obvious edge cases requiring careful preservation. These files need judgment about which docstring content to convert to inline comments vs delete entirely.

## Steps

1. Read each of the 4 files fully to identify current docstring content.
2. For each file, apply the trim pattern:
   - **Module-level docstring**: Replace multi-paragraph description with one-liner (e.g., `"""ThreatMiner passive DNS and related samples adapter."""`).
   - **Class-level docstring**: Replace with one-liner referencing BaseHTTPAdapter (e.g., `"""ThreatMiner multi-call lookup — see BaseHTTPAdapter for the template pattern."""`).
   - **Method-level docstrings**: Delete entirely for standard BaseHTTPAdapter overrides (`_build_url`, `_parse_response`, `_auth_headers`, `_make_pre_raise_hook`, `_build_request_body`).
   - **Exception — keep or convert to inline comment** the following edge cases:
     - `threatminer.py`: "ThreatMiner always returns HTTP 200; body status_code '404' = no data" — keep as inline comment near the status_code check in lookup().
     - `whois_lookup.py`: `_normalise_datetime` docstring (documents 4-way type union: datetime/list/None/str) — keep short docstring. Also keep "Port 43, not HTTP — no SSRF surface" as inline comment.
     - `ip_api.py`: "HTTP 404 for private/reserved IPs → no_data (not an error)" — keep as inline comment in `_make_pre_raise_hook`. Also "org: 'AS15169 Google LLC' — split on first space" as inline comment.
     - `asn_cymru.py`: Pipe-delimited TXT response format note — keep short comment in `_parse_response`. Also "verdict always no_data" as inline comment.
3. Verify each file imports cleanly: `python3 -c "import app.enrichment.adapters.{module}"`
4. Run tests for these 4 adapters: `python3 -m pytest tests/test_threatminer.py tests/test_whois_lookup.py tests/test_ip_api.py tests/test_asn_cymru.py -x -q`

## Must-Haves

- [ ] All 4 files have one-liner module + class docstrings
- [ ] Method-level docstrings deleted except for `_normalise_datetime` in whois_lookup.py
- [ ] Edge cases preserved as inline comments (not deleted)
- [ ] All 4 modules importable
- [ ] All adapter-specific tests pass
  - Estimate: 20m
  - Files: app/enrichment/adapters/threatminer.py, app/enrichment/adapters/whois_lookup.py, app/enrichment/adapters/ip_api.py, app/enrichment/adapters/asn_cymru.py
  - Verify: python3 -c "import app.enrichment.adapters.threatminer; import app.enrichment.adapters.whois_lookup; import app.enrichment.adapters.ip_api; import app.enrichment.adapters.asn_cymru; print('All 4 OK')" && python3 -m pytest tests/test_threatminer.py tests/test_whois_lookup.py tests/test_ip_api.py tests/test_asn_cymru.py -x -q
- [x] **T02: Trimmed 515 lines of verbose docstrings from 8 standard HTTP adapter files, leaving one-liner module + class docstrings and zero method docstrings** — Mechanical docstring trim on the 8 standard HTTP adapters that follow the BaseHTTPAdapter template pattern with no special edge cases beyond minor inline comments.

## Steps

1. For each of the 8 files, apply the identical trim pattern:
   - **Module-level docstring**: Replace with one-liner (e.g., `"""AbuseIPDB IP reputation adapter."""`).
   - **Class-level docstring**: Replace with one-liner referencing BaseHTTPAdapter (e.g., `"""AbuseIPDB check endpoint — see BaseHTTPAdapter for the template pattern."""`).
   - **Method-level docstrings**: Delete entirely for all `_build_url`, `_parse_response`, `_auth_headers`, `_make_pre_raise_hook`, `_build_request_body`, and `lookup` override docstrings.
   - **Minor edge cases to keep as inline comments** (already present in code, just ensure not deleted):
     - `abuseipdb.py`: Verdict threshold comments on if/elif branches (score >= 75 → malicious, etc.) — these are already inline comments, just verify they survive.
     - `hashlookup.py`: "200 always means known_good" — keep as one-line comment.
2. Verify all 8 files import cleanly: `python3 -c "import app.enrichment.adapters.{module}"` for each.
3. Run tests for these 8 adapters: `python3 -m pytest tests/test_abuseipdb.py tests/test_crtsh.py tests/test_greynoise.py tests/test_hashlookup.py tests/test_otx.py tests/test_shodan.py tests/test_threatfox.py tests/test_virustotal.py -x -q`

## Must-Haves

- [ ] All 8 files have one-liner module + class docstrings
- [ ] All method-level docstrings deleted
- [ ] All 8 modules importable
- [ ] All adapter-specific tests pass
  - Estimate: 20m
  - Files: app/enrichment/adapters/abuseipdb.py, app/enrichment/adapters/crtsh.py, app/enrichment/adapters/greynoise.py, app/enrichment/adapters/hashlookup.py, app/enrichment/adapters/otx.py, app/enrichment/adapters/shodan.py, app/enrichment/adapters/threatfox.py, app/enrichment/adapters/virustotal.py
  - Verify: python3 -c "import app.enrichment.adapters.abuseipdb; import app.enrichment.adapters.crtsh; import app.enrichment.adapters.greynoise; import app.enrichment.adapters.hashlookup; import app.enrichment.adapters.otx; import app.enrichment.adapters.shodan; import app.enrichment.adapters.threatfox; import app.enrichment.adapters.virustotal; print('All 8 OK')" && python3 -m pytest tests/test_abuseipdb.py tests/test_crtsh.py tests/test_greynoise.py tests/test_hashlookup.py tests/test_otx.py tests/test_shodan.py tests/test_threatfox.py tests/test_virustotal.py -x -q
- [ ] **T03: Trim remaining adapters (dns_lookup, malwarebazaar, urlhaus) and run full verification** — Apply the same mechanical trim to the final 3 adapter files, then run the full test suite and line-count verification to confirm the slice goal.

## Steps

1. For each of the 3 files, apply the standard trim pattern:
   - **Module-level docstring**: Replace with one-liner.
   - **Class-level docstring**: Replace with one-liner referencing BaseHTTPAdapter.
   - **Method-level docstrings**: Delete entirely.
2. Verify all 3 files import cleanly.
3. Run the **full** test suite: `python3 -m pytest tests/ -x -q` — all 1,061 tests must pass.
4. Verify all 15 non-base adapter modules are importable in one shot.
5. Measure total line count: `find app/enrichment/adapters -name '*.py' ! -name '__init__.py' ! -name 'base.py' -exec cat {} + | wc -l` — must be ≤1,900 (down from ~2,659 baseline).
6. Confirm `base.py` is unchanged: `wc -l app/enrichment/adapters/base.py` should be 161.

## Must-Haves

- [ ] All 3 files have one-liner module + class docstrings
- [ ] All method-level docstrings deleted
- [ ] Full test suite passes (1,061 tests, 0 failures)
- [ ] Total non-base adapter line count ≤ 1,900
- [ ] base.py unchanged at 161 lines
  - Estimate: 15m
  - Files: app/enrichment/adapters/dns_lookup.py, app/enrichment/adapters/malwarebazaar.py, app/enrichment/adapters/urlhaus.py
  - Verify: python3 -m pytest tests/ -x -q && python3 -c "
import importlib, pathlib
for f in sorted(pathlib.Path('app/enrichment/adapters').glob('*.py')):
    if f.name == '__init__.py': continue
    mod = f'app.enrichment.adapters.{f.stem}'
    importlib.import_module(mod)
    print(f'  OK {mod}')
" && echo "Non-base line count:" && find app/enrichment/adapters -name '*.py' ! -name '__init__.py' ! -name 'base.py' -exec cat {} + | wc -l && echo "base.py:" && wc -l app/enrichment/adapters/base.py
