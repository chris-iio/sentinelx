---
id: S02
parent: M003
milestone: M003
provides:
  - IOCType.EMAIL = "email" enum value in app/pipeline/models.py
  - Email regex classifier at precedence position 8 (before Domain) in app/pipeline/classifier.py
  - OTX adapter explicit frozenset excluding EMAIL in app/enrichment/adapters/otx.py
  - .ioc-type-badge--email CSS rule in app/static/src/input.css and app/static/dist/style.css
  - .filter-pill--email.filter-pill--active CSS rule in app/static/src/input.css and app/static/dist/style.css
  - 11 TestClassifyEmail tests + 5 TestExtractEmail tests in unit test suite
  - 6 E2E tests in tests/e2e/test_results_page.py proving EMAIL group renders and filter pill works
requires: []
affects:
  - S04
key_files:
  - app/pipeline/models.py
  - app/pipeline/classifier.py
  - app/enrichment/adapters/otx.py
  - app/static/src/input.css
  - app/static/dist/style.css
  - tests/test_classifier.py
  - tests/test_extractor.py
  - tests/e2e/test_results_page.py
key_decisions:
  - Email classifier must be at position 8 (before Domain) — user@evil.com would misclassify as DOMAIN otherwise
  - OTX supported_types must be explicit frozenset — frozenset(IOCType) would cause KeyError on EMAIL lookup
  - No enrichment adapters for EMAIL — display-only by design (D026, D028)
  - dist/style.css patched manually when tailwindcss CLI is unavailable — both badge and pill selectors injected directly
patterns_established:
  - When adding a new IOCType, audit all adapters for frozenset(IOCType) dynamic usage and convert to explicit sets
  - Email precedence before Domain enforced by _RE_EMAIL before _RE_DOMAIN in classify()
  - Filter pills auto-generate from grouped.keys() in _filter_bar.html — no template changes needed for new IOC types
  - dist/style.css must be patched when tailwindcss CLI is absent; use Python string replacement on known selector patterns
  - Playwright compound CSS selector (.cls1.cls2 is_visible) preferred over to_have_class() for multi-class assertions
observability_surfaces:
  - python3 -m pytest tests/test_classifier.py::TestClassifyEmail tests/test_extractor.py::TestExtractEmail -v
  - python3 -c "from app.pipeline.classifier import classify; print(classify('user@evil.com', 'user@evil.com'))"
  - python3 -c "from app.enrichment.adapters.otx import OTXAdapter; print(sorted(t.value for t in OTXAdapter.supported_types))"
  - python3 -m pytest tests/e2e/test_results_page.py -v -k email
drill_down_paths:
  - .gsd/milestones/M003/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M003/slices/S02/tasks/T02-SUMMARY.md
duration: ~30m
verification_result: passed
completed_at: 2026-03-21
---

# S02: Email IOC Extraction & Display

**Email addresses in analyst input are now extracted as IOCType.EMAIL, displayed under a dedicated EMAIL filter group in the results page, with a neutral type badge — and no enrichment fires.**

## What Happened

**T01** implemented all four production changes atomically:

1. `IOCType.EMAIL = "email"` added to the enum after `CVE` in `app/pipeline/models.py`.
2. Email classifier: `_RE_EMAIL = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")` added at position 8 in `classifier.py` — between IPv4 and Domain. This ensures `user@evil.com` classifies as EMAIL before the Domain regex sees it.
3. OTX adapter safeguard: `supported_types` changed from `frozenset(IOCType)` (dynamic, would auto-include EMAIL and crash on lookup) to an explicit frozenset of 8 types excluding EMAIL.
4. CSS badge: `.ioc-type-badge--email` appended to the neutral badge selector list in `input.css`.

T01 also confirmed 828 unit tests passing including 11 `TestClassifyEmail` and 5 `TestExtractEmail` tests.

**T02** added the CSS active pill selector and E2E tests — but the task summary's verification claims were false: the changes had not been applied to the worktree when the summary was written. The closer applied the three missing items:

1. Added `.filter-pill--email.filter-pill--active` to the neutral active pill selector list in `input.css`.
2. Patched `app/static/dist/style.css` directly (tailwindcss CLI binary absent) — both `.ioc-type-badge--email` and `.filter-pill--email.filter-pill--active` injected into existing selector groups.
3. Added 6 E2E tests to `tests/e2e/test_results_page.py` under "Email IOC rendering (R016)":
   - `test_email_ioc_card_renders` — at least 1 `.ioc-card[data-ioc-type="email"]` after submitting email text
   - `test_email_filter_pill_exists` — `.filter-pill--email` visible in filter bar
   - `test_email_filter_pill_shows_only_email_cards` — all visible cards are email type after filtering
   - `test_email_filter_pill_active_state` — `.filter-pill--email.filter-pill--active` visible when active
   - `test_all_types_pill_resets_after_email_filter` — card count restores to pre-filter total
   - `test_email_cards_have_neutral_type_badge` — `.ioc-type-badge--email` is visible with "EMAIL" text

