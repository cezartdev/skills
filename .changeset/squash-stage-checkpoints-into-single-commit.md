---
"cezartdev-skills": patch
---

feat(workflow): automatically squash intermediate checkpoint commits into a single atomic commit

- Implement `squash_stage_checkpoints` in `git_ops.py` to softly reset intermediate `chore(workflow-checkpoint)` commits to the merge base before committing.
- Ensure the final Conventional Commit created by `workflow-git-worker` consolidates all completed stage work with a unified summary body.
- Update `git_worker.prompt.md` instructions and CLI commit flags (`--base-branch`, `--no-squash`).
