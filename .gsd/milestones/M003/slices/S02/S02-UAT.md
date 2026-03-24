# S02: Email IOC Extraction & Display — UAT

**Milestone:** M003
**Written:** 2026-03-21

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S02 is fully verified by unit tests (classifier + extractor) and E2E tests (card render + filter pill behavior). The email extraction logic is deterministic and covered by 16 unit tests. The 6 E2E tests run in a real Chromium browser against the actual app. No human-perceptible design behavior needs visual inspection (emails render with the same neutral badge style as all other IOC types). R016 requires the EMAIL group appears and filters correctly — both are proved by E2E.

## Preconditions

1. Flask dev server is running (`flask run` or equivalent) — E2E tests start their own server via conftest.py fixtures.
2. Playwright browsers installed (`playwright install chromium`).
3. Python dependencies installed (`pip install -r requirements.txt`).
4. No VT API key required — all E2E tests use offline mode.

## Smoke Test

```bash
python3 -c "
from app.pipeline.extractor import run_pipeline
iocs = run_pipeline('Contact attacker@evil.com about the incident')
types = [i.type.value for i in iocs]
assert 'email' in types, f'email not found in: {types}'
print('EMAIL pipeline OK — got:', types)
"
```

Expected output: `EMAIL pipeline OK — got: ['email']` (or with domain if defanged form present).

## Test Cases

### 1. Email classification — unit level

```bash
python3 -m pytest tests/test_classifier.py::TestClassifyEmail -v
```

**Expected:** 11/11 tests pass. Confirms: plain email → EMAIL, email with subdomain → EMAIL, plus-address → EMAIL, uppercase lowercased, domain-only → not EMAIL, `@` alone → not EMAIL, URL with `@` → URL (precedence), email before domain in classifier order.

### 2. Email extraction from mixed input — unit level

```bash
python3 -m pytest tests/test_extractor.py::TestExtractEmail -v
```

**Expected:** 5/5 tests pass. Confirms: plain email extracted, defanged `user[@]evil[.]com` extracted, mixed input (email + IP + domain) all extracted, deduplication works, type hint is `IOCType.EMAIL`.

### 3. OTX adapter does not support EMAIL

```bash
python3 -c "
from app.enrichment.adapters.otx import OTXAdapter
from app.pipeline.models import IOCType
assert IOCType.EMAIL not in OTXAdapter.supported_types
print('OTX supported_types:', sorted(t.value for t in OTXAdapter.supported_types))
"
```

**Expected:** Assertion passes. Output shows 8 types: `['cve', 'domain', 'ipv4', 'ipv6', 'md5', 'sha1', 'sha256', 'url']` — EMAIL is absent.

### 4. EMAIL IOC card renders in results page — E2E

```bash
python3 -m pytest tests/e2e/test_results_page.py::test_email_ioc_card_renders -v
```

**Expected:** PASSED. At least 1 `.ioc-card[data-ioc-type="email"]` is present after submitting text containing `attacker@evil.com`.

### 5. EMAIL filter pill appears in filter bar — E2E

```bash
python3 -m pytest tests/e2e/test_results_page.py::test_email_filter_pill_exists -v
```

**Expected:** PASSED. `.filter-pill--email` is visible in the filter bar with text "EMAIL".

### 6. EMAIL filter pill filters cards correctly — E2E

```bash
python3 -m pytest tests/e2e/test_results_page.py::test_email_filter_pill_shows_only_email_cards -v
```

**Expected:** PASSED. After clicking the EMAIL pill, all visible cards have `data-ioc-type="email"`. Non-email cards are hidden.

### 7. EMAIL filter active state and reset — E2E

```bash
python3 -m pytest tests/e2e/test_results_page.py -v -k "email_filter_pill_active or all_types_pill_resets_after_email"
```

**Expected:** Both tests PASSED. Active state: `.filter-pill--email.filter-pill--active` is visible when EMAIL is selected. Reset: card count restores to pre-filter total after clicking "All Types".

### 8. Email badge CSS class present — E2E

```bash
python3 -m pytest tests/e2e/test_results_page.py::test_email_cards_have_neutral_type_badge -v
```

**Expected:** PASSED. `.ioc-type-badge--email` is visible inside email cards and its text content contains "EMAIL".

