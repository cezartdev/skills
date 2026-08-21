---
"cezartdev-skills": patch
---

fix(workflow): verify and initialize git repo without commits and create feat branch on new

- Verify and initialize `.git` without creating empty commits in `ensure_git_repository`.
- Implement `create_spec_branch` to create or activate `feat/<spec-name>` on `/workflow new`.
- Hook git repository check into universal command entrypoint and pipeline execution.
