---
id: M003
provides:
  - Per-provider concurrency semaphore dict in EnrichmentOrchestrator (VT capped at 4, zero-auth providers run freely)
  - max_workers raised from 4 to 20 to eliminate zero-auth provider starvation
  - 429-aware exponential backoff in _do_lookup_body() — base 15s × 2^n + jitter, up to 2 retries
  - IOCType.EMAIL enum value with custom defanged-form extraction regex
  - Email classifier step 7.5 (between IPv4 and Domain) in classifier.py
  - Route guard in routes.py excludes EMAIL from provider_counts (no enrichment adapters)
  - Neutral CSS badge and filter pill for email IOCs
  - Full detail page rework (ioc_detail.html) with M002 design tokens — stacked provider cards, verdict-only color, zinc neutrals
  - SVG graph label truncation removed — full provider names and IOC values rendered
  - Wider SVG viewBox (700×450) with adjusted orbit radius and center point
  - summaryTimers debounce map in enrichment.ts — 1–2 DOM rebuilds per IOC instead of 10
key_decisions:
  - D024: Per-provider semaphore (not token-bucket) — pragmatic fix for concurrency starvation, not true rate limiting
  - D025: 429 uses exponential backoff + jitter; non-429 errors preserve existing immediate retry
  - D026/D028: Email is display-only — excluded from provider_counts until an email reputation adapter exists
  - D027: _do_lookup_body() extracted so semaphore if/else stays clean without duplicating 40-line body
  - D029: Stacked provider cards replace CSS-only radio tabs on detail page — all providers visible at once
patterns_established:
  - Per-provider semaphore pattern: getattr(adapter, 'requires_api_key', False) guards semaphore creation for backward compat
  - patch target for time.sleep in orchestrator tests is always app.enrichment.orchestrator.time.sleep
  - Email classifier positioned at step 7.5 (between IPv4 and Domain) — @-character prevents false-positive domain matches
  - Custom _RE_EMAIL_EXTRACT regex over iocextract.extract_emails() — avoids adjacent-text-gobbling bug
  - Debounce map pattern (Map<string, ReturnType<typeof setTimeout>>) now used for both sort and summary row updates in enrichment.ts
  - All graph label text passes full strings through createTextNode() — no slicing at server or client layer
  - Detail page cards use .detail-provider-card + .detail-provider-header + dl.detail-result-fields pattern
  - provider_counts route guard exclusion tuple in routes.py is canonical place to gate enrichment by type
observability_surfaces:
  - orchestrator._semaphores dict reveals which providers are gated; grep "Rate limit from" in logs for 429 pressure events
  - grep -c 'summaryTimers' app/static/src/ts/modules/enrichment.ts → ≥ 3 (declaration, get, set, delete)
  - wc -c app/static/dist/main.js → bundle size gate ≤ 30,000 bytes (actual: 26,783)
  - python3 -m pytest tests/ -q --ignore=tests/e2e → 817 passed (0 failures)
  - python3 -m pytest tests/e2e/ -q → 105 passed (0 failures)
  - make typecheck → exit 0
  - python3 -c "from app.pipeline.extractor import run_pipeline; print(run_pipeline('user[@]evil[.]com'))" → IOCType.EMAIL
  - grep 'ioc-type-badge--email' app/static/dist/style.css → selector present
requirement_outcomes:
  - id: R012
    from_status: active
    to_status: validated
    proof: ioc_detail.html fully reworked with M002 zinc design tokens; stacked provider cards; verdict-only color; no inline <style>; 13 unit tests pass including test_detail_page_with_results (asserts detail-provider-card and verdict-badge--malicious) and test_detail_graph_labels_untruncated (asserts "Shodan InternetDB" in data-graph-nodes); 105 E2E passing
  - id: R014
    from_status: active
    to_status: validated
    proof: TestPerProviderSemaphore::test_zero_auth_not_blocked_by_rate_limited_provider proves zero-auth providers run freely while VT is capped at 4 concurrent; test_rate_limited_provider_concurrency_capped proves VT semaphore cap; 22 orchestrator tests pass
  - id: R015
    from_status: active
    to_status: validated
    proof: TestBackoff429 proves 429 triggers backoff sleep (test_429_triggers_backoff_sleep), non-429 errors have no backoff (test_non_429_error_no_backoff), triple-429 exhausts retries (test_triple_429_exhausts_retries), 429-then-other stops retrying (test_429_then_non_429_error_stops_retrying); 22 orchestrator tests pass
  - id: R016
    from_status: active
    to_status: validated
    proof: 9 unit tests pass (TestClassifyEmail x5, TestExtractEmail x3, TestRunPipelineEmail x1); 6 E2E tests pass covering card rendering, filter pill visibility/active state, filtering behavior, badge CSS class; pipeline smoke confirms IOCType.EMAIL from defanged input
  - id: R017
    from_status: active
    to_status: validated
    proof: summaryTimers debounce map present in enrichment.ts (grep -c returns 4 occurrences); debouncedUpdateSummaryRow() replaces direct updateSummaryRow() call; debounce pattern identical to sortTimers (100ms, clear/set/delete lifecycle); 817 unit tests, 105 E2E tests, make typecheck all pass
