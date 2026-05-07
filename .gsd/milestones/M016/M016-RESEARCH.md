# M016 — Research

**Date:** 2026-05-07

## Summary

M016 should implement EmailRep as one focused, key-gated email reputation provider rather than expanding SentinelX into raw email/header phishing triage. The existing product already treats `IOCType.EMAIL` as first-class at extraction/render time, but Online enrichment has no configured provider path for email IOCs. Adding a single EmailRep adapter closes that gap while staying inside the existing provider registry, settings, orchestrator, history, and frontend rendering architecture.

External docs confirm EmailRep’s public API shape is a simple `GET https://emailrep.io/{email}` returning `email`, `reputation`, `suspicious`, `references`, and a nested `details` object with flags such as `blacklisted`, `malicious_activity`, `credentials_leaked`, `data_breach`, `domain_exists`, `domain_reputation`, `new_domain`, `suspicious_tld`, `spam`, `free_provider`, `disposable`, `deliverable`, `valid_mx`, `spoofable`, `spf_strict`, and `dmarc_enforced`. EmailRep does not technically require an API key, but the current user decision is to make SentinelX key-gate this provider to avoid anonymous-rate-limit ambiguity and match the existing configured-provider UX.

The main implementation risk is not the HTTP call; it is preserving SentinelX’s existing analyst contract: email rows should get a compact, scannable verdict and summary, but weak contextual signals must not overstate maliciousness. The provider should map high-confidence abuse indicators into `malicious`, broader risk indicators into `suspicious`, good deliverability/reputation into `clean`, and thin/no signal into `no_data`.

## Recommendation

Add a new `EmailRepAdapter` under `app/enrichment/adapters/emailrep.py` using `BaseHTTPAdapter`. Set `supported_types = frozenset({IOCType.EMAIL})`, `requires_api_key = True`, `name = "EmailRep"`, `EMAILREP_BASE = "https://emailrep.io"`, `_build_url()` to append the URL-encoded email value, and `_auth_headers()` to include both `Key: <api key>` and a stable `User-Agent`, such as `SentinelX`. Although EmailRep supports anonymous calls, SentinelX should not expose that in M016 because the discussion chose key-gated behavior.

Use a small, explicit verdict mapper in the adapter instead of pushing verdict logic into the frontend. Suggested first-pass mapping:

- `malicious` if any of: `details.blacklisted`, `details.malicious_activity`, `details.malicious_activity_recent`, or `details.credentials_leaked_recent` is true.
- `suspicious` if `suspicious` is true, `reputation == "low"`, or any strong-but-not-definitive flags are true: `spam`, `disposable`, `credentials_leaked`, `data_breach`, `new_domain`, `suspicious_tld`, `spoofable`, `domain_exists is false`, `valid_mx is false`, or `deliverable is false`.
- `clean` if `reputation in {"high", "medium"}`, `suspicious is false`, and no risk flags are present.
- `no_data` if `reputation == "none"`, fields are missing, or the response has no usable risk/reputation signal.

Keep the frontend rendering simple and safe: add `EmailRep` to `PROVIDER_CONTEXT_FIELDS` with compact text/tag fields derived by the backend, e.g. `reputation`, `suspicious`, `references`, `risk_flags`, `domain_reputation`, `profiles`. Do not render the entire nested details object directly. Build `risk_flags` in the adapter from the true boolean flags so `row-factory.ts` can use its existing tag renderer with `textContent`.

## Implementation Landscape

### Key Files

