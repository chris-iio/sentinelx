# M017: Project Clarity & Aggressive Optimization

**Gathered:** 2026-05-12
**Status:** Ready for planning

## Project Description

SentinelX is a local Flask/TypeScript IOC triage workbench for analysts. Its important loop is: paste IOC-rich investigation text, extract indicators, optionally enrich them through configured providers, review prioritized results with expandable details, and preserve local history/diagnostics without re-querying unnecessarily.

The user’s framing for M017 was direct: “I want to figure out what this project is, and do that, and get it optimized.” The milestone must therefore make SentinelX clearer as a project and then optimize aggressively from that identity.

## Why This Milestone

Prior optimization work exists, but M017 should not blindly continue an old target list. The project has accumulated features across intake, enrichment, history, diagnostics, provider settings, and UI rendering. If future agents cannot quickly answer what SentinelX is, optimization work risks becoming generic cleanup or optimization theater.

This milestone solves that by making the current project identity durable, refreshing the optimization audit against that identity, and shipping the best current optimization opportunity with proof.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Read a separate project map and understand what SentinelX is, who it serves, the primary analyst loop, and where optimization should focus.
- Run or inspect the refreshed optimization audit and see which opportunities were shipped, deferred, or intentionally left alone.
- Use the existing SentinelX analyst flow with no regression after the shipped optimization work.

### Entry point / environment

- Entry point: local Flask web UI plus repo-native Make targets.
- Environment: local dev browser and local CLI verification lanes.
- Live dependencies involved: local SQLite stores, browser UI, Flask routes, optional third-party enrichment providers; M017 proof should prefer deterministic mocked provider/browser paths unless a slice explicitly needs live external calls.

## Completion Class

- Contract complete means: project map, PROJECT.md, requirements, audit artifact, and roadmap coverage all agree on SentinelX’s current identity and optimization scope.
- Integration complete means: shipped optimization(s) are wired through the real code path they affect and preserve intake/enrichment/results/history/diagnostics continuity.
- Operational complete means: `make verify-fast` and `make verify-deep` pass at closeout, and the final audit/project-map handoff explains remaining do-next/later/leave-alone work.

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- A future agent can read `docs/project-map.md`, `.gsd/PROJECT.md`, `M017-CONTEXT.md`, and the M017 audit artifact and understand SentinelX’s product identity and optimization priorities without this conversation.
- At least one best-current optimization ships with measurement when practical, or explicit code-path reasoning plus regression proof when measurement is not practical.
- Existing analyst-facing IOC intake, enrichment, results, history/detail, diagnostics, and security behavior remain intact under `make verify-fast` and `make verify-deep`.

## Architectural Decisions

### Living Project Map Before Optimization

**Decision:** M017 starts by producing a durable project map and refreshing `.gsd/PROJECT.md` before choosing optimization targets.

**Rationale:** The user’s main concern is that the project still feels unclear. If SentinelX’s identity is not clear, optimization work is likely to improve arbitrary code paths instead of the analyst loop.

**Alternatives Considered:**
- Keep project understanding milestone-local only — rejected because future agents need the current-state map.
- Run a generic optimization pass first — rejected because it risks repeating old assumptions and missing what the app has become.

### Optimize Around What SentinelX Is

**Decision:** Optimization target selection is biased toward the product identity: analyst intake, enrichment/results, history/detail, diagnostics, and proof loop.

**Rationale:** The user chose “what this project is” over subsystem-neutral prioritization. Backend/runtime/frontend/storage changes are all valid only insofar as they improve or protect the real SentinelX workflow.

**Alternatives Considered:**
- Optimize by subsystem neutrality — rejected because the user wants identity-grounded optimization.
- Only micro-optimize measured hot spots — too narrow; aggressive moderate refactors are acceptable when they are the best optimization and proof preserves behavior.

### Evidence-Backed Aggressive Optimization

**Decision:** M017 may ship meaningful refactors when they are the best optimization, but every shipped optimization must carry measurement when practical or explicit code-path reasoning plus regression proof.

**Rationale:** The user asked for aggressive optimization, but prior project lessons warn against optimization theater. Evidence makes the aggressive posture safe and reusable.

**Alternatives Considered:**
- Require before/after measurement for every change — too rigid for structural simplifications where direct measurement is awkward.
- Accept cleanup without proof — rejected as out of scope.

## Error Handling Strategy

Optimization must not hide failures to appear faster. Existing enrichment terminal states, provider errors, status polling semantics, cache/history behavior, browser-visible errors, diagnostics, CSP/CSRF/SSRF/DOM-safety boundaries, and secret redaction must be preserved unless a slice explicitly improves them. If product-map work finds confusing failure states, the milestone should document them and may improve them when cheap and safe.

