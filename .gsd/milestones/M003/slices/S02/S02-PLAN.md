# S02: Email IOC Extraction & Display

**Goal:** Email addresses in analyst input are extracted, classified as `IOCType.EMAIL`, and displayed in results with a distinct EMAIL group — with no enrichment firing.
**Demo:** Paste text containing `user@evil[.]com` → EMAIL group appears in results page with extracted address; filter pill auto-generated; no enrichment providers triggered.

## Must-Haves

- `IOCType.EMAIL = "email"` added to the enum in `app/pipeline/models.py`
- Email regex and classify case added to `app/pipeline/classifier.py` at position 8 (between IPv4 and Domain)
- OTX adapter's `supported_types` changed from `frozenset(IOCType)` to explicit list (prevents `KeyError` on EMAIL)
- `.ioc-type-badge--email` CSS rule added to `app/static/src/input.css`
- Unit tests for email classification (positive, negative, precedence vs URL/domain)
- Unit tests for email extraction from mixed input via `extract_iocs()`
- Pipeline integration verified: `run_pipeline()` returns `IOCType.EMAIL` IOCs

## Proof Level

- This slice proves: contract (classifier correctly identifies emails; pipeline flows them through)
- Real runtime required: no (unit tests + pipeline integration test sufficient)
- Human/UAT required: no

## Observability / Diagnostics

**Runtime signals:**
- `IOCType.EMAIL` surfaces in the results page under a dedicated EMAIL group (Jinja template renders it dynamically via `grouped.items()`).
- The `provider_counts` dict emits `"email": 0` in the enrichment summary — zero is correct and expected; no providers support email.
- `run_pipeline()` logs are the primary observability surface: any email IOC that passes through will appear in the returned list with `type=IOCType.EMAIL`.

**Inspection surface:**
- `python3 -c "from app.pipeline.models import IOCType; print(list(IOCType))"` — confirms EMAIL is in the enum.
- `python3 -c "from app.enrichment.adapters.otx import OTXAdapter; print(OTXAdapter.supported_types)"` — confirms EMAIL is absent from OTX supported types.
- `python3 -c "from app.pipeline.extractor import run_pipeline; iocs = run_pipeline('user@evil.com'); print(iocs)"` — inspect live pipeline output.

**Failure visibility:**
- If `IOCType.EMAIL` is added to the enum but OTX `supported_types` remains `frozenset(IOCType)`, the OTX adapter's `lookup()` will raise `KeyError: <IOCType.EMAIL: 'email'>` when it hits `_OTX_TYPE_MAP[ioc.type]`. This is caught by the broad `except Exception` block and returned as `EnrichmentError`, surfaced to the user as provider error text in the UI.
- If the email classifier case is omitted or placed after the domain case, `user@evil.com` will misclassify as DOMAIN. The `TestClassifyEmail::test_email_before_domain_in_precedence` test catches this.

**Redaction constraints:**
- Email addresses in analyst input may be sensitive (victim addresses). The pipeline stores them in `IOC.raw_match` and `IOC.value` — these values are only rendered via Jinja2 autoescaping (`{{ var }}`), never via `| safe`. No logging of IOC values occurs in the classifier or extractor.

## Verification

- `python3 -m pytest tests/test_classifier.py::TestClassifyEmail -v` — all email classification tests pass
- `python3 -m pytest tests/test_extractor.py::TestExtractEmail -v` — email extraction tests pass
- `python3 -m pytest tests/test_classifier.py tests/test_extractor.py -v` — all existing + new tests pass
- `python3 -c "from app.pipeline.models import IOCType; from app.enrichment.adapters.otx import OTXAdapter; assert IOCType.EMAIL not in OTXAdapter.supported_types"` — OTX does not claim email support
- `python3 -c "from app.pipeline.extractor import run_pipeline; iocs = run_pipeline('Contact user@evil.com and admin@bad.org'); types = [i.type.value for i in iocs]; assert 'email' in types; print('EMAIL pipeline OK')"` — pipeline produces email IOCs
- `python3 -m pytest tests/ -q` — full test suite passes (no regressions)
- `python3 -c "from app.enrichment.adapters.otx import OTXAdapter; from app.pipeline.models import IOCType; t = OTXAdapter.supported_types; assert IOCType.EMAIL not in t; print(f'OTX supported_types has {len(t)} types, EMAIL absent — correct')"` — diagnostic: OTX adapter explicitly excludes EMAIL, confirming the KeyError failure path is closed

