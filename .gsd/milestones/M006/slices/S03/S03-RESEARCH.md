# S03: URL IOC End-to-End Polish — Research

**Depth:** Targeted  
**Slice risk:** Low  
**Requirement:** R033 (active) — URL IOCs extracted, enriched by URLhaus/OTX/VT/ThreatFox, displayed correctly with filter pills, detail page handles URL values with slashes.

## Summary

URL IOC support is **already built** across the entire backend stack — extraction, classification, enrichment adapters (4 providers), filter pill CSS, type badge CSS. The slice is polish/verification work with **one real bug to fix** and **E2E test coverage to add**.

### What exists and works

| Layer | File(s) | Status |
|---|---|---|
| Extraction | `app/pipeline/extractor.py` — `iocextract.extract_urls(text, refang=True)` | ✅ Working, unit-tested in `tests/test_extractor.py::TestExtractURLs` |
| Classification | `app/pipeline/classifier.py` — `_RE_URL` regex, precedence 5 | ✅ Working, URL type assigned correctly |
| URLhaus adapter | `app/enrichment/adapters/urlhaus.py` — `IOCType.URL` in `_ENDPOINT_MAP` | ✅ Working, 33 unit tests in `tests/test_urlhaus.py` |
| OTX adapter | `app/enrichment/adapters/otx.py` — `IOCType.URL` in `_SECTION_MAP` + `supported_types` | ✅ Working |
| VirusTotal adapter | `app/enrichment/adapters/virustotal.py` — `IOCType.URL` in `_URL_BUILDERS` + `supported_types` | ✅ Working |
| ThreatFox adapter | `app/enrichment/adapters/threatfox.py` — `IOCType.URL` in `supported_types` | ✅ Working |
| Filter pill CSS | `app/static/src/input.css:882` — `.filter-pill--url.filter-pill--active` | ✅ Styled |
| Type badge CSS | `app/static/src/input.css:1036` — `.ioc-type-badge--url` | ✅ Styled |
| Tailwind safelist | `tailwind.config.js:14,38` — both classes safelisted | ✅ Won't be purged |
| Filter bar template | `app/templates/partials/_filter_bar.html` — dynamic pills from `grouped.keys()` | ✅ URL pill renders when URL IOCs present |
| IOC card template | `app/templates/partials/_ioc_card.html:34` — `ioc-type-badge--{{ ioc.type.value }}` | ✅ Badge renders for any type |
| Detail page template | `app/templates/ioc_detail.html` — type badge, graph, provider results | ✅ Works for any IOC type |
| Detail page route | `app/routes.py:386` — `@bp.route("/ioc/<ioc_type>/<path:ioc_value>")` | ✅ `<path:>` converter handles slashes |
| Unit test: URL route | `tests/test_ioc_detail_routes.py:92-97` — `GET /ioc/url/https://evil.com/beacon` → 200 | ✅ Passing |

### Bug: Detail link href mismatch (`/detail/` vs `/ioc/`)

**This is the one real bug this slice must fix.**

- `injectDetailLink()` in `app/static/src/ts/modules/enrichment.ts:216` generates: `/detail/<type>/<encoded_value>`
- `injectDetailLink()` in `app/static/src/ts/modules/history.ts:71` generates: `/detail/<type>/<encoded_value>`
- Flask route is: `@bp.route("/ioc/<ioc_type>/<path:ioc_value>")` → `/ioc/<type>/<value>`
- **Result:** Clicking "View full detail →" on any IOC card returns a 404.
- The existing E2E test at `tests/e2e/test_results_page.py:413-416` asserts `/detail/` — this test is **incorrect** (asserts for the broken behavior).
- The KNOWLEDGE.md entry "SentinelX detail link route is /detail/...not /ioc/" is **incorrect** — it was written before or without checking the Flask route table.

**Fix:** Change both `injectDetailLink()` functions from `/detail/` to `/ioc/`. Update the E2E test assertion. Correct the KNOWLEDGE.md entry.

**Encoding note:** `encodeURIComponent()` in JS encodes `https://evil.com/payload.exe` → `https%3A%2F%2Fevil.com%2Fpayload.exe`. Flask's `<path:>` converter auto-decodes `%2F` → `/`, so the `ioc_value` parameter receives the raw URL. Verified: both encoded and raw paths return 200 and decode to identical `ioc_value`. No encoding issue.

### What's missing: E2E test coverage

No E2E test currently exercises the URL IOC flow end-to-end:
- No test submits text containing a URL and verifies a URL-type card appears
- No test verifies the URL filter pill renders and filters correctly
- No test verifies the URL type badge displays "URL"
- No test clicks through to the detail page for a URL IOC
- The `MULTI_TYPE_IOCS` fixture in `test_results_page.py` contains no URLs
- The `MIXED_IOCS` fixture in `test_extraction.py` contains a URL but has no URL-specific assertions

## Recommendation

Three tasks, all straightforward:

1. **Fix detail link bug** — Change `/detail/` to `/ioc/` in both `enrichment.ts:216` and `history.ts:71`. Update the E2E test assertion at `test_results_page.py:415`. Run `make js` to rebuild. Correct KNOWLEDGE.md entry.

