---
estimated_steps: 10
estimated_files: 2
skills_used: []
---

# T02: Implement EmailRepAdapter with conservative verdict mapping

Why: Implement the minimal backend provider seam that S02 and S03 can consume without prematurely wiring it into Online mode.

Do:
1. Add `app/enrichment/adapters/emailrep.py` with `EmailRepAdapter(BaseHTTPAdapter)`.
2. Set `name = "EmailRep"`, `supported_types = frozenset({IOCType.EMAIL})`, and `requires_api_key = True`.
3. URL-encode email IOC values when building `https://emailrep.io/{email}`.
4. Set session auth headers with documented `Key` and stable `User-Agent` values.
5. Implement explicit verdict mapping: high-confidence abuse flags to malicious, broader risk flags/low reputation to suspicious, clean reputation with no risk flags to clean, and no/thin reputation to no_data.
6. Flatten selected fields into raw_stats, including a stable `risk_flags` array built from true boolean risk flags.
7. Avoid any `build_registry()`, settings, allowed-host, or frontend changes; those belong to later slices.

Done when: `tests/test_emailrep.py` passes and the adapter remains isolated from app-wide registration.

## Inputs

- `tests/test_emailrep.py`
- `app/enrichment/adapters/base.py`
- `app/enrichment/models.py`
- `app/pipeline/models.py`

## Expected Output

- `app/enrichment/adapters/emailrep.py`

## Verification

python3 -m pytest tests/test_emailrep.py -q

## Observability Impact

Uses existing safe_request/EnrichmentError paths; no new logs required. Error localization is via tested verdict/raw_stats behavior and BaseHTTPAdapter failure propagation.
