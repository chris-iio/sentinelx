---
estimated_steps: 8
estimated_files: 4
skills_used: []
---

# T02: Centralize duplicate IOC grouping and payload builders

Expected executor skills: tdd, verify-before-complete.

Why: The top M020 audit candidate identifies duplicated IOC grouping/template context/API serialization code across `analysis`, `api`, and `history` routes. Centralizing this seam should reduce request-path drift without changing analyst-visible behavior.

Threat Surface (Q3): Route helpers transform untrusted IOC/result data into HTML context and JSON. Preserve escaping/textContent-safe expectations, CSRF boundaries, host validation assumptions, diagnostics visibility, and secret redaction behavior; do not introduce broad `dict` passthroughs that leak provider internals.

Requirement Impact (Q4): satisfies R096 for shipped optimization proof and supports R097/R098/R099/R100; decisions D081-D083 remain in force.

Failure Modes (Q5): Helper extraction must keep missing provider and no-results paths stable; malformed result rows should degrade as existing routes did; exceptions should remain localized to test-visible route failures rather than hidden silent drops.

Load Profile (Q6): Shared helper work should make one grouping/serialization pass per response path rather than route-local duplicate passes; per-operation cost remains O(number of result rows); avoid adding DB queries or provider calls.

Negative Tests (Q7): Existing/new T01 tests should prove duplicate IOC grouping, empty inputs, missing optional fields, diagnostics/error preservation, and route-specific response shape differences.

Do: Move shared IOC template context, history IOC grouping, and serialized API response payload construction into `app/routes/_helpers.py` or complete that extraction if partially present. Update `app/routes/analysis.py`, `app/routes/api.py`, and `app/routes/history.py` to import and call those helpers while keeping route-specific concerns in place: online/offline admission, redirects, flash/error handling, history persistence, response codes, and templates. Keep helper names explicit and narrow (for example `_ioc_template_context`, `_history_ioc_template_context`, `_group_iocs_for_template`, `_group_history_iocs`, `_serialized_ioc_response_payload`) so future slices can inspect the seam. Done when focused tests pass and code-path reasoning shows no new DB/provider/runtime calls were added.

## Inputs

- `app/routes/_helpers.py`
- `app/routes/analysis.py`
- `app/routes/api.py`
- `app/routes/history.py`
- `tests/test_routes.py`
- `tests/test_api.py`
- `tests/test_history_routes.py`

## Expected Output

- `app/routes/_helpers.py`
- `app/routes/analysis.py`
- `app/routes/api.py`
- `app/routes/history.py`

## Verification

python3 -m pytest -q tests/test_routes.py tests/test_api.py tests/test_history_routes.py

## Observability Impact

Preserves existing route-visible diagnostics/failure signals while consolidating the code path a future agent inspects for grouped IOC context and API payload construction.
