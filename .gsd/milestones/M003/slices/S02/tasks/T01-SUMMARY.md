---
id: T01
parent: S02
milestone: M003
provides:
  - IOCType.EMAIL enum value ("email") in app/pipeline/models.py
  - Email classifier at precedence position 8 (between IPv4 and Domain) in app/pipeline/classifier.py
  - OTX adapter explicit supported_types frozenset excluding EMAIL in app/enrichment/adapters/otx.py
  - .ioc-type-badge--email CSS rule in app/static/src/input.css
  - TestClassifyEmail (11 tests) in tests/test_classifier.py
  - TestExtractEmail (5 tests) in tests/test_extractor.py
key_files:
  - app/pipeline/models.py
  - app/pipeline/classifier.py
  - app/enrichment/adapters/otx.py
  - app/static/src/input.css
  - tests/test_classifier.py
  - tests/test_extractor.py
key_decisions:
  - Email classifier position must be before Domain (position 8 vs 9) to prevent user@evil.com misclassifying as DOMAIN
  - OTX supported_types must be explicit frozenset rather than frozenset(IOCType) to prevent KeyError on new enum values
patterns_established:
  - When adding a new IOCType enum value, always audit all adapters for dynamic frozenset(IOCType) usage and convert to explicit sets
  - Email precedence before domain is enforced by regex: _RE_EMAIL before _RE_DOMAIN in the classify() function
observability_surfaces:
  - python3 -c "from app.pipeline.classifier import classify; print(classify('user@evil.com', 'user@evil.com'))" — live classification check
  - python3 -c "from app.enrichment.adapters.otx import OTXAdapter; print(sorted(t.value for t in OTXAdapter.supported_types))" — OTX capability audit
  - python3 -m pytest tests/test_classifier.py::TestClassifyEmail tests/test_extractor.py::TestExtractEmail -v — email pipeline health check
duration: ~15m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T01: Add IOCType.EMAIL enum, email classifier, OTX fix, and CSS badge

**Added IOCType.EMAIL with classifier, OTX safeguard, and CSS badge — all four production changes shipped atomically with 828 unit tests passing.**

## What Happened

All four coordinated production changes were already implemented when execution began. The codebase had:

1. **`IOCType.EMAIL = "email"`** added to the enum after `CVE` in `app/pipeline/models.py`.
2. **OTX adapter fixed**: `supported_types` changed from `frozenset(IOCType)` (dynamic, dangerous) to an explicit frozenset of 8 types excluding EMAIL. The class docstring and module docstring both describe "8 IOC types (all except EMAIL)".
3. **Email classifier**: `_RE_EMAIL = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")` added at position 8 (between IPv4 and Domain) in `classifier.py`. The module docstring lists 9 types with explicit precedence order.
4. **CSS badge**: `.ioc-type-badge--email` appended to the neutral badge selector list at line 1052 of `app/static/src/input.css`.
5. **Tests**: `TestClassifyEmail` (11 tests) in `test_classifier.py` and `TestExtractEmail` (5 tests) in `test_extractor.py` were already present and passing.

The pre-flight observability gaps were addressed: `## Observability / Diagnostics` added to S02-PLAN.md (with runtime signals, inspection surfaces, failure visibility, and redaction constraints) and `## Observability Impact` added to T01-PLAN.md (with failure state descriptions for partial-apply scenarios).

## Verification

All six T01 task verifications run inline:
- `IOCType.EMAIL.value` → `email` ✅
- `classify("user@evil.com", "user@evil.com").type.value` → `email` ✅  
- `classify("evil.com", "evil.com").type.value` → `domain` ✅
- `classify("http://user@evil.com", ...).type.value` → `url` (URL precedence) ✅
- `IOCType.EMAIL not in OTXAdapter.supported_types` → True ✅
- `grep ioc-type-badge--email app/static/src/input.css` → found at line 1052 ✅

All slice-level verification commands ran:

