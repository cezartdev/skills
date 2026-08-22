---
"cezartdev-skills": patch
---

fix(workflow): implement GitHub CLI readiness validation and graceful PR fallbacks for Git-Worker

- Add `check_gh_readiness()` in `git_ops.py` to validate `gh` installation, `gh auth status`, and remote `origin` configuration.
- Integrate validation gate into `create_github_pull_request()` and Stage 7 (`run_stage_git`) in `pipeline.py`.
- Update `git_worker.prompt.md` system prompt with fallback directives when `gh` is unavailable or unauthenticated.
- Display `gh` readiness status and helpful remediation messages in `/workflow run` summary.
