# SentinelX Security and Optimization Audit

Updated: 2026-07-31

## Scope

This pass reviewed the current SentinelX worktree across the Flask Analyze,
Audit, and CTF workspaces; enrichment; outbound HTTP safety; local SQLite
state; diagnostics; bounded local tool execution; isolated PoC verification;
TypeScript rendering; and verification tooling.

The intended product shape is one local-first Flask shell with three explicit
workspaces. Provider evidence, workflow state, analyst decisions, and verified
proof must remain separate.

## Fixed Security Issues

| Area | Change | Evidence |
| --- | --- | --- |
| Local admin surfaces | Settings, history, diagnostics export, HTML status, and API status now require a loopback peer address. | `app/__init__.py`, `tests/test_routes.py::test_sensitive_routes_reject_non_loopback_remote_addr` |
| Provider HTTP concurrency | HTTP adapters now use thread-local `requests.Session` instances while preserving auth headers. | `app/enrichment/adapters/base.py`, `tests/test_base_adapter.py::test_concurrent_lookup_uses_thread_local_sessions` |
| Provider endpoint validation | Outbound provider URLs must use HTTPS, must not include userinfo, and must pass the SSRF host allowlist. | `app/enrichment/http_safety.py`, `tests/test_http_safety.py` |
| Settings persistence | Provider-key/config writes now use path-scoped locking, a `0600` temp file, `fsync`, and atomic `os.replace`. Failed writes preserve the previous disk/cache state. | `app/enrichment/config_store.py`, `tests/test_config_store.py` |
| Dev-server probing | Local health probing no longer uses a generic URL opener; it uses direct `http.client.HTTPConnection` to normalized local hosts. | `tools/dev_server.py`, `tests/test_dev_server.py`, `tests/test_dev_server_process.py` |
| Browser analysis mode | Browser `/analyze` now shares the API mode allowlist and rejects invalid modes before extraction. | `app/routes/analysis.py`, `app/routes/api.py`, `tests/test_routes.py`, `tests/test_api.py` |
| Status polling cursor | Negative polling cursors are clamped instead of triggering Python tail-slice behavior. | `app/routes/enrichment_jobs.py`, `app/enrichment/orchestrator.py`, `tests/test_routes.py`, `tests/test_api.py`, `tests/test_orchestrator.py` |
| History retention | History rows are bounded by `HISTORY_MAX_ROWS` (default `500`) and oldest rows are pruned after each save. | `app/enrichment/history_store.py`, `app/config.py`, `tests/test_history_store.py`, `tests/test_config.py` |

## Simplification and Optimization Work

| Area | Change | Evidence |
| --- | --- | --- |
| Config validation | Effective app config is validated after test/runtime overrides. | `app/__init__.py`, `app/config.py`, `tests/test_config.py` |
| Provider settings view | Settings now includes a secret-free local provider readiness table without network calls. | `app/routes/settings.py`, `app/templates/settings.html`, `tests/test_settings.py` |
| Orchestrator retries | Repeated semaphore acquire/release logic is centralized in `_attempt_with_semaphore()`. | `app/enrichment/orchestrator.py`, orchestrator tests |
| Dev tooling | Cleanup and process-state paths were simplified while preserving lifecycle behavior. | `tools/dev_server.py`, dev-server tests |
| Python SIM cleanup | Safe SIM simplifications pass the configured simplifier lane. | `.venv/bin/ruff check app tools --select SIM` |

## Current Verification Evidence

| Check | Result |
| --- | --- |
| `make verify` | Passed: `2128` non-E2E pytest tests; `222` Vitest tests; TypeScript; CSS/JS build; `130` E2E tests |
| `python3 tools/security_check.py --path app --json` | Passed: no pattern or Bandit findings |
| `python3 tools/security_check.py --path tools --json` | Passed: no gate-blocking findings; 9 low-severity Bandit observations |
| `pnpm workflow:gpt-routing` | Passed |
| Flask workspace browser checks | Analyze, Audit, and CTF passed desktop and 390 px overflow checks; Audit and CTF checks fail on console or CSP errors |

## Residual Risk

No known critical, high, or medium security findings remain in the checked
application/tooling paths. Two non-blocking areas should stay on the watch list:

- Python dependency auditing depends on `pip-audit` being installed; the local
  scanner reports `pip_audit.ran=false` in this environment.
- The request body cap remains 5 MB to preserve SSH/auth-log paste workflows.
  Online provider fanout and history retention are bounded, but offline
  extraction still intentionally scans accepted input locally.
