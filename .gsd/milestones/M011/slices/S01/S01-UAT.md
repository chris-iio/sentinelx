# S01: Adapter Docstring Trim — UAT

**Milestone:** M011
**Written:** 2026-04-04T11:49:49.591Z

## UAT: Adapter Docstring Trim

### Preconditions
- Working directory: `/home/chris/projects/sentinelx`
- Python 3 with project dependencies installed
- All adapter source files present under `app/enrichment/adapters/`

### Test 1: All 16 adapter modules importable
```bash
python3 -c "
import importlib, pathlib
for f in sorted(pathlib.Path('app/enrichment/adapters').glob('*.py')):
    if f.name == '__init__.py': continue
    mod = f'app.enrichment.adapters.{f.stem}'
    importlib.import_module(mod)
    print(f'  OK {mod}')
"
```
**Expected:** All 16 modules print OK, exit code 0.

### Test 2: Full test suite unchanged
```bash
python3 -m pytest tests/ -x -q
```
**Expected:** 1,061 passed, 0 failures.

### Test 3: Non-base adapter line count ≤ 1,900
```bash
find app/enrichment/adapters -name '*.py' ! -name '__init__.py' ! -name 'base.py' -exec cat {} + | wc -l
```
**Expected:** ≤ 1,900 lines (actual: 1,597).

### Test 4: base.py unchanged
```bash
wc -l app/enrichment/adapters/base.py
```
**Expected:** 161 lines.

### Test 5: One-liner docstring convention enforced
```bash
for f in app/enrichment/adapters/*.py; do
  [ "$(basename "$f")" = "__init__.py" ] && continue
  [ "$(basename "$f")" = "base.py" ] && continue
  count=$(grep -c '"""' "$f")
  echo "$(basename "$f"): $count triple-quote lines"
done
```
**Expected:** Each non-base adapter file has exactly 4 triple-quote lines (2 pairs = module one-liner + class one-liner), except `whois_lookup.py` which has 6 (extra pair for `_normalise_datetime` short docstring).

### Test 6: Edge-case inline comments preserved
```bash
grep -c "status_code.*404" app/enrichment/adapters/threatminer.py
grep -c "port 43\|Port 43\|no SSRF\|no.*SSRF" app/enrichment/adapters/whois_lookup.py
grep -c "404.*private\|private.*404\|reserved" app/enrichment/adapters/ip_api.py
grep -c "pipe.delimited\|Pipe.delimited\|no_data" app/enrichment/adapters/asn_cymru.py
```
**Expected:** Each grep returns ≥ 1 match, confirming edge-case knowledge was not deleted.

### Test 7: No method-level docstrings remain (except _normalise_datetime)
```bash
python3 -c "
import ast, pathlib
for f in sorted(pathlib.Path('app/enrichment/adapters').glob('*.py')):
    if f.name in ('__init__.py', 'base.py'): continue
    tree = ast.parse(f.read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            ds = ast.get_docstring(node)
            if ds:
                print(f'  {f.name}:{node.name} has docstring')
"
```
**Expected:** Only `whois_lookup.py:_normalise_datetime` appears. No other method-level docstrings.