- `app/enrichment/adapters/emailrep.py` — new keyed HTTP adapter for `IOCType.EMAIL`; should subclass `BaseHTTPAdapter` and own EmailRep response parsing/verdict mapping.
- `app/enrichment/adapters/base.py` — existing template-method HTTP adapter pattern: auth headers, `is_configured()`, type guard, `safe_request()`, and parse hook.
- `app/enrichment/http_safety.py` — canonical HTTP safety path; the new adapter should dispatch through this indirectly via `BaseHTTPAdapter`.
- `app/enrichment/setup.py` — import/register `EmailRepAdapter`, read `config_store.get_provider_key("emailrep")`, add `PROVIDER_INFO` settings metadata, and update provider-count docstrings/comments from 15 to 16.
- `app/enrichment/config_store.py` — already supports generic provider keys via `[providers]`; no schema change required.
- `app/config.py` — verify `emailrep.io` is in the outbound allowed-host list; add it if absent.
- `app/routes/analysis.py` — no logic change expected; provider counts already iterate `IOCType` except CVE and use `registry.providers_for_type()`. Adding a configured email provider should make `email` counts non-zero.
- `app/static/src/ts/modules/row-factory.ts` — add `EmailRep` context field definitions for compact visible context; keep DOM creation via `createElement`/`textContent`.
- `app/static/src/ts/modules/row-factory.test.ts` — add tests proving `EmailRep` context fields render safely and are included/excluded as intended.
- `tests/test_emailrep.py` — new adapter-specific parse/verdict tests.
- `tests/test_adapter_contract.py` — add EmailRep to `ADAPTER_REGISTRY`, likely with a new `make_email_ioc` helper if one does not already exist.
- `tests/test_registry_setup.py` — update provider count, allowed hosts, provider registration, key lookup expectations, and configured-provider coverage tests.
- `tests/test_routes.py` or analysis route tests — add/adjust proof that configured provider counts include `email` when EmailRep is keyed.
- `tests/e2e/test_results_page.py` — existing email badge/filter coverage should remain; M016 should add mocked Online-mode proof that email enrichment renders EmailRep verdict/context.

### Build Order

1. **Backend adapter proof first.** Add `EmailRepAdapter` with unit tests for URL construction, auth headers, `is_configured()`, unsupported type behavior, and response parsing. This retires the API-shape and verdict-mapping risk before touching app-wide registry behavior.
2. **Registry/settings integration second.** Register the adapter in `build_registry()`, add `PROVIDER_INFO`, allowed host config, and update registry/contract tests. This proves EmailRep participates in SentinelX’s configured-provider model and makes `IOCType.EMAIL` enrichable in Online mode.
3. **Frontend/context rendering third.** Add `EmailRep` context fields and UI tests after the backend raw_stats contract is stable. Do not start frontend rendering until the adapter decides the exact field names.
4. **End-to-end mocked Online proof last.** Use mocked enrichment/status responses or the existing E2E mocking pattern to prove an email IOC renders an EmailRep verdict/context row without requiring a live API key.

### Verification Approach

Run focused tests after each stage, then full fast verification:

- Adapter: `python3 -m pytest tests/test_emailrep.py tests/test_adapter_contract.py -q`
- Registry/settings: `python3 -m pytest tests/test_registry_setup.py tests/test_settings.py tests/test_routes.py -q`
- Frontend: `make typecheck && make js && npm test -- row-factory`
- E2E mocked Online proof: targeted Playwright test for an email IOC with an EmailRep result row, e.g. `python3 -m pytest tests/e2e/test_results_page.py -k email -q`
- Final: `make verify-fast` if available and not prohibitively slow.

Observable behavior to prove:

- With no EmailRep key, `EmailRepAdapter.is_configured()` is false and `email` provider count remains zero.
- With an EmailRep key, `registry.providers_for_type(IOCType.EMAIL)` includes EmailRep and Online mode reports email provider coverage.
- An EmailRep response with high-confidence abuse flags produces a malicious/suspicious row verdict.
- A benign/high-reputation response produces a clean row verdict.
- A no-reputation/thin response produces `no_data` instead of exaggerated risk.
- UI context renders compact fields and tags without `innerHTML`.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| HTTP request safety, SSRF allowlist, response-size cap, exception handling | `BaseHTTPAdapter` + `safe_request()` | Keeps EmailRep consistent with the post-M005 adapter architecture and avoids bypassing established security behavior. |
| API key storage | `ConfigStore.get_provider_key()` / `set_provider_key()` | Generic provider-key storage already exists; no new env var or config schema is needed. |
| Provider discovery and Online dispatch | `ProviderRegistry` + `build_registry()` | Existing registry already handles configured providers, supported types, and provider counts. |
| Frontend context rendering | `PROVIDER_CONTEXT_FIELDS` + `createContextFields()` in `row-factory.ts` | Existing text-only DOM construction avoids XSS and keeps visual treatment consistent. |

