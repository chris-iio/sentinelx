# M006: M006

**Vision:** Close the gaps that keep SentinelX useful as a lightweight local tool: persist analysis history so work isn't lost when the tab closes, add WHOIS domain enrichment for the table-stakes investigation signal, polish URL IOC support end-to-end, and bring the input page in line with the quiet precision design language. No new infrastructure, no platform complexity.

## Success Criteria

- Analyst can submit IOCs, close the tab, return to the home page, see the past analysis in a recent list, click it, and see full results reloaded from stored data
- Domain IOC enrichment includes WHOIS data (registrar, creation date, expiry, name servers) alongside DNS records and other provider results
- URL IOCs pasted in free-form text are extracted, enriched by URLhaus/OTX/VT/ThreatFox, displayed with correct filter pill, and accessible on the detail page
- Home page and results page share the same visual language — zinc tokens, Inter Variable typography, verdict-only color accents
- All existing 960+ tests pass plus new tests for history, WHOIS, and URL flows

## Slices

- [x] **S01: Analysis History & Persistence** `risk:high` `depends:[]`
  > After this: Analyst submits IOCs in online mode, sees results, closes the tab, returns to the home page, sees past analysis in the recent list, clicks it, and the full results page reloads from stored data.

- [x] **S02: WHOIS Domain Enrichment** `risk:medium` `depends:[]`
  > After this: Domain IOC enrichment shows WHOIS data (registrar, creation date, expiry, name servers) in a provider detail row alongside DNS Records, VirusTotal, OTX, etc.

- [x] **S03: URL IOC End-to-End Polish** `risk:low` `depends:[]`
  > After this: Paste text containing https://evil.example.com/payload.exe — URL extracted, enriched by URLhaus/OTX/VT/ThreatFox, displayed with correct type badge and filter pill, detail page accessible via link.

- [x] **S04: Input Page Redesign** `risk:low` `depends:[S01]`
  > After this: Home page matches results page design language — zinc tokens, Inter Variable typography, quiet precision aesthetic. Recent analyses list styled consistently.

## Boundary Map

### S01 → S04

Produces:
- `app/enrichment/history_store.py` → HistoryStore class with save_analysis(), list_analyses(), load_analysis()
- `/history/<id>` route → serves stored analysis results page
- `index.html` updated with recent analyses list (server-rendered)

Consumes:
- nothing (first slice)

### S02 (independent)

Produces:
- `app/enrichment/adapters/whois_lookup.py` → WhoisAdapter class following Provider protocol
- WHOIS data rendered in domain enrichment detail rows (registrar, creation date, expiry, name servers)

Consumes:
- nothing (independent of S01)

### S03 (independent)

Produces:
- E2E test coverage for URL IOC extraction → enrichment → display → detail page
- Verified URL handling in detail page route (Flask path converter)
- Any CSS/template fixes needed for URL display

Consumes:
- nothing (independent — URL backend support already exists)

### S04 ← S01

Produces:
- Redesigned `index.html` and input CSS matching quiet precision design language
- Recent analyses list styled consistently with results page

Consumes from S01:
- Recent analyses list HTML structure and data shape
- History route for click-to-reload
