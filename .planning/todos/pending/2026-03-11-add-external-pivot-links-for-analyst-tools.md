---
created: 2026-03-11T20:16:38.586Z
title: Add external pivot links for analyst tools
area: ui
files:
  - app/static/src/ts/modules/enrichment.ts
---

## Problem

Analysts often want to cross-reference IOCs in external tools beyond the providers integrated into SentinelX. Currently there's no way to quickly jump to an external lookup — the analyst has to manually copy-paste the IOC value into each tool's search bar.

External tools identified:
- **Talos Intelligence** — Cisco's IP/domain reputation center (`talosintelligence.com/reputation_center/lookup?search={ioc}`)
- **CyberChef** — GCHQ's data transformation tool for encoding/decoding/hashing (`cyberchef.io`)
- **Censys** — Internet-wide scan data for IPs/domains
- **Shodan Web** — Full Shodan web interface (beyond InternetDB API data)

These are not provider integrations (no API calls). They are clickable pivot links that open in new tabs pre-populated with the IOC value, giving analysts one-click access to external context.

## Solution

Add a "Pivot Links" section to IOC result cards (or detail rows) that renders clickable external links for each IOC. Links should:
- Open in new tab (`target="_blank" rel="noopener"`)
- Be IOC-type-aware (e.g., Talos for IPs/domains, CyberChef for hashes)
- Use a configurable registry pattern so new tools can be added easily
