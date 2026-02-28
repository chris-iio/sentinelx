# Phase 20: Type Definitions Foundation - Research

**Researched:** 2026-02-28
**Domain:** TypeScript union types, const assertions, interface design, tsconfig strict options
**Confidence:** HIGH

## Summary

Phase 20 creates the shared TypeScript type layer before any module conversion begins. The deliverables are two files: `app/static/src/ts/types/ioc.ts` (domain types: `VerdictKey`, `IocType` union types + typed constants) and `app/static/src/ts/types/api.ts` (API shape interfaces: `EnrichmentStatus`, `EnrichmentResult`, `EnrichmentError`). The `tsconfig.json` is already correct from Phase 19 — `strict: true`, `isolatedModules: true`, `noUncheckedIndexedAccess: true`, `"types": []`. The existing `make typecheck` already passes clean on the placeholder `main.ts`. This phase adds the type files and verifies `make typecheck` still passes on all three files.

The domain model is fully known from the existing `main.js` and Flask route. `VERDICT_SEVERITY`, `VERDICT_LABELS`, and `IOC_PROVIDER_COUNTS` are already defined as plain JavaScript arrays and objects in `main.js` lines 228–250. The Flask `/enrichment/status/<job_id>` response shape is explicitly documented in `app/routes.py` via the `_serialize_result` function — every field name, type, and optionality is pinned to the Python dataclasses `EnrichmentResult` and `EnrichmentError` in `app/enrichment/models.py`. There is no ambiguity: research confirms the types directly from source, not inference.

The critical design decision is using TypeScript `as const` for typed constants (not plain `const` with widened types), union types for `VerdictKey` and `IocType` (not string enums), and discriminated unions for the API result shape (`type: "result" | "error"`). These patterns give maximum type narrowing with zero runtime cost and align with the project's IIFE/no-Node.js constraint.

**Primary recommendation:** Create `app/static/src/ts/types/` directory with two files. Use union types + `as const` assertions. Mirror the Flask response shape exactly. Keep tsconfig unchanged — it is already correct.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TYPE-01 | tsconfig.json uses `strict: true` with `isolatedModules`, `noUncheckedIndexedAccess`, and `"types": []` | Already complete from Phase 19 — tsconfig.json verified at project root with all four options set. Only verification task remains: `make typecheck` exit 0 on type files. |
| TYPE-02 | Domain types defined for Verdict, IocType, and verdict severity constants | `VerdictKey` union type from VERDICT_SEVERITY array; `IocType` union type from IOC_PROVIDER_COUNTS keys; `VERDICT_SEVERITY`, `VERDICT_LABELS`, `IOC_PROVIDER_COUNTS` typed via `as const`. All values sourced from main.js lines 228–250. |
| TYPE-03 | API response interfaces defined for enrichment polling endpoint (`/enrichment/status/{job_id}`) | Full response shape documented in routes.py `_serialize_result` + `enrichment_status`. Two result shapes (EnrichmentResult/EnrichmentError) form a discriminated union. Top-level `EnrichmentStatus` interface wraps both. |
| TYPE-04 | All DOM element access uses proper null-checking (no non-null assertions) | This requirement applies to module conversion (Phases 21-22), not Phase 20's type definition files. The type files themselves have no DOM access. However, research documents the correct DOM-access pattern for downstream modules. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| TypeScript | 5.8.3 (installed) | Union types, const assertions, interface definitions | Already installed; tsc 5.8.3 confirmed on this machine |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lib.dom.d.ts | Bundled with TS 5.8 | HTMLElement, querySelector types | Provided by `"lib": ["es2022", "dom", "dom.iterable"]` in tsconfig |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Union type (`"malicious" \| "suspicious" \| ...`) | `enum VerdictKey` | String enums generate runtime JavaScript; union types are erased at compile time — IIFE output stays minimal. Union types chosen. |
| `as const` for constants | Generic `Record<string, number>` annotation | `as const` preserves literal types enabling index lookup type errors; generic Record loses key-level type checking. `as const` chosen. |
| Discriminated union (`type: "result" \| "error"`) | Two separate interfaces without a discriminant | Discriminated unions enable exhaustive narrowing in switch statements; non-discriminated requires instanceof checks which don't apply to plain objects. Discriminated union chosen. |
| Runtime validation (Zod, io-ts) | Interface-only type assertions | API responses are from trusted internal Flask routes — runtime validation is out of scope per REQUIREMENTS.md. Interface-only chosen. |

