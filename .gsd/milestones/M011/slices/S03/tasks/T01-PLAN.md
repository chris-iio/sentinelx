---
estimated_steps: 51
estimated_files: 2
skills_used: []
---

# T01: Patch time.sleep in 4 orchestrator tests and verify CSS audit

## Description

Two independent low-risk changes in one task:

**Part A — Patch `time.sleep` in 4 orchestrator tests (~4s saved)**

Four tests trigger the non-429 retry path in `_do_lookup()` which calls `time.sleep(1)` between attempts. They don't mock it, so each takes ~1.0s. Add `with patch("app.enrichment.orchestrator.time.sleep")` around the `enrich_all()` call in each test — the exact pattern already used by 6 tests in `TestBackoff429` and `TestSemaphoreReleasedDuringBackoff`.

Tests to patch:
1. `TestEnrichAll::test_error_isolation` (line ~138) — 1 error IOC triggers retry with real sleep
2. `TestRetryBehavior::test_retry_on_failure` (line ~167) — error then success, real sleep between
3. `TestRetryBehavior::test_retry_still_fails` (line ~186) — error then error, real sleep between
4. `TestMultiAdapterDispatch::test_adapter_failure_isolated_across_providers` (line ~339) — adapter_a error triggers retry with real sleep

**CRITICAL:** The patch path MUST be `"app.enrichment.orchestrator.time.sleep"` — NOT `"time.sleep"` or `"builtins.time.sleep"`. Python resolves `time` at import time; only the module-level path works. This is documented in KNOWLEDGE.md.

**Pattern (copy from existing tests):**
```python
with patch("app.enrichment.orchestrator.time.sleep"):
    orchestrator.enrich_all("job-id", [ioc])
```

For `test_error_isolation`, the patch wraps the `enrich_all` call. The test assertions remain identical — we're only eliminating the real 1s sleep.

For `test_retry_on_failure` and `test_retry_still_fails`, same pattern — wrap `enrich_all` in the patch context manager. Existing assertions on `mock_adapter.lookup.call_count == 2` still verify retry behavior.

For `test_adapter_failure_isolated_across_providers`, this test creates its own adapters (not using the fixture). Wrap the `enrich_all` call in the patch context manager.

**Part B — CSS audit verification (R058)**

The research audit found ALL 207 custom CSS classes in `input.css` are actively referenced. No dead classes exist. Three classes that appear unreferenced in literal grep (`micro-bar-segment--suspicious`, `verdict-known_good`, `verdict-label--known_good`) are constructed via string concatenation in TypeScript:
- `row-factory.ts:336` → `"micro-bar-segment micro-bar-segment--" + verdict`
- `row-factory.ts:416` → `"verdict-badge verdict-" + verdict`
- `cards.ts:60` → `"verdict-label--" + worstVerdict`

Optionally trim the 12-line CSS LAYER OWNERSHIP RULE comment block (lines 23-46 in `input.css`) if it seems like stale guidance. This is cosmetic only.

Run `make css` after any CSS edit to verify the build still works.

## Steps

1. Open `tests/test_orchestrator.py`. Add `from unittest.mock import patch` to the imports if not already present (check first — it's likely already imported).
2. In `TestEnrichAll::test_error_isolation`, wrap the `orchestrator.enrich_all(...)` call (and everything after it that reads status) inside `with patch("app.enrichment.orchestrator.time.sleep"):`. Keep all assertions inside the `with` block.
3. In `TestRetryBehavior::test_retry_on_failure`, same pattern — wrap `orchestrator.enrich_all(...)` and assertions in the sleep patch.
4. In `TestRetryBehavior::test_retry_still_fails`, same pattern.
5. In `TestMultiAdapterDispatch::test_adapter_failure_isolated_across_providers`, same pattern.
6. Run `python3 -m pytest tests/test_orchestrator.py -q --durations=10` — verify 27 passed, and the 4 patched tests no longer appear in the slowest 10 (or show <0.01s).
7. Verify CSS: run a quick cross-reference check — `grep` a few of the "suspicious" dynamic classes against TS source to confirm they're constructed at runtime. Optionally trim the comment block at lines 23-46 in `input.css` and run `make css` to verify clean build.

## Must-Haves

- [ ] `test_error_isolation` patched with `time.sleep` mock
- [ ] `test_retry_on_failure` patched with `time.sleep` mock
- [ ] `test_retry_still_fails` patched with `time.sleep` mock
- [ ] `test_adapter_failure_isolated_across_providers` patched with `time.sleep` mock
- [ ] All 27 orchestrator tests still pass
- [ ] The 4 patched tests each run in <0.1s (down from ~1.0s)
- [ ] CSS audit verified: all classes in input.css are referenced

## Verification

```bash
# Orchestrator tests pass, patched tests fast
python3 -m pytest tests/test_orchestrator.py -q --durations=10
# Target: 27 passed; test_error_isolation, test_retry_on_failure, test_retry_still_fails,
# test_adapter_failure_isolated_across_providers NOT in slowest durations (or <0.01s)

# Full suite still passes
python3 -m pytest --tb=short -q
# Target: 1012 passed
```

## Inputs

- ``tests/test_orchestrator.py` — current test file with 4 unpatched slow tests`
- ``app/static/src/input.css` — CSS file to verify (2006 lines, 207 custom classes)`

## Expected Output

- ``tests/test_orchestrator.py` — 4 tests patched with time.sleep mock, ~4s faster`
- ``app/static/src/input.css` — optionally trimmed comment block (no class changes needed)`

## Verification

python3 -m pytest tests/test_orchestrator.py -q --durations=10 && python3 -m pytest --tb=short -q
