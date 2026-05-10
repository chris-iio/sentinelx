# S02: Registry, settings, and email provider coverage

**Goal:** Wire the S01 EmailRep adapter into SentinelX's provider registry, settings metadata/save flow, SSRF allowlist, and Online-mode provider-count reporting so configured EmailRep keys create exactly one email provider and missing EmailRep keys leave email coverage at zero.
**Demo:** After this, configuring an EmailRep key makes Online mode report provider coverage for email IOCs; without a key, email coverage remains zero.

## Must-Haves

- Must-Haves:
- EmailRep is present in the single provider registration path (`app/enrichment/setup.py`) and reads its key from `ConfigStore.get_provider_key("emailrep")`, not from environment variables or a new settings path.
- `app/config.py` allows `emailrep.io`, and registry/setup tests prove the allowlist entry is available to the adapter contract established in S01.
- `PROVIDER_INFO` exposes EmailRep on the settings page as a key-required, email-only provider with HTTPS signup metadata; saving an EmailRep key uses the existing generic provider-key storage and rebuilds `current_app.registry`.
- With no EmailRep key, `ProviderRegistry.providers_for_type(IOCType.EMAIL)` and Online-mode `provider_counts["email"]` are zero, even if some non-email provider is configured so Online mode can render.
- With an EmailRep key, `ProviderRegistry.providers_for_type(IOCType.EMAIL)` returns exactly EmailRep and Online-mode provider coverage/progress reports one email provider without adding EmailRep to domains, IPs, URLs, hashes, or CVEs.
- No task performs a live EmailRep HTTP request; all route/background behavior is mocked or asserted at registry/HTML contract level.
- Threat Surface — Abuse: a malicious or mistaken `provider_id` submitted to `/settings` must not store arbitrary config keys or mutate unsupported providers; tests should keep the existing valid-id gate intact.
- Threat Surface — Data exposure: EmailRep API keys are secrets and email IOCs are personal data; tests and UI assertions must not echo raw keys, and provider-count JSON must expose only counts, not keys or full email values beyond the existing result card.
- Threat Surface — Input trust: analyst-supplied email IOCs reach Online-mode routing and provider selection; this slice proves they affect only provider dispatch/counting, not SSRF host selection or unsupported providers.
- Requirement Impact — Requirements touched: R078 is advanced by enabling configured Online email provider coverage; R016 remains compatible because email extraction/display must still work; R008/R009 are continuity constraints for Online progress wiring and security posture.
- Requirement Impact — Re-verify: registry setup tests, settings page/key-save tests, and `/analyze` Online route tests for configured and unconfigured EmailRep states.
- Requirement Impact — Decisions revisited: none. Preserve the existing generic `ConfigStore` provider-key model, central `build_registry()` composition point, `ALLOWED_API_HOSTS` SSRF allowlist, and OTX email exclusion.

## Proof Level

- This slice proves: This slice proves route-level integration with deterministic mocked background execution. Real runtime required: no live third-party runtime; Flask route tests and existing Playwright settings checks are sufficient. Human/UAT required: no. It does not prove compact result rendering or browser-level Online email enrichment; those remain in S03/S04.

## Integration Closure

Upstream surfaces consumed: S01 `app/enrichment/adapters/emailrep.py` and its flattened result contract, existing `ConfigStore`, `ProviderRegistry`, `/settings`, and `/analyze` routes. New wiring introduced in this slice: EmailRep key metadata/storage/registry composition and Online provider-count coverage for `IOCType.EMAIL`. Remaining milestone work: S03 must render EmailRep result context safely, and S04 must prove a mocked browser Online email enrichment flow end-to-end.

## Verification

- Runtime signals: the existing settings status badge shows whether EmailRep is configured; the results page exposes `data-provider-counts` and progress text derived from registry provider coverage. Inspection surfaces: `tests/test_emailrep_registry_settings.py`, `tests/test_emailrep_online_coverage.py`, `/settings`, and the results page `data-provider-counts` attribute localize registry/settings/counting failures. Failure visibility: missing EmailRep keys remain visible as zero email coverage rather than attempted network dispatch. Redaction constraints: never log or assert raw API key values in rendered output; raw email PII should appear only through the existing IOC result rendering paths.

## Tasks

- [x] **T01: Harden EmailRep registry and settings metadata contracts** `est:45m`
  Expected executor skills_used frontmatter: `tdd`, `verify-before-complete`.
  - Files: `app/enrichment/setup.py`, `app/config.py`, `tests/test_emailrep_registry_settings.py`, `tests/test_registry_setup.py`, `tests/test_adapter_contract.py`
  - Verify: python3 -m pytest tests/test_emailrep_registry_settings.py tests/test_registry_setup.py tests/test_adapter_contract.py -q

- [x] **T02: Prove settings save and Online email provider-count reporting** `est:1h`
  Expected executor skills_used frontmatter: `tdd`, `verify-before-complete`.
  - Files: `app/routes/settings.py`, `app/routes/analysis.py`, `app/enrichment/setup.py`, `tests/test_emailrep_online_coverage.py`, `tests/e2e/test_settings.py`
  - Verify: python3 -m pytest tests/test_emailrep_online_coverage.py tests/e2e/test_settings.py tests/test_routes.py -q

## Files Likely Touched

- app/enrichment/setup.py
- app/config.py
- tests/test_emailrep_registry_settings.py
- tests/test_registry_setup.py
- tests/test_adapter_contract.py
- app/routes/settings.py
- app/routes/analysis.py
- tests/test_emailrep_online_coverage.py
- tests/e2e/test_settings.py
