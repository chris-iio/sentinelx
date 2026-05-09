# M016: Minimal Useful Product Hardening

**Gathered:** 2026-05-09
**Status:** Ready for planning

## Project Description

SentinelX is a local-first threat-intel evidence workbench. Its useful core is not “more providers” or a dense SOC dashboard; it is the fast analyst loop the product already points toward: paste messy security text, extract observables, optionally enrich them, and show transparent evidence clearly enough that the analyst can decide what matters.

The product should feel fast, efficient, and simple — closer to the clarity of a ChatGPT UI than a dashboard. That does not mean turning SentinelX into a literal chatbot. It means one obvious place to start, low ceremony, minimal visual noise, quick feedback, and results that read like useful evidence rather than UI chrome.

## Why This Milestone

SentinelX has accumulated substantial capability across prior milestones: extraction, Offline/Online modes, provider enrichment, result cards, detail pages, history reload, settings, REST APIs, verification lanes, and the M015 intake workbench. The next risk is not missing surface area; it is that the product becomes heavier than the analyst task.

M016 exists to make the current product work cleanly as a minimal useful tool. It supersedes the previous EmailRep-centered framing. Email reputation may still be useful later, but adding another provider does not answer the user’s current concern: “why don’t we just make sure the product now works, with the most minimalistic and useful UI?”

The milestone should prove and improve the existing product loop before expanding scope.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Open the local SentinelX browser app, paste suspicious text into a simple workbench, and get useful extracted evidence quickly without navigating a dense dashboard.
- Choose Offline or Online intentionally, run the analysis, and understand what is happening without ambiguous waiting states or unnecessary controls competing for attention.
- Review results that preserve transparent provider evidence while removing or quieting dashboard chrome.
- Resume a prior analysis from history when needed, without history dominating the primary paste-and-review workflow.

### Entry point / environment

- Entry point: local browser app, primarily `/`, analysis submission, results, detail/context, and history resume flows.
- Environment: local dev / browser, verified on desktop and mobile viewport sizes.
- Live dependencies involved: none for Offline mode; configured enrichment providers for Online mode; SQLite history/cache stores; local dev-server lifecycle for operational proof.

## Completion Class

- Contract complete means: route tests, frontend tests, extraction/enrichment tests, and browser fixtures prove the existing core workflow remains correct after simplification.
- Integration complete means: paste → extract → Offline/Online mode → results rendering → detail/context access → history/resume works across Flask routes, TypeScript modules, enrichment/status paths, and SQLite-backed history.
- Operational complete means: the local browser app remains fast and predictable under the supported dev-server lifecycle and established verification lanes, with runtime speed improvements backed by measurement or explicit code-path proof.

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- A real Offline paste-to-results scenario is fast, visibly simple, and still preserves extraction correctness, CSRF/security behavior, and result usability.
- A mocked Online enrichment scenario renders provider evidence correctly without clutter, ambiguous progress, or regression in live/history result application.
- A prior analysis can be resumed from history while the history surface remains secondary to the primary workbench.
- Runtime speed work cannot be hand-waved: at least one meaningful runtime path must be audited and either improved with before/after evidence or explicitly kept with code-path reasoning.
- Browser verification must exercise the UI as a product, not just prove that selectors exist.

## Architectural Decisions

### Reframe M016 away from EmailRep

**Decision:** M016 is a minimal useful product hardening milestone, not an EmailRep provider-integration milestone.

**Rationale:** The user questioned the product identity and clarified the real desire: make the current product work, make it fast and efficient, and make the UI as simple as a ChatGPT-like experience. EmailRep adds coverage, but it does not answer whether SentinelX’s existing loop is useful, fast, and minimal.

**Alternatives Considered:**
- EmailRep provider integration — useful later as email IOC coverage, but premature while product usefulness and UI weight are being questioned.
- Broader phishing investigation workbench — too wide for the current direction and risks turning SentinelX into a different product.
- Threat-intel aggregator expansion — too easy to become “more sources” instead of a better analyst loop.

---

### Product identity: local-first evidence workbench

**Decision:** Treat SentinelX as a local-first threat-intel evidence workbench: paste messy security text, extract observables, enrich when requested, and preserve transparent evidence.

**Rationale:** This framing keeps the existing architecture useful while rejecting two traps: opaque scoring and dashboard sprawl. SentinelX should help analysts see source-level evidence quickly, not pretend to be a magic risk oracle.

**Alternatives Considered:**
- Full SOC/SIEM/SOAR platform — too broad and inconsistent with the local-first, analyst-controlled workflow.
- Literal ChatGPT-style chatbot — captures the desired simplicity, but would discard useful existing extraction/enrichment structure too aggressively.
- Personal scratchpad only — too small; it underplays the product’s provider-backed evidence value.

---

### Interaction model: refined workbench, not literal chat

**Decision:** Preserve the current workbench structure but refine it hard toward minimalism, directness, and speed.

