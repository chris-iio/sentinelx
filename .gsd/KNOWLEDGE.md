# GSD Knowledge Base

Project-specific rules, recurring gotchas, and useful patterns discovered during execution.

---

## DOM: textContent="" wipes persistent child elements

**Context:** `updateSummaryRow()` in `row-factory.ts` uses `summaryRow.textContent = ""` as an immutable-rebuild pattern before re-appending verdict badge, attribution, micro-bar, etc. Any child element injected *once* (like the chevron wrapper injected by `getOrCreateSummaryRow()`) is destroyed by this clear.

**Fix pattern:** Save a reference to persistent children *before* the clear, then re-append them *after* all other children are built:
```ts
const chevronWrapper = summaryRow.querySelector(".chevron-icon-wrapper");
summaryRow.textContent = "";
// ... rebuild content ...
if (chevronWrapper) summaryRow.appendChild(chevronWrapper); // always last
```

**Rule:** Any element that must persist across incremental updates inside a "clear-and-rebuild" container must be explicitly saved before the clear and re-appended afterward.

---

## CSS: grep -c returns exit code 1 when count is 0

`grep -c 'pattern' file` exits with code 1 when there are 0 matches (grep standard behavior). In shell scripts checking for absence, use `|| echo "0"` or check with `! grep -q 'pattern' file`. Don't interpret exit code 1 as failure in absence-checking scenarios.

---

## wireExpandToggles() timing: use event delegation, not per-element binding

`wireExpandToggles()` in `enrichment.ts` is called once from `init()` — before the polling loop creates any `.ioc-summary-row` elements. Binding handlers directly on each row (via `querySelectorAll`) means 0 handlers get wired since no rows exist yet.

**Fix:** Use event delegation — bind a single `click` + `keydown` handler on the stable `.page-results` ancestor. Events from `.ioc-summary-row` elements (created at any time during polling) bubble up to the ancestor. Use `event.target.closest(".ioc-summary-row")` to identify the relevant row inside the handler.

This is the standard pattern for dynamically created elements in this codebase. The old `.chevron-toggle` approach worked because the button existed in the server-rendered template before `init()` ran — the new `.ioc-summary-row` does not.

---

## Playwright route mocking: register BEFORE navigation, not after

`page.route("**/enrichment/status/**", handler)` must be called **before** the page action that triggers the fetch (e.g., form submit, navigation). Registering after submit races against the first polling tick (750ms) and may miss it, leaving enrichment.ts with no response and the UI in an unloaded state.

Pattern: in `_navigate_online_with_mock()`, call `setup_enrichment_route_mock(page)` → then `idx.goto()` → then `idx.extract_iocs()` → then `wait_for_selector(".ioc-summary-row")`.

---

## SentinelX detail link route is /detail/<ioc_type>/<ioc_value>, not /ioc/

The `injectDetailLink()` function in enrichment.ts builds links using the Flask route `/detail/<ioc_type>/<ioc_value>`. Test assertions checking the href of `.detail-link` should match `/detail/` not `/ioc/`. The plan incorrectly assumed `/ioc/` — inspecting actual DOM output (or the Flask route table) is the definitive source.