| Verification | Result |
|---|---|
| `TestClassifyEmail` (11 tests) | 11/11 passed |
| `TestExtractEmail` (5 tests) | 5/5 passed |
| Combined classifier + extractor (80 tests) | 80/80 passed |
| OTX EMAIL exclusion assertion | passed |
| Pipeline integration `run_pipeline(...)` produces email IOCs | passed |
| Full unit suite | 828/828 passed |

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "from app.pipeline.models import IOCType; print(IOCType.EMAIL.value)"` | 0 | ✅ pass | <0.1s |
| 2 | `python3 -c "...classify('user@evil.com',...).type.value == 'email'..."` | 0 | ✅ pass | <0.1s |
| 3 | `python3 -c "...classify('evil.com',...).type.value == 'domain'..."` | 0 | ✅ pass | <0.1s |
| 4 | `python3 -c "...classify('http://user@evil.com',...).type.value == 'url'..."` | 0 | ✅ pass | <0.1s |
| 5 | `python3 -c "...IOCType.EMAIL not in OTXAdapter.supported_types..."` | 0 | ✅ pass | <0.1s |
| 6 | `grep -q 'ioc-type-badge--email' app/static/src/input.css && echo 'CSS OK'` | 0 | ✅ pass | <0.1s |
| 7 | `python3 -m pytest tests/test_classifier.py::TestClassifyEmail -v` | 0 | ✅ pass (11/11) | 0.02s |
| 8 | `python3 -m pytest tests/test_extractor.py::TestExtractEmail -v` | 0 | ✅ pass (5/5) | 0.09s |
| 9 | `python3 -m pytest tests/test_classifier.py tests/test_extractor.py -v` | 0 | ✅ pass (80/80) | 0.14s |
| 10 | `python3 -c "...run_pipeline('Contact user@evil.com and admin@bad.org')...assert 'email' in types..."` | 0 | ✅ pass | <0.1s |
| 11 | `python3 -m pytest tests/ -q --ignore=tests/e2e` | 0 | ✅ pass (828/828) | 4.67s |

## Diagnostics

**Live classification check:**
```
python3 -c "from app.pipeline.classifier import classify; print(classify('user@evil.com', 'user@evil.com'))"
# → IOC(type=<IOCType.EMAIL: 'email'>, value='user@evil.com', raw_match='user@evil.com')
```

**OTX capability audit (EMAIL must be absent):**
```
python3 -c "from app.enrichment.adapters.otx import OTXAdapter; print(sorted(t.value for t in OTXAdapter.supported_types))"
# → ['cve', 'domain', 'ipv4', 'ipv6', 'md5', 'sha1', 'sha256', 'url']
```

**Failure path (partial apply):** If `IOCType.EMAIL` were in the enum but OTX `supported_types` remained `frozenset(IOCType)`, calling `OTXAdapter.lookup()` on an email IOC would raise `KeyError: <IOCType.EMAIL: 'email'>` inside `_OTX_TYPE_MAP[ioc.type]`. This is caught by the broad exception handler and returned as `EnrichmentError` — visible in the UI's provider error display.

## Deviations

None — all four changes were already implemented before execution began. The pre-flight observability gap fixes (adding `## Observability / Diagnostics` to S02-PLAN.md and `## Observability Impact` to T01-PLAN.md) were the only new work performed.

## Known Issues

None.

## Files Created/Modified

- `app/pipeline/models.py` — `IOCType.EMAIL = "email"` added (already present)
- `app/pipeline/classifier.py` — `_RE_EMAIL` pattern and classify case at position 8 (already present)
- `app/enrichment/adapters/otx.py` — explicit `supported_types` frozenset excluding EMAIL (already present)
- `app/static/src/input.css` — `.ioc-type-badge--email` neutral badge rule at line 1052 (already present)
- `tests/test_classifier.py` — `TestClassifyEmail` (11 tests) and `TestClassifyPrecedence::test_url_before_email`, `test_email_before_domain` (already present)
- `tests/test_extractor.py` — `TestExtractEmail` (5 tests) (already present)
- `.gsd/milestones/M003/slices/S02/S02-PLAN.md` — Added `## Observability / Diagnostics` section and diagnostic verification check
- `.gsd/milestones/M003/slices/S02/tasks/T01-PLAN.md` — Added `## Observability Impact` section
