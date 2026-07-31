# SentinelX Launch Checklist

SentinelX should launch as a **local-first cybersecurity workbench** with one Flask shell and three explicit workspaces: IOC analysis, security audits, and CTF work. Do not position it as a hosted platform, a multi-user case-management system, or a fully autonomous vulnerability researcher.

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

The repo also expects downloaded local build binaries at `tools/tailwindcss` and `tools/esbuild` for asset rebuilds. They are ignored and should be recreated with checksum-verified installers:

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

## Release cleanup command

Before packaging, remove generated Python caches and confirm no release-excluded paths are staged:

```bash
find app tests tools -type d -name __pycache__ -prune -exec rm -rf {} +
git status --short
```

## Required pre-launch proof

Before tagging or announcing a release, capture fresh output for:

```bash
make verify
python3 tools/optimization_audit.py --mode baseline --output .gsd/milestones/M013/M013-AUDIT.md
```

Verification lane policy:

- Run `make verify-fast` for routine backend/frontend logic, documentation, build/test plumbing changes, and local static security scanning.
- Run `make verify-deep` whenever browser flows, result rendering, polling/status behavior, live enrichment orchestration, or analyst-visible DOM/state may be affected.
- Run full `make verify` before a release tag or handoff.

Current verified baseline from this cleanup pass:

- `make verify`: security scans for `app` and `tools` found no gate-blocking findings, 2128 non-E2E pytest tests passed, 222 Vitest tests passed, TypeScript passed, the asset build passed, and 130 E2E tests passed.

## Launch positioning

Use this promise:

> SentinelX is a local-first cybersecurity workbench for IOC analysis, evidence-backed security audits, and CTF work in one Flask app.

Avoid these claims:

- “MISP/OpenCTI replacement”
- “Enterprise multi-user TIP”
- “Hosted SOC platform”
- “Case-management replacement for TheHive”

## Minimum launch materials

- README quickstart that matches the clean install smoke path.
- One screenshot or short GIF showing paste → extracted IOCs → enrichment verdicts.
- Provider key notes: which providers require keys, where to get keys, and rate-limit expectations.
- Security note: local-first, SSRF allowlist, request timeout, response size cap, no provider calls in Offline mode, and audit tools restricted to configured workspace roots.
- Known limits: local single-user app, local SQLite state, in-memory rate limiting, Online mode depends on third-party APIs, and generated audit findings remain hypotheses until reproducible verification succeeds.

## Post-launch roadmap candidates

1. Provider health/key validation from `/settings`.
2. MISP export/import or TheHive observable handoff.
3. Dockerfile or single-command installer.
4. STIX/TAXII export after the basic local workflow is validated.
5. CI that runs `make verify-fast` and a scheduled E2E lane.
