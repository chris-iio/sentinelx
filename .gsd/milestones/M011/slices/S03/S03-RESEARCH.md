# S03 Research: Dead CSS Removal & Orchestrator Test Speed

**Slice:** S03 — Dead CSS Removal & Orchestrator Test Speed
**Milestone:** M011 — Lean & Fast
**Requirements:** R058 (Dead CSS removal), R059 (Orchestrator test speedup), R060 (all tests pass, zero behavior changes)
**Depth:** Light-to-targeted — both halves use established patterns; the CSS audit is the only investigative part and it's complete.

---

## Summary

**CSS finding:** The dead CSS audit is effectively complete — all 207 custom class names in `input.css` are actively referenced. No genuinely dead classes exist. The milestone context hypothesized `settings-provider-card` as dead, but that class does not exist in the file. Three classes (`micro-bar-segment--suspicious`, `verdict-known_good`, `verdict-label--known_good`) appear unreferenced in literal grep but are all constructed via string concatenation in TypeScript (e.g., `"micro-bar-segment--" + verdict`). The Tailwind safelist in `tailwind.config.js` is accurate and complete.

**Orchestrator finding:** 7 tests account for 6.2s of the 6.29s test suite. They fall into two categories with clear, independent fixes. The target is <1s.

---

## Recommendation

### Task 1: CSS Audit Verification & Minimal Cleanup
Since all classes are live, this task is primarily verification documentation. Optional: trim the 12-line CSS LAYER OWNERSHIP RULE comment block (lines 23-46) if the team considers it stale guidance that's now embedded in practice. The `graph-empty`, `enrichment-waiting-text`, and `enrichment-pending-text` classes are set in TypeScript but have **no CSS rules** — they're used as JS selectors only, not dead CSS (they were never in `input.css`).

**Key constraint from KNOWLEDGE.md:** Dynamic class patterns like `verdict-badge--${verdict}`, `micro-bar-segment--${verdict}`, `ioc-type-badge--${type}`, and `filter-pill--${type}` are constructed via string concatenation in TypeScript. A grep-based audit will never find literal references. The audit must cross-reference against these dynamic patterns:
- `row-factory.ts:309` → `"verdict-badge verdict-" + worstVerdict`
- `row-factory.ts:336` → `"micro-bar-segment micro-bar-segment--" + verdict`
- `row-factory.ts:416` → `"verdict-badge verdict-" + verdict`
- `cards.ts:60` → `"verdict-label--" + worstVerdict`
- `_ioc_card.html:34` → `ioc-type-badge--{{ ioc.type.value }}`

### Task 2: Orchestrator Test Speed — Patch Unpatched `time.sleep(1)` (Category 1)
**4 tests, ~4.0s saved.** These tests trigger the non-429 retry path in `_do_lookup()` which calls `time.sleep(1)` between attempts. The tests don't mock it.

| Test | Class | Why 1.0s | Fix |
|------|-------|----------|-----|
| `test_error_isolation` | `TestEnrichAll` | 1 error IOC → retry path → real `sleep(1)` | Patch `orchestrator.time.sleep` |
| `test_adapter_failure_isolated_across_providers` | `TestMultiAdapterDispatch` | 1 error adapter → retry → real `sleep(1)` | Patch `orchestrator.time.sleep` |
| `test_retry_on_failure` | `TestRetryBehavior` | Error → retry succeeds → real `sleep(1)` | Patch `orchestrator.time.sleep` |
| `test_retry_still_fails` | `TestRetryBehavior` | Error → retry fails → real `sleep(1)` | Patch `orchestrator.time.sleep` |

**Pattern (already established in `TestBackoff429`):**
```python
with patch("app.enrichment.orchestrator.time.sleep") as mock_sleep:
    orchestrator.enrich_all("job-id", [ioc])
```
This is the exact pattern from KNOWLEDGE.md: "patch `app.enrichment.orchestrator.time.sleep`" — must use the module-level patch path, not `time.sleep`.

**File:** `tests/test_orchestrator.py`
**Lines to modify:**
- `test_error_isolation` (line 138)
- `test_retry_on_failure` (line 167)
- `test_retry_still_fails` (line 186)
- `test_adapter_failure_isolated_across_providers` (line 339)

