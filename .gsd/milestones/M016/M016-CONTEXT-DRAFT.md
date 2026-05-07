# M016: Email Reputation Depth — Context Draft

**Draft saved:** 2026-05-03
**Status:** Discussion in progress

## Vision Input
The user asked for help deciding what to do next. Reflection confirmed that M016 should identify and plan the next highest-leverage product direction for SentinelX, based on current product/codebase state rather than generic brainstorming.

## Confirmed Direction So Far
- The selected direction is **Email/phishing depth**, specifically **Email reputation** rather than full raw-email/phishing-triage parsing or a no-new-provider extraction-only pass.
- The user selected the recommended path: add one focused email reputation provider and make `IOCType.EMAIL` first-class in Online mode without turning SentinelX into a mail parser.
- EmailRep should be **key-gated**: treat the provider as configured only when an API key is present, matching SentinelX's existing key-gated provider model and avoiding anonymous rate-limit surprises.
- EmailRep-style results should participate in the analyst verdict flow, not just render as passive context. High-confidence flags should map into the existing malicious/suspicious/clean/no_data language so email rows are scannable like other IOCs.
- The email row should show a **compact risk summary** at a glance: reputation/suspicious state and the strongest few flags, with full flag detail in expanded/detail views.
- M016's completion boundary is **provider integration**: one key-gated EmailRep provider works end-to-end in Online mode, with UI rendering and tests, but no raw email parsing.

## Codebase Findings
- `IOCType.EMAIL` already exists in `app/pipeline/models.py` and email IOCs are currently extracted/displayed.
- `app/pipeline/classifier.py` already classifies email addresses before domains; tests cover email classification and URL-with-@ edge cases.
- `tests/e2e/test_results_page.py` already proves email IOCs render with an EMAIL type badge/filter in results.
- `app/enrichment/setup.py` registers 15 providers; none supports `IOCType.EMAIL` today.
- `app/enrichment/adapters/otx.py` explicitly excludes `IOCType.EMAIL`; OTX is not an email lookup path here.
- Provider registration/config follows `build_registry()` + `ConfigStore.get_provider_key()` + `PROVIDER_INFO` settings metadata.
- HTTP adapters usually subclass `BaseHTTPAdapter`, dispatch through `safe_request()`, and use the shared SSRF/response-size/error handling seam.
- Online-mode provider counts are generated in `app/routes/analysis.py` by iterating `IOCType` except CVE and asking the registry for configured providers per type. Adding an email-capable configured provider should make `email` provider coverage visible to the frontend.
- Frontend provider context fields live in `app/static/src/ts/modules/row-factory.ts`; provider UI fields must be updated atomically with backend registration so the new provider's raw_stats have a safe text-only rendering path.

## External Finding
- EmailRep documentation/homepage shows a direct email reputation API pattern (`curl emailrep.io/bill@microsoft.com`) returning `reputation`, `suspicious`, `references`, and detailed flags such as `blacklisted`, `malicious_activity`, `credentials_leaked`, `data_breach`, `domain_exists`, `domain_reputation`, `new_domain`, `suspicious_tld`, `spam`, `free_provider`, `disposable`, `deliverable`, `valid_mx`, `spoofable`, `spf_strict`, and `dmarc_enforced`.
- EmailRep offers a free API key path and higher-rate-limit contact path; M016 should treat API-key configuration and missing-key behavior as part of the product scope.

## Likely In Scope If Final Depth Confirms
- One focused EmailRep-style provider adapter for `IOCType.EMAIL`.
- Settings/config support for the EmailRep key.
- Online-mode enrichment for email IOCs with real provider coverage when configured.
- Verdict mapping from EmailRep fields into SentinelX's existing verdict language.
- Compact email reputation summary rendering and expanded/detail fields using createElement/textContent-only DOM construction.
- Route/API/provider-count proof that email IOCs now have real provider coverage when configured.

## Likely Out of Scope Unless User Expands It
- Full raw email/EML parsing.
- Header-authentication analysis from pasted messages.
- Multiple email/phishing providers in one milestone.
- Pre-submit extraction preview.
- Broad results/detail redesign unrelated to email reputation.

## Remaining Discussion Needed
- Exact verdict mapping thresholds: which EmailRep flags should be malicious vs suspicious vs clean/no_data.
- Missing-provider behavior: how Online mode should communicate that email IOCs have no configured email provider when EmailRep is not keyed, especially if other providers are configured for other IOC types.
- Acceptance proof: whether fixtures/mocked provider responses are enough for contract completion, and whether any live-key smoke test should be expected or kept optional.