**Installation:** No additional installation required. TypeScript 5.8.3 is already installed.

## Architecture Patterns

### Recommended Project Structure

```
app/static/src/ts/
├── types/
│   ├── ioc.ts          # VerdictKey, IocType, VERDICT_SEVERITY, VERDICT_LABELS, IOC_PROVIDER_COUNTS
│   └── api.ts          # EnrichmentStatus, EnrichmentResultItem, EnrichmentErrorItem
└── main.ts             # existing placeholder (unchanged in Phase 20)
```

The `types/` subdirectory groups all shared types into a single importable layer. Downstream modules (Phases 21-22) import from `../types/ioc` and `../types/api` using relative paths. No barrel index file needed for two files.

### Pattern 1: Union Types for String Domains
**What:** Literal string union types for constrained string fields
**When to use:** Any field that accepts a finite set of string values — verdict states, IOC types
**Example:**
```typescript
// Source: TypeScript Handbook — Literal Types
// app/static/src/ts/types/ioc.ts

export type VerdictKey = "malicious" | "suspicious" | "clean" | "no_data" | "error";

export type IocType = "ipv4" | "ipv6" | "domain" | "url" | "md5" | "sha1" | "sha256";
```
Using `VerdictKey` as a type means any string that is not one of those five values will produce a compile error. Using `"error"` as a key into `VERDICT_LABELS` will type-check correctly; using `"invalid"` will not.

### Pattern 2: `as const` for Typed Constants
**What:** Preserves literal types on constant objects/arrays so TypeScript tracks exact keys/values
**When to use:** Any constant that is indexed by a typed key — lookup tables, severity arrays
**Example:**
```typescript
// Source: TypeScript Handbook — const assertions
// app/static/src/ts/types/ioc.ts

export const VERDICT_SEVERITY = ["error", "no_data", "clean", "suspicious", "malicious"] as const;

// Type is: readonly ["error", "no_data", "clean", "suspicious", "malicious"]
// VERDICT_SEVERITY[0] is "error", not string

export const VERDICT_LABELS: Record<VerdictKey, string> = {
    malicious:  "MALICIOUS",
    suspicious: "SUSPICIOUS",
    clean:      "CLEAN",
    no_data:    "NO DATA",
    error:      "ERROR",
} as const;

// Type is: Record<VerdictKey, string>
// Missing key "invalid" would be a compile error
// Missing key "suspicious" would be a compile error

export const IOC_PROVIDER_COUNTS: Record<IocType, number> = {
    ipv4:   2,
    ipv6:   2,
    domain: 2,
    url:    2,
    md5:    3,
    sha1:   3,
    sha256: 3,
} as const;
```

**Critical note on `VERDICT_LABELS` lookup:** Because `noUncheckedIndexedAccess: true` is set in tsconfig, indexing `VERDICT_LABELS[someKey]` where `someKey` is type `string` (not `VerdictKey`) would return `string | undefined`. Using `VerdictKey` as the index type provides `string` (not `string | undefined`). This is the precise behavior the success criterion describes.