**Rationale:** The user selected “Workbench refined” while describing the desired feel as “as simple as a ChatGPT UI.” The right move is not to rebuild the app as a chat interface; it is to make the existing input/results workflow feel sparse, obvious, and fast.

**Alternatives Considered:**
- Prompt plus answer — closest to ChatGPT, but risks prematurely throwing away route/result/detail/history structures that already support the product.
- Split workflow — preserves all existing screens, but risks keeping too much ceremony and visual weight.

---

### Speed priority: runtime speed first

**Decision:** Runtime speed is the primary speed target for M016, supported by perceived-speed and workflow simplification work where they serve the same loop.

**Rationale:** The user selected runtime speed. “Fast” should therefore be proven with measurement or code-path evidence, not just a cleaner-looking UI. UI responsiveness still matters, but it cannot substitute for actual runtime efficiency.

**Alternatives Considered:**
- Perceived speed — important for UX, but insufficient if the underlying product still waits unnecessarily.
- Workflow speed — useful, but secondary to making the current product actually fast.

---

### Minimal UI target: remove or quiet dashboard chrome

**Decision:** M016 should be willing to remove, collapse, or visually quiet dashboard chrome that competes with the primary input/results loop.

**Rationale:** The user selected dashboard chrome as the kind of complexity to remove. The desired surface is minimal and useful, not decorated, dense, or visually over-explained.

**Alternatives Considered:**
- Hide advanced controls first — potentially useful, but less central than reducing overall visual weight.
- Remove nothing until after audit — safer, but too passive given the user’s clear preference for minimalism.

---

### No new external provider by default

**Decision:** M016 should not add a new provider or new external service by default.

**Rationale:** The current milestone is about product usefulness, speed, and minimalism. New provider integration adds configuration, status, UI, and test surface area. It belongs only if the audit proves it is necessary for the core useful loop.

**Alternatives Considered:**
- Add EmailRep anyway — improves email coverage, but adds scope and does not address the product-level concern.
- Start phishing triage — significantly broader than the confirmed direction.

## Error Handling Strategy

M016 should preserve SentinelX’s existing explicit failure philosophy while simplifying the presentation. Failures should be visible, actionable, and proportionate — not hidden, but not turned into dashboard noise.

Offline mode should remain local-only and fast. Online mode should continue to distinguish configured-provider coverage, progress, terminal errors, and provider failures through the existing enrichment/status contract. History failures should remain fail-open where already designed, especially on the intake surface, so history never blocks the primary analysis loop.

Runtime improvements must not suppress errors to appear faster. If a slow path is kept, record why. If a slow path is changed, verify both the happy path and the diagnostic/failure behavior.

## Risks and Unknowns

- “Fast” is not yet quantified — M016 must identify a runtime path and prove improvement or an explicit keep-decision.
- “Minimal” can accidentally hide evidence — result simplification must preserve transparent provider facts and analyst trust.
- UI cleanup can become subjective redesign theater — use browser audit and user-loop proof, not only aesthetic preference.
- The current app has several surfaces (`/`, results, detail pages, history, settings); scope must stay tied to the core paste/review/resume loop.
- Removing dashboard chrome may break tests or stable selectors if done carelessly — preserve existing contracts or update tests intentionally.
- Existing history and live-result parity are easy to fake with presence-only assertions; final proof should exercise actual visible state and non-polling history behavior.

## Existing Codebase / Prior Art

- `.gsd/PROJECT.md` — current product state, prior milestone sequence, and M015 intake-workbench baseline.
- `.gsd/REQUIREMENTS.md` — current capability contract, especially continuity around extraction/enrichment/history after UI changes.
- `app/templates/index.html` — current intake workbench surface and likely first simplification target.
- `app/static/src/ts/modules/form.ts` — input, paste feedback, mode toggle, hidden mode contract, submit enablement.
- `app/templates/results.html` and `app/templates/partials/_ioc_card.html` — current result presentation surface.
- `app/templates/partials/_enrichment_slot.html` — current provider-evidence detail structure.
- `app/static/src/ts/modules/result-application.ts` — shared live/history rendering coordinator.
- `app/routes/analysis.py` — analysis submission and provider-count setup.
- `app/routes/enrichment.py` — Online status/progress endpoint and live polling surface.
- `app/routes/history.py` and `app/enrichment/history_store.py` — resume/history surface.
- `tools/dev_server.py` and `app/health_contract.py` — supported local lifecycle/readiness surfaces for operational proof.
- `Makefile` — established verification lanes: `make verify-fast`, `make verify-deep`, and `make verify`.

## Relevant Requirements

- R076 — Existing extraction, enrichment, history reload, CSRF/security headers, TypeScript build, and E2E behavior remain intact after intake/results UI changes.
- R070–R075 — M015 intake-workbench requirements remain relevant as the baseline being simplified and hardened.
- R009 — CSP, CSRF protection, textContent-only DOM construction, SSRF allowlist, and host validation must remain intact.
- R020/R024/R025 — Runtime, build, and security quality constraints remain part of the proof surface when touching enrichment/status/frontend paths.