duration: ~4 slices, ~2 calendar days
verification_result: passed
completed_at: 2026-03-20
---

# M003: System Efficiency & Completeness

**Per-provider concurrency, 429 backoff, email extraction, detail page design refresh, and summary row debounce — all correctness and efficiency gaps closed; 817 unit tests and 105 E2E tests passing, typecheck clean, bundle 26 KB.**

## What Happened

M003 was a correctness-and-efficiency pass across four layers of the system. All four slices delivered independently and connected cleanly at integration.

**S01 (Per-Provider Concurrency & 429 Backoff):** The root problem was a single global `max_workers=4` that serialized all 14 enrichment providers through 4 threads — zero-auth providers (Shodan, DNS, ip-api, ASN Cymru, crt.sh, Hashlookup, ThreatMiner) were artificially blocked behind VirusTotal's 4-concurrent cap. The fix was a per-provider semaphore dict keyed by adapter name: VT (and any other `requires_api_key=True` adapter) gets `Semaphore(4)`; zero-auth providers run with no gate. Global `max_workers` was raised to 20 to remove the thread-pool bottleneck. Separately, blind immediate retry on 429 errors was replaced with exponential backoff + jitter (base 15s × 2ⁿ, up to 2 retries) — non-429 errors preserve the existing immediate retry path. The inner lookup logic was extracted to `_do_lookup_body()` to keep the semaphore gate readable without duplicating the 40-line body. Seven unit tests prove VT is capped, zero-auth providers run freely, and all retry/backoff scenarios behave correctly.

**S02 (Email IOC Extraction & Display):** Email addresses were silently dropped by the classifier despite being common in phishing analyst pastes. `IOCType.EMAIL` was added to the enum, a custom `_RE_EMAIL_EXTRACT` regex was added to `extractor.py` covering clean and defanged forms (`@`, `[@]`, `(@)`, `[at]`; `[.]`, `(.)`, `[dot]`), and classifier step 7.5 was inserted between IPv4 and Domain checks. The route guard in `routes.py` excludes EMAIL from `provider_counts` (no enrichment adapters exist — D028 records this explicitly). Neutral CSS badge and filter pill were added to `input.css`. The existing Jinja type-group loop in `results.html` needed no changes — it was already generic and rendered EMAIL automatically. Nine unit tests and six E2E tests verify extraction, classification, rendering, and filter behavior end-to-end.

**S03 (Detail Page Design Refresh):** The detail page was a visual regression from the M002 results page — pre-M002 styles, truncated graph labels (12-char and 20-char slices in both Python `routes.py` and TypeScript `graph.ts`), and a fragile CSS-only radio tab pattern with an inline `<style>` block requiring Jinja-generated per-tab `:checked` selectors. The full template was rewritten with M002 design tokens (zinc surfaces, verdict-only color, consistent typography). Radio tabs were replaced with stacked provider cards — all providers visible at once with `.detail-provider-card + .detail-provider-header + dl.detail-result-fields` pattern. All label truncation was removed; the SVG viewBox was widened to 700×450 with adjusted orbit radius and smaller font-size to accommodate full provider names. Twenty-five CSS rules were added to `input.css` inside `@layer components` — no inline styles anywhere.

**S04 (Frontend Render Efficiency & Integration Verification):** `updateSummaryRow()` was being called directly on every enrichment result, causing a full DOM teardown-and-rebuild up to 10 times per IOC during streaming. The fix copied the `sortTimers` debounce pattern already in `enrichment.ts` — a `Map<string, ReturnType<typeof setTimeout>>` with 100ms delay, clear/set/delete lifecycle, and a `debouncedUpdateSummaryRow()` wrapper replacing the direct call. Two hardcoded test assertions were also corrected: OTX `supported_types` count (8→9 to reflect `IOCType.EMAIL`) and an HTML occurrence count (< 10 → < 20, where richer M002/M003 template markup produces ~12 legitimate occurrences of an IP string). All four milestone gates were confirmed: 817 unit tests, 105 E2E tests, `make typecheck` clean, bundle 26,783 bytes.

