# Phase 01: Annotations Removal - Research

**Researched:** 2026-03-15
**Domain:** Python/Flask feature removal, TypeScript module cleanup
**Confidence:** HIGH (all findings from direct codebase inspection)

## Summary

The annotations feature is self-contained and fully mapped. Every surface it touches has been
identified: one Python module, three routes in `app/routes.py`, two templates, one TypeScript
module, one secondary TypeScript module (filter.ts), and two test files (14 + 15 = 29 tests
that must be deleted or rewritten). No external package dependencies are exclusive to
annotations — `sqlite3` is stdlib and also used by `CacheStore`.

The removal is surgical. The Python side requires deleting one directory, editing one file
(`routes.py`), and removing two template blocks. The TypeScript side requires deleting one
module file and editing two files (`main.ts`, `filter.ts`). The rebuilt JS bundle must be
committed. No CSS changes are needed — annotation styles do not exist in `input.css` or
`dist/style.css` (verified). Test cleanup is the bulk of the work: delete one test file,
rewrite one, and rebuild the JS artifact.

**Primary recommendation:** Delete `app/annotations/`, excise it from `routes.py`, remove
annotation blocks from `ioc_detail.html` and `_ioc_card.html`, excise `annotations.ts` from
the TS bundle, strip tag-filter logic from `filter.ts`, delete `test_annotation_store.py`, and
rewrite the annotation-specific tests in `test_ioc_detail_routes.py`. Rebuild `dist/main.js`
with `make js`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CLEAN-01 | Annotations feature (notes, tags, tag filtering, AnnotationStore) is fully removed — no notes/tags UI on any page | Removal inventory is complete: module dir, routes, templates, TS modules, tests all identified |
| CLEAN-02 | Annotation API routes (/api/annotations/*) no longer exist | Routes are actually `/api/ioc/<type>/<value>/notes`, `/api/ioc/<type>/<value>/tags`, and `/api/ioc/<type>/<value>/tags/<tag>` — three routes in routes.py to delete |
</phase_requirements>

---

## Complete Removal Inventory

This section replaces "Standard Stack" for this phase — the work is deletion, not installation.

### Python: Files to Delete Entirely

| File | Why |
|------|-----|
| `app/annotations/__init__.py` | Empty (`__init__` for package) |
| `app/annotations/store.py` | `AnnotationStore` class — entire implementation |

The `app/annotations/` directory can be deleted after removing both files.

### Python: app/routes.py Edits (HIGH confidence — line numbers verified)

**Import to remove (line 30):**
```python
from app.annotations.store import AnnotationStore
```

**Annotation read block to remove from `analyze()` route (lines 180-185):**
```python
# Read annotations for all extracted IOCs so tags can be displayed on cards
if iocs:
    ioc_pairs = [(ioc.value, ioc.type.value) for ioc in iocs]
    annotations_map = AnnotationStore().get_all_for_ioc_values(ioc_pairs)
else:
    annotations_map = {}
```

**`annotations_map=annotations_map` kwarg to remove from `render_template` in `analyze()` (line 194).**

**`ioc_detail()` route — two items to remove:**
- Line in docstring: `Reads analyst annotations from AnnotationStore.`
- Two lines in route body (lines 317-318):
  ```python
  annotation_store = AnnotationStore()
  annotations = annotation_store.get(ioc_value, ioc_type)
  ```
- `annotations=annotations` kwarg from `render_template` call (line 341).

**Three annotation API route functions to delete entirely (lines 347-401):**
- `api_set_notes` — `POST /api/ioc/<ioc_type>/<path:ioc_value>/notes`
- `api_add_tag` — `POST /api/ioc/<ioc_type>/<path:ioc_value>/tags`
- `api_delete_tag` — `DELETE /api/ioc/<ioc_type>/<path:ioc_value>/tags/<tag>`

Note: the requirement text says `/api/annotations/*` but the actual routes are
`/api/ioc/<type>/<value>/notes` and `/api/ioc/<type>/<value>/tags[/<tag>]`. The intent of
CLEAN-02 is to remove the annotation API routes regardless of URL path — confirmed.

### Templates: Blocks to Remove

**`app/templates/ioc_detail.html`:**
- Remove `data-tags="{{ annotations.tags | tojson }}"` attribute from the outer `<div>`
  (line 4 — but keep the div with its other attributes).
- Delete the entire `{# ---- Annotations ---- #}` section (lines 21-57): the
  `<div class="detail-annotations">` block containing notes textarea, save button, tag pills,
  and tag input.

**`app/templates/partials/_ioc_card.html`:**
- Delete lines 1-2: `{% set ann_key = ... %}` and `{% set card_tags = ... %}`
- Remove `data-tags="{{ card_tags | tojson }}"` attribute from the `<div class="ioc-card">`
  (keep the div, just remove the attribute).
- Delete lines 24-30: the `{% if card_tags %}` block that renders `tag-pill--sm` pills.

### TypeScript: Files to Delete Entirely

| File | Why |
|------|-----|
| `app/static/src/ts/modules/annotations.ts` | Entire notes/tags CRUD module |

### TypeScript: app/static/src/ts/main.ts Edits

Remove two lines (lines 19 and 30):
```typescript
import { init as initAnnotations } from "./modules/annotations";
// ...
initAnnotations();
```

### TypeScript: app/static/src/ts/modules/filter.ts Edits

The `FilterState` interface has a `tag` field, and `init()` has tag-filter logic spanning
roughly lines 158-216. This block:
1. Reads `data-tags` from each card
2. Collects unique tags into a `Set`
3. Dynamically renders a `.filter-tags` row of `.filter-tag-pill` buttons
4. Wires click handlers to `filterState.tag`
5. Uses `tagMatch` inside `applyFilter()` to filter cards by tag

**Items to remove from filter.ts:**
- `tag: string` field from `FilterState` interface
- `const tagLC = filterState.tag.toLowerCase();` inside `applyFilter()`
- The `cardTagsRaw`/`cardTags`/`tagMatch` block inside `applyFilter()`
- `tagMatch &&` from the card visibility condition
- The entire tag-pills collection and rendering block at the end of `init()`
  (roughly lines 158-216)

After editing, `applyFilter()` filters only on `verdict`, `type`, and `search`.

### Build Artifact to Rebuild

After TypeScript edits, run:
```bash
make js
```
This runs esbuild and updates `app/static/dist/main.js`. This file must be committed
alongside the source changes.

### CSS: No Changes Needed

Verified: no annotation CSS classes (`tag-pill`, `filter-tag`, `detail-annot`, etc.) exist
in `app/static/src/input.css` or `app/static/dist/style.css`. The CSS is either
handled by existing generic classes or was never defined (the UI may have been unstyled
or used inline styles).

---

## Test Cleanup Inventory

### Tests to Delete Entirely

| File | Count | Reason |
|------|-------|--------|
| `tests/test_annotation_store.py` | 14 tests | Tests `AnnotationStore` which is being deleted |

### Tests to Rewrite in `tests/test_ioc_detail_routes.py`

The file has 15 tests across 3 classes. Breakdown:

**`TestIocDetailRoute` (7 tests) — keep and adapt:**
- `test_detail_page_200` — keep as-is (no annotation dependency)
- `test_detail_invalid_type` — keep as-is
- `test_detail_page_empty_cache` — remove `annotations_store_module` monkeypatch; remove import
- `test_detail_page_with_results` — remove `annotations_store_module` monkeypatch; remove import
- `test_detail_url_ioc` — remove `annotations_store_module` monkeypatch; remove import
- `test_graph_data_in_context` — remove `annotations_store_module` monkeypatch; remove import
- `test_detail_annotations_prepopulated` — **DELETE** (tests annotation pre-population)

**`TestAnnotationApiRoutes` (7 tests) — DELETE entire class:**
All tests verify the annotation API routes which are being removed.

**`TestTagsOnResultsPage` (1 test) — DELETE:**
Tests tag display on results page via `annotations_map`.

**After rewrite:** File should contain ~6 tests, all in `TestIocDetailRoute`.

The top-level imports also need cleanup:
- Remove: `from app.annotations.store import AnnotationStore`
- Keep: `from app.cache.store import CacheStore`

---

## Architecture Patterns

### Removal Order

The safest removal order avoids `ImportError` at any intermediate step:

1. **Delete test files first** (no app dependency)
2. **Edit `routes.py`** — remove import + all annotation usage
3. **Delete `app/annotations/`** — now safe since nothing imports it
4. **Edit templates** — remove annotation blocks
5. **Edit `filter.ts`** — remove tag-filter logic
6. **Delete `annotations.ts`**
7. **Edit `main.ts`** — remove import + init call
8. **Run `make js`** — rebuild bundle
9. **Verify with `flask --debug run`** — confirms no import errors
10. **Run full test suite** — confirms clean pass

### Flask Import Error Pitfall

Flask registers routes at import time. If `routes.py` still imports `AnnotationStore` when
`app/annotations/` is deleted, `flask run` throws `ImportError`. The correct sequence is:
remove the import from `routes.py` *before* deleting the module directory.

### Template Variable Cleanup

After removing `annotations_map=annotations_map` from the `analyze()` `render_template` call,
the `_ioc_card.html` partial uses `annotations_map is defined` as a guard — this evaluates
to `False` in Jinja2 when the variable is not passed. The template already handles this
gracefully (`... if annotations_map is defined else []`). However, the goal is clean
removal — delete the guard and all annotation logic from the partial entirely.

Similarly, the `ioc_detail()` route passes `annotations=annotations` to the template. After
removing this, the `ioc_detail.html` template must not reference `annotations` anywhere.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Rebuilding JS bundle | Custom esbuild invocation | `make js` (already wired) |
| Verifying no import errors | Manual inspection | `flask --debug run` in a subprocess / import check |
| Counting remaining tests | Manual count | `pytest --collect-only -q` |

---

## Common Pitfalls

### Pitfall 1: Deleting Module Before Updating Importer

**What goes wrong:** `app/annotations/` is deleted while `routes.py` still has
`from app.annotations.store import AnnotationStore`. Flask raises `ModuleNotFoundError`
on startup.

**How to avoid:** Edit `routes.py` to remove the import and all usages in the same commit
step, *before* deleting the directory.

**Warning signs:** `ModuleNotFoundError: No module named 'app.annotations'`

### Pitfall 2: Stale `dist/main.js` in Repository

**What goes wrong:** TypeScript source is edited but `make js` is not run. The committed
`dist/main.js` still contains the annotations module code. Tests pass, but the browser
would still receive the old bundle.

**How to avoid:** Always run `make js` after TypeScript edits. Include `dist/main.js` in
the same commit as the TS source changes.

**Warning signs:** `dist/main.js` unchanged after TypeScript edits (check `git diff --stat`).

### Pitfall 3: Leaving `data-tags` Attribute on IOC Cards

**What goes wrong:** `data-tags` is removed from `_ioc_card.html` template and from
`filter.ts`, but the card's `<div>` still renders `data-tags="[]"` because the template
wasn't fully cleaned up. This is cosmetic but creates noise.

**How to avoid:** Remove the entire `data-tags` attribute from the card div, not just the
Jinja2 logic that populates it.

### Pitfall 4: Partial Cleanup of `test_ioc_detail_routes.py`

**What goes wrong:** `TestAnnotationApiRoutes` is deleted but the `import AnnotationStore`
at the top of the file remains, causing `ImportError` once `app/annotations/` is gone.

**How to avoid:** After deleting test classes, audit all top-level imports in the file and
remove `from app.annotations.store import AnnotationStore`.

### Pitfall 5: Forgetting the Monkeypatch in Retained Tests

**What goes wrong:** Tests in `TestIocDetailRoute` use
`monkeypatch.setattr(annotations_store_module, ...)`. After removing the annotation module,
these monkeypatches reference a deleted module and raise `AttributeError`/`ModuleNotFoundError`.

**How to avoid:** For each retained test, remove:
- `import app.annotations.store as annotations_store_module`
- `monkeypatch.setattr(annotations_store_module, ...)`

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (confirmed in `tests/conftest.py`) |
| Config file | `pytest.ini` or `pyproject.toml` (check project root) |
| Quick run command | `pytest tests/test_ioc_detail_routes.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLEAN-01 | No annotation UI in results page HTML | integration | `pytest tests/test_ioc_detail_routes.py -x -q` | ✅ (rewrite needed) |
| CLEAN-01 | No annotation UI in IOC detail page HTML | integration | `pytest tests/test_ioc_detail_routes.py -x -q` | ✅ (rewrite needed) |
| CLEAN-01 | `flask run` starts without import errors | smoke | `python -c "from app import create_app; create_app()"` | ❌ Wave 0 |
| CLEAN-02 | `/api/ioc/*/notes` returns 404 | integration | `pytest tests/test_ioc_detail_routes.py::TestAnnotationRoutes404 -x` | ❌ Wave 0 |
| CLEAN-02 | `/api/ioc/*/tags` returns 404 | integration | `pytest tests/test_ioc_detail_routes.py::TestAnnotationRoutes404 -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_ioc_detail_routes.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_ioc_detail_routes.py::TestAnnotationRoutes404` — new test class asserting
  routes return 404; covers CLEAN-02 directly
- [ ] Smoke test assertion in `test_ioc_detail_routes.py` or a standalone `test_startup.py`
  confirming `create_app()` succeeds without import errors — covers CLEAN-01 startup criterion

---

## Code Examples

### Checking Route Removal (Success Criterion)

```python
# Verify annotation routes return 404 after removal
def test_annotation_notes_route_gone(client) -> None:
    response = client.post("/api/ioc/ipv4/1.2.3.4/notes",
                           json={"notes": "test"})
    assert response.status_code == 404

def test_annotation_tags_route_gone(client) -> None:
    response = client.post("/api/ioc/ipv4/1.2.3.4/tags",
                           json={"tag": "apt29"})
    assert response.status_code == 404

def test_annotation_tag_delete_route_gone(client) -> None:
    response = client.delete("/api/ioc/ipv4/1.2.3.4/tags/apt29")
    assert response.status_code == 404
```

### Verifying Clean `ioc_detail.html` After Removal

```python
def test_ioc_detail_no_annotation_ui(client) -> None:
    response = client.get("/ioc/ipv4/1.2.3.4")
    assert response.status_code == 200
    html = response.data.decode()
    assert "ioc-notes" not in html
    assert "detail-annotations" not in html
    assert "tag-input" not in html
    assert "Add tag" not in html
```

### Verifying Clean Results Page After Removal

```python
def test_results_page_no_tag_data(client) -> None:
    response = client.post("/analyze",
                           data={"text": "1.2.3.4", "mode": "offline"})
    assert response.status_code == 200
    html = response.data.decode()
    assert 'data-tags="' not in html
```

### Import Smoke Test

```python
def test_app_creates_without_import_error() -> None:
    from app import create_app
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False,
                      "SERVER_NAME": "localhost"})
    assert app is not None
```

---

## State of the Art

Not applicable — this phase is pure removal, not adoption of new technology.

---

## Open Questions

1. **CSS classes `tag-pill`, `filter-tag-pill`, `detail-annotations`, etc.**
   - What we know: These classes do not exist in `input.css` or `dist/style.css`.
   - What's unclear: Were they ever defined? Do they cause any visible impact if the HTML
     still contained them?
   - Recommendation: Not a blocker. Since the HTML blocks are being deleted, these classes
     disappear with the HTML. No CSS file changes required.

2. **`data-tags` attribute on ioc-card div**
   - What we know: `cards.ts` reads `data-verdict` and other card attributes; it does not
     read `data-tags`. `filter.ts` reads `data-tags` for tag filtering.
   - What's unclear: Does any other module reference `data-tags`?
   - Recommendation: After removing the tag-filter section from `filter.ts`, do a final
     grep for `data-tags` in `app/static/src/ts/` to confirm no other TS module reads it.
     Then the attribute removal from the template is safe.

---

## Sources

### Primary (HIGH confidence)

All findings from direct inspection of the SentinelX codebase at `/home/chris/projects/sentinelx/`.

| File | Finding |
|------|---------|
| `app/annotations/store.py` | `AnnotationStore` class — full SQLite implementation |
| `app/annotations/__init__.py` | Empty (1-line file) |
| `app/routes.py` | Import on line 30; usage in `analyze()` lines 180-194; `ioc_detail()` lines 307-341; three API routes lines 347-401 |
| `app/templates/ioc_detail.html` | `data-tags` on outer div; `detail-annotations` section lines 21-57 |
| `app/templates/partials/_ioc_card.html` | `ann_key`/`card_tags` variables lines 1-2; `data-tags` attribute; tag-pill block lines 24-30 |
| `app/static/src/ts/modules/annotations.ts` | Full notes/tags CRUD module (226 lines) |
| `app/static/src/ts/main.ts` | Import line 19; `initAnnotations()` call line 30 |
| `app/static/src/ts/modules/filter.ts` | `tag` in `FilterState`; `tagMatch` in `applyFilter()`; tag-pill rendering block lines 158-216 |
| `tests/test_annotation_store.py` | 14 tests — all must be deleted |
| `tests/test_ioc_detail_routes.py` | 15 tests — 6 retained, 9 deleted/rewritten |
| `app/static/src/input.css` | No annotation CSS classes present (verified) |
| `app/static/dist/style.css` | No annotation CSS classes present (verified) |

## Metadata

**Confidence breakdown:**
- Removal inventory: HIGH — every file and line identified from direct codebase read
- Test cleanup: HIGH — test files read in full, counts verified with `pytest --collect-only`
- CSS impact: HIGH — verified via Python string search of both CSS files
- Build artifact: HIGH — `make js` is the established project pattern

**Research date:** 2026-03-15
**Valid until:** Until any annotation-adjacent code is modified (stable — no external dependencies)
