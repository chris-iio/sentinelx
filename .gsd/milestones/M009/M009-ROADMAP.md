# M009: Codebase Reduction

## Vision
Reduce SentinelX's codebase through four targeted consolidations: BaseHTTPAdapter absorbs shared adapter skeleton, parametrized test suite replaces duplicated contract tests, dead CSS audit and removal, and frontend TypeScript function dedup. Zero behavior changes — the test suite is the safety net.

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | BaseHTTPAdapter + proof migration | high | — | ✅ | After this: BaseHTTPAdapter exists in base.py. Shodan (simplest HTTP adapter) subclasses it. All 25 Shodan tests pass unchanged. The migration recipe is proven. |
| S02 | Migrate remaining 11 HTTP adapters | medium | S01 | ✅ | After this: All 12 HTTP adapters use BaseHTTPAdapter. 3 non-HTTP adapters unchanged. Full test suite passes. |
| S03 | Adapter test consolidation | medium | S02 | ✅ | After this: Shared parametrized test module covers protocol/error/type-guard contract once for all 15 adapters. Per-adapter test files contain only verdict+parsing tests. Test suite passes. |
| S04 | CSS audit + frontend TypeScript dedup | low | — | ✅ | After this: Dead CSS rules removed. Shared TS module extracts duplicated functions from enrichment.ts and history.ts. make css && make js && make typecheck pass. |
