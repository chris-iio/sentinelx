# Phase 04: Deep Analysis View - Research

**Researched:** 2026-03-13
**Domain:** Bookmarkable IOC detail page, SQLite-persisted notes/tags, client-side relationship graph, filter bar tag integration
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DEEP-01 | User can click any IOC to open a dedicated detail page at a bookmarkable URL with all provider results in a tabbed layout | Flask route `GET /ioc/<ioc_type>/<path:ioc_value>` renders a Jinja2 template that re-runs enrichment from cache; IOC value is URL-path-encoded; tabbed layout is pure HTML/CSS/TS |
| DEEP-02 | User can add, edit, and delete free-text notes on any IOC; notes survive page refresh and cache clears | New `AnnotationStore` (SQLite table `ioc_annotations`) with CRUD; Flask JSON API (`/api/ioc/<ioc_type>/<path:ioc_value>/notes`); fetch-based TS module with optimistic UI |
| DEEP-03 | User can apply and remove custom text tags on any IOC; tags visible in results list and filterable | Same `AnnotationStore` table adds `tags` column (JSON list); tags serialized as JSON in SQLite; results list card shows tag pills; filter module extended with tag dimension |
| DEEP-04 | User can view a relationship graph on the detail page showing which providers returned data for the IOC and what verdict each reported | Client-side SVG graph (no third-party library); central IOC node connected to provider nodes colored by verdict; data derived from enrichment results already fetched for the page |

</phase_requirements>

---

## Summary

Phase 04 introduces three categories of new work: (1) a dedicated IOC detail page at a bookmarkable URL that reuses existing enrichment data, (2) a persistent annotation system (notes + tags) backed by a new SQLite table, and (3) a client-side relationship graph rendered as SVG.

The detail page (DEEP-01) is the foundation. The IOC value and type are encoded into a Flask route (`/ioc/<ioc_type>/<path:ioc_value>`). On load, it reads all provider results for that IOC from the enrichment cache using the existing `CacheStore`. Results are passed to a Jinja2 template that groups them into tabs — one tab per provider — using the same enrichment rendering logic the results page already uses. The tabbed layout is CSS-only (`<input type="radio">` + `<label>` trick) with no new JS framework required.

The annotation system (DEEP-02, DEEP-03) follows the `CacheStore` pattern exactly: a new `AnnotationStore` class backed by SQLite at `~/.sentinelx/annotations.db`. The schema is one table: `ioc_annotations(ioc_value, ioc_type, notes TEXT, tags TEXT, updated_at)`. Notes are plain text; tags are JSON-serialized lists. Flask exposes a minimal JSON API (`POST/DELETE /api/ioc/...notes` and `POST/DELETE /api/ioc/...tags`). The TS `annotations.ts` module handles fetch calls and DOM updates using the existing `createElement + textContent` pattern (SEC-08).

The relationship graph (DEEP-04) is the most visually novel but technically simplest component. It is a client-side SVG rendered from enrichment data already available on the detail page — no external library needed. The graph places the IOC as a central node and draws edges to provider circles colored by verdict. This is a small, bounded graph (max ~13 nodes) so manual SVG coordinate math is deterministic and readable. No force-directed layout library is needed.

**Primary recommendation:** Build all four requirements in two sequential plans — Plan 01 covers the detail page route + tabbed layout (DEEP-01) and the graph (DEEP-04); Plan 02 covers the annotation store + API + TS module + results list tag display (DEEP-02, DEEP-03).

---

## Standard Stack

### Core (already installed — no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | 3.1 | Route handler + JSON API | Already the web framework; `jsonify` handles CRUD responses |
| SQLite3 | stdlib | AnnotationStore persistence | Same pattern as CacheStore — zero dependency, thread-safe with Lock |
| pytest | existing | Unit + integration tests | Already the test framework; existing conftest fixtures reused |
| TypeScript 5.8 + esbuild | existing | annotations.ts + graph.ts modules | Existing build pipeline; add new modules, re-export from main.ts |
| Tailwind CSS standalone | 3.4.17 | Detail page and annotation UI styles | Existing CSS pipeline; new utility classes picked up automatically |

### No New Third-Party Libraries
The graph (DEEP-04) is a bounded SVG with at most ~13 nodes. A force-directed library (D3, Cytoscape.js) would add 100KB+ and break the existing no-npm-install build pattern. Manual SVG coordinate math for a hub-and-spoke layout is ~50 lines of TS. SVG is natively supported in all target browsers.

