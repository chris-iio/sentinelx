---
estimated_steps: 20
estimated_files: 4
skills_used: []
---

# T01: Trim high-gotcha adapter docstrings (threatminer, whois_lookup, ip_api, asn_cymru)

Trim docstrings in the 4 adapter files that have genuinely non-obvious edge cases requiring careful preservation. These files need judgment about which docstring content to convert to inline comments vs delete entirely.

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

## Inputs

- ``app/enrichment/adapters/threatminer.py` — current file with verbose docstrings`
- ``app/enrichment/adapters/whois_lookup.py` — current file with verbose docstrings`
- ``app/enrichment/adapters/ip_api.py` — current file with verbose docstrings`
- ``app/enrichment/adapters/asn_cymru.py` — current file with verbose docstrings`

## Expected Output

- ``app/enrichment/adapters/threatminer.py` — trimmed to one-liner docstrings + edge-case comments`
- ``app/enrichment/adapters/whois_lookup.py` — trimmed to one-liner docstrings + _normalise_datetime docstring + edge-case comments`
- ``app/enrichment/adapters/ip_api.py` — trimmed to one-liner docstrings + edge-case comments`
- ``app/enrichment/adapters/asn_cymru.py` — trimmed to one-liner docstrings + edge-case comments`

## Verification

python3 -c "import app.enrichment.adapters.threatminer; import app.enrichment.adapters.whois_lookup; import app.enrichment.adapters.ip_api; import app.enrichment.adapters.asn_cymru; print('All 4 OK')" && python3 -m pytest tests/test_threatminer.py tests/test_whois_lookup.py tests/test_ip_api.py tests/test_asn_cymru.py -x -q
