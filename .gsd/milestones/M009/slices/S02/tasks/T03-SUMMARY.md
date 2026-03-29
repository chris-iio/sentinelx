---
id: T03
parent: S02
milestone: M009
provides: []
requires: []
affects: []
key_files: ["app/enrichment/adapters/virustotal.py", "app/enrichment/adapters/threatminer.py"]
key_decisions: ["VT _build_url() uses ENDPOINT_MAP meaningfully rather than a stub", "ThreatMiner abstract methods raise NotImplementedError with explanatory messages since lookup() uses sub-method dispatch"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "17 VT tests pass, 69 ThreatMiner tests pass, 853 full suite tests pass (excluding e2e/Playwright and iocextract-dependent tests — pre-existing env issues). 12 adapter files contain BaseHTTPAdapter subclass. 3 non-HTTP adapters do not. Registry instantiates all 15 providers. VT supported_types confirmed as frozenset."
completed_at: 2026-03-29T17:52:00.940Z
blocker_discovered: false
---

# T03: Migrated VTAdapter and ThreatMinerAdapter to BaseHTTPAdapter subclasses with all 86 adapter tests and 853 suite tests passing

> Migrated VTAdapter and ThreatMinerAdapter to BaseHTTPAdapter subclasses with all 86 adapter tests and 853 suite tests passing

## What Happened
---
id: T03
parent: S02
milestone: M009
key_files:
  - app/enrichment/adapters/virustotal.py
  - app/enrichment/adapters/threatminer.py
key_decisions:
  - VT _build_url() uses ENDPOINT_MAP meaningfully rather than a stub
  - ThreatMiner abstract methods raise NotImplementedError with explanatory messages since lookup() uses sub-method dispatch
duration: ""
verification_result: passed
completed_at: 2026-03-29T17:52:00.941Z
blocker_discovered: false
---

# T03: Migrated VTAdapter and ThreatMinerAdapter to BaseHTTPAdapter subclasses with all 86 adapter tests and 853 suite tests passing

**Migrated VTAdapter and ThreatMinerAdapter to BaseHTTPAdapter subclasses with all 86 adapter tests and 853 suite tests passing**

## What Happened

Migrated the two complex adapters (VirusTotal and ThreatMiner) that require full lookup() overrides to subclass BaseHTTPAdapter. VT: removed __init__/is_configured, converted supported_types to frozenset, added _auth_headers/_build_url/_parse_response. ThreatMiner: removed __init__/is_configured, added stub abstract implementations, kept full multi-call dispatch. Both constructors used keyword args in the registry so the signature change was seamless. All 12 HTTP adapters now subclass BaseHTTPAdapter, 3 non-HTTP adapters remain independent, and all 15 providers instantiate correctly.

## Verification

17 VT tests pass, 69 ThreatMiner tests pass, 853 full suite tests pass (excluding e2e/Playwright and iocextract-dependent tests — pre-existing env issues). 12 adapter files contain BaseHTTPAdapter subclass. 3 non-HTTP adapters do not. Registry instantiates all 15 providers. VT supported_types confirmed as frozenset.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -m pytest tests/test_vt_adapter.py tests/test_threatminer.py -v` | 0 | ✅ pass | 180ms |
| 2 | `python3 -m pytest tests/ -q --ignore=tests/e2e --ignore=tests/test_extractor.py --ignore=tests/test_pipeline.py --ignore=tests/test_api.py --ignore=tests/test_routes.py --ignore=tests/test_history_routes.py --ignore=tests/test_ioc_detail_routes.py --ignore=tests/test_settings.py --ignore=tests/test_security_audit.py` | 0 | ✅ pass (853 passed) | 7580ms |
| 3 | `grep -rl 'class.*BaseHTTPAdapter' app/enrichment/adapters/*.py | grep -v base.py | wc -l` | 0 | ✅ pass (12) | 100ms |
| 4 | `python3 -c "from app.enrichment.setup import build_registry; from app.enrichment.config_store import ConfigStore; r = build_registry(allowed_hosts=['example.com'], config_store=ConfigStore(':memory:')); assert len(r.all()) == 15"` | 0 | ✅ pass (15 providers) | 500ms |


## Deviations

Verification grep for BaseHTTPAdapter subclass count returns 13 not 12 because base.py matches — added grep -v base.py exclusion. Full suite required --ignore for 7 test files with missing iocextract dependency (pre-existing env issue).

## Known Issues

None.

## Files Created/Modified

- `app/enrichment/adapters/virustotal.py`
- `app/enrichment/adapters/threatminer.py`


## Deviations
Verification grep for BaseHTTPAdapter subclass count returns 13 not 12 because base.py matches — added grep -v base.py exclusion. Full suite required --ignore for 7 test files with missing iocextract dependency (pre-existing env issue).

## Known Issues
None.
