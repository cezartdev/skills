---
"cezartdev-skills": patch
---

fix(workflow): strictly forbid manual `gh pr create` and direct `main` targeting in Git subagent

- Enforce `--base` argument requirement in `git_ops.py pr` to prevent accidental defaults to `main`.
- Update `git_worker.prompt.md` and `pipeline.py` Stage 7 subagent directives with strict prohibitions against executing raw `gh pr create` or opening PRs towards `main`.
- Require the Git Subagent to exclusively execute `workflow_runner.py pr <spec-name>` and treat execution as final.