### Pattern 3: Discriminated Union for API Response Shape
**What:** Two related interfaces joined by a literal `type` field that TypeScript can use to narrow
**When to use:** API responses with multiple shapes distinguished by a type discriminant
**Example:**
```typescript
// Source: TypeScript Handbook — Discriminated Unions
// app/static/src/ts/types/api.ts

export interface EnrichmentResultItem {
    type: "result";
    ioc_value: string;
    ioc_type: string;
    provider: string;
    verdict: VerdictKey;
    detection_count: number;
    total_engines: number;
    scan_date: string | null;
    raw_stats: Record<string, unknown>;
}

export interface EnrichmentErrorItem {
    type: "error";
    ioc_value: string;
    ioc_type: string;
    provider: string;
    error: string;
}

export type EnrichmentItem = EnrichmentResultItem | EnrichmentErrorItem;

export interface EnrichmentStatus {
    total: number;
    done: number;
    complete: boolean;
    results: EnrichmentItem[];
}
```

In consuming modules, TypeScript narrows automatically:
```typescript
if (item.type === "result") {
    // item is EnrichmentResultItem — item.verdict is VerdictKey
} else {
    // item is EnrichmentErrorItem — item.error is string
}
```

### Pattern 4: DOM Null-Checking (for TYPE-04, enforced in Phases 21-22)
**What:** Explicit null checks on all `getElementById`/`querySelector` results — no `!` non-null assertions
**When to use:** Every DOM element access in TypeScript modules
**Example:**
```typescript
// Correct: explicit null guard
const form = document.getElementById("analyze-form");
if (!form) return;

// Correct: typed assertion only after guard
const textarea = document.getElementById("ioc-text") as HTMLTextAreaElement | null;
if (!textarea) return;
// textarea is now HTMLTextAreaElement

// Wrong: non-null assertion (TYPE-04 prohibits this)
const form = document.getElementById("analyze-form")!; // never use
```

**Why `getElementById` returns `HTMLElement | null`, not a specific element type:**
`document.getElementById` always returns `HTMLElement | null`. To get `HTMLTextAreaElement`, use `as HTMLTextAreaElement | null` after the null check, or use `document.querySelector<HTMLTextAreaElement>("#ioc-text")` which infers the narrower type from the generic parameter.

### Anti-Patterns to Avoid
- **String enums** (`enum VerdictKey { malicious = "malicious" }`): Generate runtime JS (enum object). Use union types instead — zero runtime cost.
- **`any` type for API responses**: Defeats type checking. Use `EnrichmentStatus` interface.
- **Non-null assertions (`!`)**: Prohibited by TYPE-04. Use explicit `if (!el) return` guards.
- **`noUncheckedIndexedAccess` bypass via `as string`**: Casting `VERDICT_LABELS[key as VerdictKey]` is valid (avoids `undefined` possibility), but casting `VERDICT_LABELS[key as any]` defeats the type system.
- **Duplicate constants**: The type files define the canonical constants. Modules must import from `types/ioc.ts`, not redeclare their own local `VERDICT_SEVERITY` arrays.
- **Circular imports**: `api.ts` imports `VerdictKey` from `ioc.ts`. `ioc.ts` imports nothing. This is the correct dependency direction — no circularity.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| API response validation | Runtime shape checking with `typeof` chains | TypeScript interfaces at compile time | API is a trusted internal Flask route — type errors should be caught at development time, not runtime |
| Enum simulation | Object.freeze + lookup | Union types + `as const` | TypeScript union types are erased at compile time; `Object.freeze` adds runtime complexity without benefit |
| Type guard functions | `function isVerdictKey(s: string): s is VerdictKey` | Direct `VerdictKey` typing from source | The API response `verdict` field is already typed as `VerdictKey` in `EnrichmentResultItem`; no runtime guard needed for trusted internal API |

**Key insight:** Phase 20 is pure compile-time infrastructure. Everything written here disappears from the runtime bundle (types are erased). The value is IDE feedback and `tsc --noEmit` catching type errors before they reach the browser.

## Common Pitfalls

