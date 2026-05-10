# S02: Registry, settings, and email provider coverage — UAT

**Milestone:** M016
**Written:** 2026-05-09T16:42:58.180Z

# UAT — M016/S02 Registry, Settings, and Email Provider Coverage

## UAT Type

Route-level and contract-level acceptance test for EmailRep provider registration, settings persistence, SSRF allowlist coverage, and Online-mode provider-count reporting. This UAT is designed for a local/test SentinelX instance with mocked provider execution; it intentionally avoids live EmailRep network calls.

## Preconditions

- The application is running in a local/test environment.
- No live EmailRep API request is required or expected.
- The tester can clear provider keys in the test config store or start with a clean local test store.
- At least one non-email provider may be configured when testing Online-mode rendering with missing EmailRep coverage.

## Test Case 1 — EmailRep appears as key-required email-only settings metadata

1. Open `/settings`.
2. Locate the EmailRep provider row/card.
3. Confirm the UI describes EmailRep as requiring an API key and links to HTTPS signup/metadata.
4. Confirm the provider is presented for email reputation rather than domain/IP/URL/hash/CVE coverage.

**Expected outcome:** EmailRep is visible in settings as a key-required provider for email IOCs only, using the same settings page structure as other key-gated providers.

## Test Case 2 — Unknown provider IDs cannot create arbitrary settings keys

1. Submit the settings form with an unsupported `provider_id` value such as `not-a-provider` and any fake key value.
2. Return to `/settings`.
3. Inspect persisted provider state through the UI or test fixture.

**Expected outcome:** The invalid provider is rejected by the valid-provider-id gate. No arbitrary provider key is stored, and the registry is not mutated to include an unsupported provider.

## Test Case 3 — Saving an EmailRep key uses generic provider-key storage and does not echo the secret

1. Submit `/settings` with provider `emailrep` and a fake test key value.
2. Follow the redirect back to `/settings`.
3. Confirm EmailRep now reports as configured.
4. Search the rendered response text for the exact fake key value.

**Expected outcome:** EmailRep is marked configured, `current_app.registry` is rebuilt through the existing save flow, and the raw key value is not present in rendered HTML.

## Test Case 4 — Empty EmailRep key is rejected safely

1. Submit `/settings` for provider `emailrep` with an empty or whitespace-only key.
2. Return to `/settings`.
3. Check EmailRep configured status.

**Expected outcome:** The empty key is rejected or treated as missing. EmailRep is not configured, and no partial provider registration is created.

## Test Case 5 — No EmailRep key leaves Online email coverage at zero

1. Ensure no EmailRep key is configured.
2. Configure any non-email provider if needed so Online mode can render normally.
3. Submit an Online analysis containing a single email IOC, such as `analyst@example.com`, using the route/test fixture that isolates the IOC as `IOCType.EMAIL`.
4. Inspect the results page provider-count metadata (`data-provider-counts`) and visible progress/provider-count text.

**Expected outcome:** Email provider coverage is `0`. The page renders without attempting EmailRep dispatch, and no key or additional email data is exposed in provider-count JSON.

## Test Case 6 — Configured EmailRep creates exactly one email provider

1. Configure an EmailRep test key through `/settings`.
2. Submit an Online analysis containing a single email IOC.
3. Inspect `data-provider-counts` and the visible progress/provider-count text.
4. Confirm non-email IOC type counts are unchanged.

**Expected outcome:** Email provider coverage is exactly `1`, corresponding to EmailRep. EmailRep is not counted for domains, IPs, URLs, hashes, or CVEs.

## Test Case 7 — SSRF allowlist boundary remains explicit

1. Review the configured HTTP allowlist contract for the EmailRep adapter.
2. Confirm `emailrep.io` is present.
3. Confirm no arbitrary host is introduced through settings or IOC input.

**Expected outcome:** EmailRep can only use the explicit `emailrep.io` host allowed by application config. Analyst-supplied email IOCs affect provider dispatch/counting, not host selection.

## Not Proven By This UAT

- Live EmailRep API availability, quota behavior, latency, or production credential validity.
- Compact EmailRep result-row rendering; S03 owns safe compact context rendering.
- Browser-level end-to-end Online email enrichment with a mocked EmailRep result; S04 owns that deterministic proof.
- Raw EML/header phishing triage, header authentication analysis, or multiple email reputation providers, all of which remain out of scope for M016.