## Cross-Slice Verification

**S01 — VT semaphore cap + 429 backoff:**
- `TestPerProviderSemaphore::test_zero_auth_not_blocked_by_rate_limited_provider` — zero-auth runs freely while VT is capped ✓
- `TestPerProviderSemaphore::test_rate_limited_provider_concurrency_capped` — VT semaphore blocks at 4 concurrent ✓
- `TestBackoff429` x4 — 429 triggers backoff, non-429 no backoff, triple-429 exhausts retries, 429-then-other stops ✓
- `python3 -m pytest tests/test_orchestrator.py -q` → 22 passed ✓

**S02 — Email extraction + display:**
- `TestClassifyEmail` x5 — clean, uppercase, no-TLD, no-local-part, before-domain cases ✓
- `TestExtractEmail` x3 — clean, `[@]`, `[at]` forms ✓
- `TestRunPipelineEmail` x1 — defanged `user[@]evil[.]com` through full pipeline → `IOCType.EMAIL` ✓
- E2E x6 — card renders, filter pill exists/active, filters correctly, badge has neutral CSS class ✓

**S03 — Detail page design + graph labels:**
- `test_detail_page_with_results` — asserts `.detail-provider-card` and `.verdict-badge--malicious` present ✓
- `test_detail_graph_labels_untruncated` — asserts `"Shodan InternetDB"` in `data-graph-nodes` (17 chars, no truncation) ✓
- `grep -c '<style>' app/templates/ioc_detail.html` → 0 (no inline styles) ✓
- 13 detail route tests pass ✓

**S04 — Summary row debounce + integration:**
- `grep -c 'summaryTimers' app/static/src/ts/modules/enrichment.ts` → 4 (declaration + timer lifecycle) ✓
- `make typecheck` → exit 0 ✓
- `wc -c app/static/dist/main.js` → 26,783 bytes (≤ 30,000 gate) ✓
- `python3 -m pytest tests/ -q --ignore=tests/e2e` → 817 passed ✓
- `python3 -m pytest tests/e2e/ -q` → 105 passed ✓

## Requirement Changes

- R012: active → validated — detail page fully reworked with M002 design tokens; stacked provider cards; verdict-only color; untruncated graph labels; 13 unit tests + 105 E2E passing
- R014: active → validated — `TestPerProviderSemaphore` proves zero-auth providers unblocked while VT capped at 4 concurrent; 22 orchestrator tests pass
- R015: active → validated — `TestBackoff429` x4 proves 429 triggers backoff, non-429 preserves immediate retry; 22 orchestrator tests pass
- R016: active → validated — 9 unit tests + 6 E2E tests prove email extraction, classification, rendering, and filter behavior end-to-end; pipeline smoke confirms `IOCType.EMAIL` from defanged input
- R017: active → validated — `summaryTimers` debounce map present (grep confirms 4 occurrences); `debouncedUpdateSummaryRow()` replaces direct call; 100ms debounce matches `sortTimers` pattern; all 4 milestone gates passing

## Forward Intelligence

### What the next milestone should know
- The `provider_counts` route guard exclusion tuple in `routes.py` is the canonical place to gate enrichment by IOC type. Any new type added without an adapter should be added to the `not in (IOCType.CVE, IOCType.EMAIL)` tuple.
- The detail page now uses `@layer components` CSS rules exclusively — no inline styles. The stacked card pattern (`.detail-provider-card` + `.detail-provider-header` + `dl.detail-result-fields`) is established and reusable for any future provider fields.
- The debounce map pattern (`Map<string, ReturnType<typeof setTimeout>>` with clear/set/delete lifecycle) is now the standard for any DOM-rebuilding loop in `enrichment.ts` or `row-factory.ts`.
- The OTX adapter uses `frozenset(IOCType)` — it inherits all enum members automatically. Any test asserting `len(adapter.supported_types)` will need updating whenever a new `IOCType` member is added (happened in S04 when EMAIL was added: 8→9).
- The email classifier at step 7.5 is positioned defensively but relies on an `if/elif` chain with step numbers in docstrings. If a new type is inserted between IPv4 and Domain, verify the email step is not accidentally displaced.

