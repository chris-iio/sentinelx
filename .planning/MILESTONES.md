# Milestones

## v1.0 MVP (Shipped: 2026-02-24)

**Phases:** 5 (1, 2, 3, 3.1, 4) | **Plans:** 14 | **Requirements:** 34/34
**Timeline:** 4 days (2026-02-21 to 2026-02-24)
**LOC:** ~3,200 app (Python + HTML/CSS/JS) + ~3,900 tests
**Commits:** 78 (20 feat)

**Delivered:** A security-first local IOC triage tool for SOC analysts — paste text, extract and classify 8 IOC types, enrich against 3 threat intelligence providers in parallel, and review transparent per-provider verdicts.

**Key accomplishments:**
1. Security-first Flask scaffold — TRUSTED_HOSTS, CSRF, CSP, input size cap established before any route code
2. Dual-library IOC extraction (iocextract + iocsearcher) with 20-pattern defanging normalizer and deterministic 8-type classifier
3. VirusTotal API v3 adapter with full HTTP safety controls (timeout, stream+size-cap, no-redirect, SSRF allowlist) and parallel enrichment orchestrator
4. Multi-provider threat intelligence — VirusTotal, MalwareBazaar, ThreatFox dispatched in parallel with per-provider error isolation
5. Verdict clarity UX — NO RECORD vs CLEAN instantly distinguishable, collapsed no-data sections, pending provider indicators
6. Automated security regression guards — CSP, template XSS safety, adapter SSRF safety codified as pytest tests (224 tests, 97% coverage)

**Git range:** `docs: initialize project` .. `docs(phase-04): complete phase execution`

**Archives:**
- `milestones/v1.0-ROADMAP.md`
- `milestones/v1.0-REQUIREMENTS.md`
- `milestones/v1.0-MILESTONE-AUDIT.md`
- `milestones/v1.0-phases/` (phases 1-3.1)

---

