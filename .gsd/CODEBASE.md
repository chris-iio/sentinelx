# Codebase Map

Generated: 2026-05-12T06:03:14Z | Files: 191 | Described: 0/191
<!-- gsd:codebase-meta {"generatedAt":"2026-05-12T06:03:14Z","fingerprint":"d1b19e611142c10a7abe8d3c5222e58f2e4ac6dd","fileCount":191,"truncated":false} -->

### (root)/
- `.codex`
- `.env.example`
- `.gitignore`
- `Makefile`
- `package-lock.json`
- `package.json`
- `pyproject.toml`
- `README.md`
- `requirements.txt`
- `run.py`
- `tailwind.config.js`
- `tsconfig.json`
- `tsconfig.test.json`
- `vitest.config.ts`

### .artifacts/browser/2026-05-09T15-18-28-379Z-session/
- `.artifacts/browser/2026-05-09T15-18-28-379Z-session/m016-t02-browser-timeline.json`

### .reports/
- `.reports/dead-code-analysis.md`

### app/
- `app/__init__.py`
- `app/config.py`
- `app/health_contract.py`

### app/cache/
- `app/cache/__init__.py`
- `app/cache/store.py`

### app/diagnostics/
- `app/diagnostics/__init__.py`
- `app/diagnostics/contract.py`
- `app/diagnostics/redaction.py`

### app/enrichment/
- `app/enrichment/__init__.py`
- `app/enrichment/config_store.py`
- `app/enrichment/history_store.py`
- `app/enrichment/http_safety.py`
- `app/enrichment/models.py`
- `app/enrichment/orchestrator.py`
- `app/enrichment/provider.py`
- `app/enrichment/registry.py`
- `app/enrichment/setup.py`

### app/enrichment/adapters/
- `app/enrichment/adapters/__init__.py`
- `app/enrichment/adapters/abuseipdb.py`
- `app/enrichment/adapters/asn_cymru.py`
- `app/enrichment/adapters/base.py`
- `app/enrichment/adapters/crtsh.py`
- `app/enrichment/adapters/dns_lookup.py`
- `app/enrichment/adapters/emailrep.py`
- `app/enrichment/adapters/greynoise.py`
- `app/enrichment/adapters/hashlookup.py`
- `app/enrichment/adapters/ip_api.py`
- `app/enrichment/adapters/malwarebazaar.py`
- `app/enrichment/adapters/otx.py`
- `app/enrichment/adapters/shodan.py`
- `app/enrichment/adapters/threatfox.py`
- `app/enrichment/adapters/threatminer.py`
- `app/enrichment/adapters/urlhaus.py`
- `app/enrichment/adapters/virustotal.py`
- `app/enrichment/adapters/whois_lookup.py`

### app/pipeline/
- `app/pipeline/__init__.py`
- `app/pipeline/classifier.py`
- `app/pipeline/extractor.py`
- `app/pipeline/models.py`
- `app/pipeline/normalizer.py`

### app/routes/
- `app/routes/__init__.py`
- `app/routes/_helpers.py`
- `app/routes/analysis.py`
- `app/routes/api.py`
- `app/routes/detail.py`
- `app/routes/enrichment.py`
- `app/routes/history.py`
- `app/routes/settings.py`

### app/ssh/
- `app/ssh/__init__.py`
- `app/ssh/models.py`
- `app/ssh/parser.py`

### app/static/src/
- `app/static/src/input.css`

### app/static/src/ts/
- `app/static/src/ts/main.ts`

### app/static/src/ts/modules/
- *(21 files: 21 .ts)*

### app/static/src/ts/types/
- `app/static/src/ts/types/api.ts`
- `app/static/src/ts/types/ioc.ts`

### app/static/src/ts/utils/
- `app/static/src/ts/utils/dom.ts`

### app/templates/
- `app/templates/base.html`
- `app/templates/history.html`
- `app/templates/index.html`
- `app/templates/ioc_detail.html`
- `app/templates/results.html`
- `app/templates/settings.html`

### app/templates/macros/
- `app/templates/macros/icons.html`

### app/templates/partials/
- `app/templates/partials/_empty_state.html`
- `app/templates/partials/_enrichment_slot.html`
- `app/templates/partials/_filter_bar.html`
- `app/templates/partials/_ioc_card.html`
- `app/templates/partials/_verdict_dashboard.html`

### docs/
- `docs/code-analysis-launch-deck.html`
- `docs/diagnostic-export-contract.md`
- `docs/launch-checklist.md`
- `docs/optimization-audit.md`
- `docs/runtime-state-boundary.md`

### docs/plans/
- `docs/plans/2026-03-02-universal-threat-intel-hub-design.md`
- `docs/plans/2026-03-02-universal-threat-intel-hub.md`
- `docs/plans/2026-03-04-settings-page-redesign.md`

### tests/
- *(58 files: 58 .py)*

### tests/e2e/
- `tests/e2e/__init__.py`
- `tests/e2e/conftest.py`
- `tests/e2e/test_copy_buttons.py`
- `tests/e2e/test_emailrep_online.py`
- `tests/e2e/test_extraction.py`
- `tests/e2e/test_homepage.py`
- `tests/e2e/test_navigation.py`
- `tests/e2e/test_results_page.py`
- `tests/e2e/test_settings.py`
- `tests/e2e/test_ui_controls.py`
- `tests/e2e/test_url_e2e.py`

### tests/e2e/pages/
- `tests/e2e/pages/__init__.py`
- `tests/e2e/pages/index_page.py`
- `tests/e2e/pages/results_page.py`
- `tests/e2e/pages/settings_page.py`

### tools/
- `tools/dev_server.py`
- `tools/optimization_audit.py`
- `tools/runtime_state_boundary.py`
- `tools/runtime_state_repair.py`
- `tools/security_check.py`
