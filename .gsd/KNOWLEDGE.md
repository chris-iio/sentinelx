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

---

## EnrichmentOrchestrator semaphore: wrap entire lookup+retry cycle, not per-attempt

When adding per-provider `threading.Semaphore` gating to `_do_lookup()`, the semaphore must wrap the *entire* cache-check + lookup + retry + cache-store cycle (the `_do_lookup_inner()` body), **not** just each individual `adapter.lookup()` call. Wrapping only per-attempt would allow up to `cap * 2` concurrent threads inside the provider body during retry, and risks re-entrant deadlock on single-threaded exhaustion scenarios. The correct pattern is: acquire semaphore once → call inner method → release on exit.

---

## Patching time.sleep in orchestrator tests: use module-level patch path

`time` is imported at the top of `orchestrator.py` as `import time`. To mock sleep in tests, patch `"app.enrichment.orchestrator.time.sleep"` — **not** `"builtins.time.sleep"` or `"time.sleep"`. Python resolves the name at import time; patching `builtins.time` would have no effect on calls already bound in the orchestrator's namespace.

```python
with patch("app.enrichment.orchestrator.time.sleep") as mock_sleep:
    ...
    mock_sleep.assert_called()
```

This applies to any module that uses `import time` (not `from time import sleep`).

---

## EnrichmentOrchestrator backoff constants are importable for threshold assertions

`_BACKOFF_BASE` and `_MAX_RATE_LIMIT_RETRIES` are module-level constants in `app/enrichment/orchestrator.py`. Tests should import them rather than hardcoding the numeric values — this ensures threshold assertions automatically track code changes:

```python
from app.enrichment.orchestrator import _BACKOFF_BASE, _MAX_RATE_LIMIT_RETRIES
assert mock_sleep.call_args[0][0] >= _BACKOFF_BASE
```

## iocsearcher does not extract fully-defanged emails ([@] form)

When input text contains only `user[@]evil[.]com` (both `@` and `.` defanged with brackets), iocsearcher fails to recognize it as an email address. It instead extracts the domain portion (`evil.com`) or misidentifies it as a URL fragment. The normalizer correctly handles `[@]` → `@` and `[.]` → `.`, but only AFTER extraction — iocsearcher never sees the defanged form as an email candidate.

Practical implication: if analysts paste `user[@]evil[.]com` alone in text, only the domain `evil.com` will be extracted, not the email identity. Plain `user@evil.com` (undefanged) is reliably extracted.

Workaround: none without a custom pre-extraction normalization pass before iocsearcher sees the text. Accept this as a known limitation and document it in tests.

Discovered: M003/S02/T01 (email IOC support)

---

## Task summary files may be written before code changes are applied to the worktree

During M003/S03, T01 and T02 task summaries were written with verification tables showing "✅ pass" — but the actual file edits (removing `[:12]`/`[:20]` from routes.py, removing `.slice()` from graph.ts, rewriting ioc_detail.html, adding CSS rules) had not been applied to the worktree. The closer/UAT agent must always independently verify file contents, not trust task summary verification evidence.

**Rule:** Before writing a slice summary, run all slice verification commands from scratch and inspect the actual files. If any check fails, apply the missing changes first. Do not inherit "verified" status from task summaries without re-running the checks.

---

## OTXAdapter.supported_types uses an explicit frozenset, not frozenset(IOCType)

`OTXAdapter.supported_types` is defined as an explicit `frozenset({IOCType.IPV4, IOCType.IPV6, IOCType.DOMAIN, ...})` that deliberately excludes `IOCType.EMAIL` (OTX has no email lookup endpoint). It does NOT use `frozenset(IOCType)`.

**Implication:** When a new `IOCType` member is added, `OTXAdapter.supported_types` does NOT automatically include it. Tests asserting `len(OTXAdapter.supported_types) == N` will NOT need to be incremented if the new type is excluded from OTX by design. Always check each adapter's `supported_types` definition individually rather than assuming it mirrors the full enum.

**General rule:** Any adapter that uses `frozenset({...})` (explicit set) must be explicitly updated when a new type should be supported. Only adapters using `frozenset(IOCType)` auto-inherit new members — and no adapter currently does this.

Discovered: M003/S04 (S04-plan incorrectly stated OTX uses frozenset(IOCType))

---

## enrichment.ts iocVerdicts type is Record<string, VerdictEntry[]>, not Record<string, string[]>

The `iocVerdicts` accumulator in `enrichment.ts` uses `Record<string, VerdictEntry[]>` (imported from `./verdict-compute`). Any wrapper function or helper that takes `iocVerdicts` as a parameter must use this exact type — using the simpler `Record<string, string[]>` causes `TS2345` type errors at `make typecheck`. The `VerdictEntry` type includes `provider`, `verdict`, `summaryText`, `detectionCount`, `totalEngines`, and `statText` fields.

