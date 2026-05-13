---
id: T03
parent: S04
milestone: M017
key_files:
  - tools/optimization_audit.py
  - tests/test_optimization_audit.py
  - .gsd/milestones/M017/M017-AUDIT.md
key_decisions:
  - Represent S04 as a shipped do-now frontend/render outcome rather than leaving browser rendering churn as an unresolved do-next target.
  - Use the generator as the source of truth for M017 audit wording and enforce stale-language rejection in `tests/test_optimization_audit.py`.
duration: 
verification_result: passed
completed_at: 2026-05-13T17:48:37.866Z
blocker_discovered: false
---

# T03: Encoded S04’s shipped frontend/render severity-change gate outcome in the generated M017 optimization audit and audit regression tests.

**Encoded S04’s shipped frontend/render severity-change gate outcome in the generated M017 optimization audit and audit regression tests.**

## What Happened

Updated `tools/optimization_audit.py` so M017 no longer presents browser rendering churn as an unresolved do-next target after T02. The M017 ranked findings now record S04 as a shipped frontend/render optimization: removing the duplicate broad `flush()` path leaves shared result application on the existing severity-change gate, so provider-only/no-op deltas skip global dashboard recount/reorder while severity-changing deltas still update counts/order. The audit language cites the exact code path, focused result-application tests, full frontend suite, and mocked-online browser checks for results and EmailRep continuity. Updated `tests/test_optimization_audit.py` to require the S04 shipped-outcome language, R086/R088 continuity, and proof references, while rejecting stale target-only phrases. Regenerated `.gsd/milestones/M017/M017-AUDIT.md` with the canonical audit command.

## Verification

Ran the required canonical audit generation plus focused audit regression suite. The command regenerated `.gsd/milestones/M017/M017-AUDIT.md` from generator support and `tests/test_optimization_audit.py` passed all 9 tests. Also checked the generated artifact includes S04 shipped/severity-gate/mocked-online wording and omits stale browser-render target phrases.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 tools/optimization_audit.py --mode baseline --milestone-id M017 --output .gsd/milestones/M017/M017-AUDIT.md && python3 -m pytest -q tests/test_optimization_audit.py` | 0 | ✅ pass — regenerated M017 audit and 9 audit tests passed | 1332ms |
| 2 | `python3 - <<'PY'
from pathlib import Path
content=Path('.gsd/milestones/M017/M017-AUDIT.md').read_text()
checks={
 's04_shipped': "Keep S04's shipped frontend/render optimization" in content,
 'severity_gate': 'severity-change gate' in content,
 'mocked_online': 'mocked-online browser checks for results and EmailRep continuity' in content,
 'stale_measure': 'Measure browser result rendering churn after the status/fan-out target' in content,
 'stale_followup': 'M017 follow-up should focus on remaining flush-wide' in content,
}
for k,v in checks.items(): print(f'{k}={v}')
PY` | 0 | ✅ pass — generated artifact has S04 outcome language and no checked stale target phrases | 0ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `tools/optimization_audit.py`
- `tests/test_optimization_audit.py`
- `.gsd/milestones/M017/M017-AUDIT.md`
