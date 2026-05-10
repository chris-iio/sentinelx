---
estimated_steps: 4
estimated_files: 4
skills_used:
  - tdd
  - verify-before-complete
---

# T01: Whitelist EmailRep compact context fields in row-factory

Expected executor skills_used frontmatter: `tdd`, `verify-before-complete`.

Add the EmailRep frontend field whitelist and unit-test it through the public `createDetailRow()` row builder. This task closes the direct row-factory contract: EmailRep provider rows should show compact reputation/risk context from flattened `raw_stats`, while malformed nested data is ignored rather than dumped.

## Steps
1. In `app/static/src/ts/modules/row-factory.test.ts`, first add a failing `createDetailRow()` test for an `EmailRep` result with representative flattened S01 `raw_stats`: reputation, references, risk_flags, domain_reputation, profiles, first_seen/last_seen, deliverable, valid_mx, spoofable, spf_strict, and dmarc_enforced.
2. Add a negative test that includes unknown nested object fields and script-like string values, asserting the row contains no `[object Object]`, no raw JSON dump, and no created markup from provider-controlled text.
3. Implement the minimal `PROVIDER_CONTEXT_FIELDS.EmailRep` mapping in `app/static/src/ts/modules/row-factory.ts`, using existing `type: "text"` and `type: "tags"` behavior only; do not add EmailRep to `CONTEXT_PROVIDERS`.
4. Refactor only while the focused tests are green; keep labels short enough for compact row display (for example, `Reputation`, `Refs`, `Risks`, `Domain`, `Profiles`, `First seen`, `Last seen`, `Deliverable`, `MX`, `Spoofable`, `SPF`, `DMARC`).

## Must-Haves
- [ ] EmailRep detail rows render compact `.provider-context-field` elements from whitelisted flattened stats.
- [ ] `risk_flags` and `profiles` render as `.context-tag` elements, not comma-joined raw arrays or JSON.
- [ ] Boolean fields render only through the safe text path when present.
- [ ] Unknown nested object values are ignored; tests prove no `[object Object]`/raw JSON dumping.
- [ ] EmailRep remains a reputation provider and is not added to `CONTEXT_PROVIDERS`.

## Failure Modes
| Dependency | On error | On timeout | On malformed response |
|------------|----------|-----------|----------------------|
| `EmailRep` flattened `raw_stats` contract from `app/enrichment/adapters/emailrep.py` | Missing known fields simply omit those labels so the row still renders | Not applicable; frontend row rendering is synchronous | Unknown nested objects are ignored; scalar/tag values are rendered with `textContent` only |

## Load Profile
- **Shared resources**: Browser DOM node creation for each provider detail row.
- **Per-operation cost**: O(number of whitelisted EmailRep fields + rendered tags) per EmailRep result; no network, storage, or polling changes.
- **10x breakpoint**: Very large tag arrays would create more DOM spans, so this task should keep the whitelist narrow and avoid rendering arbitrary unknown arrays.

## Negative Tests
- **Malformed inputs**: Missing `raw_stats`, empty `risk_flags`, nested object fields, and non-scalar values should not crash or render unsafe text like `[object Object]`.
- **Error paths**: A no_data/error EmailRep row should keep existing no-data behavior; this task must not change `provider-row--no-data` semantics.
- **Boundary conditions**: Script-like provider strings render literally as textContent and do not become child elements; EmailRep is absent from context-only row dispatch.

## Inputs
- `app/static/src/ts/modules/row-factory.ts` — existing DOM builders and provider context whitelist.
- `app/static/src/ts/modules/row-factory.test.ts` — existing Vitest coverage for provider detail rows and context fields.
- `app/enrichment/adapters/emailrep.py` — authoritative flattened `raw_stats` field names from S01.
- `app/static/src/ts/types/api.ts` — frontend `EnrichmentResultItem` shape.

## Expected Output
- `app/static/src/ts/modules/row-factory.ts` — EmailRep compact field mapping.
- `app/static/src/ts/modules/row-factory.test.ts` — focused happy-path and malformed-payload EmailRep row tests.

## Inputs

- `app/static/src/ts/modules/row-factory.ts`
- `app/static/src/ts/modules/row-factory.test.ts`
- `app/enrichment/adapters/emailrep.py`
- `app/static/src/ts/types/api.ts`

## Expected Output

- `app/static/src/ts/modules/row-factory.ts`
- `app/static/src/ts/modules/row-factory.test.ts`

## Verification

npx vitest run app/static/src/ts/modules/row-factory.test.ts

## Observability Impact

Signals changed: EmailRep `.provider-context-field` and `.context-tag` DOM nodes become the inspectable UI signal for flattened reputation/risk context. Future inspection: run `npx vitest run app/static/src/ts/modules/row-factory.test.ts` and inspect failures for missing labels, unsafe nested value rendering, or accidental context-provider dispatch.