### Task 3: Orchestrator Test Speed — Replace `time.sleep()` Concurrency Proofs (Category 2)
**3 tests, ~2.2s saved.** These use real `time.sleep()` inside mock `side_effect` functions to create artificial latency for concurrency measurement.

| Test | Class | Current | Target |
|------|-------|---------|--------|
| `test_enrich_all_parallel_execution` | `TestEnrichAll` | `sleep(0.5)` × 5 IOCs = ~1.0s | `threading.Barrier(5)` — barrier proves all 5 threads started concurrently; timeout 2s proves no deadlock. No sleep needed. |
| `test_vt_peak_concurrency_capped_at_4` | `TestPerProviderSemaphore` | `sleep(0.3)` × 8 IOCs = ~0.6s | `threading.Event` + `threading.Lock` counter — each lookup increments `current_vt`, waits on a shared Event, then decrements. Peak check via `max()`. Release Event once all 8 lookups have entered. |
| `test_zero_auth_completes_without_waiting_for_vt` | `TestPerProviderSemaphore` | `sleep(0.3)` VT side effect = ~0.6s | VT side effect waits on `Event` (simulating slowness without real sleep). DNS side effect completes instantly. Assert DNS completed all 8 before VT event is released. |

**For `test_enrich_all_parallel_execution`:** The current test uses wall-clock timing (`elapsed < 3.0`) which is fundamentally flawed for CI — thread scheduling variance can cause false failures. Replace with a `threading.Barrier(N+1)` pattern: each mock lookup waits at the barrier. If execution is parallel, all N threads reach the barrier simultaneously and proceed. If sequential, the barrier times out. Also need to patch `orchestrator.time.sleep` to avoid the retry delay.

**For the semaphore tests:** The existing counter+lock pattern in `test_vt_peak_concurrency_capped_at_4` (lines 390-420) is correct for peak measurement. The sleep is only needed to keep threads alive long enough to measure overlap. Replace `time.sleep(0.3)` with an `Event.wait()` that releases after all threads have entered the critical section. The key insight: we don't need real time delay, just thread coordination.

---

## Implementation Landscape

### Files Modified
| File | Change | Est. Lines |
|------|--------|-----------|
| `tests/test_orchestrator.py` | Patch `time.sleep` in 4 tests; rewrite 3 concurrency tests with sync primitives | ~60 lines changed |
| `app/static/src/input.css` | Possible minor comment trimming; no class removals needed | 0-15 lines |

### Verification Commands
```bash
# Orchestrator tests pass and are fast
python3 -m pytest tests/test_orchestrator.py -q --durations=10
# Target: 27 passed in <1s

# Full test suite still passes
python3 -m pytest --tb=short -q
# Target: all tests pass, count unchanged

# CSS build still works (if input.css touched)
make css
# Target: clean exit

# Typecheck still passes
make typecheck
# Target: clean exit
```

### Risk Assessment
- **Low risk** for Category 1 (patching `time.sleep`): This is the exact same pattern already used by 6 tests in `TestBackoff429` and `TestSemaphoreReleasedDuringBackoff`. The mock is scoped to each test via `with patch(...)`.
- **Medium risk** for Category 2 (sync primitive rewrites): `threading.Barrier` and coordinated `Event` patterns require careful design to avoid test deadlocks. Use `timeout` parameters on all blocking calls.
- **No risk** for CSS: audit found no dead classes. If the task is limited to verification + optional comment trim, there's nothing to break.

### Natural Task Boundaries
1. **CSS audit** (verification only) — independent, can run in parallel with test work
2. **Patch unpatched `time.sleep`** — mechanical, low risk, saves ~4s immediately
3. **Rewrite concurrency proofs** — higher complexity, saves ~2s, benefits from Task 2 being done first (so we can measure cumulative improvement)

Task 2 should be done before Task 3 so cumulative timing can be verified at each step.

---

## Skill Discovery

No specialized skills needed — this is standard Python test refactoring and CSS auditing using `grep`/`rg`. The `threading` module patterns (`Barrier`, `Event`, `Lock`) are Python stdlib. No external libraries involved.
