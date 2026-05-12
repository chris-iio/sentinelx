# S03: App route and analyst affordance — UAT

**Milestone:** M018
**Written:** 2026-05-12T10:15:13.591Z

## UAT Type
Manual app/API acceptance test for the diagnostic export route and analyst download affordance.

## Preconditions
- SentinelX is running locally with the S03 changes.
- Optional: configure a test-only provider secret in local settings to confirm it is not present in exported bytes.
- The analyst can access the local web UI and/or run `curl` against the local app.

## Steps
1. Open the SentinelX UI and locate the floating settings/navigation controls.
2. Activate the diagnostic download affordance labeled `Download diagnostic export`.
3. Confirm the browser downloads a `.zip` file named like `sentinelx-diagnostic-YYYY-MM-DD.zip`.
4. Alternatively, run `curl -i -o sentinelx-diagnostic.zip http://localhost:<port>/diagnostics/export`.
5. Inspect response headers and confirm `Content-Type: application/zip`, `Content-Disposition: attachment`, and numeric `X-Diagnostic-Sources` are present.
6. Open the ZIP file and confirm it contains `manifest.json`.
7. Open `manifest.json` and confirm it includes per-source outcomes and a source-count summary matching `X-Diagnostic-Sources`.
8. Search the raw ZIP bytes and extracted text for any configured provider secret value; the secret must not appear.
9. Exercise an assembly-failure scenario in a test/staging environment by forcing bundle assembly to raise an error.
10. Request `/diagnostics/export` again and confirm the response is HTTP 500 with `text/plain` body `Diagnostic export failed. Check server logs.` and no stack trace, exception message, or secret value.
11. Make more than three rapid export requests within a minute and confirm the route is rate-limited.

## Expected Outcomes
- Analysts can reach a supported local export path from the app UI.
- Successful exports are ZIP downloads with deterministic headers and `manifest.json`.
- Provider secrets and raw API keys are absent from the returned archive bytes.
- Source inventory is visible both in `X-Diagnostic-Sources` and inside `manifest.json`.
- Failures are visible but bounded: user-facing response is safe, and operational detail is confined to server logs.
- Excessive rapid export attempts are limited by the shared limiter.

## Edge Cases
- Missing or failing diagnostic sources should be represented as bounded per-source outcomes in the manifest rather than crashing the whole route unless assembly itself fails.
- If assembly itself fails, the response must not include traceback text, internal file paths, exception messages, or configured secrets.
- If the analyst retries too quickly, rate limiting may return a limiter response before a new export is generated.

## Not Proven By This UAT
- Full browser automation that downloads and inspects the archive end-to-end; this is owned by S04.
- Analyst-facing documentation for safe sharing and limits; this is owned by S04.
- Cloud log shipping, SIEM integration, multi-user access control, or long-term retention policy; these remain outside M018 scope.
