# M016: Minimal Useful Product Hardening

**Vision:** Make SentinelX feel like a fast, minimal, local-first IOC evidence workbench: paste suspicious text, extract observables, optionally enrich them, review transparent evidence, and resume prior work without dashboard clutter. M016 deliberately avoids new provider expansion unless later evidence proves it is necessary.

## Success Criteria

- The primary workbench is visibly simpler and less dashboard-like while preserving Offline/Online semantics.
- Offline paste-to-results remains local-only and is backed by fresh runtime evidence.
- Online mode remains explicit about configured provider work, progress, failures, and source-level evidence.
- Results are easier to scan: dashboard chrome is removed, collapsed, or visually quieted without hiding evidence.
- History resume remains available but secondary, and replay does not re-query providers.
- Desktop and mobile browser proof covers the core loop.
- Final verification uses established lanes, including `make verify-fast` after implementation.

## Slices

- [ ] **S01: Product-loop baseline and stale-plan cleanup** `risk:medium` `depends:[]`
  > After this: M016 docs/state point away from EmailRep, the current `/` → analyze → results → history loop has a browser/code audit, and at least one runtime baseline is recorded for the Offline path.

  **Tasks**
  - T01 Replace stale EmailRep execution plan with minimal-product research and roadmap.
  - T02 Audit the current browser loop on desktop/mobile and record concrete friction points.
  - T03 Capture baseline timing for Offline paste-to-results or the closest deterministic route/browser path.

  **Acceptance**
  - `M016-RESEARCH.md`, `M016-ROADMAP.md`, and `.gsd/STATE.md` agree on the minimal-useful-product direction.
  - The audit identifies specific UI/runtime targets rather than generic redesign goals.
  - Baseline evidence exists before speed claims are made.

- [ ] **S02: Minimal intake workbench** `risk:medium` `depends:[S01]`
  > After this: `/` has one obvious paste-and-extract surface, mode choice remains explicit but quieter, and recent history no longer competes with the primary action.

  **Likely work**
  - Shorten hero/mode copy while preserving accessible status text.
  - Keep stable form contracts: CSRF, `#ioc-text`, `#mode-input`, mode toggle behavior, submit disablement, Offline default.
  - Make recent analyses visually secondary, collapsed, or less rail-like.
  - Preserve fail-open history behavior.

  **Acceptance**
  - Empty, error, paste, clear, Offline, and Online-selection states remain understandable.
  - Mobile layout keeps the input first and avoids clipped controls.
  - Existing form tests are updated/kept green.

- [ ] **S03: Scannable results without dashboard chrome** `risk:high` `depends:[S01]`
  > After this: results prioritize extracted IOCs and transparent evidence; provider progress/failure remains visible, but KPI/dashboard surfaces are reduced or collapsed.

  **Likely work**
  - Replace or quiet `_verdict_dashboard.html` provider/KPI chrome.
  - Keep result-card verdict labels and provider evidence visible.
  - Make filters/search compact and proportionate to result count/mode.
  - Preserve export behavior where already supported, but keep it secondary.
  - Keep detail/context links and text-only DOM rendering.

  **Acceptance**
  - Offline results show IOC count and cards with minimal controls.
  - Mocked Online results show progress/terminal provider state without visual overload.
  - Provider failures/no-data remain visible and actionable.
  - Result rendering tests and browser fixtures cover live and history application paths.

- [ ] **S04: Runtime and integration hardening** `risk:high` `depends:[S02,S03]`
  > After this: one meaningful runtime path has before/after evidence or explicit keep-decision, and the full paste/extract/enrich/review/resume loop is verified.

  **Likely work**
  - Optimize the measured bottleneck if evidence points to a safe improvement.
  - If no code change is warranted, record code-path reasoning and measured baseline.
  - Verify Offline paste-to-results on desktop and mobile.
  - Verify mocked Online enrichment progress/result rendering.
  - Verify history resume does not re-enrich or poll live status.

  **Acceptance**
  - Runtime evidence is committed or referenced in the slice notes/artifact.
  - `make verify-fast` passes after touched code/build artifacts are updated.
  - Browser proof exercises the product loop, not only selector existence.

## Boundary Map

- **In:** Core workbench UX, results UI simplification, history-as-secondary UX, Offline/Online semantics, runtime measurement, targeted speed improvement, browser verification.
- **Out:** EmailRep provider integration, raw EML/header analysis, phishing-triage expansion, SIEM/SOAR workflows, opaque AI scoring, new external services by default.
- **Keep stable:** CSRF/security behavior, text-only DOM construction, Offline local-only guarantee, provider registry/configuration model, existing history/cache persistence semantics, stable test selectors unless intentionally updated.

## Notes

EmailRep is now a future backlog candidate, not M016 execution scope. If later work adds email provider coverage, it should be planned as a separate provider milestone after the minimal product loop is proven.
