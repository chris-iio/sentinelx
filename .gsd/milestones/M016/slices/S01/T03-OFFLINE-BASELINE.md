# T03 Offline Paste-to-Results Runtime Baseline

## Purpose

Capture a repeatable M016 baseline for the Offline paste-to-results path before any optimization work claims a speed improvement.

## Baseline path

Deterministic Flask test-client benchmark of `POST /analyze` with `mode=offline`, plus split timings for:

- `run_pipeline()` + `group_by_type()` extraction/classification/grouping cost.
- `results.html` template rendering cost with precomputed grouped IOCs.
- Full `/analyze` POST wall-clock cost.

No external enrichment providers are contacted in this path.

## Exact command used

Run from the repository root:

```bash
python3 - <<'PY'
import gc
import json
import os
import statistics
import tempfile
import time

# Keep benchmark state isolated from the user's persistent ~/.sentinelx stores.
os.environ['HOME'] = tempfile.mkdtemp(prefix='sentinelx-bench-home-')
os.environ.setdefault('SECRET_KEY', 'benchmark-secret-key')

from app import create_app
from app.pipeline.extractor import run_pipeline
from app.pipeline.models import group_by_type
from flask import render_template

SAMPLE_LINES = []
for idx in range(1, 9):
    SAMPLE_LINES.append(f"Alert {idx}: source 198.51.100.{idx} connected to http://evil{idx}.example.com/login and user phish{idx}@example.net")
for idx in range(1, 5):
    SAMPLE_LINES.append(f"Hash set {idx}: {idx:032x} {idx:040x} {idx:064x}")
SAMPLE_LINES.extend([
    "Observed CVE-2024-3094 in dependency notes and callback to 203.0.113.45.",
    "Defanged indicators include hxxps://malware[.]example[.]org/dropper and admin(at)example.org.",
])
SAMPLE_TEXT = "\n".join(SAMPLE_LINES)

app = create_app({
    'TESTING': True,
    'WTF_CSRF_ENABLED': False,
    'SERVER_NAME': 'localhost',
    'RATELIMIT_ENABLED': False,
})
client = app.test_client()

def ms(fn, iterations):
    samples = []
    for _ in range(iterations):
        start = time.perf_counter()
        result = fn()
        samples.append((time.perf_counter() - start) * 1000)
    return result, samples

def summarize(samples):
    ordered = sorted(samples)
    return {
        'iterations': len(samples),
        'min_ms': round(min(samples), 3),
        'median_ms': round(statistics.median(samples), 3),
        'mean_ms': round(statistics.mean(samples), 3),
        'p95_ms': round(ordered[int(len(ordered) * 0.95) - 1], 3),
        'max_ms': round(max(samples), 3),
    }

# Warm imports/templates/caches outside the measured loop.
iocs = run_pipeline(SAMPLE_TEXT)
grouped = group_by_type(iocs)
with app.test_request_context('/analyze', method='POST'):
    render_template('results.html', grouped=grouped, mode='offline', total_count=len(iocs), no_results=False)
for _ in range(3):
    response = client.post('/analyze', data={'text': SAMPLE_TEXT, 'mode': 'offline'})
    assert response.status_code == 200, response.status_code

gc.disable()
try:
    _, pipeline_samples = ms(lambda: group_by_type(run_pipeline(SAMPLE_TEXT)), 50)
    render_samples = []
    with app.test_request_context('/analyze', method='POST'):
        for _ in range(50):
            start = time.perf_counter()
            html = render_template('results.html', grouped=grouped, mode='offline', total_count=len(iocs), no_results=False)
            render_samples.append((time.perf_counter() - start) * 1000)
    def full_post():
        response = client.post('/analyze', data={'text': SAMPLE_TEXT, 'mode': 'offline'})
        assert response.status_code == 200, response.status_code
        return len(response.data)
    response_bytes, full_samples = ms(full_post, 30)
finally:
    gc.enable()

group_counts = {ioc_type.value: len(items) for ioc_type, items in grouped.items()}
summary = {
    'mode': 'offline',
    'input': {
        'lines': len(SAMPLE_LINES),
        'characters': len(SAMPLE_TEXT),
        'unique_iocs': len(iocs),
        'group_counts': group_counts,
    },
    'timings': {
        'pipeline_plus_group_by_type': summarize(pipeline_samples),
        'template_render_only': summarize(render_samples),
        'full_post_analyze': summarize(full_samples),
    },
    'response_bytes': response_bytes,
    'environment': {
        'python': os.popen('python3 --version').read().strip(),
        'testing': True,
        'csrf': 'disabled',
        'rate_limit': 'disabled',
        'home_isolated': True,
        'external_providers': 'not contacted; POST used mode=offline',
    },
}
print(json.dumps(summary, indent=2, sort_keys=True))
PY
```

## Input size and shape

- Lines: 14
- Characters: 1,578
- Unique extracted IOCs: 50
- IOC mix:
  - CVE: 1
  - domains: 11
  - emails: 9
  - IPv4s: 8
  - MD5: 4
  - SHA1: 4
  - SHA256: 4
  - URLs: 9

## Timing results

Raw output was captured in `.gsd/exec/be3938ef-78a1-4f66-9ca4-1613f5b36304.stdout`.

| Check | Iterations | Min | Median | Mean | P95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `run_pipeline()` + `group_by_type()` | 50 | 6.305 ms | 6.713 ms | 6.808 ms | 7.581 ms | 7.892 ms |
| `results.html` render only | 50 | 0.734 ms | 0.839 ms | 0.861 ms | 1.018 ms | 1.097 ms |
| Full Flask test-client `POST /analyze` | 30 | 7.726 ms | 8.118 ms | 8.311 ms | 9.074 ms | 9.525 ms |

Full response size for the representative sample was 59,015 bytes.

## Environment caveats

- Python: 3.10.12
- Flask app created with `TESTING=True`, `WTF_CSRF_ENABLED=False`, `SERVER_NAME=localhost`, and `RATELIMIT_ENABLED=False` so repeated measurements do not trip CSRF or per-route rate limits.
- `HOME` was pointed at a temporary directory before importing the app so `~/.sentinelx` cache/history stores were isolated from local user state.
- The measurement is server-side/test-client wall-clock only; it does not include browser DOM parsing, CSS, JS hydration, or network latency.
- Garbage collection was disabled during measured loops and re-enabled afterward to reduce run-to-run noise.

## S04 speed target and optimization direction

For a representative 50-IOC Offline paste, preserve full Flask `POST /analyze` p95 at or below **12 ms** on this local benchmark shape. If S04 observes regression, prioritize extraction/classification (`run_pipeline()` and library calls) before template rendering: extraction/grouping accounts for most measured wall time, while server-side render-only cost is about 1 ms p95.

Do not infer a user-visible browser timing target from this artifact alone; browser DOM work should be measured separately if S04 changes card markup, filtering, CSS, or client-side behavior.
