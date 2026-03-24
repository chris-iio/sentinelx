---
estimated_steps: 4
estimated_files: 4
---

# T01: Add IOCType.EMAIL enum, email classifier, OTX fix, and CSS badge

**Slice:** S02 — Email IOC Extraction & Display
**Milestone:** M003

## Description

Add full production code support for email IOC extraction. This is four coordinated changes that must ship together: the enum value, the classifier case, the OTX adapter fix, and the CSS badge variant. Adding EMAIL to IOCType without fixing OTX would crash the OTX adapter with a `KeyError` because OTX uses `frozenset(IOCType)` which dynamically includes all enum values, and `_OTX_TYPE_MAP` has no `EMAIL` key.

No template changes are needed — the results page Jinja templates already loop dynamically over `grouped.keys()` for type pills and `grouped.items()` for IOC cards. The IOC card template uses `ioc.type.value` dynamically for the badge CSS class.

No normalizer changes needed — it already handles `[@]` → `@`, `(@)` → `@`, `[at]` → `@`.

No extractor changes needed — iocsearcher already emits `name=email` for email addresses.

No routes.py changes needed — `provider_counts` will emit `"email": 0` which is harmless (no providers support email enrichment, so 0 is correct).

## Steps

1. **Add `EMAIL = "email"` to `IOCType` enum** in `app/pipeline/models.py`. Add it after `CVE = "cve"` (line 30). No other changes needed in this file — `group_by_type()` and the `IOC` dataclass are generic over the enum.

2. **Fix OTX adapter `supported_types`** in `app/enrichment/adapters/otx.py`. Replace line 85:
   ```python
   supported_types: frozenset[IOCType] = frozenset(IOCType)  # ALL enum values
   ```
   with:
   ```python
   supported_types: frozenset[IOCType] = frozenset({
       IOCType.IPV4, IOCType.IPV6, IOCType.DOMAIN, IOCType.URL,
       IOCType.MD5, IOCType.SHA1, IOCType.SHA256, IOCType.CVE,
   })
   ```
   This must happen in the same task as adding the enum value. Update the class docstring and module docstring accordingly — change "Supports all 8 IOC types" to "Supports all IOC types except EMAIL" or similar.

3. **Add email regex and classify case** in `app/pipeline/classifier.py`:
   - Add compiled regex near the other patterns:
     ```python
     _RE_EMAIL = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
     ```
   - Add classify case at position 8 (between IPv4 check at position 7 and Domain check at position 8). The current Domain check is at position 8 — email must come BEFORE domain because `evil.com` in `user@evil.com` would match the domain regex if the email isn't caught first. Insert between the IPv4 block and the Domain block:
     ```python
     # 8. Email
     if _RE_EMAIL.match(v):
         return IOC(type=IOCType.EMAIL, value=v.lower(), raw_match=raw_match)
     ```
   - Renumber Domain to position 9 in the comment.
   - Update the module docstring and `classify()` docstring to reflect 9 types and the new precedence order.

4. **Add CSS badge variant** in `app/static/src/input.css`. The neutral badge rule at lines 1044-1051 lists all IOC type badge variants. Append `.ioc-type-badge--email` to the selector list:
   ```css
   .ioc-type-badge--ipv4,
   .ioc-type-badge--ipv6,
   .ioc-type-badge--domain,
   .ioc-type-badge--url,
   .ioc-type-badge--md5,
   .ioc-type-badge--sha1,
   .ioc-type-badge--sha256,
   .ioc-type-badge--cve,
   .ioc-type-badge--email    { color: var(--text-muted); border-color: var(--border-default); }
   ```

## Must-Haves

