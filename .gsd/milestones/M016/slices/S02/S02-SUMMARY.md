---
id: S02
parent: M016
milestone: M016
provides:
  - Central registry/settings EmailRep wiring for downstream S03/S04 work
  - Deterministic proof that an EmailRep key creates exactly one email provider and no non-email provider coverage
  - Security contract coverage for unknown-provider rejection, secret redaction, and explicit SSRF host allowlist
requires:
  - slice: S01
    provides: EmailRep adapter contract, email-only support, safe request path, conservative verdict mapping, and flattened raw_stats fields consumed by registry/UI proof.
affects:
  - S03
  - S04
key_files:
  - app/enrichment/setup.py
  - app/config.py
  - tests/test_emailrep_registry_settings.py
  - tests/test_emailrep_online_coverage.py
  - .gsd/PROJECT.md
key_decisions:
  - Provider key lookup failures during registry composition are treated as missing keys so key-required providers remain unconfigured instead of aborting startup.
  - EmailRep uses the existing generic ConfigStore provider-key model and central build_registry() composition path; no environment-variable fallback or new settings mechanism was added.
patterns_established:
  - Key-gated provider integration should be tested through metadata, registry composition, provider-count, and route-level settings contracts before UI result rendering is added.
  - Provider-count JSON remains a safe diagnostic surface: expose counts by IOC type, not provider secrets or extra IOC data.
  - For EmailRep route tests, isolate the analysis pipeline to a single IOCType.EMAIL fixture when asserting provider counts so domain extraction from example email domains does not create unrelated provider-count noise.
observability_surfaces:
  - /settings EmailRep configured/unconfigured status badge/metadata
  - Results page `data-provider-counts` attribute
  - Online progress/provider-count text derived from registry coverage
  - Focused tests: `tests/test_emailrep_registry_settings.py` and `tests/test_emailrep_online_coverage.py`
drill_down_paths:
  - .gsd/milestones/M016/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M016/slices/S02/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-05-09T16:42:58.180Z
blocker_discovered: false
---

# S02: Registry, settings, and email provider coverage

**EmailRep is now wired into registry/settings/Online provider-count coverage as an email-only, key-gated provider without live third-party calls.**

## What Happened

S02 closed the product wiring between the S01 EmailRep adapter contract and SentinelX Online-mode provider coverage. The central `build_registry()` path now includes EmailRep through the existing key-required provider composition model and reads `ConfigStore.get_provider_key("emailrep")`; missing, empty, or failed key reads leave EmailRep unconfigured rather than aborting startup or adding a partial provider. `emailrep.io` is covered by the existing SSRF allowlist contract, and tests pin that EmailRep remains scoped to `IOCType.EMAIL` only.

The settings route contract is now covered at the Flask client/HTML level. `PROVIDER_INFO` exposes EmailRep as a key-required, email-only provider with HTTPS signup metadata; `/settings` POST persists through `ConfigStore.set_provider_key("emailrep", ...)`, rejects empty keys and unknown provider IDs, redirects without echoing raw key material, and rebuilds `current_app.registry` through the existing generic save path. No new settings mechanism or environment-variable path was introduced.

Online-mode coverage is proven with deterministic mocked route behavior. With no EmailRep key, `ProviderRegistry.providers_for_type(IOCType.EMAIL)` and results-page `data-provider-counts`/progress coverage report zero email providers, even when another non-email provider is configured so Online mode can render. With an EmailRep key, email coverage reports exactly one provider and does not add EmailRep to domain, IP, URL, hash, or CVE coverage. This slice did not perform any live EmailRep HTTP requests; all behavior is asserted through registry, settings, and route-level contracts.

Gate coverage: Security posture is preserved by keeping the valid-provider-id gate for `/settings`, using generic secret storage without key echoing, and proving unsupported provider IDs cannot mutate arbitrary config. Input trust is constrained to provider selection/counting: email IOCs affect only email provider coverage and do not broaden SSRF host selection beyond the explicit `emailrep.io` allowlist. Operational readiness is covered by the existing settings status badge, results-page `data-provider-counts`, and provider-count/progress text: missing keys fail visibly as zero email coverage, while configured keys show one email provider before S03/S04 add result rendering and browser-level enrichment proof.

## Verification

Fresh slice verification ran via `gsd_exec` run `83294ccf-f23d-41f1-b11c-41c83039927f` before completion:

- `python3 -m pytest tests/test_emailrep_registry_settings.py tests/test_registry_setup.py tests/test_adapter_contract.py -q` → exit 0, `235 passed in 0.34s`.
- `python3 -m pytest tests/test_emailrep_online_coverage.py tests/e2e/test_settings.py tests/test_routes.py -q` → exit 0, `68 passed in 17.40s`.

Task-level evidence also covered focused EmailRep registry/settings tests, route-level coverage tests, and LSP diagnostics for changed test/source files. Observability/diagnostic surfaces verified: `/settings` EmailRep configured/unconfigured status, results-page `data-provider-counts`, and Online progress provider counts for email with and without the key. No live third-party EmailRep request was made.

## Requirements Advanced

- R078 — Advanced by enabling configured Online email provider coverage through key-gated EmailRep registry/settings wiring and provider-count proof.
- R016 — Preserved email IOC extraction/display compatibility while adding optional Online email provider coverage.
- R008 — Preserved Online progress/provider-count wiring via route-level tests with and without EmailRep.
- R009 — Preserved SSRF allowlist, valid-provider-id gating, and secret redaction contracts while adding EmailRep settings support.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

None.

## Deviations

None. T02 found that the existing production settings save path, registry rebuild, and results-page provider-count behavior already satisfied the route contract once tests were added; no production source change was needed for that task. During closeout, the slice had to be reopened/replayed because an earlier auto-mode recovery marked the DB complete while leaving a blocker placeholder summary, missing UAT, and unchecked roadmap projection.

## Known Limitations

This slice proves provider registration, settings persistence, allowlist coverage, and Online provider counts only. It does not prove rendered EmailRep result context (S03) or a browser-level mocked Online email enrichment flow (S04), and it deliberately does not make live EmailRep HTTP requests.

## Follow-ups

S03 should consume the S01 flattened EmailRep `raw_stats` contract and S02 provider-count wiring to render compact, safe reputation/risk context using existing textContent/createElement paths. S04 should then prove the full mocked browser Online flow from email IOC submission through EmailRep verdict/context display without a live key.

## Files Created/Modified

- `app/enrichment/setup.py` — Added fail-closed key lookup handling for key-required provider composition and included EmailRep in the central registration path.
- `app/config.py` — EmailRep host allowlist contract covered for adapter use.
- `tests/test_emailrep_registry_settings.py` — Added registry/settings metadata, allowlist, missing-key, configured-key, and email-only provider boundary tests.
- `tests/test_emailrep_online_coverage.py` — Added Flask route tests for settings save/redaction/rejection and Online email provider-count coverage.
- `.gsd/PROJECT.md` — Refreshed project state to reflect M016/S02 completion and the EmailRep registry/settings/provider-count contract.
