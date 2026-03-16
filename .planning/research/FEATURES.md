# Feature Research

**Domain:** Threat intelligence results page — multi-source aggregation, unified presentation
**Milestone:** v1.1 Results Page Redesign
**Researched:** 2026-03-16
**Confidence:** HIGH (platform patterns from official docs + direct inspection); MEDIUM (specific
implementation approaches, comparative analysis based on public documentation)

---

## Context: This Is a Presentation Redesign, Not a Feature Addition

The app already ships 14 providers, per-IOC detail pages, export, bulk input, cache, filter bar,
and verdict dashboard. The problem is not missing data — it is how that data is presented.

Current state: 14 provider rows (verdict badge + attribution + stat text + context fields) displayed
inside an expandable accordion per IOC card. Summary row shows worst verdict + consensus badge.
Context providers (IP Context, DNS Records, Cert History, ThreatMiner, ASN Intel) are pinned to top
of the expanded section. All other providers are sorted by severity descending.

The problem statement: "results feel like 14 separate search results stapled together, not one
cohesive report. Information isn't uniform across providers. Mix of verdicts, context rows, no-data
rows feels disjointed."

This research answers: what design patterns do the best threat intelligence platforms use to make
multi-source results feel like one unified answer?

---

## How the Best Platforms Solve This

### VirusTotal: Separation by Information Type, Not Source

VirusTotal's core architectural insight is that different questions deserve different views, and
sources should be subordinate to those views. Their tab structure for file/URL reports:

- **Summary header** (always visible): Detection ratio ("X / Y" flagged), community score, hash,
  timestamp, tags. This is the unified answer at a glance.
- **Detection tab**: Partner verdict grid — all vendor results in one flat table, grouped by
  verdict category (malicious / suspicious / clean / undetected). Sources appear as rows within
  categories, not as the organizational unit.
- **Details tab**: Metadata (file properties, HTTP headers, DNS records) — type-specific context
  separated from reputation judgments.
- **Relations tab**: Relationships and pivots — all IOC-to-IOC connections independent of which
  source found them.
- **Community tab**: Analyst notes and votes — separated from automated signals.

Key lesson: **verdict assessment** and **contextual intelligence** and **relationships** are
fundamentally different kinds of information and should never be mixed in the same section.

Domain/IP reports in VirusTotal intentionally omit partner verdicts (because vendors don't rate IPs
as "malicious" the same way they rate files). Instead they show pure context — passive DNS, WHOIS,
ASN, communicating files. This distinction between IOC types is a critical design principle.

### Hybrid Analysis: Severity-First, Source-Secondary

Hybrid Analysis leads with a **threat score** (e.g., 66/100) and an **AV detection rate** (e.g.,
9%) in the header — the synthesized judgment — before any source is named. Then it groups findings
into **Malicious Indicators** / **Suspicious Indicators** / **Informative Indicators** with counts.
Within each group, items show their source type (Static Parser, API Call, Registry Access) as an
attribute, not the organizing principle.

The MITRE ATT&CK matrix section organizes tactics/techniques without naming which analyzer found
each — the framework is the organizing lens, not the tool.

Key lesson: **group by threat signal type** (malicious / suspicious / informative / context), not
by provider name. Provider is an attribute within a group, not a section header.

### Shodan: Category-First, Drill-Down Architecture

Shodan's host page opens with a **General Information block** (location, org, ISP, ASN) — a single
unified identity section that collapses all provider outputs for that category. Then **Web
Technologies** as a second block. Then **Open Ports** as navigable tab anchors.

Each port section reveals nested detail (SSL cert, banners, service identification, vulnerability
CVEs) via sequential drill-down. The user never sees "nginx reports X, Shodan reports Y" — they see
a unified answer for the port with all data synthesized under one heading.

Key lesson: **group by topic/category** (identity, network, reputation, behavior), not by data
source. Multiple sources feeding the same category should appear together under that category.

### IntelOwl: DataModel Synthesis

IntelOwl v6.2+ introduced "DataModels" that normalize all analyzer outputs into standardized keys
before display. Instead of showing OTX's response format next to ThreatFox's response format, both
are mapped to `{ ip_reputation, asn, last_seen, associated_malware }` and displayed uniformly.

