---
"cezartdev-skills": patch
---

fix(workflow): strictly enforce feat/<spec> target base branch for pull requests

- Ensure `target_base` in `pipeline.py` and `git_ops.py` always points to `feat/<spec>` and never falls back to `main`.
- Automatically create and push `feat/<spec>` to `origin` when pushing staging changes so that GitHub PRs correctly target the feature mainline branch.
- Emphasize the PR base target invariant in `git_worker.prompt.md`.
