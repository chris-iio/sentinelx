<p align="center">
  <img src="app/static/images/screenshot.png" alt="SentinelX" width="600">
</p>

<p align="center">
  Quick paste tool for IOC search results
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/flask-3.1-green" alt="Flask 3.1">
  <img src="https://img.shields.io/badge/tests-224-brightgreen" alt="Tests 224">
  <img src="https://img.shields.io/badge/coverage-97%25-brightgreen" alt="Coverage 97%">
</p>

## How It Works

1. **Extract** — Pulls IOCs out of messy, unstructured text (dual-library: iocextract + iocsearcher)
2. **Normalize** — Handles defanged indicators (`hxxp://`, `[.]`, `{.}`, 20+ obfuscation patterns)
3. **Classify** — Types each IOC: IPv4, IPv6, domain, URL, MD5, SHA1, SHA256, CVE
4. **Enrich** (optional) — Hits VirusTotal, MalwareBazaar, and ThreatFox in parallel