The tabbed layout (DEEP-01) uses a CSS-only tab pattern (`<input type="radio" name="tab">` with `<label for>` and `:checked + sibling` CSS rules) — no JS tab library needed.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual SVG graph | D3.js or Cytoscape.js | D3/Cytoscape add 100-300KB bundle weight; hub-and-spoke graph is too simple to justify; breaks no-npm-install convention |
| CSS-only tabs | Alpine.js tab component | Alpine.js not in stack; CSS-only is zero JS, accessibility-compatible with aria attributes |
| New SQLite DB file | Extending cache.db | Separate file (`annotations.db`) keeps concerns clean and allows `CacheStore.clear()` to not destroy user notes |
| JSON API for annotations | Form POST + redirect | JSON API enables optimistic UI without page reload; consistent with existing `/enrichment/status` polling pattern |

**Installation:** None required.

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── annotations/
│   ├── __init__.py
│   └── store.py             # AnnotationStore — SQLite CRUD for notes + tags
├── routes.py                # Edit: add /ioc/<ioc_type>/<path:ioc_value> + /api/ioc/... routes
├── templates/
│   ├── ioc_detail.html      # New: detail page template (extends base.html)
│   └── partials/
│       ├── _ioc_detail_tabs.html    # New: tabbed provider results partial
│       └── _relationship_graph.html # New: SVG graph placeholder (populated by JS)
└── static/src/ts/
    ├── modules/
    │   ├── annotations.ts   # New: notes + tags CRUD via fetch API
    │   └── graph.ts         # New: SVG relationship graph renderer
    └── main.ts              # Edit: import + init annotations and graph modules
tests/
├── test_annotation_store.py # New: unit tests for AnnotationStore
└── test_ioc_detail_routes.py # New: integration tests for detail + API routes
```

### Pattern 1: AnnotationStore (mirrors CacheStore exactly)

**What:** SQLite-backed annotation persistence with the exact same class structure as `CacheStore`.
**When to use:** Whenever user-authored data must survive cache clears and process restarts.

```python
# Source: app/cache/store.py — AnnotationStore follows this pattern verbatim

