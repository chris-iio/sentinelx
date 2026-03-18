---
estimated_steps: 6
estimated_files: 5
---

# T02: Audit security contracts — CSP, CSRF, SEC-08 textContent-only

**Slice:** S04 — Functionality integration + polish
**Milestone:** M002

## Description

R009 requires that security posture doesn't regress during the UI redesign: CSP headers, CSRF protection, textContent-only DOM construction (SEC-08), and absence of dangerous patterns like eval/document.write. This is a read-only audit task — it produces grep-based evidence for each security contract. If any violation is found, fix it.

S01–S03 introduced new DOM construction in `row-factory.ts` (summary rows, chevron SVG, provider details) and `enrichment.ts` (detail link injection). All were built with `createElement`+`textContent`+`setAttribute` per SEC-08, but this task provides the formal evidence.

## Steps

1. Check for innerHTML in production TS code:
   ```
   grep -n 'innerHTML' app/static/src/ts/modules/*.ts
   ```
   Any matches must be in comments only. If any executable `innerHTML` usage exists, refactor to `createElement`+`textContent`.

2. Verify CSP header:
   ```
   grep -n 'Content-Security-Policy' app/__init__.py
   ```
   Must find the header definition with `script-src 'self'` (or stricter).

3. Verify CSRF protection:
   ```
   grep -n -i 'csrf' app/__init__.py
   grep -n 'csrf-token' app/templates/base.html
   ```
   Must find `CSRFProtect` initialization in `__init__.py` and `<meta name="csrf-token">` in `base.html`.

4. Check for dangerous patterns:
   ```
   grep -rn 'document\.write\|eval(' app/static/src/ts/
   ```
   Must return 0 matches.

5. Review `.style.xxx` assignments in enrichment.ts and filter.ts:
   ```
   grep -n '\.style\.' app/static/src/ts/modules/enrichment.ts app/static/src/ts/modules/filter.ts
   ```
   All matches must be DOM element property access (e.g., `el.style.width = "50%"`) — not inline `<style>` element injection. Confirm each match is safe.

6. Verify DOM construction patterns in new S01–S03 code (row-factory.ts, enrichment.ts):
   ```
   grep -n 'createElement\|createElementNS\|textContent\|setAttribute' app/static/src/ts/modules/row-factory.ts app/static/src/ts/modules/enrichment.ts
   ```
   Confirm these files use the SEC-08 pattern exclusively. Cross-reference with step 1 to ensure no innerHTML fallbacks.

Document all results in the task summary.

## Must-Haves

- [ ] 0 `innerHTML` in executable TS code (comments OK)
- [ ] CSP `Content-Security-Policy` header found in `app/__init__.py`
- [ ] CSRF: `CSRFProtect` in `__init__.py` and `csrf-token` meta in `base.html`
- [ ] 0 matches for `document.write` or `eval(` in TS code
- [ ] All `.style.xxx` assignments are DOM property access, not style element injection
- [ ] All DOM construction in row-factory.ts and enrichment.ts uses createElement+textContent+setAttribute

## Verification

- All grep commands produce expected results (documented with line numbers)
- No security violations found, or violations fixed with evidence of fix

## Inputs

- T01 completed: builds and E2E pass (confirms code is in a working state)
- S03 forward intelligence: new DOM construction in row-factory.ts and enrichment.ts used createElement pattern

## Expected Output

- Security audit evidence document with pass/fail for each R009 sub-contract, including grep output with line numbers
- If any violations found: fix applied with before/after evidence