### Pitfall 1: `noUncheckedIndexedAccess` Makes Record Lookups Return `T | undefined`
**What goes wrong:** `VERDICT_LABELS[someString]` returns `string | undefined` when `someString` is typed as `string`, not `VerdictKey`. Consuming code that assumes `string` breaks.
**Why it happens:** `noUncheckedIndexedAccess: true` adds `undefined` to all index signatures, including `Record<string, T>`.
**How to avoid:** Type the constant as `Record<VerdictKey, string>` and ensure all indexing is done with `VerdictKey` values, not plain `string`. When converting modules, use `VERDICT_LABELS[verdict as VerdictKey]` only when `verdict` is already narrowed to a known verdict value.
**Warning signs:** `Type 'string | undefined' is not assignable to type 'string'` errors in Phase 21 when accessing `VERDICT_LABELS[result.verdict]`.

### Pitfall 2: `scan_date` Field Optionality
**What goes wrong:** Flask `_serialize_result` returns `"scan_date": r.scan_date` where `r.scan_date` is `str | None`. The TypeScript interface must declare `scan_date: string | null`, not `scan_date?: string`. The JS code checks `if (scanDateStr)` which handles both `null` and `""` — the TypeScript type must match the actual shape.
**Why it happens:** Developers sometimes use `field?: T` (optional property) when the field is always present but potentially null. These are different: `field?: T` means the key may be absent from the object; `field: T | null` means the key is always present but its value may be null.
**How to avoid:** Use `scan_date: string | null` (always present, possibly null). The Flask JSON response always includes `scan_date` as a key, even when its value is `None` (serialized as JSON `null`).
**Warning signs:** TypeScript narrowing `if (result.scan_date)` works correctly for both; but `result.scan_date.length` without a null check would error with `string | null` but silently work with `string | undefined` (wrong).

### Pitfall 3: `raw_stats` Type
**What goes wrong:** Flask `_serialize_result` includes `"raw_stats": r.raw_stats` where `r.raw_stats` is typed as `dict` (Python). In TypeScript, this should be `Record<string, unknown>`, not `object` or `any`.
**Why it happens:** `object` in TypeScript does not allow property access; `any` defeats type checking. `Record<string, unknown>` is the correct representation of an arbitrary JSON object.
**How to avoid:** Use `raw_stats: Record<string, unknown>` in `EnrichmentResultItem`. The consuming modules never access specific fields of `raw_stats`, so `unknown` values are appropriate.
**Warning signs:** `Element implicitly has an 'any' type` or `Property 'X' does not exist on type 'object'` when someone tries to access `raw_stats.detections` in Phase 21.

### Pitfall 4: `IocType` Does Not Include `"cve"`
**What goes wrong:** Python `IOCType` enum includes `CVE = "cve"` (8 types), but `IOC_PROVIDER_COUNTS` in `main.js` only covers 7 types (no `"cve"`). MalwareBazaar, ThreatFox, and VirusTotal do not support CVE lookup. The `IocType` in the TypeScript constant `IOC_PROVIDER_COUNTS` must only cover the 7 enrichable types.
**Why it happens:** Developers might copy all 8 values from `IOCType` Python enum to the TypeScript `IocType` union, then find `IOC_PROVIDER_COUNTS` doesn't have a `"cve"` entry.
**How to avoid:** Define `IocType` as the 7 enrichable types only (ipv4, ipv6, domain, url, md5, sha1, sha256). CVE IOCs are extracted and displayed but never enriched. If a broader IOC classification union is needed in future, a separate `AllIocType` can include `"cve"`.
**Warning signs:** TypeScript error `Property 'cve' is missing in type` when trying to add `cve` to `IOC_PROVIDER_COUNTS`.

### Pitfall 5: Exporting Constants as `const` Without `export`
**What goes wrong:** `isolatedModules: true` in tsconfig requires each file to be a proper module. A file with only `type` declarations and no `export` will fail with `TS1208: ... cannot be compiled under '--isolatedModules'`.
**Why it happens:** Developers write type declarations without `export`, making the file a script (not a module).
**How to avoid:** Ensure every file in `app/static/src/ts/` has at least one `export`. Both `ioc.ts` and `api.ts` will naturally have `export` statements for their types and constants.
**Warning signs:** `error TS1208: 'ioc.ts' cannot be compiled under '--isolatedModules'`.