## Scope

### In Scope

- Product-level browser audit of the current core loop.
- Runtime-speed investigation and one or more targeted speed improvements where evidence supports them.
- Minimal UI simplification of the workbench/results/history surfaces, especially dashboard chrome.
- Clearer loading, empty, no-provider, and failure states where they affect the core loop.
- Preservation of Offline and Online semantics.
- Verification that history/resume remains available but secondary.
- Desktop and mobile viewport proof for the simplified flow.

### Out of Scope / Non-Goals

- EmailRep provider integration by default.
- Raw EML parsing, header authentication analysis, or broad phishing triage.
- Rebuilding SentinelX as a literal chat application.
- Full SOC/SIEM/SOAR workflows, team case management, alert ingestion, or live monitoring.
- Opaque AI scoring or hiding provider-level evidence behind a single magic verdict.
- Adding visual chrome, dashboards, dense metrics, or new panels unless they directly improve the core loop.

## Technical Constraints

- Preserve stable form IDs and contracts used by the current intake flow: CSRF, `#ioc-text`, hidden mode input, mode toggle behavior, submit behavior, and Offline/Online semantics.
- Preserve text-only DOM construction and safe rendering patterns; do not introduce `innerHTML` rendering for external provider/input data.
- Use existing Flask routes and TypeScript modules unless the audit finds a concrete reason to change architecture.
- Runtime speed work must be measured or justified by explicit code-path reasoning.
- UI simplification must be verified in a real browser; selector-level tests alone are not enough.
- Use established verification lanes rather than inventing new wrappers: `make verify-fast` for routine proof, `make verify-deep` for browser/live-results surface proof, and `make verify` for full pre-handoff proof when appropriate.
- Do not degrade history replay: reloading a past analysis must not re-query providers.

## Integration Points

- Intake form / analysis route — the start of the minimal workflow and the place where ceremony must be lowest.
- Extraction pipeline — must remain correct and fast for Offline mode.
- Enrichment orchestrator / status endpoint — candidate runtime path for Online speed and progress clarity.
- Result rendering coordinator — must keep live and history behavior aligned while simplifying visible output.
- History store/routes — must keep resume available but visually secondary.
- CSS/TypeScript build pipeline — must produce generated assets and preserve responsive behavior.
- Local dev-server health/lifecycle — operational proof surface for browser verification.

## Testing Requirements

M016 should combine product-facing browser proof with focused regression and runtime evidence.

Required proof classes:

- Unit/route tests for touched backend behavior, especially analysis, enrichment status, history, CSRF/security, and no-provider/failure paths.
- Frontend TypeScript/Vitest tests for touched modules such as form behavior, result application, filtering/details, or context rendering.
- Generated asset proof through the existing build targets.
- Browser proof for Offline paste-to-results on desktop and mobile.
- Browser proof for mocked Online enrichment rendering, including progress/terminal state and provider evidence visibility.
- Browser proof for history resume that confirms history does not poll/re-enrich and visible state matches the saved result.
- Runtime evidence for at least one speed target: before/after timing, benchmark-like script, browser timing, or explicit code-path reasoning with verification.
- Final verification should include `make verify-fast`; if results/intake/browser surfaces change materially, include the appropriate deep/browser verification lane.

## Acceptance Criteria

M016 planning should turn this context into slices that satisfy these acceptance criteria:

- The primary workbench is visibly simpler and less dashboard-like while preserving the useful Offline/Online choice.
- The current product loop works end-to-end: paste, extract, optionally enrich, review, open details/context where useful, and resume from history.
- Dashboard chrome is removed, collapsed, or visually quieted where it competes with the input/results loop.
- Runtime speed work is evidence-backed; no “it feels faster” claim is accepted without measurement or code-path proof.
- The simplified UI preserves transparent provider evidence and does not introduce opaque scoring.
- Offline mode remains local-only and fast.
- Online mode remains explicit about provider work, progress, and failures.
- History remains available but secondary.
- Desktop and mobile layouts remain usable without overflow or clipped clickable elements.
- No new provider, phishing triage, or platform scope is introduced unless a later explicit decision reopens that scope.

## Open Questions

- Which runtime path should be measured first: extraction, initial page load, analysis submission, enrichment status polling, result rendering, or history resume? Current thinking: start from the actual browser loop and let evidence pick the path.
- How aggressive should result-card simplification be? Current thinking: remove chrome first, but keep provider evidence discoverable and trustworthy.
- Should the final UI move toward a single prompt-and-response page over future milestones? Current thinking: not in M016; refine the existing workbench first.
- What exact performance bar should define “fast enough”? Current thinking: M016 planning should set concrete timing targets after a baseline browser/runtime audit.