### What's fragile
- `_RE_EMAIL_EXTRACT` deduplication keys by raw value — if `iocsearcher` also emits a clean email, the second `_add()` call with `type_hint="email"` overwrites the type hint silently. Correct behavior today, but could surprise future work with multiple extractors for the same IOC.
- `_RE_EMAIL_EXTRACT` does not handle curly-brace defanging (`user{at}evil.com`). Standard analyst conventions (`[@]`, `[at]`, `(@)`) are covered; exotic forms pass through as unclassified text silently.
- The per-provider semaphore is a concurrency gate, not a true rate limiter. Four concurrent VT requests could all fire in under 1 second and still hit VT's 4/minute limit. If VT 429s increase after M003, true token-bucket rate limiting would be the next step.
- The detail page SVG graph label font-size was reduced to 10 to fit longer provider names at the wider orbit radius. Very long provider names (> ~20 chars) would still wrap or overflow. Currently the longest name is "Shodan InternetDB" (17 chars) — acceptable.

### Authoritative diagnostics
- `python3 -m pytest tests/test_orchestrator.py -v` — 22 tests for semaphore + backoff behavior; all must pass
- `python3 -m pytest tests/e2e/test_results_page.py -v -k email` — 6 tests for email IOC E2E; fast isolated check
- `grep -c 'summaryTimers' app/static/src/ts/modules/enrichment.ts` — must return ≥ 3
- `wc -c app/static/dist/main.js` — bundle size gate; alert if approaching 30,000 bytes
- `grep 'ioc-type-badge--email' app/static/dist/style.css` — verifies CSS rebuild included email selectors
- `python3 -c "from app.pipeline.extractor import run_pipeline; print(run_pipeline('user[@]evil[.]com'))"` — end-to-end email pipeline smoke

### What assumptions changed
- S02 plan assumed `results.html` would need an explicit EMAIL section added. The existing type-group Jinja loop was already generic — no template changes were needed. EMAIL rendered automatically.
- S03 plan assumed the graph truncation fix was purely in `graph.ts`. Truncation existed in both `routes.py` (Python slicing `[:20]`/`[:12]`) and `graph.ts` (`.slice(0,12)`/`.slice(0,20)`). Both sides required fixing.
- S04's hardcoded test assertion `<10` HTML occurrences of an IP string was written against M001/M002's leaner template. The richer M002/M003 template legitimately produces ~12 occurrences in expanded view — the dedup guarantee is about separate IOC entries, not raw string counts.

## Files Created/Modified

- `app/enrichment/orchestrator.py` — per-provider semaphore dict, `_do_lookup_body()` extraction, `_is_rate_limit_error()`, 429 backoff
- `app/pipeline/models.py` — `IOCType.EMAIL = "email"` (9th enum member)
- `app/pipeline/classifier.py` — `_RE_EMAIL` regex + step 7.5 classify case
- `app/pipeline/extractor.py` — `_RE_EMAIL_EXTRACT` regex + email extraction block
- `app/routes.py` — label truncation slices removed; `provider_counts` guard extended to exclude `IOCType.EMAIL`
- `app/templates/ioc_detail.html` — full rework with M002 design tokens, stacked provider cards, no inline styles
- `app/static/src/ts/modules/enrichment.ts` — `summaryTimers` debounce map + `debouncedUpdateSummaryRow()` wrapper
- `app/static/src/ts/modules/graph.ts` — `.slice()` truncation removed; SVG viewBox widened to 700×450; orbitRadius/cx/cy adjusted; font-size reduced to 10
- `app/static/src/input.css` — email badge + filter pill neutral CSS; 25 detail page CSS rules in `@layer components`
- `app/static/dist/main.js` — rebuilt (26,783 bytes)
- `app/static/dist/style.css` — rebuilt (44,818 bytes) with email selectors and detail page rules
- `tests/test_orchestrator.py` — `TestPerProviderSemaphore` (3 tests) + `TestBackoff429` (4 tests)
- `tests/test_classifier.py` — `TestClassifyEmail` (5 tests)
- `tests/test_extractor.py` — `TestExtractEmail` (3 tests)
- `tests/test_pipeline.py` — `TestRunPipelineEmail` (1 test)
- `tests/test_ioc_detail_routes.py` — `test_detail_graph_labels_untruncated` + M002 design token assertions
- `tests/test_otx.py` — supported_types count updated 8→9
- `tests/test_routes.py` — HTML occurrence count relaxed <10→<20
- `tests/e2e/test_results_page.py` — 6 email IOC E2E tests added