## Constraints

- SentinelX’s product decision is key-gated EmailRep, even though EmailRep’s public docs say the API can be used anonymously with lower rate limits.
- EmailRep requires a User-Agent header; missing User-Agent returns HTTP 403 according to the docs root.
- EmailRep uses `Key: [api key]` as the documented auth header, not `Authorization: Bearer`.
- Invalid EmailRep API keys return HTTP 401 according to the docs root.
- `emailrep.io` must be present in `Config.ALLOWED_OUTBOUND_HOSTS` or `safe_request()` will reject the call before network dispatch.
- Do not make OTX support email; project knowledge explicitly notes OTX excludes `IOCType.EMAIL` by design.
- Provider UI fields must be updated atomically with backend registration; otherwise EmailRep data may enrich successfully but render no useful context.
- Use `textContent`/`createElement` only for EmailRep fields. Email addresses, profiles, and flags are external data.

## Common Pitfalls

- **Using anonymous EmailRep because the API allows it** — Avoid this in M016; the user selected key-gated behavior. Anonymous support can be a later explicit setting.
- **Wrong auth header** — EmailRep docs use `Key`, not `key`, `X-API-Key`, or `Authorization`.
- **Missing User-Agent** — EmailRep returns 403 without a user-agent; set a stable session header in `_auth_headers()`.
- **Overstating reputation as safety** — EmailRep’s own FAQ says high reputation does not mean an email is safe because accounts can be compromised or spoofed. Map high reputation to clean only when no risk flags are present.
- **Rendering nested `details` raw** — Flatten backend-selected fields into `raw_stats` keys like `risk_flags`; do not dump the whole object into the DOM.
- **Forgetting adapter contract registry updates** — Adding a provider requires updating parametrized adapter contract tests or they will stop representing the full provider set.
- **Forgetting allowed host config** — The adapter can be correct but still fail with an SSRF/allowed-host error if `emailrep.io` is not configured.

## Open Risks

- The docs navigation surfaced ReadMe-style field definitions and root auth behavior, but specific per-endpoint ReadMe.io pages returned 404 when fetched directly. Implementation should verify live endpoint behavior through mocked tests and, if a real key is available, an optional manual smoke test.
- EmailRep’s response for invalid emails, unknown emails, and rate limiting needs implementation-time confirmation. Use `pre_raise_hook` if specific status codes should map to `no_data` or clean user-facing errors.
- Exact verdict thresholds may need tuning after seeing real-world EmailRep samples; start conservative and make the mapping explicit/tested so it can be changed safely.

## Sources

- EmailRep homepage confirms simple `curl emailrep.io/bill@microsoft.com` API shape and sample fields including `reputation`, `suspicious`, `references`, and `details` flags (source: [emailrep.io](https://emailrep.io/)).
- EmailRep docs root confirms API key is optional upstream, keyed requests use `Key: [your api key]`, missing User-Agent returns 403, and invalid key returns 401 (source: [docs.emailrep.io](https://docs.emailrep.io/)).
- EmailRep GitHub README defines response field meanings for `reputation`, `suspicious`, `references`, and all key `details` flags (source: [sublime-security/emailrep.io README](https://raw.githubusercontent.com/sublime-security/emailrep.io/master/README.md)).
- SentinelX adapter architecture and registration seams verified from local files: `app/enrichment/adapters/base.py`, `app/enrichment/setup.py`, `app/enrichment/config_store.py`, `app/routes/analysis.py`, and `app/static/src/ts/modules/row-factory.ts`.