### 9. Full E2E suite — no regressions

```bash
python3 -m pytest tests/e2e/ -v
```

**Expected:** 105/105 passed (99 original + 6 new email tests).

### 10. Full unit suite — no regressions

```bash
python3 -m pytest tests/ -q --ignore=tests/e2e
```

**Expected:** 828 passed.

## Edge Cases

### Defanged email `user[@]evil[.]com`

Submit only: `user[@]evil[.]com`

**Expected behavior:** The domain `evil.com` is extracted (not the email address). This is a **known limitation**: iocsearcher doesn't recognize the fully-defanged form as an email candidate. Only the domain portion survives extraction. No EMAIL card appears.

This is documented as a known limitation in KNOWLEDGE.md and is acceptable for M003.

### Mixed input: email + IP + domain

Submit: `Contact attacker@evil.com about 8.8.8.8 and evil.com`

**Expected:** Three cards appear — one EMAIL, one IPV4, one DOMAIN. Filter bar shows 4 pills: "All Types", "EMAIL", "IPV4", "DOMAIN". Each type filters correctly in isolation.

### Email with plus addressing

Submit: `admin+security@company.com`

**Expected:** Classifies as EMAIL (`admin+security@company.com`). Verify:
```bash
python3 -c "from app.pipeline.classifier import classify; r = classify('admin+security@company.com', 'admin+security@company.com'); assert r.type.value == 'email'; print(r.value)"
```

### URL containing `@` sign

Submit: `http://user@evil.com/path`

**Expected:** Classifies as URL, not EMAIL (URL precedence is higher than EMAIL in classify()). Verify:
```bash
python3 -c "from app.pipeline.classifier import classify; r = classify('http://user@evil.com/path', 'http://user@evil.com/path'); assert r.type.value == 'url'; print(r.type.value)"
```

## Failure Signals

- `KeyError: <IOCType.EMAIL: 'email'>` in OTX adapter logs → OTX `supported_types` was accidentally set to `frozenset(IOCType)` again (not explicit set). Run OTX assertion from Test Case 3.
- Email card renders with wrong badge type (e.g., `data-ioc-type="domain"`) → Email classifier is placed after Domain regex in `classifier.py`. Check position 8 in the classify() if/elif chain.
- `.filter-pill--email` not visible after submitting email text → Either no email IOC was extracted (check pipeline smoke test) or Jinja's `grouped.keys()` doesn't include EMAIL (check that `IOCType.EMAIL` is in the enum).
- Badge text color is bright/colored rather than muted → `.ioc-type-badge--email` is missing from the neutral selector group in `dist/style.css`. Check: `grep 'badge--email' app/static/dist/style.css`.
- E2E tests skip or collect 0 for `-k email` → Tests don't exist in `test_results_page.py` or the function names changed. Run `grep -n 'def test_email' tests/e2e/test_results_page.py`.

## Not Proven By This UAT

- **Live enrichment suppression for EMAIL**: Unit tests confirm EMAIL is excluded from OTX `supported_types`, and no other adapters are wired for email. But a live run (online mode with API key) confirming zero provider calls for an email IOC was not performed. Risk is low — adapter exclusion is enforced at the orchestrator level by `adapter.supported_types` check.
- **Defanged email recovery**: No UAT case proves `user[@]evil[.]com` can be extracted as an email. This requires a custom pre-extraction normalization pass and is deferred.
- **Email IOC on detail page**: The detail page for an email IOC was not tested (email IOCs have no enrichment, so the detail page would show empty sections). S03 covers detail page design only for enriched types.

## Notes for Tester

- All E2E tests use offline mode — no API key or network access required.
- The `EMAIL_IOC_TEXT` fixture in `test_results_page.py` uses `"Contact attacker@evil.com or admin@phish.org about the incident."` — two emails + sentence words. Only email IOCs are extracted (no IPs or domains in this text beyond the email domains embedded in the addresses themselves).
- Email badge styling is intentionally neutral (same muted color as all other non-verdict elements) — don't expect a distinctive email color. R003 explicitly requires verdict is the only loud color.
- The `make css` command fails because `./tools/tailwindcss` binary is not installed. The dist CSS was manually patched. If you need to rebuild CSS for any reason, run `make tailwind-install` first.
