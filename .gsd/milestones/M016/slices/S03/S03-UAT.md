# S03: Compact EmailRep result rendering — UAT

**Milestone:** M016
**Written:** 2026-05-10T06:04:49.258Z

## UAT Type

Deterministic frontend fixture UAT; no live third-party EmailRep key, browser server flow, or network request required.

## Preconditions

1. Worktree contains the S03 frontend changes.
2. Node dependencies are installed.
3. No EmailRep API key is required.
4. The rebuilt bundle path is `app/static/dist/main.js`.

## Steps

1. Run `npx vitest run app/static/src/ts/modules/row-factory.test.ts app/static/src/ts/modules/result-application.test.ts`.
2. Confirm the row-factory EmailRep tests pass for compact context rendering.
3. Confirm the malformed-payload test passes: script-like strings are rendered as text, unknown nested objects are omitted, and neither raw JSON nor `[object Object]` appears.
4. Confirm the result-application EmailRep fixture passes for an email IOC card with `data-provider-counts={"email":1}`.
5. Run `npx tsc --noEmit`.
6. Run `make js` and confirm `app/static/dist/main.js` is rebuilt successfully.

## Expected Outcomes

- EmailRep appears as a reputation provider row, not a context-only provider.
- The expanded provider row exposes compact whitelisted fields such as reputation, references, risk flags, domain reputation, profiles, first/last seen, deliverability/MX/spoofing, and email-auth booleans where present.
- The IOC summary/verdict surfaces update from the EmailRep result.
- Unknown nested raw payloads are not dumped into the DOM.
- Script-like provider-controlled values are treated as text, not markup.
- TypeScript remains type-correct and the production JS bundle builds.

## Edge Cases

- Unknown nested fields in `raw_stats` must not render.
- Non-scalar whitelisted values must not render as `[object Object]`.
- Tag arrays should render only scalar tags.
- Script-looking strings must not create script nodes or executable markup.
- EmailRep must not be added to `CONTEXT_PROVIDERS`, because it contributes verdict/attribution state.

## Not Proven By This UAT

- A full browser submission flow in Online mode.
- Live EmailRep API behavior or key validation.
- Third-party network availability.
- Route-mocked end-to-end browser proof; this remains S04 scope.