### Pitfall 6: `verdict` field in `EnrichmentResultItem` is `VerdictKey`, not `string`
**What goes wrong:** Using `verdict: string` in the interface loses type information. The value is always one of the 5 `VerdictKey` literals as returned by Flask (`malicious`, `suspicious`, `clean`, `no_data`, `error`).
**Why it happens:** Developers default to `string` for API string fields without checking whether a tighter type is available.
**How to avoid:** Use `verdict: VerdictKey` in `EnrichmentResultItem`. Import `VerdictKey` from `./ioc` in `api.ts`. This creates the dependency `api.ts → ioc.ts`, which is the correct direction.
**Warning signs:** Phase 21 modules can't use verdict values to index `VERDICT_LABELS` without casting.

## Code Examples

Verified patterns from codebase sources:

### `app/static/src/ts/types/ioc.ts` — complete file
```typescript
// Domain types and constants for IOC triage.
// These are the TypeScript equivalents of the constants in the legacy main.js.

/**
 * Verdict keys as returned by the Flask enrichment API.
 * Ordered from least to most severe (matches VERDICT_SEVERITY index order).
 */
export type VerdictKey = "error" | "no_data" | "clean" | "suspicious" | "malicious";

/**
 * IOC types supported by the enrichment pipeline.
 * Note: "cve" is extracted but not enriched — excluded from this union.
 */
export type IocType = "ipv4" | "ipv6" | "domain" | "url" | "md5" | "sha1" | "sha256";

/**
 * Verdict severity order — index 0 is least severe, index 4 is most severe.
 * Used to compute the "worst" verdict across multiple providers.
 * Source: main.js line 228.
 */
export const VERDICT_SEVERITY = [
    "error",
    "no_data",
    "clean",
    "suspicious",
    "malicious",
] as const satisfies readonly VerdictKey[];

/**
 * Human-readable display labels for verdict strings.
 * Source: main.js lines 231-237 (UI-06).
 */
export const VERDICT_LABELS: Record<VerdictKey, string> = {
    malicious:  "MALICIOUS",
    suspicious: "SUSPICIOUS",
    clean:      "CLEAN",
    no_data:    "NO DATA",
    error:      "ERROR",
} as const;

/**
 * Expected enrichment provider count per IOC type.
 * VT supports all 7, MB supports hashes, TF supports all 7.
 * Hashes get 3 providers; ipv4/ipv6/domain/url get 2.
 * Source: main.js lines 242-250.
 */
export const IOC_PROVIDER_COUNTS: Record<IocType, number> = {
    ipv4:   2,
    ipv6:   2,
    domain: 2,
    url:    2,
    md5:    3,
    sha1:   3,
    sha256: 3,
} as const;
```

**Note on `satisfies` keyword:** `as const satisfies readonly VerdictKey[]` validates that all array elements are valid `VerdictKey` literals at compile time, while preserving the `readonly tuple` type (not widening to `VerdictKey[]`). This is a TypeScript 4.9+ feature, available in TS 5.8.3. If simpler is preferred, `as const` alone is sufficient — the tuple type is still preserved.

### `app/static/src/ts/types/api.ts` — complete file
```typescript
// API response interfaces for the enrichment polling endpoint.
// Source: app/routes.py _serialize_result + enrichment_status route.
// Source: app/enrichment/models.py EnrichmentResult + EnrichmentError.

import type { VerdictKey } from "./ioc";

/**
 * A successful enrichment result from a TI provider.
 * Matches the "type": "result" branch of _serialize_result in routes.py.
 */
export interface EnrichmentResultItem {
    type: "result";
    ioc_value: string;
    ioc_type: string;
    provider: string;
    verdict: VerdictKey;
    detection_count: number;
    total_engines: number;
    scan_date: string | null;
    raw_stats: Record<string, unknown>;
}

/**
 * An enrichment failure from a TI provider (timeout, auth error, etc.).
 * Matches the "type": "error" branch of _serialize_result in routes.py.
 */
export interface EnrichmentErrorItem {
    type: "error";
    ioc_value: string;
    ioc_type: string;
    provider: string;
    error: string;
}

/**
 * Discriminated union of all possible enrichment result shapes.
 * TypeScript narrows automatically in switch/if blocks on the `type` field.
 */
export type EnrichmentItem = EnrichmentResultItem | EnrichmentErrorItem;

/**
 * Top-level response shape of GET /enrichment/status/{job_id}.
 * Matches the jsonify({...}) call in routes.py enrichment_status.
 */
export interface EnrichmentStatus {
    total: number;
    done: number;
    complete: boolean;
    results: EnrichmentItem[];
}
```

