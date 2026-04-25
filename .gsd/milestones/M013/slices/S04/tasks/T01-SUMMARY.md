---
id: T01
parent: S04
milestone: M013
key_files:
  - app/static/src/ts/modules/result-application.ts
  - app/static/src/ts/modules/result-application.test.ts
key_decisions:
  - Cached stable per-IOC DOM handles inside createResultApplicationCoordinator() and reused them across apply(), flush(), and finalize() instead of repeating whole-document lookups.
  - Snapshotted data-provider-counts once per coordinator creation so pending-indicator fallback behavior stays identical without reparsing page metadata on every streamed result.
  - Kept summary-row/detail-link creation lazy and coordinator-local so polling cadence, results ownership resolution, payload shape, and DOM-safety rules stayed unchanged.
duration: 
verification_result: passed
completed_at: 2026-04-25T07:04:23.437Z
blocker_discovered: false
---

# T01: Cached per-IOC result DOM handles in the shared coordinator and added parity/fallback coverage.

**Cached per-IOC result DOM handles in the shared coordinator and added parity/fallback coverage.**

## What Happened

Refactored the shared live/history result-application coordinator to build a coordinator-local cache of stable per-IOC DOM handles on first touch. Each cache entry now retains the card, enrichment slot, stable section containers, copy button, and the provider-count total derived from the server-rendered page metadata, so subsequent apply(), flush(), and finalize() operations reuse local nodes instead of rediscovering cards/slots or reparsing JSON on the hot path. I kept dynamic rows lazy through the existing row-factory/shared-rendering helpers, preserved graceful no-op behavior for missing cards/slots/sections, and left enrichment polling cadence, results ownership/runtime semantics, and route payload handling unchanged. I also expanded focused Vitest coverage to prove cache reuse, provider-count fallback semantics for missing/malformed metadata, malformed slot/card fail-soft behavior, repeated-result worst-verdict convergence, and the existing live/history finalize/link/copy parity contract.

## Verification

Ran the slice verification command after the last code change: `npx vitest run app/static/src/ts/modules/result-application.test.ts app/static/src/ts/modules/enrichment.test.ts app/static/src/ts/modules/history.test.ts app/static/src/ts/modules/main.test.ts app/static/src/ts/modules/row-factory.test.ts`, which passed 64/64 tests with exit code 0. Also launched the local Flask app, submitted an online analysis for `1.2.3.4` with a mocked `/enrichment/status/*` response, and verified the real `/analyze` results page preserved the analyst-visible signals this slice cares about: `.page-results[data-results-owner='live'][data-results-runtime='live']`, `.enrichment-slot--loaded`, `.ioc-summary-row`, `.detail-link`, `MALICIOUS`, `Enrichment complete`, and `Tokyo, JP` were all present; a direct DOM read confirmed `data-enrichment="VirusTotal: malicious (2/70 engines)"`, detail href `/ioc/ipv4/1.2.3.4`, and a cleared pending indicator once the mocked payload matched the server-rendered provider-count metadata.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `npx vitest run app/static/src/ts/modules/result-application.test.ts app/static/src/ts/modules/enrichment.test.ts app/static/src/ts/modules/history.test.ts app/static/src/ts/modules/main.test.ts app/static/src/ts/modules/row-factory.test.ts` | 0 | ✅ pass | 991ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `app/static/src/ts/modules/result-application.ts`
- `app/static/src/ts/modules/result-application.test.ts`
