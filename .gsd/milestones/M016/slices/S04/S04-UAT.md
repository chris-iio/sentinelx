# S04: Mocked Online email enrichment proof — UAT

**Milestone:** M016
**Written:** 2026-05-11T18:48:02.058Z

## UAT Type

Automated browser integration UAT using a real Flask live server, CSRF-enabled settings/analyze routes, real bundled frontend, Playwright browser, and mocked `/enrichment/status/**` response. No live EmailRep key or third-party request is required.

## Preconditions

1. The app can run its E2E Flask live server and Playwright browser dependencies.
2. Test configuration is isolated from production/local analyst settings.
3. EmailRep is registered as a key-gated provider for email IOCs from prior M016 slices.

## Steps

1. Open the real Settings UI.
2. Save a syntactically valid fake EmailRep key through the settings form.
3. Reload settings and confirm EmailRep is shown as configured while the raw fake key is not displayed.
4. Arm the EmailRep E2E status route mock before submitting Online analysis.
5. Submit a single email IOC, `analyst@example.com`, through the real Online index form.
6. Wait for enrichment polling to apply the mocked status payload to the results page.
7. Inspect `.page-results` for live ownership, deterministic fake job id, and `data-provider-counts` containing `email: 1`.
8. Locate the email IOC card and verify the EmailRep verdict/summary attribution is visible.
9. Expand the IOC row and inspect `.enrichment-section--reputation` for an EmailRep provider detail row.
10. Confirm compact EmailRep context fields are shown for reputation, references, risk flags, domain reputation, profiles, MX/deliverability/spoofing/auth-related flags, and related whitelisted scalar/list fields.
11. Confirm script-like raw values render as text, no `<script>` nodes are created, unsupported nested raw values are omitted, raw object/JSON dumping is absent, and the fake key is not echoed.

## Expected Outcomes

- EmailRep can be configured through the real settings UI with a fake key in the test environment.
- Online mode reports one configured email provider and renders an email IOC result from the mocked EmailRep status response.
- The existing shared polling/result-application/row-factory path renders the verdict and compact context row safely.
- No live EmailRep network request or real API key is needed.
- Neighboring mocked enrichment and settings tests remain passing.

## Edge Cases Covered

- Script-like strings in allowed EmailRep fields remain inert text.
- Unsupported nested raw_stats payloads are not dumped into the UI.
- The fake provider key is redacted from page text.
- Existing mocked IP enrichment route behavior remains unchanged.

## Not Proven By This UAT

- Live EmailRep API availability, latency, rate limiting, or real credential validity.
- Raw EML/header phishing triage.
- Multiple email reputation providers.
- Diagnostic bundle export for enrichment/settings failures.