### Verification scratch — demonstrates TYPE-01 and TYPE-02 behavior
```typescript
// This is NOT a file to create — it illustrates what the planner should
// verify in the success criteria test.

import type { VerdictKey } from "./types/ioc";
import { VERDICT_LABELS } from "./types/ioc";

// This MUST be a type error (non-existent verdict key):
// const label = VERDICT_LABELS["invalid"];
// Error: Type '"invalid"' cannot be used as an index type.

// This MUST type-check correctly:
const key: VerdictKey = "malicious";
const label = VERDICT_LABELS[key]; // string — no undefined, key is VerdictKey
```

### Verification scratch — demonstrates TYPE-03 discriminated union narrowing
```typescript
// This is NOT a file to create — it illustrates correct narrowing.

import type { EnrichmentItem } from "./types/api";

function handle(item: EnrichmentItem): void {
    if (item.type === "result") {
        // TypeScript knows: item is EnrichmentResultItem
        const v: VerdictKey = item.verdict; // ok
    } else {
        // TypeScript knows: item is EnrichmentErrorItem
        const e: string = item.error; // ok
        // item.verdict; // compile error — EnrichmentErrorItem has no verdict
    }
}
```

### Existing tsconfig.json (verified — no changes needed)
```json
{
  "compilerOptions": {
    "target": "es2022",
    "lib": ["es2022", "dom", "dom.iterable"],
    "module": "es2022",
    "moduleResolution": "Bundler",
    "strict": true,
    "noEmit": true,
    "isolatedModules": true,
    "noUncheckedIndexedAccess": true,
    "types": [],
    "skipLibCheck": false
  },
  "include": ["app/static/src/ts/**/*.ts"]
}
```
Source: `/home/chris/projects/sentinelx/tsconfig.json` — verified current content. The `include` glob `app/static/src/ts/**/*.ts` already covers the new `types/` subdirectory. No tsconfig changes needed.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `string` for verdict values | Literal union types (`"malicious" \| ...`) | TypeScript 2.0+ literal types (2016) | IDE autocomplete, compile-time typo detection |
| `enum` for string constants | Union types + `as const` | TypeScript 3.4 `as const` (2019) | Zero runtime output; safer narrowing |
| `any` for API responses | Specific interfaces matching backend shape | TypeScript strict mode adoption (2020+) | Type errors caught at development time |
| `!` non-null assertions | Explicit null guard patterns | TypeScript strict community practice | Eliminates silent null reference errors |
| Optional properties for nullable JSON | `field: T \| null` | TypeScript discriminated null practice | Correctly models always-present-but-nullable JSON fields |

**Deprecated/outdated:**
- `enum` for string domains: Generates runtime JS object; union types preferred in modern TypeScript for zero-overhead string literal enforcement
- `type A = string` with JSDoc `@type`: Replaced by proper TypeScript syntax since TS became standard
- `Object.freeze` for runtime constant protection: Unnecessary when `as const` provides compile-time immutability

## Open Questions

1. **Should `IocType` include `"cve"`?**
   - What we know: The Python `IOCType` enum includes `CVE = "cve"`. CVEs appear in extracted IOC lists. The `IOC_PROVIDER_COUNTS` constant in `main.js` does not include `"cve"`. No enrichment provider supports CVE lookup.
   - What's unclear: Future phases may need to handle CVE IOC cards differently in the UI (type filtering, display).
   - Recommendation: Exclude `"cve"` from `IocType` in `IOC_PROVIDER_COUNTS` (matches current JS). If needed, a separate `AllIocType = IocType | "cve"` can be added in a future phase for the filter bar's `data-ioc-type` attribute values.

