---
"cezartdev-skills": minor
---

feat(workflow): add --no-worktree flag for in-place pipeline execution without isolated worktrees

- Implement `--no-worktree` option in `workflow run` and `workflow pr` commands to run all 7 pipeline stages directly in the current working directory on the active branch.
- Update `pipeline.py`, `pipeline_graph.py`, and `workflow_runner.py` to support in-place stage sync, branch resolution, and PR targeting when no isolated worktree is created.
- Update `git_worker.prompt.md` and `SKILL.md` documentation to describe `--no-worktree` behavior, branch targeting semantics, and composability with `--only`/`--from`.
