---
estimated_steps: 2
estimated_files: 2
skills_used: []
---

# T02: Frontend config fixes — tsconfig incremental + tailwind email safelist (R024)

**Slice:** S04 — Test DRY-up — shared adapter fixtures
**Milestone:** M004

## Description

R024 requires three config fixes: (1) `tsconfig.json` must include `"incremental": true` to avoid full re-typechecks on every `make typecheck`, (2) the Tailwind safelist must include `ioc-type-badge--email` and `filter-pill--email` (including active variant) — these classes were added in M003/S02 for email IOC support but never safelisted, so Tailwind purges them in production builds. The `dist/main.js` content glob issue from R024 is already resolved (not present in current config).

## Steps

1. **Add `"incremental": true` to `tsconfig.json`** — insert into `compilerOptions` object. Current compilerOptions:
   ```json
   {
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
   }
   ```
   Add `"incremental": true` after `"skipLibCheck": false`. Note: `incremental` works with `noEmit` in TypeScript 5+ (requires `tsBuildInfoFile` or uses default `.tsbuildinfo`).

2. **Add email safelist entries to `tailwind.config.js`** — add these entries to the `safelist` array, near the existing `ioc-type-badge--*` and `filter-pill--*` entries:
   - `"ioc-type-badge--email"` — after the other `ioc-type-badge--*` entries (after `ioc-type-badge--cve`)
   - `"filter-pill--email"` — after the other `filter-pill--*` entries (after `filter-pill--cve`)

## Must-Haves

- [ ] `tsconfig.json` compilerOptions includes `"incremental": true`
- [ ] `tailwind.config.js` safelist includes `ioc-type-badge--email`
- [ ] `tailwind.config.js` safelist includes `filter-pill--email`
- [ ] `npx tsc --noEmit` exits cleanly (0)

## Verification

- `grep -q '"incremental": true' tsconfig.json && echo OK` — must print OK
- `grep -q "ioc-type-badge--email" tailwind.config.js && echo OK` — must print OK
- `grep -q "filter-pill--email" tailwind.config.js && echo OK` — must print OK
- `npx tsc --noEmit` — must exit 0

## Inputs

- `tsconfig.json` — current TypeScript config, needs `incremental` added
- `tailwind.config.js` — current Tailwind config, needs email safelist entries

## Expected Output

- `tsconfig.json` — updated with `"incremental": true`
- `tailwind.config.js` — updated with email safelist entries

## Observability Impact

- **TypeScript incremental build**: After this change, `npx tsc --noEmit` generates a `.tsbuildinfo` file that caches type-check state. Subsequent runs are faster. If a future task sees stale type errors after structural changes, delete `.tsbuildinfo` and re-run.
- **Tailwind email classes**: `ioc-type-badge--email` and `filter-pill--email` are now preserved through Tailwind's purge step. If email IOC badges or filter pills disappear in production builds, check `tailwind.config.js` safelist. Diagnostic: `npx tailwindcss --content ./app/templates/**/*.html -o /dev/null --minify 2>&1 | grep -c email` or inspect the generated CSS for the class names.
- **Failure state**: If `npx tsc --noEmit` fails after this change, the `.tsbuildinfo` cache may be stale — delete it and retry. If Tailwind classes are missing, `grep "email" tailwind.config.js` confirms safelist presence.