- [ ] `IOCType.EMAIL` exists with value `"email"`
- [ ] OTX `supported_types` is an explicit frozenset NOT containing `IOCType.EMAIL`
- [ ] `classify("user@evil.com", "user@evil.com")` returns `IOC(type=IOCType.EMAIL, ...)`
- [ ] `classify("evil.com", "evil.com")` still returns `IOC(type=IOCType.DOMAIN, ...)`
- [ ] `classify("http://user@evil.com/path", ...)` returns `IOC(type=IOCType.URL, ...)` (URL precedence)
- [ ] `.ioc-type-badge--email` CSS rule exists in `input.css`

## Verification

- `python3 -c "from app.pipeline.models import IOCType; print(IOCType.EMAIL.value)"` → prints `email`
- `python3 -c "from app.pipeline.classifier import classify; r = classify('user@evil.com', 'user@evil.com'); assert r is not None and r.type.value == 'email' and r.value == 'user@evil.com'; print('OK')"` → prints `OK`
- `python3 -c "from app.pipeline.classifier import classify; r = classify('evil.com', 'evil.com'); assert r.type.value == 'domain'; print('Domain OK')"` → prints `Domain OK`
- `python3 -c "from app.pipeline.classifier import classify; r = classify('http://user@evil.com', 'http://user@evil.com'); assert r.type.value == 'url'; print('URL precedence OK')"` → prints `URL precedence OK`
- `python3 -c "from app.enrichment.adapters.otx import OTXAdapter; from app.pipeline.models import IOCType; assert IOCType.EMAIL not in OTXAdapter.supported_types; print('OTX OK')"` → prints `OTX OK`
- `grep -q 'ioc-type-badge--email' app/static/src/input.css && echo 'CSS OK'` → prints `CSS OK`

## Observability Impact

**Signals changed by this task:**
- `IOCType.EMAIL` is now a valid enum member — any code that iterates `list(IOCType)` will include it.
- `OTXAdapter.supported_types` changes from a dynamic `frozenset(IOCType)` (all values) to an explicit frozenset of 8 types. Inspecting it now gives an accurate capability declaration with EMAIL absent.
- The classifier's `_RE_EMAIL` pattern and position-8 branch are new code paths. A future agent can verify these are active by calling `classify("user@evil.com", "user@evil.com")` and asserting `result.type == IOCType.EMAIL`.

**Inspection surface:**
- `python3 -c "from app.pipeline.classifier import classify; print(classify('user@evil.com', 'user@evil.com'))"` — confirms live classification path.
- `python3 -c "from app.enrichment.adapters.otx import OTXAdapter; print(sorted(t.value for t in OTXAdapter.supported_types))"` — lists OTX capabilities; EMAIL must be absent.

**Failure state visibility:**
- If this task is partially applied (enum added, OTX not fixed): importing `OTXAdapter` and calling `lookup()` on any email IOC raises `KeyError` inside `lookup()`, caught by the broad exception handler and surfaced as `EnrichmentError`. Observable via the UI's provider error display or unit test failure in `TestClassifyEmail`.
- If the email classifier position is wrong (after domain): `TestClassifyEmail::test_email_before_domain_in_precedence` fails with `AssertionError` — the result type will be `IOCType.DOMAIN`.

**No new log statements introduced** — classifier is a pure function; observability is via test assertions and Python REPL inspection.

## Inputs

- `app/pipeline/models.py` — current `IOCType` enum with 8 values (IPV4 through CVE)
- `app/pipeline/classifier.py` — current classifier with 8 precedence positions
- `app/enrichment/adapters/otx.py` — line 85 uses `frozenset(IOCType)` for `supported_types`
- `app/static/src/input.css` — lines 1044-1051 list all type badge CSS selectors

## Expected Output

- `app/pipeline/models.py` — `IOCType` enum has 9 values including `EMAIL = "email"`
- `app/pipeline/classifier.py` — 9-position classifier with email at position 8 (before domain at 9)
- `app/enrichment/adapters/otx.py` — explicit `supported_types` frozenset with 8 types (no EMAIL)
- `app/static/src/input.css` — `.ioc-type-badge--email` included in neutral badge selector
