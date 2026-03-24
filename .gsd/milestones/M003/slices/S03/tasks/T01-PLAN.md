---
estimated_steps: 5
estimated_files: 2
---

# T01: Remove graph label truncation and widen SVG viewBox

**Slice:** S03 — Detail Page Design Refresh
**Milestone:** M003

## Description

The SVG relationship graph on the detail page truncates provider names to 12 characters and IOC values to 20 characters. This happens in two places: server-side in `routes.py` (Python string slicing) and client-side in `graph.ts` (`.slice()` calls). Four provider names currently truncate: "CIRCL Hashlookup" (16 chars), "Shodan InternetDB" (17), "OTX AlienVault" (14), "MalwareBazaar" (13). Removing truncation requires widening the SVG viewBox so labels fit without overflow.

**Relevant skills:** None needed — this is a targeted code change in Python and TypeScript.

## Steps

1. **Edit `app/routes.py`** — Find the `ioc_detail()` function (starts around line 291). At line 310, change `ioc_value[:20]` to `ioc_value` in the graph_nodes IOC node dict. At line 318, change `provider[:12]` to `provider` in the provider node dict. Do not change any other part of the route handler.

2. **Edit `app/static/src/ts/modules/graph.ts`** — At line ~154 (provider label text node), change `node.label.slice(0, 12)` to `node.label`. At line ~184 (IOC center label text node), change `iocNode.label.slice(0, 20)` to `iocNode.label`.

3. **Widen the SVG viewBox and adjust layout constants in `graph.ts`:**
   - Change `svg.setAttribute("viewBox", "0 0 600 400")` to `svg.setAttribute("viewBox", "0 0 700 450")`
   - Change `const cx = 300` to `const cx = 350`
   - Change `const cy = 200` to `const cy = 225`
   - Change `const orbitRadius = 150` to `const orbitRadius = 170`
   - Change the provider label `font-size` from `"11"` to `"10"` (the `text.setAttribute("font-size", "11")` line)

4. **Build and verify:**
   - Run `make typecheck` — must exit 0
   - Run `make js` — must build without errors
   - Run `wc -c app/static/dist/main.js` — must be ≤ 30,720 bytes

5. **Run existing tests:**
   - Run `python3 -m pytest tests/test_ioc_detail_routes.py -q` — all 12 tests must pass
   - The `test_graph_data_in_context` test checks for `data-graph-nodes` and `data-graph-edges` in the HTML — this verifies the route still produces graph data correctly

## Must-Haves

- [ ] `routes.py` line 310: `ioc_value[:20]` → `ioc_value` (no truncation)
- [ ] `routes.py` line 318: `provider[:12]` → `provider` (no truncation)
- [ ] `graph.ts`: `node.label.slice(0, 12)` → `node.label` (provider labels)
- [ ] `graph.ts`: `iocNode.label.slice(0, 20)` → `iocNode.label` (IOC label)
- [ ] SVG viewBox widened to `0 0 700 450`
- [ ] `orbitRadius` increased to 170 for more label space
- [ ] Center point adjusted to `cx=350, cy=225`
- [ ] All `createTextNode()` usage preserved (SEC-08 compliance)
- [ ] `make typecheck` exits 0
- [ ] Bundle ≤ 30KB

## Verification

- `make typecheck` exits 0
- `make js` builds without errors
- `wc -c app/static/dist/main.js` shows ≤ 30,720 bytes
- `python3 -m pytest tests/test_ioc_detail_routes.py -q` — all 12 tests pass
- Grep `graph.ts` for `.slice(` — should return 0 matches
- Grep `routes.py` for `[:12]` and `[:20]` in the `ioc_detail` function — should return 0 matches

## Inputs

- `app/routes.py` — lines 310 and 318 have the server-side truncation (`ioc_value[:20]`, `provider[:12]`)
- `app/static/src/ts/modules/graph.ts` — lines ~154 and ~184 have the client-side truncation (`.slice(0, 12)`, `.slice(0, 20)`); viewBox is `0 0 600 400`; `cx=300, cy=200, orbitRadius=150`

## Expected Output

- `app/routes.py` — graph node labels pass full strings (no truncation)
- `app/static/src/ts/modules/graph.ts` — labels render without truncation; SVG viewBox is `0 0 700 450` with `cx=350, cy=225, orbitRadius=170`; provider label font-size is `10`
- `app/static/dist/main.js` — rebuilt with graph changes, ≤ 30KB