The filter pill generation is entirely automatic: `_filter_bar.html` iterates `grouped.keys()` and generates a pill for every IOC type present in results. No template changes were needed.

## Verification

| Check | Result |
|---|---|
| `TestClassifyEmail` (11 tests) | 11/11 passed |
| `TestExtractEmail` (5 tests) | 5/5 passed |
| Full unit suite (828 tests) | 828/828 passed |
| OTX EMAIL exclusion assertion | passed |
| Pipeline smoke: `run_pipeline('Contact user@evil.com and admin@bad.org')` produces email IOCs | passed |
| E2E email tests (6 tests) | 6/6 passed |
| Full E2E suite (105 tests) | 105/105 passed |
| `.ioc-type-badge--email` in input.css and dist/style.css | confirmed |
| `.filter-pill--email.filter-pill--active` in input.css and dist/style.css | confirmed |

## New Requirements Surfaced

- None.

## Deviations

- **T02 code changes missing at time of summary**: The T02 task summary reported all changes as verified and complete, but `.filter-pill--email.filter-pill--active` was not in input.css, dist/style.css had not been rebuilt, and 0 E2E tests existed. The closer applied all three missing items. This matches the KNOWLEDGE.md pattern ("Task summary files may be written before code changes are applied to the worktree").

- **tailwindcss CLI absent**: The `make css` command requires `./tools/tailwindcss` binary which is not present in the worktree. Instead of attempting to install the binary, dist/style.css was patched directly via Python string replacement on the known selector patterns. This is safe for stable utility CSS output but means the dist may diverge from input.css if new Tailwind utility classes are added in future slices.

## Known Limitations

- **Fully-defanged email form** (`user[@]evil[.]com`): iocsearcher does not extract this form as an email address — only the domain `evil.com` is extracted. Plain `user@evil.com` is reliably extracted. This is a known limitation documented in KNOWLEDGE.md and accepted for this milestone.

- **tailwindcss CLI binary missing**: Future slices that need CSS rebuilds must either install the binary (`make tailwind-install`) or continue with direct dist patching.

## Follow-ups

- S04 should confirm the full E2E suite passes with the 6 new email tests counted in the ≥99 gate (now at 105 total).
- If tailwindcss CLI is needed in S03 or S04, install with `make tailwind-install` before running `make css`.
- Email enrichment adapters (EmailRep, Spamhaus) are out of scope for M003 — tracked in D026.

## Files Created/Modified

- `app/pipeline/models.py` — `IOCType.EMAIL = "email"` added
- `app/pipeline/classifier.py` — `_RE_EMAIL` pattern and classify case at position 8
- `app/enrichment/adapters/otx.py` — explicit `supported_types` frozenset excluding EMAIL
- `app/static/src/input.css` — `.ioc-type-badge--email` and `.filter-pill--email.filter-pill--active` selectors added
- `app/static/dist/style.css` — both email selectors patched into minified output
- `tests/test_classifier.py` — `TestClassifyEmail` (11 tests) + precedence tests
- `tests/test_extractor.py` — `TestExtractEmail` (5 tests)
- `tests/e2e/test_results_page.py` — 6 email IOC rendering and filtering E2E tests

## Forward Intelligence

### What the next slice should know
- The E2E suite is now at 105 tests. The M003 milestone DoD says "≥ 99 E2E tests" — S04's gate needs to verify 105+ pass, not just 99.
- `_filter_bar.html` auto-generates pills from `grouped.keys()` — adding a new IOCType requires only the model + classifier change, not template changes.
- dist/style.css was last rebuilt March 20 04:34 and then manually patched. If S03 or S04 adds new CSS that requires a full rebuild, install `./tools/tailwindcss` with `make tailwind-install` first.

### What's fragile
- **dist/style.css manual patch** — the minified CSS was patched with Python string replacement. If the surrounding selector text changes (e.g., a new IOC type badge is added before "email" alphabetically), the replacement string won't match and the patch will silently fail. The source of truth remains `input.css`.
- **Email classifier position** — `_RE_EMAIL` must remain before `_RE_DOMAIN` in `classify()`. If someone reorders the classifier cases, `user@evil.com` will classify as DOMAIN. The `test_email_before_domain_in_precedence` test catches this.

### Authoritative diagnostics
- `python3 -m pytest tests/e2e/test_results_page.py -v -k email` — 6 tests, definitive proof of EMAIL group rendering
- `python3 -c "from app.pipeline.classifier import classify; print(classify('user@evil.com', 'user@evil.com'))"` — live classification check
- `grep 'badge--email\|pill--email' app/static/dist/style.css` — confirms both selectors in dist

### What assumptions changed
- T02 plan assumed tailwindcss would be available via `make css` — it isn't. The binary must be explicitly installed.
- T02 plan assumed filter pill generation needed a template change — it doesn't. The template already iterates `grouped.keys()` dynamically.
- T02's verification table showed all checks as passing before the code was written — don't trust task summary verification tables without re-running the checks independently.
