# M020 Discussion Log

## Exchange — 2026-05-15T19:24:27.238Z

### Arch

Architecturally, how should M020 organize the aggressive rewrite work?

- **Audit-led rewrites (Recommended)** — Make M020 start by upgrading the audit runner to find rewrite candidates across all seams, then implement ranked changes.
- **Seam-first rewrite** — Begin with a planned architectural split around the known big seams, then use tests/audit proof to validate the rewrite.
- **Subsystem-by-subsystem** — Let each slice independently scout, refactor, and prove one subsystem without a central M020 audit expansion.

**Selected:** Audit-led rewrites (Recommended)

---
## Exchange — 2026-05-15T19:25:53.044Z

### Failures

We can go deep on error handling and failure modes, or I can apply sensible defaults based on the architecture decisions above. Which do you prefer?

- **Use defaults (Recommended)** — I’ll specify practical defaults: fail closed on proof gaps, preserve diagnostics/redaction, and require rollback/revert when behavior proof fails.
- **Go deep** — We’ll spend another round detailing failure behavior for audit generation, rewrites, provider errors, UI failures, and rollback.

**Selected:** Use defaults (Recommended)

---
## Exchange — 2026-05-15T19:27:17.204Z

### Quality

What quality bar should M020 use before calling the aggressive optimization work done?

- **Strict proof bar (Recommended)** — Require audit proof, focused regression tests, fast verification for every change, deep verification for UI/live seams, and final full verification.
- **Faster proof bar** — Use the same proof model but allow final full verification only, reducing repeated verification during implementation.
- **Benchmark-heavy bar** — Add heavier before/after benchmarks for every optimization candidate, even where code-path reasoning would normally suffice.

**Selected:** Strict proof bar (Recommended)

---
## Exchange — 2026-05-15T19:58:39.864Z

### Depth Check

Did I capture the depth right?

- **Yes, you got it (Recommended)** — Proceed to write M020 planning artifacts from the confirmed depth summary.
- **Not quite — let me clarify** — Pause writing and let you correct the milestone depth before artifacts are created.

**Selected:** Yes, you got it (Recommended)

---
