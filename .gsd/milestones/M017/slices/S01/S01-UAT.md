# S01: Current-State Project Map — UAT

**Milestone:** M017
**Written:** 2026-05-12T17:55:45.138Z

# S01: Current-State Project Map — UAT

**Milestone:** M017
**Written:** 2026-05-12

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S01 shipped documentation/state artifacts only; the slice contract is document existence, structural completeness, concrete code-path references, optimization priorities, and absence of placeholders. No runtime behavior was changed.

## Preconditions

- Repository is checked out at the completed S01 state.
- `docs/project-map.md` and `.gsd/PROJECT.md` are present.
- No application server or seeded data is required.

## Smoke Test

Run the S01 closeout verification command or inspect the artifacts manually. A passing smoke test shows `docs/project-map.md` is non-empty, has multiple `##` sections, includes concrete SentinelX app paths, includes ranked optimization priorities, and `.gsd/PROJECT.md` points future agents back to the project map/seam inventory.

## Test Cases

### 1. Project map explains the product identity and analyst loop

1. Open `docs/project-map.md`.
2. Confirm it describes what SentinelX is, who it serves, and the main analyst IOC intake/enrichment/results loop.
3. **Expected:** A fresh reader can understand SentinelX as an analyst-facing IOC triage/enrichment application without needing prior conversation context.

### 2. Project map contains concrete architecture seams

1. In `docs/project-map.md`, locate the architecture seam inventory.
2. Confirm seams include concrete file-path references such as `app/enrichment`, `app/routes`, and/or `app/pipeline`.
3. **Expected:** S02 can tie audit findings to real code paths rather than abstract product areas.

### 3. Project map contains ranked optimization priorities

1. In `docs/project-map.md`, locate the optimization priorities section.
2. Confirm at least three named optimization targets are ranked or clearly prioritized and include relevant file references.
3. **Expected:** The next optimization audit has an identity-grounded starting list of targets.

### 4. Project summary points to the authoritative seam map

1. Open `.gsd/PROJECT.md`.
2. Confirm it references `docs/project-map.md` and includes seam/path pointers under `app/enrichment`, `app/routes`, or `app/pipeline`.
3. **Expected:** Future agents can use `.gsd/PROJECT.md` as a concise first-read summary and then drill into `docs/project-map.md` for the full seam inventory.

## Edge Cases

### Placeholder leakage

1. Search both artifacts for `TBD` or `TODO`.
2. **Expected:** No placeholder markers remain in either `docs/project-map.md` or `.gsd/PROJECT.md`.

### Runtime independence

1. Do not start the SentinelX server.
2. Run the artifact checks against the two files.
3. **Expected:** UAT still passes because S01 is documentation/state only and does not depend on runtime services.

## Failure Signals

- `docs/project-map.md` is missing, empty, or too sparse to explain the product/analyst loop.
- Architecture seams are described only abstractly and do not include concrete file paths.
- Optimization priorities are absent, unranked, or not tied to code paths.
- `.gsd/PROJECT.md` fails to reference the project map/seam inventory.
- Either artifact contains `TBD` or `TODO` placeholders.

## Not Proven By This UAT

- No runtime IOC intake, enrichment, results, history, diagnostics, or security behavior is proven by this slice.
- No optimization has been implemented or measured yet; this slice only creates the identity and seam map that S02 consumes.
- The ranked priorities are audit inputs, not final proof that any target is the best implementation candidate.

## Notes for Tester

Treat `docs/project-map.md` as the authoritative detailed map. `.gsd/PROJECT.md` is intentionally concise and should point to the project map rather than repeat it.
