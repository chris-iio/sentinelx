---
estimated_steps: 6
estimated_files: 2
skills_used: []
---

# T03: Capture Offline paste-to-results runtime baseline

Why: M016 says SentinelX should be fast. That claim needs a fresh baseline before optimization work begins.

Do:
1. Choose the most deterministic baseline path available: Flask test-client `POST /analyze` in Offline mode, browser submit timing, or both.
2. Use a representative sample with enough IOCs to exercise extraction and result rendering without external providers.
3. Capture wall-clock timing and, if practical, split extraction vs template/render cost.
4. Save the command and output in a small M016 artifact or slice note.
5. Identify whether S04 should optimize extraction, rendering, browser DOM work, or simply preserve a good baseline.
6. Do not claim speed improvement in T03; this is baseline only.

Done when: There is a repeatable command/output that future work can compare against.

## Inputs

- `app/routes/analysis.py`
- `app/pipeline/extractor.py` / `run_pipeline()`
- Existing tests or fixtures for analysis submissions.

## Expected Output

- Baseline timing artifact or documented command output.
- Candidate speed target for S04.

## Verification

The artifact must include:

- Exact command or script used.
- Input size/shape.
- Timing result(s).
- Environment caveats if any.

## Observability Impact

May add a temporary or durable benchmark-style script only if useful. Prefer a simple documented command if that gives enough signal.
