# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v6.0 — Analyst Experience

**Shipped:** 2026-03-14
**Phases:** 4 | **Plans:** 11 | **Sessions:** ~6

### What Was Built
- Zero-auth IP intelligence (GeoIP, rDNS, proxy flags) via ip-api.com
- Known-good hash detection via CIRCL hashlookup with distinct KNOWN GOOD verdict
- Live DNS records (A/MX/NS/TXT) via dnspython for domain IOCs
- Certificate transparency history via crt.sh for domain IOCs
- Passive DNS pivoting via ThreatMiner for all IOC types
- Bookmarkable per-IOC detail page with CSS-only tabbed provider results
- SVG hub-and-spoke relationship graph on detail page
- Analyst annotations (notes + tags) with SQLite persistence
- Tag-based filtering on results page

### What Worked
- **Zero-auth provider pattern** was extremely productive — each new adapter followed the same Protocol + register() pattern, averaging 5 minutes per plan
- **TDD discipline** caught real bugs early — ThreatMiner's string "404" status code, DNS NXDOMAIN edge cases
- **CONTEXT_PROVIDERS generalization** in Phase 02-03 paid dividends — ThreatMiner (Phase 03) wired with zero frontend changes
- **Phase execution speed** — 11 plans across 4 phases completed in ~3 days, most plans under 15 minutes
- **Separate AnnotationStore DB** — clean architectural decision that prevented cache clear from destroying analyst work

### What Was Inefficient
- **Phase 01 verification gap** — Phase 01 was executed before the verification workflow was fully established, causing 6 requirements to fail 3-source cross-reference at audit time (documentation gap, not feature gap)
- **ROADMAP.md progress table** had stale data from previous milestones (v1.1, v1.2, v3.0 rows showed wrong numbers)
- **Phase 04 plan checkboxes** in ROADMAP.md never got checked despite plans completing — manual tracking drift

### Patterns Established
- **Zero-auth adapter pattern:** HTTP safety controls + validate_endpoint + TIMEOUT + read_limited for all HTTP adapters; DNS adapters skip HTTP safety entirely
- **Context row rendering:** CONTEXT_PROVIDERS module-scope set routes providers through shared createContextRow() — adding a context provider requires zero renderer changes
- **Separate SQLite DBs:** Different persistence concerns (cache vs annotations) use separate database files for lifecycle independence
- **CSS-only interactivity:** Tab switching via radio inputs + adjacent sibling selectors — no JavaScript required

### Key Lessons
1. **Run verification during phase execution, not after** — retroactive verification is busywork; inline verification catches real issues
2. **Generalize rendering paths early** — the CONTEXT_PROVIDERS pattern created in Phase 02 made Phases 03 and 04 trivially fast
3. **Zero-auth providers maximize analyst value** — 5 of 13 providers now require no configuration, meaning SentinelX is useful immediately after install
4. **Separate DBs for separate lifecycles** — AnnotationStore using its own SQLite file was the right call; mixing it with cache would have created a data loss footgun

### Cost Observations
- Model mix: ~80% sonnet, ~20% opus (opus for planning/research, sonnet for execution)
- Sessions: ~6 across 3 days
- Notable: Plans averaged under 10 minutes each — the provider adapter pattern is now extremely efficient

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v6.0 | ~6 | 4 | Research-first + Nyquist validation adopted; zero-auth provider pattern |

### Cumulative Quality

| Milestone | Tests | Coverage | Providers |
|-----------|-------|----------|-----------|
| v1.0 | 224 | 97% | 3 |
| v4.0 | 542 | ~95% | 8 |
| v5.0 | 483 | ~95% | 8 |
| v6.0 | 848+ | ~95% | 13 |

### Top Lessons (Verified Across Milestones)

1. **TDD catches real bugs** — verified across v1.0 (SSRF), v4.0 (provider edge cases), v6.0 (ThreatMiner status codes, DNS NXDOMAIN)
2. **Protocol + Registry pattern scales** — went from 3 to 13 providers with zero orchestrator changes across v4.0 and v6.0