Their "Visualizers" aggregate across multiple analyzers (e.g., "DNS Visualizer aggregates all DNS
analyzer reports") so the display unit is the topic, not the tool.

Key lesson: **normalize provider output to domain fields** before display. "Reputation" means the
same thing whether it comes from AbuseIPDB or GreyNoise — the label should match, not the provider
name.

### URLScan.io: Context First, Security Second

URLScan organizes scan results as: infrastructure (IPs/domains/technologies found) → statistics
(counts, protocols) → enrichment (geolocation, ASN, rankings) → security verdicts (threat
analysis, community). Context establishes what something IS before the verdict establishes whether
it's BAD.

Key lesson: **establish identity before making judgment**. Show "this IP is in US-East, owned by
Hetzner, serving port 443 with Nginx" before "3 providers flagged this as malicious."

---

## Feature Landscape

### Table Stakes (Analysts Expect These)

Features that any analyst would expect from a unified threat intelligence results view.
Missing these makes the redesign feel superficial.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Verdict-first summary per IOC | Every serious TI platform leads with the judgment — analyst should know malicious/clean before reading any detail | LOW | Already exists as worst-verdict badge; needs better visual hierarchy/prominence |
| Clear visual separation of verdict vs context providers | VirusTotal, Shodan, URLScan all separate "reputation signals" from "contextual data" — mixing them creates confusion | MEDIUM | Currently all rows in one flat list; context providers pinned to top but visually identical to verdict rows |
| Grouped provider display by category | Hybrid Analysis, Shodan group signals by type (malicious / suspicious / informative / context) not by source name | MEDIUM | Currently: flat list sorted by severity. Needed: category sections with counts per section |
| Provider count shown in summary ("3/9 flagged") | VT shows "X/Y engines"; HA shows AV detection rate — analysts want denominator, not just numerator | LOW | Consensus badge `[2/5]` partially does this; needs to be more prominent and readable |
| Empty/no-data state clearly separated from clean verdict | A provider that has no record ≠ a provider that checked and found nothing | LOW | Currently both map to `no_data` label; "checked and clean" vs "no record found" are different signals |
| Context fields readable without expanding details | Shodan shows key fields (open ports, vulns) inline on the search results card — critical context should not require expansion | MEDIUM | Currently context fields (GeoIP, ASN, ports) are hidden in expanded accordion; minimal context should always be visible |
| IOC type badge clearly visible | Every platform distinguishes IP / domain / URL / hash — different types have different signals, the analyst must know which they're looking at | LOW | Already implemented; needs consistent prominent placement |
| Scan date or data freshness indicator | Analysts care whether VirusTotal result is from today or 6 months ago; stale data changes the verdict meaning | LOW | `scan_date` is already in `EnrichmentResultItem`; not currently surfaced in summary row |

### Differentiators (What Makes This Feel Like One Report)

Features that go beyond "list of provider results" toward "unified intelligence report."
These are the features that make the difference between 14 results stapled together and one answer.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Category-grouped provider sections | Show verdict-producing providers in one section ("Reputation"), context providers in another ("Infrastructure"), zero-data providers collapsed or in a third section ("No Data") — matching Hybrid Analysis / VirusTotal pattern | MEDIUM | Requires template redesign of enrichment-details; existing CONTEXT_PROVIDERS set is the seed for this grouping |
| Inline context summary always visible | Show 2-3 key context fields (GeoIP country, ASN org, open port count) directly in the IOC card header without requiring expansion — the "at a glance" context that establishes identity before judgment | MEDIUM | Requires context providers to complete before card renders context line; may need to wait for first context result |
| Verdict breakdown micro-bar | Visual "3 malicious / 2 suspicious / 4 clean / 5 no data" bar within each IOC card — matches Hybrid Analysis's "Malicious/Suspicious/Informative" count approach; richer than current `[2/5]` text badge | MEDIUM | Client-side, requires count tracking already in iocVerdicts; pure CSS/DOM addition |
| Provider category icons/labels | Distinct visual treatment for reputation providers (flag icon) vs infrastructure context (server icon) vs passive intel (clock icon) — reinforces that different rows answer different questions | LOW | CSS token + icon addition; high visual impact for low implementation cost |
| "No data" section collapsed by default | Move all no-data providers into a collapsed section ("5 providers had no record") rather than showing them as flat rows equal to providers with actual findings | LOW | Currently no-data rows appear in the same sorted list; separating them reduces visual noise significantly |
| Worst-verdict summary as report headline | Make the worst-verdict badge the dominant visual element in the IOC card — current badge is 12-16px text in a row; should be the first thing the eye goes to (size hierarchy matching VT's large X/Y detection ratio) | LOW | CSS change to verdict-label/verdict-badge sizing in ioc-card-header; high impact, low cost |
| Staleness indicator on cached results | Show "data from 4h ago" on summary row when result was served from cache — matches VT's timestamp-in-summary approach; tells analyst whether to trust the verdict or re-query | LOW | `cached_at` field already exists in EnrichmentResultItem and is shown in expanded detail rows; surface in summary row |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Composite threat score (e.g., "74/100") | Feels like a unified answer; analysts want one number | Hides the reasoning; obscures which providers drove the score; SentinelX's core design philosophy is transparency — "never invent scores"; composite scores require calibration that doesn't exist here | Use verdict breakdown bar (malicious count / responded count) — visual but not invented |
| Provider logo/branding in rows | Looks professional, easier to recognize at a glance | Significantly increases page weight (14 logos × number of IOCs); logos require licensing verification; textContent-only DOM rule makes inline SVG complex | Use consistent provider name abbreviations with color-coded category badges |
| Auto-expand all IOC cards | Analyst wants everything visible immediately | 10 IOCs × 14 providers = 140 rows visible simultaneously; catastrophic for scan time and cognitive load | Expand only the highest-severity IOC by default; let analyst expand others on demand |
| Tabs instead of accordion | VT uses tabs; tabs look modern | For a card-per-IOC layout, tabs would require tab state per card (complex JS) and break the at-a-glance comparison across IOCs; accordion lets all IOCs remain scannable simultaneously | Keep accordion; improve category sections within the accordion |
| Inline verdict editing / analyst override | Analyst wants to mark "VT says clean but I disagree" | Annotations were removed in v7.0 for good reason — couples triage tool to case management; introduces mutable state; conflicts with cache invalidation model | Direct analysts to their TIP/SIEM for case notes; detail page already exists for deep investigation |
| Real-time confidence scoring across providers | Weight providers by reputation (VT = high trust, unknown = low trust) | Requires maintaining a trust model that goes stale as providers change quality; creates false precision; different providers answer different questions (AbuseIPDB answers "is this reported" not "is this malicious") | Show provider category (reputation vs passive intel) as context so analyst applies their own mental weights |
| Progressive disclosure with infinite scroll | Modern UX pattern; avoids long pages | IOC triage is a compare-all-IOCs task, not a read-one-article task; infinite scroll breaks the analyst's mental model of "I have N IOCs to triage" | Show all IOC cards, keep cards compact, use filter bar to reduce visible set |

---

## Feature Dependencies

```
Category-Grouped Provider Sections
    requires──> CONTEXT_PROVIDERS set (already exists in enrichment.ts)
    requires──> verdict count tracking per category (iocVerdicts already tracks this)
    requires──> template redesign of .enrichment-details container
    enables──> "No Data" section collapsed by default (trivially add third group)
    enables──> Provider category icons/labels (apply per group, not per row)

Inline Context Summary (always visible)
    requires──> context provider results arrive before card renders full summary
    requires──> IOC card template change (new .ioc-context-inline slot)
    depends on──> enrichment.ts routing context vs verdict results differently
    conflicts with──> showing nothing until all providers complete (current behavior)

Verdict Breakdown Micro-Bar
    requires──> per-verdict count tracking (iocVerdicts already has this data)
    requires──> CSS bar component
    enhances──> Worst-verdict summary as report headline
    replaces──> current [flagged/responded] consensus badge (same data, better display)

Worst-Verdict as Report Headline
    requires──> CSS hierarchy change in .ioc-card-header
    is independent of──> grouped sections (works immediately as CSS-only change)

Staleness Indicator on Summary Row
    requires──> cached_at already in EnrichmentResultItem (already exists)
    requires──> updateSummaryRow() to surface cached_at when all results are from cache
    is independent of──> category grouping

No-Data Section Collapsed by Default
    requires──> Category-Grouped Provider Sections (no_data is a group)
    is a low-cost win once grouping exists
```

### Dependency Notes

- **Grouping is the backbone change.** Most differentiators become simple once the three-section
  structure (Reputation / Infrastructure Context / No Data) exists. Category icons, collapsed
  no-data section, and section-level counts all follow from grouping.

- **Inline context summary is independent of grouping** but higher-complexity. It requires
  enrichment.ts to write context fields into a new DOM slot in the card header (above the accordion)
  rather than only into the expanded details container.

- **Worst-verdict as headline is purely CSS.** No JS changes required — make the existing
  `.verdict-label` in `.ioc-card-header` significantly larger (24-28px vs current 12-14px).
  Highest impact-to-cost ratio of any change.

- **Verdict breakdown bar is purely additive JS.** The `iocVerdicts` data structure already
  accumulates every verdict entry. Computing counts by verdict type and rendering a bar is a
  `updateSummaryRow()` change + CSS addition.

---

## MVP Definition (v1.1)

### Launch With (v1.1 Core)

Minimum changes that address the "14 separate results stapled together" problem.

- [ ] Worst-verdict as report headline — make verdict badge the dominant element in card header
  (CSS sizing change, zero JS changes, highest ROI)
- [ ] Category-grouped provider sections — Reputation section (verdict-producing providers) /
  Infrastructure Context section (CONTEXT_PROVIDERS) / No Data section (collapsed by default)
- [ ] Verdict breakdown micro-bar — visual count of malicious/suspicious/clean/no-data providers
  (replaces `[2/5]` consensus text badge with visual representation)
- [ ] No-data section collapsed by default — removes visual noise from flat provider list
- [ ] Provider category labels — distinct label/icon for "Reputation" vs "Infrastructure" sections

### Add After Validation (v1.1.x)

Features to add once core restructure is working and tested.

- [ ] Inline context summary — once grouping is stable, surface 2-3 key context fields directly
  in card header (GeoIP country + ASN org for IPs; creation age for domains)
- [ ] Staleness indicator in summary row — surface `cached_at` when data is not fresh
- [ ] Scan date on summary row — show most recent scan date from verdict providers

### Future Consideration (v1.2+)

- [ ] Per-category expand/collapse toggle — collapse "Infrastructure" section by default for
  clean IOCs where context adds noise
- [ ] IOC card sort by IOC type (group all IPs together, then domains, etc.) as an alternative
  to current severity sort — useful for bulk input with mixed IOC types

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Worst-verdict as report headline (CSS only) | HIGH — first thing analyst reads | LOW — CSS sizing | P1 |
| Category-grouped provider sections | HIGH — eliminates "14 results" feel | MEDIUM — JS + template | P1 |
| No-data section collapsed by default | HIGH — reduces noise immediately | LOW — CSS default state | P1 |
| Verdict breakdown micro-bar | MEDIUM — richer than text badge | MEDIUM — JS count + CSS bar | P1 |
| Provider category labels/icons | MEDIUM — reinforces information structure | LOW — CSS tokens | P2 |
| Inline context summary (always visible) | MEDIUM — eliminates mandatory expand for context | HIGH — new DOM slot, enrichment.ts change | P2 |
| Staleness indicator on summary row | LOW-MEDIUM — data freshness matters for verdict trust | LOW — cached_at already available | P2 |
| Scan date on summary row | LOW — detail-level info | LOW — scan_date already available | P3 |

**Priority key:**
- P1: Must have for v1.1 — directly addresses the "stapled together" problem
- P2: Should have — improves information coherence and context visibility
- P3: Nice to have — polish

---

## Competitor Feature Analysis

How the best platforms handle the specific problems SentinelX currently exhibits.

| Problem | VirusTotal Approach | Hybrid Analysis Approach | Our Approach (v1.1) |
|---------|---------------------|--------------------------|---------------------|
| 14 sources feel separate | Tabs separate verdict / metadata / relations / community — verdict is the primary tab | Group by signal type (malicious / suspicious / informative), not by source | Three-section accordion: Reputation / Infrastructure Context / No Data |
| Context vs verdict mixed | Domain/IP reports have zero vendor verdicts — pure context only; file reports have zero context in detection tab | Indicators section separates malicious / suspicious / informative rows | CONTEXT_PROVIDERS rendered in their own section, visually distinct from verdict section |
| Verdict clarity | Large X/Y ratio in header is the dominant visual element | Threat score + AV detection rate in header before any source details | Worst-verdict badge promoted to dominant headline element in card |
| No-data providers as noise | Not shown — VirusTotal only lists engines that returned a result | Informative indicators section separates low-signal results | No-data section collapsed by default with count shown ("5 had no record") |
| Context fields buried | Details tab separate from detection; always shown by default | Informative indicators always visible in summary | Inline context summary (2-3 fields) always visible in card header |

---

## Sources

- [VirusTotal Reports Documentation](https://docs.virustotal.com/docs/results-reports) — Official
  tab structure, field names, domain/IP vs file/URL report differences (HIGH confidence)
- [Shodan Host Page](https://www.shodan.io/host/203.185.191.41) — Live inspection of Shodan host
  report information architecture (HIGH confidence — direct observation)
- [IntelOwl Usage Documentation](https://intelowlproject.github.io/docs/IntelOwl/usage/) — DataModel
  synthesis approach, Visualizer aggregation pattern (HIGH confidence — official docs)
- [Hybrid Analysis Sample Report](https://hybrid-analysis.com/sample/b558f0b1444be5df69027315f7aad563c54a3f791cebbb96a56fce7e5176f8f5/) —
  Live inspection of Malicious/Suspicious/Informative indicator grouping (HIGH confidence)
- [ANY.RUN Malware Analysis Report blog](https://any.run/cybersecurity-blog/malware-analysis-report/) —
  ANY.RUN report section structure and hierarchy (MEDIUM confidence — marketing blog)
- [URLScan.io About](https://urlscan.io/about/) — "digestible chunks, analyst-first approach"
  design philosophy (MEDIUM confidence — official but brief)
- [SentinelX enrichment.ts](../app/static/src/ts/modules/enrichment.ts) — Current implementation
  of summary row, consensus badge, context row, detail row, sort logic (HIGH confidence — source)
- [SentinelX _ioc_card.html / _enrichment_slot.html templates](../app/templates/partials/) —
  Current DOM structure (HIGH confidence — source)

---

*Feature research for: SentinelX v1.1 Results Page Redesign*
*Researched: 2026-03-16*
