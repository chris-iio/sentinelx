# S02: Mode clarity without semantic churn — UAT

**Milestone:** M015
**Written:** 2026-04-26T09:00:21.127Z

# UAT: S02 Mode clarity without semantic churn

## Preconditions

- Run the SentinelX Flask app from the repository root with the generated assets from `make build`.
- Use synthetic IOC text only, for example `192.0.2.44` or `example.com`.
- Start from a clean browser session at `/`.
- If testing online results locally, use the repository's mocked/provider E2E setup; in an unconfigured environment, the existing online no-provider redirect/settings behavior is acceptable and should not be treated as an S02 regression.

## Test Case 1 — Default offline mode is clear and contract-compatible

1. Open `/`.
2. Inspect the intake command card.

Expected outcomes:
- The paste textarea remains the dominant control.
- A visible mode section is present with an `Analysis mode` heading or equivalent mode title.
- Offline and Online choices are visible and textually distinct.
- The default/offline safety copy is visible before submit.
- The online copy clearly references provider/enrichment behavior.
- `#mode-input` exists as a hidden input with `name="mode"` and `value="offline"`.
- `#mode-toggle-widget` exists with `data-mode="offline"`.
- `#mode-toggle-btn` is a real `type="button"` with `aria-pressed="false"` and descriptive ARIA wiring.
- The Extract button is disabled while the textarea is empty.

## Test Case 2 — Paste-to-results remains unchanged in Offline mode

1. Open `/`.
2. Paste `192.0.2.44` into the IOC textarea.
3. Confirm the Extract button becomes enabled and still says `Extract`.
4. Submit without changing mode.

Expected outcomes:
- The submitted form sends `mode=offline` from the hidden input.
- The app reaches the existing results flow.
- The results page shows an offline mode indicator.
- Offline extraction does not require provider configuration and does not make outbound provider HTTP calls.

## Test Case 3 — Click toggling synchronizes all observable mode state

1. Open `/`.
2. Click the mode toggle button once.
3. Inspect the mode state.
4. Click the mode toggle button again.

Expected outcomes after the first click:
- `#mode-input.value` is `online`.
- `#mode-toggle-widget[data-mode]` is `online`.
- `#mode-toggle-btn[aria-pressed]` is `true`.
- The visible status copy describes online/provider enrichment intent.
- The Extract button keeps the text `Extract` and receives the online mode styling/state.

Expected outcomes after the second click:
- `#mode-input.value` returns to `offline`.
- `#mode-toggle-widget[data-mode]` returns to `offline`.
- `#mode-toggle-btn[aria-pressed]` returns to `false`.
- The visible status copy returns to the offline/default safety message.
- The Extract button keeps the text `Extract` and returns to offline mode styling/state.

## Test Case 4 — Keyboard operation is accessible

1. Open `/`.
2. Tab to the mode toggle button.
3. Press Space.
4. Press Enter.

Expected outcomes:
- Keyboard focus is visible on the toggle button.
- Space activates the native button and toggles the mode to online with hidden input, widget data, ARIA, and status text synchronized.
- Enter activates the native button and toggles the mode back to offline with the same synchronized surfaces.
- No custom keyboard trap is introduced; normal tab order continues through the form.

## Test Case 5 — Online selection preserves existing route semantics

1. Open `/`.
2. Toggle the mode to Online.
3. Paste a synthetic IOC such as `example.com`.
4. Click Extract.

Expected outcomes:
- The submitted form sends `mode=online` from `#mode-input`.
- In the mocked/provider E2E environment, the results page shows an online mode indicator.
- In a local environment without configured providers, the existing no-provider/settings redirect behavior remains intact.
- No new pre-submit provider calls, history reads, local storage writes, polling, or preview UI occur on `/` before submit.

## Edge Cases

- Empty textarea: Extract stays disabled regardless of Offline/Online mode.
- Invalid or stale initial mode value in the DOM is normalized back to a supported offline/online state by the form module.
- Missing required mode markup should fail fast in tests rather than silently creating alternate selectors.
- Rebuilt assets should be served by a fresh dev-server process during manual smoke tests; if browser behavior looks stale after `make build`, restart the managed dev server before retesting.
