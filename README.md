<p align="center">
  <img src="app/static/images/screenshot.png" alt="SentinelX" width="600">
</p>

<p align="center">
  <strong>A local IOC triage tool built for SOC analysts.</strong><br>
  Paste in whatever you've got — alert snippets, email headers, threat reports, raw indicators — and let it pull out, classify, and optionally enrich IOCs against real threat intel sources.
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

No magic threat scores. You see the provider, the timestamp, and the raw verdict — you make the call.

## Quick Start

```bash
# Clone and set up
git clone git@github.com:chris-iio/sentinelx.git
cd sentinelx
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run (localhost only, port 5000)
python run.py
```

Open `http://127.0.0.1:5000` in your browser.

### Online Mode (Optional)

Want live enrichment? Just add your VirusTotal API key:

```bash
echo "VT_API_KEY=your_key_here" > .env
```

MalwareBazaar and ThreatFox are public — no key needed.

## Modes

| Mode | What Happens | Network Calls |
|------|-------------|---------------|
| **Offline** | Extract + classify only | Zero |
| **Online** | Extract + classify + enrich via VT, MalwareBazaar, ThreatFox | Parallel, with strict timeouts |

## Architecture

```
app/
├── __init__.py          # Flask factory + security scaffold
├── config.py            # Configuration from env vars
├── routes.py            # Web routes (/, /analyze, /settings)
├── pipeline/            # IOC processing pipeline
│   ├── extractor.py     #   Dual-library IOC extraction
│   ├── normalizer.py    #   Defang/normalization
│   ├── classifier.py    #   IOC type classification
│   └── models.py        #   Pipeline data models
├── enrichment/          # Threat intelligence layer
│   ├── orchestrator.py  #   Parallel enrichment coordination
│   ├── models.py        #   Enrichment data models
│   ├── http_safety.py   #   Safe HTTP with SSRF prevention
│   └── adapters/        #   Provider implementations
│       ├── virustotal.py
│       ├── malwarebazaar.py
│       └── threatfox.py
├── templates/           # Jinja2 templates
└── static/              # CSS, JS, fonts, images
```

## Security

Security isn't bolted on — it's the foundation. All defenses land before any feature code:

- **Localhost only** — binds to `127.0.0.1`, never `0.0.0.0`
- **CSP** — `default-src 'self'; script-src 'self'`
- **CSRF protection** — Flask-WTF on all POST endpoints
- **Rate limiting** — per-route via Flask-Limiter
- **Input validation** — all user input and API responses treated as untrusted
- **No redirect following** — outbound requests never follow redirects
- **No URL fetching** — only calls intelligence APIs, never crawls target URLs
- **No eval/exec/subprocess** — deterministic code paths only
- **Secrets in env vars only** — API keys never logged or rendered
- **Jinja2 autoescaping** — `textContent` only, no `innerHTML` with untrusted data
- **Strict timeouts** — max response size on all outbound HTTP

## Development

### Build CSS

Tailwind CSS uses the standalone CLI — no Node.js needed:

```bash
# One-time: download Tailwind CLI
make tailwind-install

# Build CSS (one-shot)
make css

# Watch mode for development
make css-watch
```

### Run Tests

```bash
# All tests (unit + integration)
pytest

# With coverage
pytest --cov=app --cov-report=term-missing

# Skip E2E tests
pytest -m "not e2e"

# E2E tests (requires Playwright)
pytest -m e2e
```

### Lint

```bash
ruff check .
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10, Flask 3.1 |
| IOC Extraction | iocextract, iocsearcher |
| HTTP | requests (with SSRF guards) |
| Frontend | Tailwind CSS, vanilla JS |
| Fonts | Inter Variable, JetBrains Mono Variable (self-hosted) |
| Icons | Heroicons v2 (inline SVG) |
| Tests | pytest, Playwright |

## License

Personal/internal use. No license specified yet.
