# M020: Audit-Led Aggressive Refactor and Deep Optimization

**Gathered:** 2026-05-15
**Status:** Ready for planning

## Project Description

SentinelX is a local, security-focused web application for analyst IOC triage. Its core loop is: paste investigation text or SSH/security artifacts, extract IOCs, optionally enrich those indicators through threat-intelligence providers, and review analyst-friendly results with history, detail pages, filtering, copy/export, and diagnostics.

M020 is an aggressive refactor and deep optimization milestone. The user asked to "refactor the code and do a deep optimization" and confirmed that this means a serious codebase-wide effort to find structural inefficiencies, remove unnecessary complexity, tighten slow paths, and leave the app easier to maintain and faster to run.

## Why This Milestone

Prior optimization work shipped narrow, evidence-backed wins and created a mature optimization audit workflow. M020 exists because the user now wants a deeper pass: aggressive rewrites are allowed when current evidence shows architectural drag, but the work must not become cosmetic cleanup or unsupported optimization claims.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Inspect a generated M020 audit artifact that ranks aggressive rewrite candidates and records shipped, rejected, deferred, and leave-alone outcomes.
- Use SentinelX's analyst workflow after the refactors: intake, extraction, enrichment, results, history/detail, diagnostics, filtering, copy, and export still work.
- Trust that shipped optimizations have measurement or explicit code-path reasoning plus regression proof.

### Entry point / environment

- Entry point: local Flask web UI, Makefile verification targets, and `tools/optimization_audit.py`.
- Environment: local dev and browser e2e environment.
- Live dependencies involved: existing threat-intelligence provider adapters are continuity surfaces, but M020 does not add new external services.

## Completion Class

- Contract complete means: generated audit artifact, focused seam tests, and requirement coverage all exist and map to shipped or rejected outcomes.
- Integration complete means: changed seams are wired into the real SentinelX app and verified through `make verify-fast`, `make verify-deep` when required, and final `make verify`.
- Operational complete means: diagnostics, explicit failure states, redaction boundaries, and generated closeout proof remain inspectable after the aggressive rewrites.

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- A source-generated M020 audit artifact ranks aggressive rewrite candidates and records current outcomes.
- At least the highest-confidence aggressive rewrite target is shipped or explicitly rejected with evidence.
- SentinelX's analyst IOC triage loop still works end-to-end through final `make verify`.
- Browser-visible or live-enrichment-visible changes are proven through `make verify-deep`; routine code changes are proven through focused tests and `make verify-fast`.
- Failure visibility, diagnostics, and redaction boundaries are preserved rather than hidden for speed.

## Architectural Decisions

### Audit-Led Rewrites

**Decision:** Organize M020 around audit-led rewrites. The milestone starts by broadening/deepening the optimization audit so rewrite candidates are ranked by current evidence, then implementation slices ship or reject the highest-value targets.

**Rationale:** The codebase already has `tools/optimization_audit.py`, `docs/project-map.md`, and M017 proof patterns. Since the user chose an aggressive rewrite pass, the safest way to allow big changes without optimization theater is to first make the audit capable of identifying cross-seam rewrite targets.

**Alternatives Considered:**
- Seam-first rewrite — faster to start, but higher risk of rewriting the wrong boundary before evidence is current.
- Subsystem-by-subsystem — simpler planning, but risks fragmented findings and duplicated proof work.

### Strict Proof Bar

**Decision:** Keep the existing SentinelX proof bar: measurement when practical, explicit code-path reasoning when measurement is awkward, focused regression tests around changed seams, `make verify-fast` for implementation slices, `make verify-deep` for browser/live-enrichment-visible changes, and final `make verify`.

**Rationale:** Aggressive refactors create regression risk across Flask routes, enrichment orchestration, persistence, TypeScript browser behavior, templates, diagnostics, and tests. The proof bar preserves confidence while still allowing substantial rewrites.

**Alternatives Considered:**
- Faster proof bar with final-only verification — lower command cost but higher risk of late integration failures.
- Benchmark-heavy proof for every candidate — strongest evidence, but likely over-measures small refactors and slows the milestone.

### Preserve Analyst Loop as Integration Contract

**Decision:** Existing analyst behavior remains the integration contract unless a slice explicitly changes a behavior and proves the new contract.

**Rationale:** SentinelX's value is the fast local analyst workbench loop. Deep optimization should not hide failures, remove diagnostics, break history replay, or make provider behavior less inspectable.

**Alternatives Considered:**
- Allow product redesign during optimization — rejected because it would blur scope and make regression proof ambiguous.

## Error Handling Strategy

- Audit failures are visible, not hidden. The audit runner may write a partial/incomplete artifact when a capture fails, but the command should exit nonzero and mark evidence incomplete.
- No speedup may hide failures. Provider failures, status terminal states, diagnostics errors, and UI rendering problems must remain explicit.
- Proof gaps block implementation claims. If a rewrite cannot be measured or reasoned about clearly, it stays in later or leave-alone.
- Security/redaction regressions block completion. Diagnostics, exports, logs, audit artifacts, and browser output must not expose secrets or unsafe IOC HTML.
- Browser-visible changes require browser proof. Anything touching polling, result application, DOM state, history replay, or analyst-visible UI needs `make verify-deep`.
- Failed rewrites should be rejected cleanly. If a candidate proves too risky or low-value, the slice should record an explicit rejection/keep-decision in the audit rather than forcing a change.
- Behavior preservation is the default.

