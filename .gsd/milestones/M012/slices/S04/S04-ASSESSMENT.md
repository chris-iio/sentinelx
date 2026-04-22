# S04 Persistence and Helper-Layer Assessment

**Verdict:** Keep the WAL-backed persistence layers and the full-fidelity history replay path as-is. The only justified near-term follow-through is the helper-local diagnostics/measurement seam already added in T01.

## Reader and Action

This assessment is for the next SentinelX maintainer closing M012 or planning follow-on optimization work. After reading it, they should be able to decide whether to schedule persistence/helper refactors now, next, later, or not at all.

## Evidence Base

This ranking is grounded in the current code and fresh proof, not generic optimization advice:

- `app/cache/store.py` still uses one persistent SQLite connection with `journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=5000`, in-memory temp store, and a `cached_at` index.
- `app/enrichment/history_store.py` uses the same WAL-mode baseline and `save_analysis()` still persists full serialized results so `/history/<id>` can replay analyst-visible output without re-enrichment.
- `app/routes/_helpers.py` still concentrates the helper/runtime seam: orchestrator registry lifetime, cursor-based status slicing, and `_run_enrichment_and_save()` persistence handoff.
- `app/routes/settings.py` plus `app/templates/settings.html` now expose the additive helper-local History Save Diagnostics surface from T01, giving operators aggregate save outcomes without reading logs or opening analyst result pages.
- Prior slice research and fresh focused verification continue to show the persistence seam is healthy and the helper seam is the only place where additional inspection is currently justified.

## Do now

1. **Keep the shipped helper diagnostics surface and use it as the decision-grade inspection seam.**
   - The new `/settings` History Save Diagnostics section is the right current observability boundary because it surfaces helper-owned save attempts, successes, failures, skips, and coarse last-outcome metadata without changing `HistoryStore` row shape.
   - This satisfies the slice requirement to leave one additive inspection surface for helper-layer persistence health.

2. **Close M012 with an explicit keep decision for persistence.**
   - `app/cache/store.py` is already using the intended WAL-mode, persistent-connection SQLite profile.
   - `app/enrichment/history_store.py` already preserves the product-critical full-results replay behavior.
   - No new measurement in M012 shows contention, write amplification, or request-path waste large enough to justify rewriting either store now.

3. **Preserve the two continuity seams intentionally left untouched in this slice.**
   - `_get_enrichment_status()` and its `?since=` cursor behavior in `app/routes/_helpers.py` were left alone because earlier slices already proved that contract and this slice produced no evidence that cursor slicing is the bottleneck.
   - `HistoryStore.save_analysis()` continuity was left alone because the current full-results payload is what makes `/history/<id>` instant and faithful to the original analyst session.

## Do next

1. **Measure the helper/runtime seam before proposing structural change.**
   - If future work still suspects hidden cost, measure around `_run_enrichment_and_save()` and the helper-owned lifecycle in `app/routes/_helpers.py` first.
   - The most useful next proof would be concurrent online-job measurements showing whether save latency, save-failure frequency, or helper coordination materially impacts analyst experience.

2. **Use the `/settings` diagnostics surface as the first trigger for any follow-up.**
   - Revisit helper work only if the aggregate counters start showing repeated failures, excessive skips, or timestamps/outcomes that disagree with expected history continuity.
   - If that surface stays calm, storage and helper rewrites remain unjustified.

## Later

1. **Revisit SQLite concurrency or retention only if real evidence appears.**
   - `app/cache/store.py` and `app/enrichment/history_store.py` both use coarse locking around a shared connection. That is a deliberate safety tradeoff, not an accidental omission.
   - A later milestone could explore a different connection model, scheduled cache cleanup, or DB-size controls, but only if realistic load or file-growth measurements show current behavior becoming costly.

2. **Consider helper decomposition only if the helper seam becomes meaningfully harder to reason about.**
   - Today `app/routes/_helpers.py` is still a manageable concentration point.
   - If future features expand its responsibilities, split based on measured complexity and ownership boundaries, not because the file merely looks like a seam.

## Leave alone

1. **Leave the WAL-backed stores alone.**
   - Keep `app/cache/store.py` and `app/enrichment/history_store.py` on the current WAL-mode/persistent-connection path unless future measurement proves contention or operational pain.

2. **Leave full-fidelity history replay alone.**
   - Keep `HistoryStore.save_analysis()` storing full serialized results and keep `/history/<id>` replay using that persisted payload.
   - Replacing this with summary-only storage or re-enrichment-on-load would trade away analyst continuity and quota efficiency without any current evidence of payoff.

3. **Leave `_get_enrichment_status()` cursor semantics alone.**
   - The `?since=` contract remains the right bounded polling shape and this slice found no evidence that it should be reworked as part of persistence/helper optimization.

## Requirement Impact

- **R022** — Advanced by explicitly preserving WAL-mode cache/history behavior in `app/cache/store.py` and `app/enrichment/history_store.py` because the current evidence still supports keeping that design.
- **R040** — Advanced by making the keep/change call from measured proof and seam-specific code-path reasoning rather than structural taste.
- **R008** — Protected by preserving `HistoryStore.save_analysis()` full-results continuity so `/history/<id>` keeps replaying the same analyst-visible output shape.
- **R019** — Protected by intentionally leaving `_get_enrichment_status()` and its `?since=` cursor behavior unchanged in this slice.

## Ranked Conclusion

The correct M012 closeout stance is:

- **Do now:** keep the helper-local diagnostics surface and record an explicit keep decision for the WAL-backed stores and history replay path.
- **Do next:** gather helper/runtime measurements only if the new diagnostics or future live runs show a concrete problem.
- **Later:** consider deeper store/helper redesign only with real concurrent-load or file-growth evidence.
- **Leave alone:** WAL-mode SQLite storage, full-results history replay, and `_get_enrichment_status()` cursor semantics.

Unless new measurement disproves this assessment, SentinelX should preserve the current persistence architecture and treat helper-layer diagnostics/measurement as the only justified near-term follow-through.
