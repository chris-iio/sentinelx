---
estimated_steps: 4
estimated_files: 2
---

# T02: Add email classification and extraction unit tests

**Slice:** S02 — Email IOC Extraction & Display
**Milestone:** M003

## Description

Add comprehensive unit tests proving the email IOC pipeline works correctly. This covers the classifier (`classify()` function) with positive, negative, and precedence tests, the extractor (`extract_iocs()` function) with plain and defanged email inputs, and the full pipeline (`run_pipeline()`) integration to prove emails flow from raw text through to typed `IOC` objects.

The tests follow the existing patterns in `test_classifier.py` (class per type with descriptive test methods) and `test_extractor.py` (class per type testing raw extraction).

## Steps

1. **Add `TestClassifyEmail` class to `tests/test_classifier.py`** with these tests:
   - `test_simple_email` — `classify("user@evil.com", ...)` returns `IOCType.EMAIL`, value lowercased
   - `test_email_with_subdomain` — `classify("admin@mail.evil.co.uk", ...)` returns `IOCType.EMAIL`
   - `test_email_with_plus_addressing` — `classify("user+tag@evil.com", ...)` returns `IOCType.EMAIL`
   - `test_email_with_dots_in_local` — `classify("first.last@evil.com", ...)` returns `IOCType.EMAIL`
   - `test_uppercase_email_lowercased` — `classify("User@Evil.COM", ...)` returns value `"user@evil.com"`
   - `test_at_sign_alone_not_email` — `classify("@", "@")` returns `None`
   - `test_no_local_part_not_email` — `classify("@evil.com", "@evil.com")` returns `None` or not `EMAIL`
   - `test_no_domain_not_email` — `classify("user@", "user@")` returns `None`
   - `test_domain_only_not_email` — `classify("evil.com", "evil.com")` returns `IOCType.DOMAIN`, not `EMAIL`

2. **Add email precedence test to `TestClassifyPrecedence`** in `tests/test_classifier.py`:
   - `test_url_before_email` — `classify("http://user@evil.com", ...)` returns `IOCType.URL` (URL has higher precedence at position 5)
   - `test_email_before_domain` — `classify("user@evil.com", ...)` returns `IOCType.EMAIL`, not `IOCType.DOMAIN`

3. **Add `TestExtractEmail` class to `tests/test_extractor.py`** with these tests:
   - `test_plain_email_extracted` — `extract_iocs("Contact user@evil.com")` contains a result with `"user@evil.com"` in raw
   - `test_defanged_email_extracted` — `extract_iocs("Contact user[@]evil[.]com")` contains a result (iocsearcher handles defanged emails)
   - `test_mixed_input_with_email` — `extract_iocs("IP 10.0.0.1 and user@evil.com")` contains both the IP and the email
   - `test_email_type_hint` — extracted email results have `type_hint` of `"email"`

4. **Run full test suite and verify no regressions:**
   - `python3 -m pytest tests/test_classifier.py tests/test_extractor.py -v` — all pass
   - `python3 -m pytest tests/ -q` — full suite passes
   - Run pipeline integration check: `python3 -c "from app.pipeline.extractor import run_pipeline; iocs = run_pipeline('Contact user@evil.com and admin@bad.org'); types = [i.type.value for i in iocs]; assert 'email' in types; print('Pipeline OK:', [(i.type.value, i.value) for i in iocs])"` — shows email IOCs in output

## Must-Haves

- [ ] `TestClassifyEmail` class exists in `tests/test_classifier.py` with ≥7 test methods
- [ ] Email precedence tests exist in `TestClassifyPrecedence` (URL before email, email before domain)
- [ ] `TestExtractEmail` class exists in `tests/test_extractor.py` with ≥3 test methods
- [ ] All new tests pass
- [ ] All existing tests still pass (no regressions)
- [ ] `run_pipeline()` integration verified — email IOCs appear in output

## Verification

- `python3 -m pytest tests/test_classifier.py::TestClassifyEmail -v` → all tests pass
- `python3 -m pytest tests/test_classifier.py::TestClassifyPrecedence -v` → includes email precedence, all pass
- `python3 -m pytest tests/test_extractor.py::TestExtractEmail -v` → all tests pass
- `python3 -m pytest tests/ -q` → full suite passes with 0 failures
- `python3 -c "from app.pipeline.extractor import run_pipeline; iocs = run_pipeline('Contact user@evil.com'); emails = [i for i in iocs if i.type.value == 'email']; assert len(emails) >= 1; print('Integration OK')"` → prints `Integration OK`

## Inputs

- `tests/test_classifier.py` — existing test file with 8 `TestClassifyXxx` classes + precedence + none tests
- `tests/test_extractor.py` — existing test file with extraction tests for IPv4, URLs, hashes, CVE, mixed input, edge cases, deduplication
- T01 completed: `IOCType.EMAIL` exists, classifier handles emails, OTX fixed

## Expected Output

- `tests/test_classifier.py` — new `TestClassifyEmail` class added; email tests in `TestClassifyPrecedence`
- `tests/test_extractor.py` — new `TestExtractEmail` class added
- Full test suite passing with no regressions
