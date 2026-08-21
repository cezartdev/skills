---
"cezartdev-skills": patch
---

fix(workflow): eliminate .gitkeep files and enforce deterministic runtime directory creation

- Remove all `.gitkeep` file creation across `.workflow/` directory tree and specification folders.
- Implement `ensure_workflow_directories()` and `ensure_spec_directories()` in `scaffolder.py` to deterministically create any missing directories on demand.
- Hook directory verification into command dispatch and pipeline initialization to handle fresh repository clones where empty directories were not tracked.