Discovered: M003/S04/T01 (initial debouncedUpdateSummaryRow used wrong type)

---

## Playwright to_have_class() does exact class-list matching, not substring/regex, with plain strings

Playwright's `to_have_class()` with a plain string argument performs **exact class-list matching** (the full `className` attribute must equal the string), not substring or regex matching. To assert that an element has a specific class combination (e.g., `filter-pill--email filter-pill--active`), use a compound CSS selector with `page.locator(".cls1.cls2")` and assert it `to_be_visible()` — not `to_have_class(".cls1.cls2")`.

Regex pattern strings like `r".*class-name.*"` work correctly with `to_have_class()` and are safe for partial class assertions on elements that may have other classes.

**Correct patterns:**
```python
# Assert specific class combo present (compound selector):
expect(page.locator(".filter-pill--email.filter-pill--active")).to_be_visible()

# Assert partial class with regex:
expect(locator).to_have_class(r".*is-open.*")
```

Discovered: M003/S02/T02 (initial email filter active-state test failed with plain string)

---

## tools/tailwindcss binary is not committed to git and may be absent in fresh worktrees

The `tools/tailwindcss` standalone binary (used by `make css`) is gitignored and not present in freshly-created worktrees. If `make css` exits with code 127 ("No such file or directory"), the binary needs to be sourced:

```bash
# Copy from main project tree if available:
cp /home/chris/projects/sentinelx/tools/tailwindcss ./tools/tailwindcss
chmod +x ./tools/tailwindcss

# Or install via Makefile target (downloads from GitHub):
make tailwind-install
```

**Symptom:** `make css` exits 127 with `./tools/tailwindcss: No such file or directory`. This is silent if the caller only checks overall build success — `style.css` may appear to exist (from a previous build) but won't contain newly added CSS rules.

**Check:** `grep -c 'expected-class-name' app/static/dist/style.css` — if a recently added CSS class returns 0, the style.css was not rebuilt. Run `ls tools/tailwindcss` to confirm binary presence before diagnosing further.

Discovered: M003/S03 (closer found binary missing in worktree; task summary claimed `make css` passed)

---

## EnrichmentOrchestrator semaphore: per-attempt semantics SUPERSEDE per-cycle semantics (M003→M004)

**Supersedes the "wrap entire lookup+retry cycle" entry above.**

The M003 pattern (acquire semaphore once, wrap the entire cache+lookup+retry+cache-store cycle) was the correct initial design. M004/S01 deliberately changed this to **per-attempt** semantics: the semaphore wraps only one HTTP attempt inside `_single_attempt()`, and `time.sleep()` backoff runs **outside** the semaphore in `_do_lookup()`.

**Why it changed:** Under the M003 pattern, a VT 429 response triggers `time.sleep(delay)` while holding the semaphore. With 4 IOCs simultaneously getting 429s, all 4 slots sleep for the full backoff duration — stalling every queued IOC for 47+ seconds. The per-attempt pattern releases the slot immediately after the attempt, allowing other IOCs to proceed while the current one sleeps.

**Current pattern (M004+):**
```python
# _do_lookup() — semaphore wraps only one attempt
sem.acquire()
try:
    result = _single_attempt(...)  # cache-check + adapter.lookup() + cache-store
finally:
    sem.release()
# sleep OUTSIDE the semaphore:
if is_429:
    time.sleep(backoff_delay)
elif should_retry:
    time.sleep(1)
sem.acquire()  # re-acquire for retry
...
```

**Note on the re-entrant concern from M003:** The M003 note about "cap * 2 concurrent threads" and re-entrant deadlock only applies if a single function acquires the semaphore twice on the same thread. In the per-attempt pattern, the semaphore is released before the retry loop iteration; there is no double-acquire on a single thread.

Discovered: M004/S01/T01

---

## requests.exceptions.SSLError is a subclass of ConnectionError — handler ordering is a correctness constraint

In the `requests` library, `requests.exceptions.SSLError` inherits from `requests.exceptions.ConnectionError`. If both handlers are present and `ConnectionError` appears before `SSLError`, the `SSLError` branch will **never execute** — all SSL errors fall into the `ConnectionError` handler silently.

**Mandatory ordering in requests adapters:**
```python
except requests.exceptions.SSLError:
    return EnrichmentError(ioc=ioc, provider=self.name, error="SSL/TLS error")
except requests.exceptions.ConnectionError:
    return EnrichmentError(ioc=ioc, provider=self.name, error="Connection failed")
```

This is a correctness constraint, not a style preference. A future refactor that alphabetizes exception handlers would break this silently.

**Verification:** `grep -n 'SSLError\|ConnectionError' app/enrichment/adapters/abuseipdb.py` — the SSLError line number must always be smaller than the ConnectionError line number.

**Full correct chain in requests adapters (as of M004/S01):**
`Timeout` → `HTTPError` → `SSLError` → `ConnectionError` → `Exception`

