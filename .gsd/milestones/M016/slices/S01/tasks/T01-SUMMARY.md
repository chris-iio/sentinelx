# T01 Summary: Replace stale EmailRep plan with minimal-product research and roadmap

## What changed

- Replaced the stale EmailRep-centered `M016-RESEARCH.md` with product research for SentinelX as a minimal local-first IOC evidence workbench.
- Replaced the EmailRep `M016-ROADMAP.md` with four product-hardening slices: baseline cleanup, minimal intake workbench, scannable results, and runtime/integration hardening.
- Updated active state wording to point at `M016: Minimal Useful Product Hardening` and the next product-loop audit action.
- Rewrote S01 and task plans so current execution no longer points at `EmailRepAdapter` implementation.
- Saved web research artifacts under `.firecrawl/` for reference.

## Key decision

EmailRep is now treated as a future provider backlog candidate, not M016 execution scope. M016 should first prove the current paste/extract/enrich/review/resume loop is useful, fast, and minimal.

## Verification

Run the grep command from `T01-PLAN.md` after the latest edits. Stale active EmailRep execution references should be gone; explicitly superseded historical mentions in research/summary files are acceptable.

## Next

Proceed to T02: audit the current browser loop on desktop/mobile and record concrete UI/runtime friction points.
