---
estimated_steps: 16
estimated_files: 8
skills_used: []
---

# T02: Trim standard HTTP adapter docstrings (abuseipdb, crtsh, greynoise, hashlookup, otx, shodan, threatfox, virustotal)

Mechanical docstring trim on the 8 standard HTTP adapters that follow the BaseHTTPAdapter template pattern with no special edge cases beyond minor inline comments.

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

## Inputs

- ``app/enrichment/adapters/abuseipdb.py` — current file with verbose docstrings`
- ``app/enrichment/adapters/crtsh.py` — current file with verbose docstrings`
- ``app/enrichment/adapters/greynoise.py` — current file with verbose docstrings`
- ``app/enrichment/adapters/hashlookup.py` — current file with verbose docstrings`
- ``app/enrichment/adapters/otx.py` — current file with verbose docstrings`
- ``app/enrichment/adapters/shodan.py` — current file with verbose docstrings`
- ``app/enrichment/adapters/threatfox.py` — current file with verbose docstrings`
- ``app/enrichment/adapters/virustotal.py` — current file with verbose docstrings`

## Expected Output

- ``app/enrichment/adapters/abuseipdb.py` — trimmed to one-liner docstrings`
- ``app/enrichment/adapters/crtsh.py` — trimmed to one-liner docstrings`
- ``app/enrichment/adapters/greynoise.py` — trimmed to one-liner docstrings`
- ``app/enrichment/adapters/hashlookup.py` — trimmed to one-liner docstrings`
- ``app/enrichment/adapters/otx.py` — trimmed to one-liner docstrings`
- ``app/enrichment/adapters/shodan.py` — trimmed to one-liner docstrings`
- ``app/enrichment/adapters/threatfox.py` — trimmed to one-liner docstrings`
- ``app/enrichment/adapters/virustotal.py` — trimmed to one-liner docstrings`

## Verification

python3 -c "import app.enrichment.adapters.abuseipdb; import app.enrichment.adapters.crtsh; import app.enrichment.adapters.greynoise; import app.enrichment.adapters.hashlookup; import app.enrichment.adapters.otx; import app.enrichment.adapters.shodan; import app.enrichment.adapters.threatfox; import app.enrichment.adapters.virustotal; print('All 8 OK')" && python3 -m pytest tests/test_abuseipdb.py tests/test_crtsh.py tests/test_greynoise.py tests/test_hashlookup.py tests/test_otx.py tests/test_shodan.py tests/test_threatfox.py tests/test_virustotal.py -x -q