## Tasks

- [x] **T01: Add IOCType.EMAIL enum, email classifier, OTX fix, and CSS badge** `est:25m`
  - Why: This is the complete production code change for email IOC support. The enum, classifier, OTX fix, and CSS badge must all ship together — adding EMAIL to the enum without fixing OTX would crash the adapter with `KeyError`.
  - Files: `app/pipeline/models.py`, `app/pipeline/classifier.py`, `app/enrichment/adapters/otx.py`, `app/static/src/input.css`
  - Do: (1) Add `EMAIL = "email"` to `IOCType` enum after `CVE`. (2) In `classifier.py`, add compiled regex `_RE_EMAIL = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")` and a classify case at position 8 (between IPv4 and Domain) returning `IOC(type=IOCType.EMAIL, value=v.lower(), raw_match=raw_match)`. (3) In `otx.py` line 85, replace `frozenset(IOCType)` with explicit `frozenset({IOCType.IPV4, IOCType.IPV6, IOCType.DOMAIN, IOCType.URL, IOCType.MD5, IOCType.SHA1, IOCType.SHA256, IOCType.CVE})`. (4) In `input.css`, append `,\n    .ioc-type-badge--email` to the neutral badge selector list (lines 1044-1051).
  - Verify: `python3 -c "from app.pipeline.models import IOCType; print(IOCType.EMAIL)"` succeeds; `python3 -c "from app.pipeline.classifier import classify; r = classify('user@evil.com', 'user@evil.com'); assert r.type.value == 'email'"` succeeds; `python3 -c "from app.enrichment.adapters.otx import OTXAdapter; from app.pipeline.models import IOCType; assert IOCType.EMAIL not in OTXAdapter.supported_types"` succeeds
  - Done when: EMAIL enum exists, classifier returns IOCType.EMAIL for valid emails, OTX adapter excludes EMAIL from supported_types, CSS badge rule covers email

- [x] **T02: Add email classification and extraction unit tests** `est:20m`
  - Why: Proves the email pipeline works end-to-end with comprehensive positive/negative/precedence tests and integration verification through `run_pipeline()`.
  - Files: `tests/test_classifier.py`, `tests/test_extractor.py`
  - Do: (1) Add `TestClassifyEmail` class to `test_classifier.py` with tests: simple email, email with subdomains, email with plus addressing, uppercase email lowercased, domain-only string not classified as email, `@` alone not email, URL with `@` classified as URL not email. (2) Add email precedence test to `TestClassifyPrecedence`: email vs domain (email wins for `user@evil.com`). (3) Add `TestExtractEmail` class to `test_extractor.py` with tests: plain email extracted, defanged email `user[@]evil[.]com` extracted, mixed input with email + IP + domain, email deduplication. (4) Run full test suite to confirm no regressions.
  - Verify: `python3 -m pytest tests/test_classifier.py tests/test_extractor.py -v` — all tests pass; `python3 -m pytest tests/ -q` — full suite passes
  - Done when: All new email tests pass, all existing tests still pass, `run_pipeline()` integration test confirms emails flow through the pipeline

## Files Likely Touched

- `app/pipeline/models.py`
- `app/pipeline/classifier.py`
- `app/enrichment/adapters/otx.py`
- `app/static/src/input.css`
- `tests/test_classifier.py`
- `tests/test_extractor.py`