## Risks and Unknowns

- The audit may find many micro-optimizations but fewer true rewrite-worthy seams — this matters because M020 is meant to be deep, not a micro-cleanup pass.
- Large rewrites could break analyst-visible behavior — this matters because the app must still work as a fast local IOC triage workbench.
- Persistence, provider, and frontend seams may look tempting but still require evidence — prior decisions explicitly warn against optimization theater.
- The audit runner may need significant expansion before it can judge deeper architectural changes — this matters because S01 must produce actionable targets, not just prose.

## Existing Codebase / Prior Art

- `docs/project-map.md` — current product identity and architecture seam inventory.
- `docs/optimization-audit.md` — existing optimization audit workflow and artifact contract.
- `tools/optimization_audit.py` — generated audit runner and measurement/proof surface to extend for M020.
- `Makefile` — repo-native `verify-fast`, `verify-deep`, `verify`, and audit targets.
- `.gsd/milestones/M017/M017-SUMMARY.md` — records the instruction that future optimization work should start from the project map, regenerate the audit artifact, and preserve the proof bar.
- `app/enrichment/orchestrator.py`, `app/routes/`, `app/pipeline/`, `app/cache/store.py`, `app/static/src/ts/modules/`, and `app/templates/` — likely seams for audit-led rewrite candidates.

## Relevant Requirements

- R094 — M020 advances this by creating the generated milestone-specific audit surface.
- R095 — M020 advances this by ranking aggressive rewrite targets before implementation.
- R096 — M020 advances this by tying shipped/rejected outcomes to evidence.
- R097 — M020 advances this by preserving analyst workflows through implementation and final verification.
- R098 — M020 advances this by using strict focused, fast, deep, and final verification lanes.
- R099 — M020 advances this by preserving explicit failures, diagnostics, and redaction boundaries.
- R100 — M020 advances this by recording durable generated audit and closeout outcomes.

## Scope

### In Scope

- Broadening/deepening the generated M020 optimization audit.
- Aggressive refactors or optimizations when audit evidence supports them.
- Backend, frontend, templates, persistence/cache/history, enrichment orchestration, tests, and tooling.
- Focused regression tests for changed seams.
- Updating generated audit outcomes after implementation slices.
- Final integrated closeout proof.

### Out of Scope / Non-Goals

- Cosmetic-only cleanup without measurable or maintainability payoff.
- New product features unrelated to speed, clarity, reliability, or maintainability.
- New external provider integrations.
- Broad UI/product redesign.
- Hand-edited audit artifact as source of truth.
- Optimization claims without proof.

## Technical Constraints

- Preserve existing analyst workflows unless a slice explicitly changes and proves a new contract.
- Preserve diagnostics, failure visibility, CSP/DOM safety, and redaction boundaries.
- Use generated audit artifacts rather than hand-patched markdown where practical.
- Use repo-native verification lanes from `Makefile`.
- Do not rewrite stable seams solely because they are imperfect.

## Integration Points

- Flask routes — request handling, analysis, enrichment status, history/detail/settings/diagnostics surfaces.
- Enrichment orchestrator and provider registry — fan-out, cache, retries/backoff, status snapshots, diagnostics.
- SQLite cache/history stores — local persistence and reload continuity.
- TypeScript browser modules — polling, result application, filtering, export/copy, history/settings interactions.
- Templates — analyst-visible DOM structure and server-rendered data contracts.
- Audit runner and Makefile — generated optimization proof and verification lanes.

## Testing Requirements

- Focused Python or TypeScript tests should cover each changed seam.
- `make verify-fast` is required for implementation slices.
- `make verify-deep` is required for browser-visible, live-enrichment, polling/status, or shared result-application changes.
- Final `make verify` is required before milestone completion.
- Generated M020 audit artifact should be regenerated after implementation slices so it reflects shipped/rejected outcomes.

## Acceptance Criteria

- M020 produces a generated audit artifact for this milestone, not hand-written optimization prose.
- The audit ranks rewrite candidates into do-now, do-next, later, and leave-alone outcomes.
- Each shipped refactor or optimization is tied back to an audit target.
- Each shipped change has either measurement evidence or explicit code-path reasoning.
- Focused regression tests protect every changed seam.
- Analyst-visible workflows remain intact: intake, extraction, enrichment, results, history/detail, diagnostics, filtering/copy/export.
- Rejected risky optimizations are documented as keep-decisions, not silently dropped.
- Final verification proves the app still works end-to-end.

## Open Questions

- Which exact target S02 ships depends on the M020 audit output.
- Whether S03 or S04 finds a second rewrite target strong enough to ship, or records a rejection/leave-alone outcome, depends on S01 and S02 evidence.