## Risks and Unknowns

- Optimizing the wrong thing — if the project map is shallow, later slices may ship irrelevant performance work.
- Stale M012/M013 assumptions — previous optimization evidence may no longer describe the current code after M014-M016.
- Browser/results regressions — frontend render or polling optimizations can silently break live/history parity, expansion, filtering, copy/export, or no-data detail behavior.
- Failure hiding — speed changes that remove diagnostic context would make a security triage tool less trustworthy.

## Existing Codebase / Prior Art

- `docs/project-map.md` — new M017 durable map of SentinelX’s identity and optimization seams.
- `tools/optimization_audit.py` — existing M013 audit runner to extend or adapt for M017.
- `docs/optimization-audit.md` — existing audit contract and ranking vocabulary.
- `.gsd/milestones/M013/M013-AUDIT.md` — prior optimization baseline and shipped/leave-alone decisions.
- `app/routes/_helpers.py` — request/status/history diagnostics seam.
- `app/enrichment/orchestrator.py` — runtime/provider orchestration and diagnostics seam.
- `app/cache/store.py` and `app/enrichment/history_store.py` — local persistence seam.
- `app/static/src/ts/modules/result-application.ts` — shared live/history result application and current frontend render seam.
- `README.md` — current operational and verification guidance, update if project identity stays unclear.

## Relevant Requirements

- R084 — advanced by S01 through project map and PROJECT.md refresh.
- R085 — advanced by S02 through identity-grounded audit criteria.
- R086 — advanced by S03/S04 through shipped best-current optimization work.
- R087 — advanced by S02-S05 through measurement/reasoning and verification evidence.
- R088 — advanced by S03-S05 through continuity and regression proof.
- R089 — validated by S05 closeout with full verification lanes.
- R090-R091 — kept deferred to prevent M017 from becoming an unbounded future optimization program or feature redesign.
- R092-R093 — enforced as out-of-scope guardrails.

## Scope

### In Scope

- Create a separate project map artifact explaining SentinelX’s current identity.
- Refresh `.gsd/PROJECT.md` and update README/docs only where needed for clarity.
- Refresh or adapt the optimization audit for M017.
- Rank current optimization opportunities against the project map.
- Ship the best supported optimization, including moderate refactors if justified.
- Preserve and verify analyst-facing intake, enrichment, results, history/detail, diagnostics, and security behavior.
- Close with full fast/deep verification and durable audit evidence.

### Out of Scope / Non-Goals

- Major new analyst-facing product features.
- Broad future optimization program beyond M017’s best supported targets.
- Speculative rewrites without project-identity grounding or proof.
- Speed changes that hide failures, remove diagnostics, leak secrets, or weaken security boundaries.

## Technical Constraints

- Use the existing Flask/TypeScript/SQLite architecture unless evidence strongly justifies a local refactor.
- Preserve existing route contracts and browser behavior unless a slice explicitly changes and verifies them.
- Avoid live third-party provider dependence in routine proof; prefer deterministic mocked online flows.
- Do not log or expose secrets.
- Keep M013’s measurement-or-code-path-reasoning proof discipline.

## Integration Points

- Flask routes — request/status/history/detail/settings/diagnostics surfaces.
- Enrichment orchestrator and provider registry — runtime/provider behavior and diagnostic snapshots.
- SQLite cache/history stores — local persistence and reload continuity.
- Browser TypeScript modules — polling, result application, filtering, sorting, expansion, copy/export.
- Make verification lanes — `make verify-fast`, `make verify-deep`, and audit runner commands.

## Testing Requirements

- Use focused tests for whichever seam is optimized.
- Run `make verify-fast` for shipped optimization work.
- Run `make verify-deep` for any browser/results/enrichment/status behavior change and at final closeout regardless.
- Audit artifact should capture command evidence where practical.
- Browser-visible changes need deterministic mocked-online proof, not just static assertions.

## Acceptance Criteria

- `docs/project-map.md` exists and explains SentinelX in current-state, product/codebase terms.
- `.gsd/PROJECT.md` is refreshed and points to the capability contract and M017 sequence.
- M017 audit artifact ranks current optimization opportunities in do-now/do-next/later/leave-alone buckets.
- At least one best-current optimization ships, unless the audit explicitly proves that no code change is justified now.
- All shipped optimization claims cite measurement or explicit code-path reasoning and fresh regression proof.
- `make verify-fast` and `make verify-deep` pass at closeout.

## Open Questions

- Which specific optimization will S02 rank highest after the fresh M017 audit — current thinking is that frontend result rendering or a project-map-aware audit-tool extension are likely candidates, but S02 must decide from evidence.
