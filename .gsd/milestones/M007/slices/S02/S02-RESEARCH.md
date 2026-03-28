# S02 Research: Docstring Trimming & Dead CSS

**Depth:** Light — straightforward cleanup with established patterns, no new technology.

## Summary

This slice removes duplicated SEC-control docstring text from 12 HTTP adapter files and removes dead CSS. The work is mechanical: every HTTP adapter duplicates SEC-04/05/06/07/16 descriptions that now live once in `http_safety.py`'s `safe_request()` docstring. The CSS portion is minimal — `consensus-badge` is already gone (0 hits). The only dead CSS is a stale comment on line 1300 of `input.css`.

## Recommendation

Two tasks:
1. **Docstring trimming** (12 HTTP adapter files) — remove SEC bullet lists from module docstrings, trim class docstrings, shorten lookup() docstrings. Keep API-specific semantics (verdict rules, response codes, quirks). Replace SEC boilerplate with a one-line "See safe_request() in http_safety.py" reference.
2. **Dead CSS cleanup** — remove the stale `.chevron-toggle` comment at line 1300 of `input.css`. No actual dead CSS rules exist — all other candidates (filter-pill variants, verdict-* variants, ioc-type-badge variants) are dynamically generated via template interpolation or JS string concatenation.

## Implementation Landscape

### Files in scope

**12 HTTP adapter files** (exclude `__init__.py`, `dns_lookup.py`, `asn_cymru.py`, `whois_lookup.py`):
| File | Total lines | Docstring lines | Docstring % |
|------|-------------|-----------------|-------------|
| abuseipdb.py | 195 | 99 | 51% |
| crtsh.py | 179 | 77 | 43% |
| greynoise.py | 197 | 93 | 47% |
| hashlookup.py | 159 | 74 | 47% |
| ip_api.py | 225 | 102 | 45% |
| malwarebazaar.py | 155 | 65 | 42% |
| otx.py | 196 | 86 | 44% |
| shodan.py | 173 | 75 | 43% |
| threatfox.py | 183 | 73 | 40% |
| threatminer.py | 329 | 142 | 43% |
| urlhaus.py | 195 | 85 | 44% |
| virustotal.py | 212 | 57 | 27% |
| **Total** | **2398** | **1028** | **43%** |

**1 CSS file**: `app/static/src/input.css` (2071 lines) — line 1300 stale comment only.

**3 NON-HTTP adapters to SKIP** (their docstrings are explanatory, not boilerplate):
- `dns_lookup.py` — port 53, explains why http_safety is NOT used
- `asn_cymru.py` — port 53, same pattern
- `whois_lookup.py` — port 43, same pattern

### Duplicated text patterns to remove

**Pattern 1: SEC bullet list in module docstring** (8 of 12 adapters have full list):
```
  - SEC-04: timeout=(5, 30) on all requests
  - SEC-05: stream=True + byte counting, 1 MB response cap
  - SEC-06: allow_redirects=False on all requests
  - SEC-07/SEC-16: ALLOWED_API_HOSTS allowlist enforced before every network call
```
→ Replace with: `Delegates all HTTP safety controls to safe_request() in http_safety.py.`

**Pattern 2: "Thread safety" line in module + class docstrings** (appears twice in each file):
```
Thread safety: a persistent requests.Session is created in __init__ and reused across
lookup() calls (TCP connection pooling).
```
→ Keep ONE instance (class docstring). Remove from module docstring.

**Pattern 3: "Validates the X endpoint against the SSRF allowlist" in lookup() docstring** (all 12):
```
Validates the X endpoint against the SSRF allowlist before any
network call. Makes a GET request with full safety controls and
parses the response.
```
→ Replace with: `Calls safe_request() and parses the response.`

**Pattern 4: "SSRF allowlist" args description in class docstring** (all 12):
```
    Args:
        allowed_hosts: SSRF allowlist -- only these hostnames may be contacted.
```
→ Keep — this is API documentation, not SEC boilerplate.

### What to KEEP in each adapter

- API endpoint URLs and response format documentation
- Verdict thresholds / priority rules
- Response code semantics (what 200/404/429 mean for this specific API)
- Auth quirks (e.g., AbuseIPDB's capital 'Key' header)
- API-specific notes (e.g., VT's detection_stats type mapping)

### Dead CSS analysis

- `consensus-badge`: 0 hits in templates, JS, or CSS source. Already fully removed.
- `chevron-toggle`: Only a stale comment at `input.css:1300`. No rules exist.
- All `filter-pill--{type}`, `ioc-type-badge--{type}`, `verdict-*` classes: **NOT dead** — generated via Jinja `{{ ioc_type.value }}` interpolation and JS `"verdict-" + worstVerdict` concatenation.

### Verification strategy

1. `python3 -m pytest` — all 1057+ tests pass (zero behavior change)
2. `python3 -c "import app.enrichment.adapters.<name>"` — each adapter imports cleanly after docstring edits
3. `wc -l app/enrichment/adapters/*.py` — measurable LOC reduction (target: ~400 lines removed, from ~3009 to ~2600)
4. `grep -c 'SEC-04\|SEC-05\|SEC-06\|SEC-07\|SEC-16' app/enrichment/adapters/*.py` — returns 0 for all files

### Task decomposition suggestion

- **T01: Trim HTTP adapter docstrings** — all 12 files in one task. Mechanical find-and-replace. Verify imports + tests after each batch.
- **T02: Dead CSS cleanup** — remove stale comment from `input.css`. Trivial.

T01 and T02 are independent — no ordering dependency. T02 is <1 minute of work; could be folded into T01 if the planner prefers a single task.

### Requirements covered

- **R037** (Adapter docstring trimming) — primary target of this slice
- **R038** (Dead CSS removal) — secondary target; mostly already done; stale comment cleanup remains
- **R040** (All tests pass, zero behavior changes) — verification gate

### Risks

None. This is pure comment/docstring editing + one CSS comment removal. No code logic changes. The 1057-test suite is the safety net.
