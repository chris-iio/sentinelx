# Milestones

## v1.0 Foundation (Shipped: 2026-03-14)

**Timeline:** 2026-02-21 → 2026-03-14 (22 days, 9 internal milestones)
**LOC:** ~4,923 Python + ~2,459 TS + ~635 templates + ~12,350 tests
**Tests:** 757+ unit/integration + 91 E2E
**Providers:** 14 (6 zero-auth, 1 public, 7 key-auth)

**Delivered:** A universal threat intelligence hub for SOC analysts. Paste free-form text — alerts, email headers, threat reports, raw IOCs — and get the complete intelligence picture from 14 providers at once with transparent per-provider verdicts.

**Capability summary:**
- IOC extraction from free-form text with 20-pattern defanging normalizer and 8-type classifier
- 14 threat intel providers via Provider Protocol + Registry architecture
- Results page: summary rows with worst verdict + consensus badges, expandable per-provider details
- Bookmarkable per-IOC detail page with tabbed provider results + SVG relationship graph
- Dark-first design system (zinc/emerald/teal), TypeScript 5.8 + esbuild, Tailwind CSS standalone
- SQLite cache with configurable TTL, client-side export (JSON/CSV/clipboard), bulk input mode
- Security-first: CSP, CSRF, SSRF allowlist, textContent-only DOM, no innerHTML

**Internal milestone history (collapsed):**

| # | Name | Shipped | Key Feature |
|---|------|---------|-------------|
| 1 | MVP | 2026-02-24 | Core IOC extraction + enrichment (3 providers) |
| 2 | UX Overhaul | 2026-02-25 | Card layout + filtering |
| 3 | Modern UI Redesign | 2026-02-28 | Design tokens + components |
| 4 | Visual Experience | 2026-02-28 | Page-level polish + animations |
| 5 | Home Page Modernization | 2026-02-28 | Minimal header + compact controls |
| 6 | TypeScript Migration | 2026-03-01 | JS→TS with strict types |
| 7 | Universal Threat Intel Hub | 2026-03-03 | 8 providers + registry + unified UX |
| 8 | Quality-of-Life | 2026-03-09 | Cache + export + bulk input |
| 9 | Analyst Experience + cleanup | 2026-03-14 | 14 providers + detail page + ASN intel |

**Git range:** initial commit → `ae48000`

---
