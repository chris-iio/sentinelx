# S02: Recovery tooling and safe cleanup — UAT

**Milestone:** M014
**Written:** 2026-04-25T11:22:39.929Z

Preconditions: repo root, Python, Git. Step 1: run make repair-runtime-state and confirm exit 0. Step 2: run the JSON command and confirm machine-readable output. Step 3: run temp-repo tracked-transient and unignored-transient scenarios and confirm deindex/quarantine behavior. Step 4: re-run repair and confirm no-op behavior.
