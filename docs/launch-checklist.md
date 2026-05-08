# SentinelX Launch Checklist

SentinelX should launch as a **local IOC triage workbench**: paste messy incident text, extract indicators, enrich with configured providers, review verdicts, and export/share findings. Do not position it as a full threat-intelligence platform or case-management replacement.

## Release artifact boundary

Ship source and documented bootstrap steps. Do **not** ship local/runtime artifacts:

- `.env` or any real provider keys
- `.sentinelx/` user config/history/cache directories
- `.firecrawl/` research scratch output
- `.gsd/runtime/**`, `.gsd/activity/**`, `.bg-shell/**`, pytest/cache/build output
- `node_modules/`
- `everything-claude-code/` local reference checkout
- Python `__pycache__/` / `*.pyc`

Tracked generated assets are intentional:

- `app/static/dist/main.js`
- `app/static/dist/style.css`

The repo also expects downloaded local build binaries at `tools/tailwindcss` and `tools/esbuild` for asset rebuilds. They are ignored and should be recreated with:

```bash
make tailwind-install
make esbuild-install
```

## Clean install smoke path

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
npm install
make tailwind-install
make esbuild-install
make verify
make dev-server-start
```

Open the local server, visit `/settings`, add any provider API keys you want to use, then test both offline and online flows.

## Required pre-launch proof

Before tagging or announcing a release, capture fresh output for:

```bash
make verify
python3 tools/security_check.py --json
python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md
```

Current verified baseline from this cleanup pass:

- `make verify`: 1051 non-E2E pytest passed, 87 Vitest passed, TypeScript passed, asset build passed, 125 E2E passed.
- `tools/security_check.py --json`: 0 critical/high/medium/low findings.

## Launch positioning

Use this promise:

> SentinelX is a local-first IOC triage workbench for analysts who need fast paste-to-enrichment workflows without deploying a full TIP.

Avoid these claims:

- “MISP/OpenCTI replacement”
- “Enterprise multi-user TIP”
- “Hosted SOC platform”
- “Case-management replacement for TheHive”

## Minimum launch materials

- README quickstart that matches the clean install smoke path.
- One screenshot or short GIF showing paste → extracted IOCs → enrichment verdicts.
- Provider key notes: which providers require keys, where to get keys, and rate-limit expectations.
- Security note: local-first, SSRF allowlist, request timeout, response size cap, no real provider calls in offline mode.
- Known limits: local single-user app, local SQLite history/cache, in-memory rate limiting, online mode depends on third-party API availability and keys.

## Post-launch roadmap candidates

1. Provider health/key validation from `/settings`.
2. MISP export/import or TheHive observable handoff.
3. Dockerfile or single-command installer.
4. STIX/TAXII export after the basic local workflow is validated.
5. CI that runs `make verify-fast`, security scan, and a scheduled E2E lane.
