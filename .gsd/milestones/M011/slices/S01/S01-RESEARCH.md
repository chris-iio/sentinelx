# S01 Research: Adapter Docstring Trim

## Summary

Straightforward mechanical trim of 15 non-base adapter files. 1,097 docstring lines across 15 files; ~1,003 removable, keeping ~94 lines for one-liners and genuine edge cases. base.py (79 docstring lines) is the canonical reference and stays untouched.

No tests reference `__doc__` attributes. No imports depend on docstrings. Zero behavioral risk.

## Recommendation

Three tasks by file group size, largest/riskiest first:

1. **Trim high-gotcha adapters** (4 files: threatminer, whois_lookup, ip_api, asn_cymru) — these have genuinely non-obvious edge cases that must be preserved as comments or short docstrings. ~380 lines removed.
2. **Trim standard HTTP adapters** (8 files: abuseipdb, crtsh, greynoise, hashlookup, otx, shodan, threatfox, virustotal) — pure boilerplate removal; keep one-liner module + class docstrings, delete method-level docstrings that restate what the code does. ~475 lines removed.
3. **Trim remaining adapters** (3 files: dns_lookup, malwarebazaar, urlhaus) — same pattern as T02. ~151 lines removed. Verify full suite passes.

## Implementation Landscape

### Files to Modify (15 files)

| File | Current Lines | Docstring Lines | Est. Remove | Edge Cases to Preserve |
|------|-------------|----------------|-------------|----------------------|
| `threatminer.py` | 341 | 161 | ~151 | "Always returns HTTP 200, body status_code '404' = no data" |
| `whois_lookup.py` | 251 | 83 | ~71 | Datetime polymorphism (datetime/list/None/str), no HTTP safety imports, port 43 not HTTP |
| `ip_api.py` | 182 | 81 | ~73 | HTTP 404 for private/reserved IPs (not an error), org field "AS15169 Google LLC" split format |
| `asn_cymru.py` | 205 | 91 | ~83 | Pipe-delimited TXT response format (needed to understand `_parse_response`), verdict always no_data |
| `abuseipdb.py` | 148 | 73 | ~68 | Verdict thresholds (score >= 75 → malicious, etc.) — keep as short comment in `_parse_response` |
| `crtsh.py` | 170 | 73 | ~68 | None |
| `greynoise.py` | 150 | 67 | ~62 | None |
| `hashlookup.py` | 119 | 56 | ~51 | "200 always means known_good" — one line |
| `otx.py` | 162 | 68 | ~63 | None |
| `shodan.py` | 127 | 51 | ~46 | None |
| `threatfox.py` | 150 | 60 | ~55 | None |
| `virustotal.py` | 216 | 67 | ~62 | None |
| `dns_lookup.py` | 163 | 62 | ~57 | None |
| `malwarebazaar.py` | 117 | 42 | ~37 | None |
| `urlhaus.py` | 154 | 62 | ~57 | None |

**Total estimated removal: ~1,003 lines** (target was ~650)

### File NOT Modified

- `base.py` (161 lines, 79 docstring lines) — canonical reference for the template-method pattern. All per-adapter docs should defer to it.

### Trim Pattern

For each file:

**Module-level docstring:** Replace multi-paragraph description with one-liner. Example:
```python
"""AbuseIPDB IP reputation adapter."""
```

**Class-level docstring:** Replace with one-liner. Example:
```python
"""AbuseIPDB check endpoint — see BaseHTTPAdapter for the template pattern."""
```

**Method-level docstrings:** Delete entirely for methods that are 1:1 implementations of BaseHTTPAdapter abstract methods (`_build_url`, `_parse_response`, `_auth_headers`, `_make_pre_raise_hook`, `_build_request_body`). The base class docstrings describe these contracts.

**Exception:** Keep method docstrings only when they document non-obvious behavior:
- `_parse_response` in whois_lookup.py (datetime polymorphism handling)
- `_parse_response` in asn_cymru.py (pipe-delimited TXT format)
- `_call` / `lookup` in threatminer.py (HTTP 200 always, body-level status codes)
- `_normalise_datetime` in whois_lookup.py (the type union is the whole point)

### Edge Cases That Must Be Preserved (from KNOWLEDGE.md)

These gotchas must survive as either short docstrings or inline comments:

1. **ThreatMiner always HTTP 200** — `# ThreatMiner always returns HTTP 200; body status_code "404" = no data`
2. **WHOIS datetime polymorphism** — keep `_normalise_datetime` docstring (it documents the 4-way type union)
3. **WHOIS no HTTP safety** — `# Port 43, not HTTP — no SSRF surface, no http_safety imports`
4. **ipinfo.io 404 for private IPs** — `# HTTP 404 for private/reserved IPs → no_data (not an error)`
5. **ipinfo.io org field format** — `# org: "AS15169 Google LLC" — split on first space`
6. **AbuseIPDB verdict thresholds** — inline comments on the if/elif branches (already present in code)
7. **Hashlookup 200 = known_good** — one-line note
8. **ASN Cymru pipe-delimited format** — keep short format note in `_parse_response`

### Verification Strategy

```bash
# 1. All tests pass unchanged
python3 -m pytest tests/ -x -q

# 2. All adapter modules importable (no syntax errors from bad docstring edits)
python3 -c "
import importlib, pathlib
for f in sorted(pathlib.Path('app/enrichment/adapters').glob('*.py')):
    if f.name == '__init__.py': continue
    mod = f'app.enrichment.adapters.{f.stem}'
    importlib.import_module(mod)
    print(f'  ✓ {mod}')
"

# 3. Line count reduction
find app/enrichment/adapters -name '*.py' ! -name '__init__.py' -exec cat {} + | wc -l
# Expected: ~1,813 (down from 2,816 = ~1,003 reduction)

# 4. Type check still clean
make typecheck
```

### Task Seams

Work divides naturally by "gotcha density":
- **T01: High-gotcha files** (threatminer, whois_lookup, ip_api, asn_cymru) — requires careful reading to identify which lines to keep. ~15 min.
- **T02: Standard HTTP adapters** (abuseipdb, crtsh, greynoise, hashlookup, otx, shodan, threatfox, virustotal) — mechanical; same trim pattern for all 8. ~15 min.
- **T03: Remaining adapters + verification** (dns_lookup, malwarebazaar, urlhaus) — same pattern, then run full suite. ~10 min.

All three tasks are independent (no file overlap) and can be verified with `python3 -c "import ..."` per-task plus a final full test run in T03.
