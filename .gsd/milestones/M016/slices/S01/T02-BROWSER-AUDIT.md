# T02 Browser Loop Audit — M016 S01

**Date:** 2026-05-09
**Server path:** `make dev-server-start` / `make dev-server-status` against `http://127.0.0.1:5000/`
**Sample used:** mixed IOC text containing URL, IPv4, SHA256, domains, and email.

## Product-loop observations

### 1. Desktop intake (`/`)

- **Observed state:** Desktop `1280x800` opens focused on `#ioc-text` with a strong single-purpose command card: "Paste indicators. Extract fast." The textarea is prominent and Offline is visibly selected.
- **Helpful:** The hero and `#analyze-form` make the primary paste/extract loop clear.
- **Friction:** `.recent-analyses-rail` is visible beside the primary input before the user has submitted anything, and its repeated timestamps/status pills visually compete with the paste task.
- **References:** `app/templates/index.html:5` `.intake-workbench`; `app/templates/index.html:37-41` `.mode-toggle`; `app/templates/index.html:72` `.recent-analyses-rail`.

### 2. Mobile intake (`/`)

- **Observed state:** Mobile `390x844` keeps the hero and textarea visible, but the analysis mode panel starts near the bottom of the first viewport and `.form-actions` falls below the fold (`top≈889px` while viewport height is `844px`). The recent history rail starts around `964px`.
- **Helpful:** The first viewport still communicates Offline-first extraction and gives a large paste target.
- **Friction:** Submit is not visible after landing/focusing the textarea, so a first-time mobile user must scroll before extracting. The mode explanation is long relative to mobile space.
- **References:** `app/templates/index.html:21` `#ioc-text`; `app/templates/index.html:37-59` `.mode-toggle`; `app/templates/index.html:61-70` `.form-actions`; `app/templates/index.html:72` `.recent-analyses-rail`.

### 3. Offline submit and results (`POST /analyze`, rendered at `/analyze`)

- **Observed state:** Offline sample produced **6 unique IOCs**: URL, IPv4, SHA256, two domains, and email. Results render as compact `.ioc-card` rows with `Copy` and `Detail` actions, preserving the evidence/detail affordance.
- **Helpful:** Offline path feels local and simple. The header communicates mode/count, and result cards are scannable.
- **Friction:** For an all-`no_data` Offline set, `_filter_bar.html` still renders six verdict filters plus type pills and search. That row is heavier than the evidence for a small list where only `No Data` is populated.
- **References:** `app/templates/results.html:5-18` `.page-results` / `.results-header`; `app/templates/partials/_filter_bar.html:2-24` `.filter-bar-wrapper`, verdict buttons, type pills, search; `app/templates/partials/_ioc_card.html:30-54` `.ioc-card`, `.ioc-card-actions`, details link.

### 4. Online/progress observation (`POST /analyze` in Online mode)

- **Observed state:** Online path rendered `.page-results[data-results-owner="live"]`, polled `/enrichment/status/<job>?since=...`, displayed `16/19 providers complete`, and showed an `#enrich-warning` for VirusTotal authentication. Provider coverage row showed `16 registered · 9 configured · 7 need API keys`.
- **Helpful:** The progress/status mechanism is honest and observable; cards update with provider context, errors, and pending provider text.
- **Friction:** The top of the page becomes dashboard-like: warning banner, progress bar, KPI dashboard, provider coverage, filter row, export menu, and cards all compete. Error cards say `ERROR` while the summary line still says "No providers returned data for this IOC", which reads contradictory when the issue is authentication.
- **References:** `app/templates/results.html:26-33` `.export-group`; `app/templates/results.html:39` `#enrich-warning`; `app/templates/results.html:44-48` `#enrich-progress`; `app/templates/partials/_verdict_dashboard.html:1-27` `#verdict-dashboard`; `app/templates/partials/_verdict_dashboard.html:29-34` `.provider-coverage-row`; `app/templates/partials/_enrichment_slot.html:1` `.enrichment-slot`; `app/static/src/ts/modules/enrichment.ts:25-46` live owner/progress wiring.

### 5. History resume

- **Observed state:** Clicking a `.recent-analysis-row` resumed `/history/<id>` with `.page-results[data-results-owner="history"]`; browser network logs showed **no fetch/XHR requests** during the history replay check. History renders previously enriched card context and `Enrichment complete`.
- **Helpful:** Resume is genuinely useful: one click restores prior analysis without re-running enrichment or polling.
- **Friction:** On mobile, a resumed online history page inherits live-style dashboard chrome: export dropdown, progress/status, KPI dashboard, coverage row, filter bar, then cards. This makes the historical evidence feel secondary.
- **References:** `app/templates/index.html:89-91` `.recent-analysis-row`; `app/routes/history.py:15` `history_list`; `app/routes/history.py:23` `history_detail`; `app/templates/results.html:3-5` `resolved_results_owner`; `app/static/src/ts/modules/history.ts:26-41` history owner/progress completion wiring.

## Prioritized target list for S02/S03

### Must-fix for minimal product loop

1. **Make mobile submit reachable without scrolling past a large mode panel.** Collapse or shorten `.mode-toggle-copy`, make `.form-actions` sticky/closer to `#ioc-text`, or reduce textarea/mode vertical footprint on mobile. References: `app/templates/index.html:21`, `app/templates/index.html:37-70`.
2. **Quiet recent history on initial intake.** Preserve resume, but collapse `.recent-analyses-rail` or move it behind a compact disclosure/secondary route link so it does not compete with first-use paste. References: `app/templates/index.html:72-111`; `app/templates/base.html:25` history nav.
3. **Simplify result controls for small/offline sets.** Keep type/search affordances, but hide zero-count verdict filters or collapse the full verdict filter row when all cards are `no_data` Offline. References: `app/templates/partials/_filter_bar.html:2-24`; `app/static/src/ts/modules/filter.ts:38`, `app/static/src/ts/modules/filter.ts:132`.
4. **Replace Online KPI dashboard with compact status by default.** Preserve status/progress and evidence, but collapse `#verdict-dashboard` and `.provider-coverage-row` unless the user asks for provider/status details. References: `app/templates/partials/_verdict_dashboard.html:1-34`; `app/templates/results.html:44-48`.
5. **Clarify auth-error card copy.** When provider failures drive an `ERROR` verdict, avoid saying "No providers returned data" as the summary. References: `.enrichment-slot` in `app/templates/partials/_enrichment_slot.html:1`; live rendering in `app/static/src/ts/modules/shared-rendering.ts` and `app/static/src/ts/modules/result-application.ts`.

### Nice-to-have polish

1. **Keep `Copy` and `Detail` actions, but visually quiet copy buttons.** Detail links are valuable evidence affordances; copy can be less dominant on mobile cards. References: `app/templates/partials/_ioc_card.html:37-53`.
2. **Preserve history resume, but label it as a secondary continuation action.** The dedicated `/history` route and nav icon are enough for deeper browsing; index can show only one compact recent item or a disclosure. References: `app/templates/history.html:11`; `app/templates/base.html:25`.
3. **Use Online progress as a verification target.** Future UI changes should verify `#enrich-progress-text`, `#enrich-warning`, `.ioc-card[data-verdict]`, and history `data-results-owner="history"` rather than relying on screenshots alone.

## Verification checklist coverage

- ✅ Desktop intake observation recorded.
- ✅ Mobile intake observation recorded.
- ✅ Offline results observation recorded.
- ✅ Online/progress observation recorded with real polling and warning state.
- ✅ History resume observation recorded with no XHR requests in browser network log.
- ✅ Recommended changes include concrete file/selector references.
