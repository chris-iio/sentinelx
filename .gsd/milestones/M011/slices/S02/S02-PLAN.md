# S02: Per-Adapter Test Consolidation

**Goal:** Consolidate per-adapter granular field tests (test_raw_stats_has_asn_key, test_detection_count_always_zero, etc.) into single response-shape tests that assert the full result object.
**Demo:** After this: After this: granular one-field-per-test patterns collapsed into single response-shape tests; ~400-600 test lines removed; all tests still pass.

## Tasks
