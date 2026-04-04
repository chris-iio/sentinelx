---
estimated_steps: 17
estimated_files: 3
skills_used: []
---

# T03: Trim remaining adapters (dns_lookup, malwarebazaar, urlhaus) and run full verification

Apply the same mechanical trim to the final 3 adapter files, then run the full test suite and line-count verification to confirm the slice goal.

## Steps

1. For each of the 3 files, apply the standard trim pattern:
   - **Module-level docstring**: Replace with one-liner.
   - **Class-level docstring**: Replace with one-liner referencing BaseHTTPAdapter.
   - **Method-level docstrings**: Delete entirely.
2. Verify all 3 files import cleanly.
3. Run the **full** test suite: `python3 -m pytest tests/ -x -q` — all 1,061 tests must pass.
4. Verify all 15 non-base adapter modules are importable in one shot.
5. Measure total line count: `find app/enrichment/adapters -name '*.py' ! -name '__init__.py' ! -name 'base.py' -exec cat {} + | wc -l` — must be ≤1,900 (down from ~2,659 baseline).
6. Confirm `base.py` is unchanged: `wc -l app/enrichment/adapters/base.py` should be 161.

## Must-Haves

- [ ] All 3 files have one-liner module + class docstrings
- [ ] All method-level docstrings deleted
- [ ] Full test suite passes (1,061 tests, 0 failures)
- [ ] Total non-base adapter line count ≤ 1,900
- [ ] base.py unchanged at 161 lines

## Inputs

- ``app/enrichment/adapters/dns_lookup.py` — current file with verbose docstrings`
- ``app/enrichment/adapters/malwarebazaar.py` — current file with verbose docstrings`
- ``app/enrichment/adapters/urlhaus.py` — current file with verbose docstrings`

## Expected Output

- ``app/enrichment/adapters/dns_lookup.py` — trimmed to one-liner docstrings`
- ``app/enrichment/adapters/malwarebazaar.py` — trimmed to one-liner docstrings`
- ``app/enrichment/adapters/urlhaus.py` — trimmed to one-liner docstrings`

## Verification

python3 -m pytest tests/ -x -q && python3 -c "
import importlib, pathlib
for f in sorted(pathlib.Path('app/enrichment/adapters').glob('*.py')):
    if f.name == '__init__.py': continue
    mod = f'app.enrichment.adapters.{f.stem}'
    importlib.import_module(mod)
    print(f'  OK {mod}')
" && echo "Non-base line count:" && find app/enrichment/adapters -name '*.py' ! -name '__init__.py' ! -name 'base.py' -exec cat {} + | wc -l && echo "base.py:" && wc -l app/enrichment/adapters/base.py