DEFAULT_ANNOTATIONS_PATH = Path.home() / ".sentinelx" / "annotations.db"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS ioc_annotations (
    ioc_value   TEXT NOT NULL,
    ioc_type    TEXT NOT NULL,
    notes       TEXT NOT NULL DEFAULT '',
    tags        TEXT NOT NULL DEFAULT '[]',
    updated_at  TEXT NOT NULL,
    PRIMARY KEY (ioc_value, ioc_type)
)
"""

class AnnotationStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path if db_path is not None else DEFAULT_ANNOTATIONS_PATH
        self._lock = threading.Lock()
        self._db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        conn = self._connect()
        conn.execute(_CREATE_TABLE)
        conn.commit()
        conn.close()

    def get(self, ioc_value: str, ioc_type: str) -> dict:
        """Return annotation dict with 'notes' (str) and 'tags' (list[str])."""
        ...

    def set_notes(self, ioc_value: str, ioc_type: str, notes: str) -> None:
        """Upsert notes for an IOC."""
        ...

    def set_tags(self, ioc_value: str, ioc_type: str, tags: list[str]) -> None:
        """Upsert tags (serialized as JSON) for an IOC."""
        ...

    def delete(self, ioc_value: str, ioc_type: str) -> None:
        """Delete all annotations for an IOC."""
        ...
```

**Key decisions:**
- Tags stored as JSON string in a TEXT column — avoids a join table for a max of ~20 tags
- `PRIMARY KEY (ioc_value, ioc_type)` — one row per IOC, upserted with `INSERT OR REPLACE`
- `threading.Lock()` on write operations — same as CacheStore (Flask runs threaded)
- Separate `annotations.db` file — `CacheStore.clear()` must NOT destroy user notes

### Pattern 2: IOC Detail Route

**What:** Flask route that reads all cached provider results for one IOC and renders a detail page.
**When to use:** When the analyst clicks an IOC value in the results list.

```python
# Source: adapted from existing routes.py patterns

@bp.route("/ioc/<ioc_type>/<path:ioc_value>")
@limiter.limit("30 per minute")
def ioc_detail(ioc_type: str, ioc_value: str) -> str:
    """Render the deep analysis detail page for a single IOC.

    Reads all cached enrichment results for this IOC from CacheStore.
    Reads existing annotations from AnnotationStore.
    Renders ioc_detail.html with provider results grouped by provider name.

    Uses <path:ioc_value> to handle IOCs containing slashes (URLs).
    """
    # Validate ioc_type against known IOC types
    valid_types = {t.value for t in IOCType}
    if ioc_type not in valid_types:
        return render_template("404.html"), 404

    cache = CacheStore()
    annotations_store = AnnotationStore()

    # Pull all cached results for this IOC across all providers
    provider_results = cache.get_all_for_ioc(ioc_value, ioc_type)
    annotations = annotations_store.get(ioc_value, ioc_type)

    return render_template(
        "ioc_detail.html",
        ioc_value=ioc_value,
        ioc_type=ioc_type,
        provider_results=provider_results,   # list of dicts
        annotations=annotations,             # {notes: str, tags: list[str]}
    )
```

**CRITICAL:** `CacheStore` needs a new method `get_all_for_ioc(ioc_value, ioc_type)` that returns ALL cached provider results for one IOC (not filtering by TTL — the analyst is reviewing historical data). This is a new query: `SELECT provider, result_json FROM enrichment_cache WHERE ioc_value=? AND ioc_type=?`.

### Pattern 3: Annotation JSON API

**What:** Minimal REST API endpoints for notes and tags CRUD.
**When to use:** The annotations.ts module calls these via fetch on user action.

```python
# New routes in routes.py

@bp.route("/api/ioc/<ioc_type>/<path:ioc_value>/notes", methods=["POST"])
@limiter.limit("30 per minute")
def api_set_notes(ioc_type: str, ioc_value: str):
    """Save or update notes for an IOC. Body: {"notes": "..."}."""
    data = request.get_json(silent=True) or {}
    notes = str(data.get("notes", ""))[:10000]  # cap at 10KB
    store = AnnotationStore()
    store.set_notes(ioc_value, ioc_type, notes)
    return jsonify({"ok": True, "notes": notes})

@bp.route("/api/ioc/<ioc_type>/<path:ioc_value>/tags", methods=["POST"])
@limiter.limit("30 per minute")
def api_set_tags(ioc_type: str, ioc_value: str):
    """Add a tag to an IOC. Body: {"tag": "apt29"}."""
    data = request.get_json(silent=True) or {}
    tag = str(data.get("tag", "")).strip()[:100]  # cap tag length
    if not tag:
        return jsonify({"ok": False, "error": "tag cannot be empty"}), 400
    store = AnnotationStore()
    ann = store.get(ioc_value, ioc_type)
    tags = ann["tags"]
    if tag not in tags:
        tags = [*tags, tag]
    store.set_tags(ioc_value, ioc_type, tags)
    return jsonify({"ok": True, "tags": tags})

@bp.route("/api/ioc/<ioc_type>/<path:ioc_value>/tags/<tag>", methods=["DELETE"])
@limiter.limit("30 per minute")
def api_delete_tag(ioc_type: str, ioc_value: str, tag: str):
    """Remove a tag from an IOC."""
    store = AnnotationStore()
    ann = store.get(ioc_value, ioc_type)
    tags = [t for t in ann["tags"] if t != tag]
    store.set_tags(ioc_value, ioc_type, tags)
    return jsonify({"ok": True, "tags": tags})
```

**CSRF note:** The JSON API must be CSRF-exempt (`@csrf.exempt`) or use the CSRF token in the JS fetch headers. Since the existing `CSRFProtect` is app-wide, the cleanest approach for the JSON API is to send the CSRF token in the request body and use `flask_wtf.csrf.validate_csrf` manually, OR to decorate the API routes with `@csrf.exempt`. The latter is simpler and acceptable because these endpoints only affect user-authored annotation data (not security-critical state). Mark with a SEC comment explaining the rationale.

### Pattern 4: IOC Detail Page Tabbed Layout

**What:** CSS-only tab switcher using the `<input type="radio">` pattern.
**When to use:** A fixed set of tabs that don't need dynamic insertion.

```html
<!-- Source: CSS-only tab pattern — no JS dependency -->
<div class="ioc-detail-tabs">
  {% for result in provider_results %}
  <input type="radio" name="provider-tab"
         id="tab-{{ loop.index }}"
         class="tab-radio"
         {% if loop.first %}checked{% endif %}>
  <label for="tab-{{ loop.index }}" class="tab-label">
    {{ result.provider }}
  </label>
  {% endfor %}

  {% for result in provider_results %}
  <div class="tab-panel">
    {# Provider result fields rendered here #}
  </div>
  {% endfor %}
</div>
```

**Tailwind/CSS approach:** Use `peer` classes or custom CSS with `.tab-radio:checked ~ .tab-panel` selector to show the active tab. Since Tailwind standalone doesn't do dynamic `peer` for sibling relationships well with radio buttons, the tab panel visibility is best handled with a small CSS block in the template's `<style>` or a dedicated `.tab-panel` + `.tab-radio:checked` rule in the stylesheet.

### Pattern 5: SVG Relationship Graph (DEEP-04)

**What:** Client-side SVG hub-and-spoke graph. One central IOC node, N provider nodes around it, edges colored by verdict.
**When to use:** The detail page for any IOC with at least one enrichment result.

The graph is rendered by `graph.ts` when it finds a `#relationship-graph` element containing `data-graph-data` (JSON attribute injected by Jinja2).

```typescript
// Source: project pattern — createElement + setAttribute only (SEC-08)

interface GraphNode {
  id: string;        // provider name or ioc value
  label: string;     // display text (truncated)
  verdict: VerdictKey | "ioc";  // controls color
  role: "ioc" | "provider";
}

interface GraphEdge {
  from: string;   // always "ioc"
  to: string;     // provider name
  verdict: VerdictKey;
}

function renderGraph(container: HTMLElement, nodes: GraphNode[], edges: GraphEdge[]): void {
  const svgNS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNS, "svg");
  svg.setAttribute("viewBox", "0 0 600 400");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "IOC relationship graph");

  // Place IOC node at center (300, 200)
  // Distribute provider nodes in a circle around it
  const cx = 300, cy = 200, radius = 150;
  const providerNodes = nodes.filter(n => n.role === "provider");
  providerNodes.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / providerNodes.length;
    const x = cx + radius * Math.cos(angle);
    const y = cy + radius * Math.sin(angle);
    // Draw edge first (under nodes)
    // Draw circle with verdict color
    // Draw label text
  });

  container.appendChild(svg);
}
```

**Verdict color map (consistent with existing CSS):**
```typescript
const VERDICT_COLORS: Record<string, string> = {
  malicious:  "#ef4444",   // red-500 — matches existing .verdict-malicious
  suspicious: "#f97316",   // orange-500
  clean:      "#22c55e",   // green-500
  known_good: "#3b82f6",   // blue-500
  no_data:    "#6b7280",   // gray-500
  error:      "#6b7280",   // gray-500
  ioc:        "#8b5cf6",   // purple-500 — distinct center node
};
```

**Graph data injection:** Jinja2 renders the graph container with embedded JSON:
```html
<div id="relationship-graph"
     data-graph-nodes="{{ graph_nodes | tojson }}"
     data-graph-edges="{{ graph_edges | tojson }}">
</div>
```
The Flask route constructs `graph_nodes` and `graph_edges` from `provider_results`. This keeps rendering logic in Python (where the data is) and avoids a second fetch from the browser.

### Pattern 6: Click-to-Detail from Results Page

**What:** Each IOC card in the results list needs a clickable link to the detail page.
**When to use:** In `_ioc_card.html` — a simple `<a>` tag, not JS navigation.

```html
<!-- In _ioc_card.html — add a detail link to .ioc-card-actions -->
<a href="{{ url_for('main.ioc_detail', ioc_type=ioc.type.value, ioc_value=ioc.value) }}"
   class="btn btn-detail"
   aria-label="View details for {{ ioc.value }}">Detail</a>
```

No JS navigation needed. The link is a standard anchor. On the detail page, the browser's back button returns to the results page.

**Bookmarkable URL constraint:** URLs like `/ioc/domain/evil.com` and `/ioc/url/https://evil.com/beacon` must be valid. Flask's `<path:ioc_value>` converter handles forward slashes in the value. IOC values do not contain `?` or `#` characters (they are canonical/refanged by the pipeline).

### Pattern 7: Tag Display in Results List (DEEP-03)

**What:** Tags stored in `AnnotationStore` must be visible on the IOC cards in the results list and filterable.
**When to use:** After the analyst has tagged IOCs in a previous session.

This requires the results page route to read annotations for all IOCs in the current result set. The `AnnotationStore` needs a `get_all(ioc_values)` bulk query for performance. Tags are injected into the Jinja2 template as `data-tags` attributes on each `.ioc-card`.

**Filter integration:** The existing `filter.ts` `FilterState` gains a `tag: string` dimension. Tag filter pills are rendered dynamically from the set of distinct tags present in `data-tags` attributes across all cards.

### Anti-Patterns to Avoid

- **Storing enrichment results for the detail page via a new fetch:** The detail page must read from `CacheStore` server-side — no client-side fetch to `/enrichment/status` on the detail page, because that polling API is job-based and ephemeral. The route reads from cache directly.
- **Putting tags in a separate SQLite table:** A `TEXT` column storing JSON is correct for tags at this scale (max ~20 tags per IOC). A full tag normalization table adds complexity with no benefit.
- **Using innerHTML to render annotations:** The security constraint SEC-08 applies everywhere — use `textContent` and `createElement`. Notes rendered to the DOM must use `textContent`, never `innerHTML`.
- **Caching annotation reads in JS module state:** Annotations must always be fetched fresh from the API on page load — stale module state causes inconsistency after save/delete cycles.
- **Making the CSRF token optional for the annotation API:** Either send the CSRF token via fetch header (`X-CSRFToken`) or `@csrf.exempt` the JSON routes. Do not silently fail with 400 CSRF errors; the analyst will see save failures with no explanation.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Graph layout algorithm | Force-directed physics simulation | Fixed hub-and-spoke coordinate math | 13 nodes max; force-directed is overkill and adds library weight |
| Tab component | JS-driven tab switching with state | CSS-only `<input type="radio">` pattern | Zero JS, accessible, works without JS enabled |
| SQLite connection pooling | Thread-local connection pool | `sqlite3.connect(check_same_thread=False)` + `threading.Lock()` | CacheStore already uses this pattern; proven safe for Flask threading |
| Tag autocomplete | Full-text search / trie | None (free-text input) | Analysts know their own tags; autocomplete is out of scope |
| Rich text notes | Markdown parser + renderer | Plain `<textarea>` + `textContent` | Markdown increases XSS surface; plain text is correct for SEC-08 |
| URL encoding for IOC values | Custom encoder | Flask `<path:>` converter + `url_for()` with `ioc_value=` kwarg | `url_for` handles encoding; `<path:>` handles decoding |

**Key insight:** Every non-trivial problem in this phase has an existing solution in the codebase. The implementation is additive, not inventive.

---

## Common Pitfalls

### Pitfall 1: URL Routing for IOC Values Containing Slashes
**What goes wrong:** Using `<string:ioc_value>` instead of `<path:ioc_value>` means URL `IOCs` like `https://evil.com/beacon` (type=url) generate a 404 because Flask interprets the slash as a path separator.
**Why it happens:** `<string:>` is the default converter and stops at `/`.
**How to avoid:** Always use `<path:ioc_value>` for the IOC value segment in ALL detail and API routes.
**Warning signs:** URL-type IOCs cannot be opened in the detail view; test with a URL IOC explicitly.

### Pitfall 2: CacheStore TTL Filters Out Detail Page Results
**What goes wrong:** The existing `CacheStore.get()` applies a TTL check. If called with `ttl_seconds` on the detail page, expired results are invisible to the analyst. The detail page is a retrospective view — TTL must NOT apply.
**Why it happens:** The existing `get()` method has mandatory TTL filtering; a careless reuse silently hides old results.
**How to avoid:** Add `CacheStore.get_all_for_ioc(ioc_value, ioc_type) -> list[dict]` that queries without TTL check. This method is additive — it does not change existing cache behavior.
**Warning signs:** Detail page shows 0 provider tabs for IOCs whose cache entries are older than TTL.

### Pitfall 3: CSRF Failures on Annotation API
**What goes wrong:** The fetch calls from `annotations.ts` get rejected with HTTP 400 (CSRF validation failed) because `flask_wtf.CSRFProtect` is app-wide and requires the CSRF token on all non-GET requests.
**Why it happens:** The existing JS code only uses `fetch` for GET requests (the polling endpoint). The annotation API is the first POST/DELETE via `fetch`.
**How to avoid:** Two options: (A) decorate the API routes with `@csrf.exempt` and add a SEC comment, or (B) read the CSRF token from `<meta name="csrf-token">` in `base.html` and send it as an `X-CSRFToken` header in all fetch calls. Option B is more correct but requires adding the meta tag to `base.html`. Choose B for SEC compliance; document in code.
**Warning signs:** Notes save UI shows no error but notes are not saved; check the network tab for HTTP 400.

### Pitfall 4: Tags Not Visible on Results Page After Navigation
**What goes wrong:** Analyst tags an IOC on the detail page, presses Back, and the results page shows no tags because the results page was rendered before the annotation existed (it's server-rendered HTML that doesn't re-query on client navigation).
**Why it happens:** Browser caching or standard form-post HTML navigation means the old results page HTML is served from cache.
**How to avoid:** The results page route reads annotations for ALL IOCs in the result set from `AnnotationStore` before rendering. The browser Back button re-renders from the Flask server (results are a POST response — browsers typically don't cache POST responses). Verify this works by testing the Back button flow explicitly.
**Warning signs:** Tags appear on detail page but not on results page after Back.

### Pitfall 5: Annotation Store File Permissions
**What goes wrong:** `annotations.db` is created without restrictive permissions, leaving analyst notes world-readable.
**Why it happens:** `sqlite3.connect()` uses OS default umask.
**How to avoid:** Follow `CacheStore` pattern exactly: `self._db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)`. The directory is created with 0o700; the `.db` file inherits umask (typically 0o644). To restrict the file itself, use `os.chmod(db_path, 0o600)` after first creation, like CacheStore's SEC-17 pattern.

### Pitfall 6: Graph SVG XSS via IOC Value
**What goes wrong:** IOC value or provider name inserted into SVG `<text>` element via `textContent` is safe, but if inserted via `setAttribute("innerHTML", ...)` or similar, it can trigger XSS in SVG context.
**Why it happens:** SVG has a different content model from HTML; `<script>` in SVG is executable.
**How to avoid:** All SVG text nodes use `document.createTextNode(value)` appended to the `<text>` element. No `textContent` on elements with children; no `setAttribute` with user-controlled values in SVG namespace. The IOC value must go through `createTextNode`.

### Pitfall 7: Detail Page Route Missing from Rate Limiter
**What goes wrong:** The detail page route omits `@limiter.limit()`, making it exempt from rate limiting and an easy DoS vector (each request reads SQLite).
**Why it happens:** Rate limiter decorators are easily forgotten on new routes.
**How to avoid:** All new routes (detail page + all API endpoints) must have `@limiter.limit()`. Use `"30 per minute"` for the detail page (matches settings routes) and `"30 per minute"` for API endpoints.

---

## Code Examples

### AnnotationStore.get_all (bulk read for results page)
```python
# Source: CacheStore.stats() pattern — query without TTL
def get_all_for_ioc_values(
    self, ioc_pairs: list[tuple[str, str]]
) -> dict[str, dict]:
    """Read annotations for multiple IOCs at once.

    Args:
        ioc_pairs: list of (ioc_value, ioc_type) tuples

    Returns:
        Dict mapping "ioc_value|ioc_type" -> {"notes": str, "tags": list[str]}
    """
    result = {}
    with self._connect() as conn:
        for ioc_value, ioc_type in ioc_pairs:
            row = conn.execute(
                "SELECT notes, tags FROM ioc_annotations WHERE ioc_value=? AND ioc_type=?",
                (ioc_value, ioc_type),
            ).fetchone()
            key = f"{ioc_value}|{ioc_type}"
            if row:
                notes, tags_json = row
                result[key] = {"notes": notes, "tags": json.loads(tags_json)}
            else:
                result[key] = {"notes": "", "tags": []}
    return result
```

### CacheStore new method: get_all_for_ioc
```python
# New method on CacheStore — no TTL filter (retrospective view)
def get_all_for_ioc(self, ioc_value: str, ioc_type: str) -> list[dict]:
    """Return all cached results for one IOC, across all providers.

    No TTL check — the detail page shows all historical data.

    Returns:
        List of dicts, each with provider, result_json (parsed), cached_at.
    """
    with self._connect() as conn:
        rows = conn.execute(
            "SELECT provider, result_json, cached_at FROM enrichment_cache "
            "WHERE ioc_value = ? AND ioc_type = ?",
            (ioc_value, ioc_type),
        ).fetchall()
    results = []
    for provider, result_json, cached_at in rows:
        data = json.loads(result_json)
        data["provider"] = provider
        data["cached_at"] = cached_at
        results.append(data)
    return results
```

### TypeScript annotations.ts skeleton
```typescript
// Source: enrichment.ts fetch pattern (SEC-08 compliant)

interface AnnotationResponse {
  ok: boolean;
  notes?: string;
  tags?: string[];
  error?: string;
}

async function saveNotes(iocType: string, iocValue: string, notes: string): Promise<void> {
  const url = `/api/ioc/${iocType}/${encodeURIComponent(iocValue)}/notes`;
  const resp = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),  // reads from <meta name="csrf-token">
    },
    body: JSON.stringify({ notes }),
  });
  const data: AnnotationResponse = await resp.json();
  if (!data.ok) throw new Error(data.error ?? "Failed to save notes");
}

function getCSRFToken(): string {
  const meta = document.querySelector<HTMLMetaElement>('meta[name="csrf-token"]');
  return meta?.content ?? "";
}

export function init(): void {
  const detailPage = document.querySelector<HTMLElement>(".page-ioc-detail");
  if (!detailPage) return;
  // Wire notes textarea + save button
  // Wire tag add input + tag delete buttons
}
```

### TypeScript graph.ts rendering skeleton
```typescript
// Source: project pattern — createElementNS for SVG (SEC-08 compliant)

const SVG_NS = "http://www.w3.org/2000/svg";

export function renderRelationshipGraph(container: HTMLElement): void {
  const nodesAttr = container.getAttribute("data-graph-nodes");
  const edgesAttr = container.getAttribute("data-graph-edges");
  if (!nodesAttr || !edgesAttr) return;

  const nodes: GraphNode[] = JSON.parse(nodesAttr) as GraphNode[];
  const edges: GraphEdge[] = JSON.parse(edgesAttr) as GraphEdge[];

  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 600 400");
  svg.setAttribute("width", "100%");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Provider relationship graph for IOC");

  // ... coordinate math + circle + text creation ...
  container.appendChild(svg);
}

export function init(): void {
  const graphContainer = document.getElementById("relationship-graph");
  if (!graphContainer) return;
  renderRelationshipGraph(graphContainer);
}
```

### Jinja2 CSRF meta tag (add to base.html)
```html
<!-- In base.html <head> — enables JS fetch CSRF -->
<meta name="csrf-token" content="{{ csrf_token() }}">
```

### Filter bar tag extension (filter.ts)
```typescript
// Extend FilterState with tags dimension
interface FilterState {
  verdict: string;
  type: string;
  search: string;
  tag: string;   // NEW — empty string = "all tags"
}

// In applyFilter(), add:
const searchTagLC = filterState.tag.toLowerCase();
const cardTagsRaw = attr(card, "data-tags") || "[]";
const cardTags: string[] = JSON.parse(cardTagsRaw) as string[];
const tagMatch = searchTagLC === "" ||
  cardTags.some(t => t.toLowerCase() === searchTagLC);

card.style.display = verdictMatch && typeMatch && searchMatch && tagMatch ? "" : "none";
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Full-page JS tab frameworks (Bootstrap tabs) | CSS-only radio tab pattern | ~2020 (CSS `:has()` / peer patterns matured) | Zero JS, accessibility-compatible, no library |
| D3.js for all graphs | Manual SVG for small bounded graphs | Industry best practice for small N | ~90KB bundle savings; simpler code |
| innerHTML for dynamic content | createElement + textContent | Phase 01 (SEC-08) | Required by project security policy |
| Separate DB per feature | Single `~/.sentinelx/` directory for all persistence | Already established | Consistent user data location |

**Deprecated/outdated:**
- `url_for()` with `<string:>` converter for IOC values: breaks for URL-type IOCs containing `/`; must use `<path:>`.

---

## Open Questions

1. **CSRF strategy for annotation API**
   - What we know: `flask_wtf.CSRFProtect` is app-wide; all POST/DELETE routes require CSRF validation
   - What's unclear: Whether to use `@csrf.exempt` + SEC comment, or `X-CSRFToken` header pattern
   - Recommendation: Use `X-CSRFToken` header (Option B) — add `<meta name="csrf-token" content="{{ csrf_token() }}">` to `base.html`; read it in `annotations.ts`. This is more correct and keeps CSRF protection active. The `@csrf.exempt` path is simpler but weaker.

2. **Tags visibility on results page: read cost**
   - What we know: The results page may show up to N IOCs (no current hard cap documented). Reading annotations for all of them in one route handler adds SQLite queries.
   - What's unclear: Whether N IOCs causes meaningful latency. Typical analyst pastes are 5-20 IOCs.
   - Recommendation: Use a single `WHERE ioc_value IN (...)` query for the entire batch, not N individual queries. The `get_all_for_ioc_values` method above handles this. For up to 20 IOCs, this is negligible.

3. **Detail page when IOC is not in cache**
   - What we know: An analyst can navigate directly to `/ioc/ipv4/1.2.3.4` without having run enrichment first.
   - What's unclear: Whether to show an empty detail page, redirect to home, or show a "not yet enriched" message.
   - Recommendation: Show the detail page with a "No enrichment data available for this IOC. Run online enrichment from the main page." message. Still show the notes/tags UI so the analyst can annotate IOCs they've researched externally. The route renders correctly with an empty `provider_results` list.

4. **Graph layout for IOCs with many providers (13 providers)**
   - What we know: Up to 13 providers are registered. A 13-node circular layout around a center node at radius 150 in a 600x400 viewBox is geometrically tight but renderable.
   - What's unclear: Whether provider labels (which can be long, e.g., "OTX AlienVault") overlap at 13 nodes.
   - Recommendation: Truncate labels to 12 characters in the graph. Use a `title` element inside each SVG group for the full name (accessible tooltip). Increase SVG viewBox to `0 0 700 500` if overlap is observed during development.

---

## Validation Architecture

nyquist_validation is enabled in .planning/config.json.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, no new install needed) |
| Config file | None at project root — run via `python -m pytest` |
| Quick run command | `python -m pytest tests/test_annotation_store.py tests/test_ioc_detail_routes.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEEP-01 | `GET /ioc/<ioc_type>/<path:ioc_value>` returns 200 | integration | `python -m pytest tests/test_ioc_detail_routes.py::test_detail_page_200 -x` | ❌ Wave 0 |
| DEEP-01 | Detail page with no cache shows "no data" message | integration | `python -m pytest tests/test_ioc_detail_routes.py::test_detail_page_empty_cache -x` | ❌ Wave 0 |
| DEEP-01 | Detail page with cached results shows provider tabs | integration | `python -m pytest tests/test_ioc_detail_routes.py::test_detail_page_with_results -x` | ❌ Wave 0 |
| DEEP-01 | URL-type IOC with slashes routes correctly | integration | `python -m pytest tests/test_ioc_detail_routes.py::test_detail_url_ioc -x` | ❌ Wave 0 |
| DEEP-01 | `CacheStore.get_all_for_ioc()` returns results without TTL filter | unit | `python -m pytest tests/test_cache_store.py::test_get_all_for_ioc -x` | ❌ Wave 0 (existing file, new test) |
| DEEP-02 | `AnnotationStore` creates DB and table on init | unit | `python -m pytest tests/test_annotation_store.py::test_init -x` | ❌ Wave 0 |
| DEEP-02 | `set_notes` / `get` round-trip | unit | `python -m pytest tests/test_annotation_store.py::test_notes_round_trip -x` | ❌ Wave 0 |
| DEEP-02 | Notes survive a `CacheStore.clear()` call | integration | `python -m pytest tests/test_annotation_store.py::test_notes_survive_cache_clear -x` | ❌ Wave 0 |
| DEEP-02 | `POST /api/ioc/<type>/<value>/notes` saves notes | integration | `python -m pytest tests/test_ioc_detail_routes.py::test_api_set_notes -x` | ❌ Wave 0 |
| DEEP-02 | Notes API returns 400 for oversize notes | integration | `python -m pytest tests/test_ioc_detail_routes.py::test_api_notes_size_cap -x` | ❌ Wave 0 |
| DEEP-03 | `set_tags` / `get` round-trip | unit | `python -m pytest tests/test_annotation_store.py::test_tags_round_trip -x` | ❌ Wave 0 |
| DEEP-03 | `POST /api/ioc/<type>/<value>/tags` adds tag | integration | `python -m pytest tests/test_ioc_detail_routes.py::test_api_add_tag -x` | ❌ Wave 0 |
| DEEP-03 | `DELETE /api/ioc/<type>/<value>/tags/<tag>` removes tag | integration | `python -m pytest tests/test_ioc_detail_routes.py::test_api_delete_tag -x` | ❌ Wave 0 |
| DEEP-03 | Duplicate tags not stored twice | unit | `python -m pytest tests/test_annotation_store.py::test_no_duplicate_tags -x` | ❌ Wave 0 |
| DEEP-03 | Tags visible in results page HTML | integration | `python -m pytest tests/test_ioc_detail_routes.py::test_tags_on_results_page -x` | ❌ Wave 0 |
| DEEP-04 | Graph data (nodes + edges) passed to template | integration | `python -m pytest tests/test_ioc_detail_routes.py::test_graph_data_in_context -x` | ❌ Wave 0 |
| DEEP-04 | Graph SVG renders (visual) | manual | Open `/ioc/<type>/<value>` in browser, verify graph appears | N/A |
| DEEP-04 | Filter bar shows tag pills when tags present | manual | Tag an IOC, return to results, verify tag pill appears | N/A |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_annotation_store.py tests/test_ioc_detail_routes.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_annotation_store.py` — covers DEEP-02 and DEEP-03 unit tests (init, notes CRUD, tags CRUD, no-duplicates, notes survive cache clear)
- [ ] `tests/test_ioc_detail_routes.py` — covers DEEP-01 (route 200/empty/with-results, URL IOC routing), DEEP-02/03 API tests, DEEP-04 graph data
- [ ] Add `test_get_all_for_ioc` to existing `tests/test_cache_store.py` (new method, new test in existing file)
- [ ] Add `<meta name="csrf-token">` to `app/templates/base.html` (CSRF strategy prerequisite)

*(No new framework install needed — pytest already present)*

---

## Sources

### Primary (HIGH confidence)
- Existing codebase: `app/cache/store.py` — canonical SQLite pattern (CacheStore) that AnnotationStore mirrors exactly
- Existing codebase: `app/routes.py` — route handler patterns, jsonify, limiter decorators
- Existing codebase: `app/static/src/ts/modules/enrichment.ts` — DOM construction pattern (SEC-08), fetch pattern
- Flask documentation (verified from knowledge): `<path:>` converter handles slashes in URL segments
- Python stdlib `sqlite3` + `threading.Lock` — same as CacheStore, no new library

### Secondary (MEDIUM confidence)
- CSS-only radio tab pattern — well-documented browser feature (`:checked` + sibling selectors), supported in all modern browsers; no external verification needed
- SVG coordinate math for hub-and-spoke layout — standard geometry; no library required; coordinates verified by inspection

### Tertiary (LOW confidence)
- `flask_wtf` CSRF `X-CSRFToken` header behavior — based on project knowledge of Flask-WTF; the specific header name `X-CSRFToken` is the Flask-WTF convention but should be verified against the installed version during implementation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new libraries; all patterns established in the codebase
- Architecture (AnnotationStore): HIGH — direct CacheStore clone; SQLite + threading.Lock is proven
- Architecture (detail route): HIGH — Flask `<path:>` converter + Jinja2 template is straightforward
- Architecture (graph): HIGH — bounded SVG, no library, hub-and-spoke math is deterministic
- Pitfalls: HIGH for CSRF/URL routing/TTL; MEDIUM for tag display performance (untested at scale)
- Test coverage: HIGH — all behaviors mapped to specific test classes/methods

**Research date:** 2026-03-13
**Valid until:** 2026-06-13 (all dependencies stable; Flask 3.1 and SQLite3 stdlib are not fast-moving)
