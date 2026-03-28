# S02: REST API blueprint — UAT

**Milestone:** M008
**Written:** 2026-03-28T05:34:09.566Z

## UAT: REST API Blueprint\n\n- [x] POST /api/analyze accepts JSON body with text field\n- [x] Returns structured JSON with iocs array, grouped summary, total_count\n- [x] Default mode is offline (no enrichment)\n- [x] Online mode returns job_id and status_url\n- [x] GET /api/status/<job_id> returns polling progress\n- [x] API routes exempt from CSRF\n- [x] Browser POST routes still require CSRF\n- [x] Rate limits applied (10/min analyze, 120/min status)\n- [x] Validation errors return 400 with descriptive JSON\n- [x] 18 new tests + 1057 existing = 1075 total, all passing
