# S02 Research: Recent Analyses → Dedicated /history Page

## Summary

Straightforward move of the Recent Analyses section from the home page to a new `/history` route. All backend infrastructure exists (`HistoryStore.list_recent()`, `history.py` route module, detail route). The work is: remove HTML from index.html, create history.html template, add a `/history` list route in history.py, add a nav link in base.html, move/adapt the toggle JS, keep the CSS, update tests.

## Recommendation

Three tasks:
1. **Backend route + template** — add `history_list()` to `history.py`, create `history.html`, add nav link to `base.html`
2. **Frontend cleanup** — remove Recent Analyses HTML from `index.html`, remove `list_recent` call from `index()` route in `analysis.py`, remove/adapt `initRecentAnalysesToggle()` from `ui.ts`
3. **Tests** — update `test_history_routes.py` (move `TestIndexWithHistory` assertions to `/history`), update `test_routes.py` if needed

Tasks 1 and 2 could be a single task since they're tightly coupled. Task 3 depends on 1+2.

## Implementation Landscape

### What exists

| File | Role | Lines of interest |
|------|------|-------------------|
| `app/routes/history.py` | History route module. Has `history_detail()`. New `history_list()` goes here. | Full file, 46 lines |
| `app/routes/analysis.py` | `index()` calls `history_store.list_recent(limit=10)` and passes `recent_analyses` to template. Lines 20-26. | Remove the list_recent call, stop passing `recent_analyses` |
| `app/templates/index.html` | Lines 61-82: Recent Analyses section (conditional on `recent_analyses`). | Remove lines 61-82 |
| `app/templates/base.html` | Line 24-26: `<nav class="floating-settings">` with settings icon only. | Add `/history` link here |
| `app/static/src/ts/modules/ui.ts` | Lines 45-60: `initRecentAnalysesToggle()` — collapses/expands section. Called from `init()` at line 64. | Keep function (used on history page). The `if (!section) return` guard means it's already a no-op on pages without the section. |
| `app/static/src/input.css` | Lines 1981-2116: All `.recent-analyses*` and `.recent-analysis-*` CSS rules. | Keep in place — still used by history page |
| `app/enrichment/history_store.py` | `list_recent(limit=20)` at line 155. Already returns `[{id, input_text, total_count, top_verdict, created_at}]`. | Reused as-is |
| `tests/test_history_routes.py` | Lines 210-246: `TestIndexWithHistory` class — 4 tests assert Recent Analyses on `/`. | Rewrite to assert against `/history` instead of `/` |

### New files

| File | Purpose |
|------|---------|
| `app/templates/history.html` | Extends `base.html`. Lists recent analyses. Reuses the same HTML structure from index.html lines 62-82 but always visible (no collapse toggle needed — the page IS the history). |

### Route design

```python
@bp.route("/history")
@limiter.limit("30 per minute")
def history_list():
    """List recent analyses."""
    analyses = current_app.history_store.list_recent(limit=50)
    return render_template("history.html", analyses=analyses)
```

The history page should show more entries than the home page did (50 vs 10). The collapse toggle is unnecessary — on a dedicated page the list is always visible.

### Nav link

Add to `base.html` `<nav class="floating-settings">`:
```html
<a href="{{ url_for('main.history_list') }}" class="nav-link nav-link--icon" aria-label="History">{{ icon("clock", class="nav-icon nav-icon--lg") }}</a>
```

Check which icons are available in the icon macro — `clock` may need to be added or an existing icon reused.

### Template design

`history.html` is a simple list page. The existing `.recent-analyses-*` CSS classes can be reused directly. The toggle mechanism and `is-open` class are unnecessary since the list is always visible. Simplest approach: render the list open by default (add `is-open` class statically or just show the list without the toggle wrapper).

### JS impact

`initRecentAnalysesToggle()` in `ui.ts` has a guard `if (!section) return`. After removing the section from index.html, this function becomes a permanent no-op (history page won't use the collapse pattern). It can be removed entirely, or left as dead code. Cleaner to remove it.

If the history page needs no JS toggle (list is always visible), then `initRecentAnalysesToggle()` should be deleted from `ui.ts` and its call removed from `init()`.

### Test impact

- `TestIndexWithHistory` in `test_history_routes.py` (4 tests): Rewrite to test `/history` route instead of `/`
  - `test_index_shows_recent_analyses` → `test_history_list_shows_analyses`
  - `test_index_no_history` → `test_history_list_empty`
  - `test_index_history_error_graceful` → `test_history_list_error_graceful`
  - `test_index_shows_verdict_badge` → `test_history_list_shows_verdict_badge`
- `test_index_returns_200` in `test_routes.py` (line 19): Should still pass — index page still returns 200, just without recent analyses
- No E2E tests touch recent analyses (confirmed: `grep -rn 'recent.analy' tests/e2e/` returns nothing)

### Requirements

- **R053** (active) — Recent Analyses removed from home page → this slice delivers it
- **R054** (active) — Dedicated /history page → this slice delivers it
- **R055** (active, shared) — All tests pass, zero behavior changes → verified at slice end

### Available icons

Need to check what the icon macro supports for the nav link.

### Risks

None significant. The only subtle point is ensuring the `url_for('main.history_list')` name doesn't collide with `history_detail` — it won't, since Flask uses the function name, and they're different functions.
