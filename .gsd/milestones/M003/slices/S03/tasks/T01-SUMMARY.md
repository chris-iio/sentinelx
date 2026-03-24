---
id: T01
parent: S03
milestone: M003
provides:
  - Full provider name display in SVG graph (no truncation)
  - Full IOC value display in SVG graph center node
  - Wider SVG viewBox (700×450) with adjusted orbit radius and center point
key_files:
  - app/routes.py
  - app/static/src/ts/modules/graph.ts
  - app/static/dist/main.js
key_decisions:
  - Reduced provider label font-size from 11 to 10 to help longer names fit at the wider orbit radius
patterns_established:
  - All graph label text passes full strings through createTextNode() — no slicing at any layer (server or client)
observability_surfaces:
  - data-graph-nodes attribute on #relationship-graph contains full provider names — inspect via DevTools or curl + grep
  - SVG viewBox attribute verifiable via document.querySelector('svg').getAttribute('viewBox') in browser console
  - python3 -m pytest tests/test_ioc_detail_routes.py -q — regression guard for label content
  - wc -c app/static/dist/main.js — bundle size guard (26,648 bytes after rebuild)
duration: 8m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T01: Remove graph label truncation and widen SVG viewBox

**Removed `[:20]`/`[:12]` Python slicing in `routes.py` and `.slice(0,12)`/`.slice(0,20)` in `graph.ts`; widened SVG viewBox to 700×450 with `orbitRadius=170`, `cx=350`, `cy=225`, and provider label `font-size` reduced to 10 — all 12 existing tests pass, bundle is 26KB.**

## What Happened

Four edits were made across two files:

1. **`app/routes.py` line 310** — `ioc_value[:20]` → `ioc_value` in the IOC center node dict
2. **`app/routes.py` line 318** — `provider[:12]` → `provider` in the provider node dict
3. **`app/static/src/ts/modules/graph.ts`** — `node.label.slice(0, 12)` → `node.label` (provider label text node); font-size simultaneously reduced 11→10
4. **`app/static/src/ts/modules/graph.ts`** — `iocNode.label.slice(0, 20)` → `iocNode.label` (IOC center label text node)

Layout constants adjusted in the same file: `viewBox` `0 0 600 400` → `0 0 700 450`, `cx` 300→350, `cy` 200→225, `orbitRadius` 150→170.

All `createTextNode()` usages were preserved throughout (SEC-08 compliance). No new DOM construction patterns were introduced.

## Verification

- `make typecheck` — tsc `--noEmit` exited 0, no TypeScript errors
- `make js` — esbuild rebuilt `app/static/dist/main.js` (26.0kb), no errors
- `wc -c app/static/dist/main.js` — 26,648 bytes (≤ 30,720 limit)
- `python3 -m pytest tests/test_ioc_detail_routes.py -q` — 12 passed in 0.39s
- `grep -n "slice(" app/static/src/ts/modules/graph.ts` — 0 matches
- `grep -n "\[:12\]\|\[:20\]" app/routes.py` — 0 matches
- `grep -n "viewBox\|const cx\|const cy\|orbitRadius" app/static/src/ts/modules/graph.ts` — confirmed `0 0 700 450`, cx=350, cy=225, orbitRadius=170

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `make typecheck` | 0 | ✅ pass | 3.2s |
| 2 | `make js` | 0 | ✅ pass | 3.2s |
| 3 | `wc -c app/static/dist/main.js` | 0 (26648 ≤ 30720) | ✅ pass | <1s |
| 4 | `python3 -m pytest tests/test_ioc_detail_routes.py -q` | 0 (12 passed) | ✅ pass | 2.5s |
| 5 | `grep -n "\.slice(" app/static/src/ts/modules/graph.ts` | 1 (0 matches) | ✅ pass | <1s |
| 6 | `grep -n "\[:12\]\|\[:20\]" app/routes.py` | 1 (0 matches) | ✅ pass | <1s |

## Diagnostics

- **Inspect label content at runtime:** `curl http://localhost:5000/ioc/ipv4/1.2.3.4 | grep -o 'data-graph-nodes="[^"]*"'` — the JSON blob should contain full provider names (e.g. `"Shodan InternetDB"`, `"CIRCL Hashlookup"`).
- **Inspect SVG layout:** Open browser DevTools → Elements, find the `<svg>` inside `#relationship-graph`, confirm `viewBox="0 0 700 450"`.
- **Re-check truncation:** `grep -rn "\.slice(0," app/static/src/ts/modules/graph.ts` and `grep -n "\[:12\]\|\[:20\]" app/routes.py` — both must return no output.
- **Bundle size regression guard:** `wc -c app/static/dist/main.js` — must stay ≤ 30,720 bytes.

## Deviations

None — implementation followed the plan exactly.

## Known Issues

None. The T02 task will add a `test_detail_graph_labels_untruncated` regression test that seeds "Shodan InternetDB" and asserts the full name appears in `data-graph-nodes` — this test does not yet exist.

## Files Created/Modified

- `app/routes.py` — removed `[:20]` and `[:12]` truncation from graph_nodes construction in `ioc_detail()`
- `app/static/src/ts/modules/graph.ts` — removed `.slice()` calls on provider and IOC labels; widened viewBox to 700×450; adjusted cx/cy/orbitRadius; reduced provider font-size from 11 to 10
- `app/static/dist/main.js` — rebuilt artifact (26KB)
- `.gsd/milestones/M003/slices/S03/S03-PLAN.md` — added `## Observability / Diagnostics` section per pre-flight requirement; marked T01 `[x]`
