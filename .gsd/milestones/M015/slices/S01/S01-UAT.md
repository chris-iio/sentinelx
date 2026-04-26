# S01: Fast intake command surface — UAT

**Milestone:** M015
**Written:** 2026-04-26T08:45:59.331Z

# S01: Fast intake command surface — UAT

**Milestone:** M015
**Written:** 2026-04-26

## UAT Type

- UAT mode: mixed
- Why this mode is sufficient: S01 is a UI/layout foundation with a preserved form contract. Flask route tests prove the server-rendered HTML/security contract, Playwright proves browser-visible behavior and responsive hierarchy, and the live offline extraction test proves the primary analyst fast path still reaches existing results without provider dependency.

## Preconditions

- The SentinelX app can be served locally with the current Flask test/dev configuration.
- Frontend assets have been generated from source with `make build`.
- Browser tests run with synthetic IOC text only; no real secrets, provider keys, or analyst history are needed.
- History data is not required and should not appear on `/` during S01.

## Smoke Test

Open `/` and confirm the page shows a visually dominant command card containing the IOC textarea, Offline/Online toggle, Clear, and disabled Extract button. Paste a synthetic IOC such as `8.8.8.8`; Extract should enable, submitting in default Offline mode should navigate to results, and results should indicate Offline Mode with extracted IOC content.

## Test Cases

### 1. Command-card intake shell renders with stable form controls

1. Visit `/`.
2. Inspect the page for `.page-index`, `.intake-workbench`, and `.command-card`.
3. Confirm the form is `#analyze-form`, posts to `/analyze`, includes a hidden `csrf_token`, and contains `#ioc-text`, `#submit-btn`, `#clear-btn`, `#mode-input`, `#mode-toggle-widget`, and `#mode-toggle-btn`.
4. **Expected:** All command-card and stable form-control selectors exist; `#mode-input` defaults to `offline`; the textarea remains named `text`; no selector required by `form.ts` or downstream slices is missing.

### 2. Fast paste-to-results path remains unchanged

1. Visit `/`.
2. Confirm Extract is disabled before entering IOC text.
3. Enter synthetic IOC text such as `8.8.8.8\nexample.com` into `#ioc-text`.
4. Confirm Extract becomes enabled.
5. Submit without changing mode.
6. **Expected:** The browser reaches the existing results page, the mode is Offline, IOC counts/results appear, and no online provider dependency is required.

### 3. Empty and whitespace input still fail safely

1. Submit an empty or whitespace-only form to `/analyze`.
2. **Expected:** The server returns the existing `.alert-error` path instead of attempting extraction, and the input remains handled by the existing POST route with CSRF protection.

### 4. Desktop and mobile hierarchy keep intake primary

1. Render `/` at a desktop viewport.
2. Confirm the command card is visible and visually central/dominant.
3. Render `/` at a mobile viewport.
4. Confirm the command surface stacks cleanly and remains primary rather than being crowded by secondary content.
5. **Expected:** `.command-card` stays visible and primary at both viewport sizes; supporting copy/layout reinforces fast intake.

### 5. S01 scope boundaries are respected

1. Visit `/`.
2. Search for pre-submit preview UI and Recent Analyses/recent rail content.
3. **Expected:** Neither a pre-submit IOC preview nor Recent Analyses markup appears in S01; those concerns remain deferred to later slices.

## Edge Cases

### Offline no-HTTP behavior

1. Submit valid synthetic IOC text with default `mode=offline`.
2. **Expected:** Offline route behavior makes zero outbound HTTP provider calls and still produces extraction results.

### Security headers and CSRF

1. GET `/` and inspect response headers/HTML.
2. **Expected:** Existing security headers are present and the form includes CSRF protection.

### Generated asset consistency

1. Run `make build`.
2. **Expected:** Tailwind and esbuild complete successfully; generated CSS/JS are produced from source rather than hand-edited.

## Failure Signals

- Missing `.page-index`, `.intake-workbench`, `.command-card`, or any stable form-control selector.
- `#mode-input` no longer defaults to `offline`.
- Extract does not enable after entering text, or starts enabled on an empty form.
- Submitting valid offline IOC text does not reach results.
- Empty/whitespace submissions bypass `.alert-error` handling.
- `/` renders Recent Analyses or pre-submit preview UI during S01.
- `make build`, `npx tsc --noEmit`, route tests, or Playwright homepage/extraction tests fail.

## Not Proven By This UAT

- S02's clarified Offline/Online visual/keyboard/accessibility redesign.
- S03's compact Recent Analyses rail, links to `/history/<id>`, and history-list failure handling.
- S04's final integrated full-repository proof across all M015 slices.
- Any online provider enrichment behavior beyond preserving that S01 did not change the form contract.

## Notes for Tester

- Treat this as the foundation slice: the important user-facing change is that the front door now feels like a command-card workbench, while behavior remains intentionally conservative.
- Ignore the absence of Recent Analyses on `/`; that is expected until S03.
- Ignore deeper mode-control polish; S01 preserves the existing hidden mode contract and leaves visual/keyboard clarification to S02.