Discovered: M004/S01/T02

---

## Adapter module docstrings mentioning "requests.get/requests.post" break slice grep verification

When updating adapter implementations from bare `requests.get()` calls to `self._session.get()`, the slice-level verification check `grep -rn 'requests\.get\|requests\.post' app/enrichment/adapters/*.py` will match **docstring** text as well as code. Stale thread-safety docstrings that say "uses a fresh requests.get call per lookup()" will produce false failures.

**Pattern:** After updating adapter implementations, also update:
1. Module-level docstring `Thread safety:` line (usually line 25-35)
2. Class-level docstring `Thread safety:` line (usually 10-15 lines into the class)

**Old text (pre-Session):**
`Thread safety: a fresh requests.get call is used per lookup() call (no shared Session).`

**New text (post-Session):**
`Thread safety: a persistent requests.Session is created in __init__ and reused across lookup() calls (TCP connection pooling).`

**Why the edit tool can cause indentation errors:** When replacing a 4-space-indented class docstring line with a text that matches both module-level (0-space) and class-level (4-space) occurrences, the first `edit` call replaces one occurrence and the second may target wrong text. Always verify `python3 -c "import app.enrichment.adapters.X"` after docstring edits.

Discovered: M004/S02/T04

---

## Adapter test mock pattern: adapter._session = MagicMock() (post-M004/S02)

As of M004/S02, all 12 adapter test files use a direct mock assignment pattern instead of `with patch("requests.get")`:

```python
adapter = SomeAdapter(allowed_hosts=["example.com"])
adapter._session = MagicMock()
adapter._session.get.return_value = mock_resp  # or .post for malwarebazaar/urlhaus/threatfox
result = adapter.lookup(ioc)
adapter._session.get.assert_called_once()
```

**For auth header tests:** Since headers are session-level, check `dict(adapter._session.headers)` — NOT `call_kwargs["headers"]`.

**S04 (test DRY-up) must use this pattern** for any shared fixtures or helpers.

Discovered: M004/S02/T02

---

## ipinfo.io returns HTTP 404 for private/reserved IPs

Unlike ip-api.com (which returned HTTP 200 + `{"status": "fail"}`), ipinfo.io returns HTTP 404 for private IPs like `192.168.1.1` or `10.0.0.1`. The ip_api adapter handles this by checking `resp.status_code == 404` *before* calling `resp.raise_for_status()`, returning `EnrichmentResult(verdict="no_data", raw_stats={})`.

**Contract:** Private IP = "no data" (clean result), NOT an error. Tests use `mock_resp.status_code = 404` without a JSON body.

**ipinfo.io `org` field format:** `"AS15169 Google LLC"` — split on first space to extract ASN number and ISP name (same approach as the old ip-api.com `as` field).

Discovered: M004/S02/T03

---

## Debounced event handlers require E2E POM wait-after-fill

When adding `setTimeout`-based debounce to an `input` event handler (e.g., `applyFilter()` in filter.ts), Playwright's `.fill()` triggers the `input` event synchronously but the handler now defers execution. E2E tests using bare `assert` (not Playwright `expect()` with auto-retry) will assert before the debounced function fires.

**Fix:** Add `page.wait_for_timeout(debounce_ms + 50)` in the POM method after `fill()`. Example: `search()` in `results_page.py` waits 150ms after fill for the 100ms debounce.

**Note:** This only affects assertions that don't use Playwright's auto-retry matchers. `expect(locator).to_have_count(N)` retries, but `assert locator.get_attribute(...) == "..."` does not.

Discovered: M004/S03/T02

---

## ConfigStore: write-through cache invalidation prevents stale reads

`ConfigStore._cached_cfg` caches the parsed `ConfigParser` in memory. The cache is populated on `_read_config()` and invalidated (set to `None`) on `_save_config()`. This ensures the next read after a write hits disk, not a stale cache.

**Constraint:** Any new method that modifies the config file must call `self._cached_cfg = None` afterward (or delegate to `_save_config()`). Direct file writes that bypass `_save_config()` will leave the cache stale — the in-memory parser will return old values.

**Pattern:**
```python
def _read_config(self):
    ...
    self._cached_cfg = cfg
    return cfg

def _save_config(self, cfg):
    ...write to file...
    self._cached_cfg = None  # invalidate
```

Discovered: M004/S02/T04

---

## Descoped work creates accurate summaries, not false claims

M004 planned `safe_request()` consolidation, registry caching in `create_app()`, and routes decomposition. These were descoped during execution (S01 re-focused on concurrency; S02 re-focused on IO performance). The S01 summary initially stated "all 12 adapters use safe_request()" — which was inherited from the plan, not from reality.

**Rule:** When a task or slice is re-scoped, the summary must explicitly document what was NOT delivered, not silently inherit success claims from the original plan. Milestone closers must independently verify every success criterion, not trust slice summaries.

Discovered: M004 closer verification