2. **Add URL E2E tests** — New test file `tests/e2e/test_url_e2e.py` covering:
   - Submit text with URL → verify URL card appears with correct type badge
   - Verify URL filter pill renders in filter bar
   - Click URL filter pill → only URL cards visible
   - Online mode with URL mock → verify enrichment, verdict, detail link
   - Click detail link → verify detail page loads at `/ioc/url/...` with correct content
   - Use the existing page object + mock patterns from `test_results_page.py`

3. **Verify existing unit tests still pass** — Run full test suite; no code changes to backend needed.

## Implementation Landscape

### Files to modify

| File | Change |
|---|---|
| `app/static/src/ts/modules/enrichment.ts:216` | `/detail/` → `/ioc/` |
| `app/static/src/ts/modules/history.ts:71` | `/detail/` → `/ioc/` |
| `tests/e2e/test_results_page.py:415` | Assert `/ioc/` instead of `/detail/` |
| `.gsd/KNOWLEDGE.md` | Correct the "detail link route" entry |

### Files to create

| File | Purpose |
|---|---|
| `tests/e2e/test_url_e2e.py` | URL IOC end-to-end test suite |

### Files unchanged (confirmed working)

- `app/pipeline/extractor.py` — URL extraction works
- `app/pipeline/classifier.py` — URL classification works
- `app/enrichment/adapters/urlhaus.py` — URL enrichment works
- `app/enrichment/adapters/otx.py` — URL enrichment works
- `app/enrichment/adapters/virustotal.py` — URL enrichment works
- `app/enrichment/adapters/threatfox.py` — URL enrichment works
- `app/routes.py` — Detail page route handles URLs correctly
- `app/templates/ioc_detail.html` — Renders correctly for URL type
- `app/templates/partials/_ioc_card.html` — Type badge renders for URL
- `app/templates/partials/_filter_bar.html` — Filter pill renders for URL
- `app/static/src/input.css` — URL CSS classes exist
- `tailwind.config.js` — URL classes safelisted

### Build commands

- `make js` — rebuild TypeScript after fixing detail link
- `make css` — not needed (CSS already has URL classes)
- `python3 -m pytest tests/ -x -q --ignore=tests/e2e` — unit tests (930 pass currently)
- `python3 -m pytest tests/e2e/test_url_e2e.py -x -v` — new URL E2E tests
- `python3 -m pytest tests/e2e/test_results_page.py -x -v` — existing E2E test (after fixing assertion)

### E2E mock pattern for URL IOCs

New URL mock response should follow the existing pattern in `conftest.py:MOCK_ENRICHMENT_RESPONSE_8888`:

```python
MOCK_ENRICHMENT_RESPONSE_URL = {
    "total": 2,
    "done": 2,
    "complete": True,
    "next_since": 2,
    "results": [
        {
            "type": "result",
            "ioc_value": "https://malware.example.com/payload.exe",
            "ioc_type": "url",
            "provider": "URLhaus",
            "verdict": "malicious",
            "detection_count": 1,
            "total_engines": 1,
            "scan_date": "2026-03-15T12:00:00Z",
            "raw_stats": {"url_status": "online"},
        },
        {
            "type": "result",
            "ioc_value": "https://malware.example.com/payload.exe",
            "ioc_type": "url",
            "provider": "VirusTotal",
            "verdict": "malicious",
            "detection_count": 5,
            "total_engines": 70,
            "scan_date": "2026-03-15T12:00:00Z",
            "raw_stats": {},
        },
    ],
}
```

### Risk assessment

- **Detail link fix:** Zero risk. Two-character path change in two files. `make js` rebuilds.
- **E2E tests:** Low risk. Follow established patterns. No flaky timing — use `setup_enrichment_route_mock()` BEFORE navigation (per KNOWLEDGE.md).
- **Flask path handling:** Verified working — `<path:ioc_value>` captures URL with slashes, `encodeURIComponent` encoding is decoded correctly by Flask.

### Tools binary note

Per KNOWLEDGE.md: `tools/tailwindcss` may be absent in worktrees. Only matters if CSS rebuild is needed — it's NOT needed for this slice (URL CSS already exists). If `make js` needs esbuild, verify `tools/esbuild` presence similarly. `make js` target should be checked.

### Verification commands

```bash
# 1. Confirm detail link fix compiled into JS
grep -c "/ioc/" app/static/dist/main.js   # should find occurrences
grep -c "/detail/" app/static/dist/main.js # should be 0 (or only in non-link contexts)

# 2. Unit tests pass
python3 -m pytest tests/ -x -q --ignore=tests/e2e

# 3. URL detail route works
python3 -c "
import sys; sys.path.insert(0, '.')
from app import create_app
app = create_app()
with app.test_client() as c:
    r = c.get('/ioc/url/https://evil.com/payload.exe')
    assert r.status_code == 200, f'Got {r.status_code}'
    print('URL detail route: OK')
"

# 4. E2E tests pass
python3 -m pytest tests/e2e/test_url_e2e.py -x -v
python3 -m pytest tests/e2e/test_results_page.py::test_detail_link_injected_after_enrichment_complete -x -v
```
