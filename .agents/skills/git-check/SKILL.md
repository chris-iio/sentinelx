---
name: git-check
description: Inspect or integrate authorized upstream Git changes that may overlap local work. Never mutate Git state without explicit authorization.
---

# Git Check

Read root `AGENTS.md`.

1. Fetch `origin` and inspect status and branch state.
2. Stop when dirty work overlaps incoming changes; never stash it automatically.
3. Inspect relevant commits, diffs, file and function overlap, and references left
   by upstream moves or deletions.
4. Perform only the authorized integration.

Treat route contracts, provider and secret configuration, SSRF and HTTP-safety
boundaries, diagnostics redaction, SQLite persistence, and browser selector or
state contracts as semantic conflicts. Inspect surrounding merged code, run
focused verification, and stop for product or security decisions.

Report the resulting tip, conflicts, verification, and actual delivery state.
