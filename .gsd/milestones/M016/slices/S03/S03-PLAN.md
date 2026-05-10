# S03: Compact EmailRep result rendering

**Goal:** Render EmailRep enrichment results as compact, safe analyst-facing reputation/risk context in the existing result-row UI, consuming the flattened S01 raw_stats contract and the S02 email provider-count wiring without adding nested raw JSON dumping or a provider-specific unsafe renderer.
**Demo:** After this, mocked EmailRep results render compact reputation and risk context in the existing result row UI without unsafe nested-data dumping.

## Must-Haves

- Must-Haves:
- EmailRep renders through the existing reputation-provider detail-row path in `app/static/src/ts/modules/row-factory.ts`; it must not be added to `CONTEXT_PROVIDERS` because it contributes verdict/attribution state.
- `EmailRep` raw_stats fields from `app/enrichment/adapters/emailrep.py` are whitelisted into compact context fields: reputation, references, risk flags, domain reputation, profiles, first/last seen, deliverability/MX/spoofing, and email-auth booleans where present.
- Rendering uses the existing `createElement`/`textContent` provider-context path; tests prove script-like strings are text and nested objects/unknown raw payloads are not dumped as JSON or `[object Object]`.
- A shared coordinator fixture proves an `ioc_type="email"` card with `data-provider-counts={"email":1}` places EmailRep in `.enrichment-section--reputation`, updates the summary row/verdict label, and exposes compact risk context in the expanded provider row.
- No task performs a live EmailRep HTTP request or requires an EmailRep key; all proof is deterministic frontend fixtures.
- Threat Surface — Abuse: malicious or malformed provider payloads may include nested objects, script-like strings, or excessive-looking flags; the UI must whitelist scalar/tag fields and render them as text only.
- Threat Surface — Data exposure: email IOCs are PII and EmailRep keys are secrets; this slice must not introduce key rendering/logging, and must not dump raw nested provider payloads that could contain unexpected personal data.
- Threat Surface — Input trust: remote EmailRep response data reaches the browser DOM through `raw_stats`; the trusted boundary is the flattened adapter contract plus frontend field whitelist, not arbitrary provider JSON.
- Requirement Impact — Requirements touched: R078 is directly advanced by rendering EmailRep email enrichment depth; R016 must remain compatible with existing email IOC display; R008 result rendering/polling continuity and R009 SEC-08/textContent security are compatibility constraints.
- Requirement Impact — Re-verify: `row-factory` DOM builders, shared `result-application` live/history rendering path, TypeScript typecheck, and JS bundle build.
- Requirement Impact — Decisions revisited: honor D074 and S01's flattened raw_stats decision; do not reintroduce nested raw provider dumping or a separate EmailRep-specific renderer.

## Proof Level

- This slice proves: This slice proves fixture-level frontend contract/integration through Vitest DOM tests and TypeScript/build checks. Real runtime required: no live third-party runtime and no browser server flow. Human/UAT required: no. It does not prove the full mocked Online browser submission path; S04 remains responsible for end-to-end browser proof.

## Integration Closure

Upstream surfaces consumed: S01 `app/enrichment/adapters/emailrep.py` flattened raw_stats contract and S02 provider-count wiring for `IOCType.EMAIL`. New wiring introduced in this slice: EmailRep field whitelist in `app/static/src/ts/modules/row-factory.ts` and shared result-application proof that EmailRep appears as a reputation row for email IOCs. Remaining milestone work: S04 must route-mock Online enrichment and prove a browser can submit an email IOC and see the EmailRep verdict/context row without a live key.

## Verification

- Runtime signals: the existing `.ioc-summary-row`, `.verdict-label`, `.enrichment-section--reputation .provider-detail-row`, and `.provider-context-field` DOM surfaces show whether EmailRep rendered and which compact context fields survived the whitelist. Inspection surfaces: `app/static/src/ts/modules/row-factory.test.ts` localizes field-formatting regressions; `app/static/src/ts/modules/result-application.test.ts` localizes shared live/history coordinator regressions; `app/static/dist/main.js` proves the bundled UI contains the wiring. Failure visibility: tests should fail distinctly for missing EmailRep fields, wrong section placement, unsafe `[object Object]` dumping, and broken summary/verdict updates. Redaction constraints: no API keys or raw nested provider payloads should be rendered or asserted; script-like values must be treated as text, not markup.

## Tasks

- [x] **T01: Whitelist EmailRep compact context fields in row-factory** `est:45m`
  Expected executor skills_used frontmatter: `tdd`, `verify-before-complete`.
  - Files: `app/static/src/ts/modules/row-factory.ts`, `app/static/src/ts/modules/row-factory.test.ts`, `app/enrichment/adapters/emailrep.py`, `app/static/src/ts/types/api.ts`
  - Verify: npx vitest run app/static/src/ts/modules/row-factory.test.ts

- [x] **T02: Prove EmailRep renders through shared result application** `est:45m`
  Expected executor skills_used frontmatter: `tdd`, `verify-before-complete`.
  - Files: `app/static/src/ts/modules/result-application.test.ts`, `app/static/src/ts/modules/row-factory.test.ts`, `app/static/src/ts/modules/row-factory.ts`, `app/static/dist/main.js`
  - Verify: npx vitest run app/static/src/ts/modules/row-factory.test.ts app/static/src/ts/modules/result-application.test.ts && npx tsc --noEmit && make js

## Files Likely Touched

- app/static/src/ts/modules/row-factory.ts
- app/static/src/ts/modules/row-factory.test.ts
- app/enrichment/adapters/emailrep.py
- app/static/src/ts/types/api.ts
- app/static/src/ts/modules/result-application.test.ts
- app/static/dist/main.js
