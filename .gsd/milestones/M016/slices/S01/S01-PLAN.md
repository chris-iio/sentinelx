# S01: EmailRep launch-readiness bundle

**Goal:** Add the backend EmailRep adapter and keep the already-implemented registry/settings/E2E/docs launch-readiness wiring in the same bundled change.
**Demo:** After this, EmailRep is a tested, key-gated email provider with settings/registry coverage and deterministic mocked Online-mode proof.

## Must-Haves

- EmailRepAdapter subclasses BaseHTTPAdapter and dispatches through safe_request.
- Adapter supports only IOCType.EMAIL and returns unsupported-type errors for non-email IOCs.
- Adapter is key-gated and sends documented Key plus User-Agent headers.
- Unit tests cover malicious, suspicious, clean, and no_data verdict mapping.
- raw_stats exposes flattened compact fields such as reputation, suspicious, references, risk_flags, domain_reputation, and profiles.
- Shared adapter contract tests include EmailRep without registering it in app/enrichment/setup.py yet.

## Proof Level

- This slice proves: unit + adapter-contract

## Integration Closure

Scope reconciliation on 2026-05-08: implementation intentionally went beyond the original adapter-only boundary. Keep the bundled registry/settings/E2E/docs work rather than reverting it; S02-S04 in the milestone roadmap are now absorbed/reserved follow-ups unless fresh gaps are found.

## Verification

- Adapter failures should remain visible through existing safe_request/EnrichmentError behavior. Dedicated tests cover auth/status/malformed-response surfaces enough that future agents can localize failures to adapter mapping vs shared HTTP plumbing.

## Tasks

- [x] **T01: Pin the EmailRep adapter contract in tests** `est:45m`
  Why: Lock the EmailRep adapter contract before implementation so verdict thresholds and flattened raw_stats do not drift during coding.
  - Files: `tests/test_emailrep.py`, `tests/helpers.py`, `app/pipeline/models.py`
  - Verify: python3 -m pytest tests/test_emailrep.py -q (expected red until T02 creates the adapter)

- [x] **T02: Implement EmailRepAdapter with conservative verdict mapping** `est:1h`
  Why: Implement the minimal backend provider seam that S02 and S03 can consume without prematurely wiring it into Online mode.
  - Files: `app/enrichment/adapters/emailrep.py`, `tests/test_emailrep.py`
  - Verify: python3 -m pytest tests/test_emailrep.py -q

- [x] **T03: Add EmailRep to shared adapter contract coverage** `est:45m`
  Why: Prove the new adapter obeys the same shared adapter invariants as existing HTTP adapters before downstream slices register it.
  - Files: `tests/test_adapter_contract.py`, `tests/helpers.py`, `app/enrichment/adapters/emailrep.py`
  - Verify: python3 -m pytest tests/test_emailrep.py tests/test_adapter_contract.py -q

## Files Likely Touched

- tests/test_emailrep.py
- tests/helpers.py
- app/pipeline/models.py
- app/enrichment/adapters/emailrep.py
- tests/test_adapter_contract.py