2. **Should `VERDICT_SEVERITY` be typed as `readonly VerdictKey[]` or preserve the tuple type?**
   - What we know: The `satisfies` keyword (TS 4.9+, available in 5.8) can validate element types while preserving tuple type. Plain `as const` gives a readonly tuple of literals. `as const satisfies readonly VerdictKey[]` gives both.
   - What's unclear: Whether the planner prefers simpler (`as const` alone) or explicit validation (`as const satisfies`).
   - Recommendation: Use `as const` alone in the initial implementation — it's simpler and sufficient. The tuple type is preserved, and TS will error if any non-`VerdictKey` string is added. Add `satisfies` annotation if a future reviewer requests it.

3. **Should `api.ts` import `VerdictKey` using `import type` or regular `import`?**
   - What we know: `isolatedModules: true` requires type-only imports to use `import type` syntax when the import is used only as a type (not as a runtime value).
   - What's unclear: Whether `VerdictKey` is used only as a type in `api.ts` (it is — only in the interface definition).
   - Recommendation: Use `import type { VerdictKey } from "./ioc"` in `api.ts`. This is correct because `VerdictKey` is a type alias (not a value), and `import type` is mandatory under `isolatedModules` for type-only imports to prevent esbuild from including unnecessary runtime imports.

## Validation Architecture

> nyquist_validation is not configured in .planning/config.json — skipping this section.

## Sources

### Primary (HIGH confidence)
- `/home/chris/projects/sentinelx/app/static/main.js` lines 228–250 — `VERDICT_SEVERITY`, `VERDICT_LABELS`, `IOC_PROVIDER_COUNTS` exact values confirmed
- `/home/chris/projects/sentinelx/app/routes.py` `_serialize_result` function — every field name and type in the JSON response confirmed from source
- `/home/chris/projects/sentinelx/app/enrichment/models.py` — `EnrichmentResult` and `EnrichmentError` dataclass fields confirmed
- `/home/chris/projects/sentinelx/app/pipeline/models.py` — `IOCType` Python enum values confirmed (8 types including CVE)
- `/home/chris/projects/sentinelx/tsconfig.json` — verified: `strict: true`, `isolatedModules: true`, `noUncheckedIndexedAccess: true`, `"types": []` all present; no changes needed
- `make typecheck` — verified: exits 0 on current `main.ts` placeholder; TypeScript 5.8.3 installed
- TypeScript Handbook: Literal Types — union type syntax and behavior
- TypeScript Handbook: const assertions — `as const` behavior and tuple type preservation
- TypeScript Handbook: Discriminated Unions — type narrowing with `type` discriminant field
- TypeScript TSConfig Reference: `noUncheckedIndexedAccess` — confirms `Record<K, V>[K]` returns `V` (not `V | undefined`) when key is typed as `K`
- TypeScript TSConfig Reference: `isolatedModules` — confirms `import type` requirement for type-only imports

### Secondary (MEDIUM confidence)
- TypeScript 4.9 `satisfies` operator documentation — `as const satisfies` pattern for dual validation + literal preservation; available in TS 5.8
- TypeScript strict mode community practice — `!` non-null assertion prohibition; explicit guard pattern widely documented

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — TypeScript 5.8.3 installed and verified; no new dependencies
- Architecture: HIGH — type file structure directly derived from codebase audit (main.js, routes.py, models.py); no inference required
- Pitfalls: HIGH — all pitfalls derived from specific tsconfig options (`noUncheckedIndexedAccess`, `isolatedModules`), field optionality in Python models, and domain-specific knowledge (CVE not in provider counts)

**Research date:** 2026-02-28
**Valid until:** 2026-03-28 (TypeScript 5.8 is stable; API shape is locked to Flask backend; no external dependencies)
