---
estimated_steps: 5
estimated_files: 4
skills_used:
  - review
  - test
  - debug-like-expert
---

# T03: Convert VT and ThreatFox — remove Sessions, migrate test mocks

**Slice:** S01 — Adapter Simplification
**Milestone:** M002

## Description

Convert VirusTotal and ThreatFox adapters from `requests.Session()` to `safe_request()`. This is the highest-risk task in the slice because it requires updating ~29 test mock patches from `patch("requests.Session")` to `patch("requests.get")`/`patch("requests.post")`. A single missed mock will cause a test to fail or make real HTTP calls. Work one adapter at a time and verify tests pass before moving to the next.

## Steps

1. **Convert `app/enrichment/adapters/virustotal.py`:**
   - In `lookup()`: remove `session = requests.Session()` and `session.headers.update(...)` lines.
   - Replace `resp = session.get(url, timeout=TIMEOUT, allow_redirects=False, stream=True)` + 404 check + `raise_for_status()` + `read_limited(resp)` block with:
     ```python
     body = safe_request("GET", url, self._allowed_hosts,
                         headers={"x-apikey": self._api_key, "Accept": "application/json"},
                         no_data_on_404=True)
     ```
   - If `body is None`, return the existing 404 no_data `EnrichmentResult`.
   - If body returned, call `_parse_response(ioc, body)`.
   - Keep VT's `_map_http_error()` — catch `requests.exceptions.HTTPError` and delegate to it.
   - Update imports: `from app.enrichment.http_safety import safe_request` (remove `TIMEOUT`, `read_limited`, `validate_endpoint`).

2. **Migrate `tests/test_vt_adapter.py` mocks (16 patches):**
   - Every `with patch("requests.Session") as mock_session_cls:` block currently does:
     ```python
     mock_session = mock_session_cls.return_value
     mock_resp = MagicMock()
     mock_session.get.return_value = mock_resp
     ```
   - Change to:
     ```python
     with patch("requests.get") as mock_get:
         mock_resp = MagicMock()
         mock_get.return_value = mock_resp
     ```
   - All `mock_resp` setup (`.status_code`, `.raise_for_status()`, `.iter_content()`) stays the same.
   - **Run VT tests after this step:** `/home/chris/projects/sentinelx/.venv/bin/python -m pytest tests/test_vt_adapter.py -v --tb=short`

3. **Convert `app/enrichment/adapters/threatfox.py`:**
   - In `lookup()`: remove `session = requests.Session()` and `session.headers.update(...)` lines.
   - Replace `resp = session.post(TF_BASE, json=payload, ...)` + `raise_for_status()` + `read_limited(resp)` block with:
     ```python
     body = safe_request("POST", TF_BASE, self._allowed_hosts,
                         json=payload,
                         headers={"Content-Type": "application/json", "Auth-Key": self._api_key})
     ```
   - Update imports: `from app.enrichment.http_safety import safe_request`.

4. **Migrate `tests/test_threatfox.py` mocks (13 patches):**
   - Every `with patch("requests.Session") as mock_session_cls:` block currently does:
     ```python
     mock_session = mock_session_cls.return_value
     mock_resp = MagicMock()
     mock_session.post.return_value = mock_resp
     ```
   - Change to:
     ```python
     with patch("requests.post") as mock_post:
         mock_resp = MagicMock()
         mock_post.return_value = mock_resp
     ```
   - **Run ThreatFox tests after this step:** `/home/chris/projects/sentinelx/.venv/bin/python -m pytest tests/test_threatfox.py -v --tb=short`

5. **Run full test suite:** `/home/chris/projects/sentinelx/.venv/bin/python -m pytest tests/ -q --tb=short` → 924 passed, 0 failed.

## Must-Haves

- [ ] VT adapter uses `safe_request("GET", ...)` — no `requests.Session()` usage
- [ ] VT's `_map_http_error()` still handles 429/401/403 mapping (adapter-specific, not absorbed into `safe_request`)
- [ ] ThreatFox adapter uses `safe_request("POST", ...)` — no `requests.Session()` usage
- [ ] All 16 VT test mocks migrated from `patch("requests.Session")` to `patch("requests.get")`
- [ ] All 13 ThreatFox test mocks migrated from `patch("requests.Session")` to `patch("requests.post")`
- [ ] 924/924 tests pass

## Verification

- `/home/chris/projects/sentinelx/.venv/bin/python -m pytest tests/test_vt_adapter.py tests/test_threatfox.py -v --tb=short` → all pass
- `/home/chris/projects/sentinelx/.venv/bin/python -m pytest tests/ -q --tb=short` → 924 passed, 0 failed
- `grep -c 'requests.Session' app/enrichment/adapters/virustotal.py app/enrichment/adapters/threatfox.py` → 0 for both
- `grep -c 'requests.Session' tests/test_vt_adapter.py tests/test_threatfox.py` → 0 for both

## Inputs

- `app/enrichment/http_safety.py` — contains `safe_request()` (from T01)
- `app/enrichment/adapters/virustotal.py` — Session-based GET adapter (241 LOC)
- `app/enrichment/adapters/threatfox.py` — Session-based POST adapter (200 LOC)
- `tests/test_vt_adapter.py` — 16 `patch("requests.Session")` mocks to migrate
- `tests/test_threatfox.py` — 13 `patch("requests.Session")` mocks to migrate

## Expected Output

- `app/enrichment/adapters/virustotal.py` — refactored to use `safe_request()`, no Session
- `app/enrichment/adapters/threatfox.py` — refactored to use `safe_request()`, no Session
- `tests/test_vt_adapter.py` — all mocks use `patch("requests.get")`
- `tests/test_threatfox.py` — all mocks use `patch("requests.post")`
