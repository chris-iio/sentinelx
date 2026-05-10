---
id: S01
parent: M016
milestone: M016
provides:
  - A backend EmailRep adapter class for downstream registry/settings work.
  - A stable flattened EmailRep `raw_stats` field contract for downstream row rendering.
  - Mocked fixtures and contract tests for future regression checks.
requires:
  []
affects:
  - S02
  - S03
  - S04
key_files:
  - app/enrichment/adapters/emailrep.py
  - tests/test_emailrep.py
  - tests/test_adapter_contract.py
  - .gsd/PROJECT.md
key_decisions:
  - Use conservative EmailRep verdict mapping: confirmed abuse flags are malicious; low-confidence risk/low-reputation signals are suspicious; high reputation with no risk flags is clean; absent/unknown reputation is no_data.
  - Expose compact flattened EmailRep `raw_stats` instead of preserving nested provider payloads for downstream rendering.
patterns_established:
  - New HTTP providers should enter through `BaseHTTPAdapter` and shared adapter-contract tests before UI/registry work relies on them.
  - Provider-specific tests should pin request shape, auth headers, IOC type guard, representative verdict mapping, and flattened UI-facing stats.
observability_surfaces:
  - HTTP status/auth failures surface via existing `safe_request`/`EnrichmentError` behavior.
  - Unsupported IOC types return an adapter-local error without network dispatch.
  - Focused pytest suites identify whether a failure is EmailRep-specific mapping/request shape (`tests/test_emailrep.py`) or shared adapter protocol (`tests/test_adapter_contract.py`).
drill_down_paths:
  - .gsd/milestones/M016/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M016/slices/S01/tasks/T02-SUMMARY.md
  - .gsd/milestones/M016/slices/S01/tasks/T03-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-05-09T15:25:22.267Z
blocker_discovered: false
---

# S01: EmailRep adapter contract

**S01 establishes a tested EmailRep backend adapter contract with conservative email-only reputation mapping, key-gated request shape, flattened raw_stats, and shared adapter-contract coverage.**

## What Happened

S01 closes the backend adapter seam for EmailRep. The delivered adapter lives at `app/enrichment/adapters/emailrep.py`, subclasses `BaseHTTPAdapter`, supports only `IOCType.EMAIL`, requires an API key, and uses the shared HTTP safety path for request execution and failure shaping. Its request contract URL-encodes the email IOC into `https://emailrep.io/{email}`, sends EmailRep's documented `Key` header plus `User-Agent: SentinelX`, and keeps auth/session behavior inside the existing adapter/session pattern.

The verdict mapping is deliberately conservative. High-confidence abuse indicators such as blacklisting, malicious activity, recent credential leakage, or breach flags map to `malicious`; lower-confidence risky state such as low reputation, suspicious response state, new/suspicious domains, disposable mail, failed deliverability/MX checks, or spoofability maps to `suspicious`; high-reputation responses without risk flags map to `clean`; and absent/unknown reputation maps to `no_data`. Detection counts remain compact and conservative: malicious/suspicious findings use EmailRep `references`, while clean/no_data responses do not inflate detections.

The adapter also establishes the downstream raw-stats contract for S03 rendering. `raw_stats` is flattened into compact fields (`reputation`, `suspicious`, `references`, `risk_flags`, `domain_reputation`, `profiles`, first/last seen, domain existence, deliverability, MX, spoofing, SPF, and DMARC flags) instead of exposing nested provider payloads. This gives UI work a safe, predictable field list to render with existing `textContent`/`createElement` patterns.

Shared adapter-contract coverage now includes EmailRep, proving common invariants alongside the existing providers: provider name, API-key configuration behavior, supported/excluded IOC type guards, HTTP method dispatch through the mocked adapter session, safe host configuration, malformed/status error surfaces, and no network call for unsupported types. EmailRep-specific tests pin the malicious, suspicious, clean, no_data, thin response, unsupported type, HTTP 401, header, key-gating, and URL-encoding contracts.

Operational readiness is adapter-local for this slice. Health signal: `tests/test_emailrep.py` and `tests/test_adapter_contract.py` pass with EmailRep included. Failure signal: auth/status failures surface as existing `EnrichmentError` values through `safe_request`, and unsupported non-email IOCs return an adapter error without calling the network. Recovery procedure: localize EmailRep failures first to `tests/test_emailrep.py` for provider mapping/request-shape changes, then to `tests/test_adapter_contract.py` for shared adapter invariant regressions. Monitoring gaps: live EmailRep API behavior, registry/settings coverage, result-row rendering, and mocked Online-mode browser proof are intentionally left to S02-S04.

Important downstream note: the repository currently contains EmailRep registry/settings references in addition to the adapter contract. This S01 closeout verified the adapter-contract proof and did not treat registry/UI behavior as accepted product proof; S02 should explicitly verify and reconcile provider registration, allowed-host coverage, settings metadata, and configured/unconfigured provider counts before considering that layer complete.

## Verification

Fresh slice-level verification was run after the assembled adapter work: `python3 -m pytest tests/test_emailrep.py tests/test_adapter_contract.py -q` exited 0 with `198 passed in 0.22s` (gsd_exec `1b66a502-6821-4057-815e-f527efc247e2`). This covers the EmailRep-specific malicious/suspicious/clean/no_data mapping, key-gated request headers, URL encoding, unsupported-type guard, HTTP 401 safe_request propagation, and shared adapter contract invariants. Task summaries also record the original red-test pinning in T01, the implementation/test pass in T02, and the shared adapter-contract pass in T03.

## Requirements Advanced

- R078 — Begins the previously deferred email/phishing enrichment depth by proving the EmailRep adapter contract; not yet enough to validate full email enrichment depth because registry, UI, and Online E2E proof remain.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

None.

## Deviations

Task summaries for T02/T03 include browser/offline baseline artifacts that are broader than the inlined S01 adapter contract plan. Slice closure is based on the adapter-contract pytest proof required by the S01 plan. The current repository also contains EmailRep registry/settings references beyond S01's stated adapter-only integration closure; downstream S02 must explicitly verify and reconcile those seams rather than assume they are complete.

## Known Limitations

No live EmailRep smoke test was run. Registry/settings behavior, compact UI rendering, and mocked Online-mode email enrichment are intentionally unproven by S01 and remain in S02-S04. The adapter flattens selected EmailRep fields only; raw nested provider dumping is intentionally avoided.

## Follow-ups

S02 should verify EmailRep's provider registry/config-store/settings behavior, allowed-host entry, key-gated coverage counts for `IOCType.EMAIL`, and zero coverage without a key. S03 should consume the flattened `raw_stats` contract for compact safe rendering. S04 should route-mock EmailRep and prove an Online email IOC renders an EmailRep verdict/context row without a live key.

## Files Created/Modified

- `app/enrichment/adapters/emailrep.py` — EmailRep adapter implementation with email-only support, key-gated request headers, safe_request dispatch, conservative verdict mapping, and flattened raw_stats.
- `tests/test_emailrep.py` — Provider-specific mocked tests for verdict mapping, flattened stats, key gating, auth headers, URL encoding, unsupported type, and HTTP 401 handling.
- `tests/test_adapter_contract.py` — Shared adapter contract registry includes EmailRep so common adapter invariants are exercised with all providers.
- `.gsd/PROJECT.md` — Project state refreshed to note M016 active and S01 EmailRep adapter-contract completion.
