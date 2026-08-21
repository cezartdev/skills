---
"cezartdev-skills": patch
---

fix(workflow): harden worktree sandboxing, test command whitelist, and non-destructive sync for Socket compliance

- Enforce mathematical commonpath validation and strict sandbox bounds on `resolve_worktree_path` in `worktree_manager.py`.
- Replace history-rewriting git rebase with non-destructive merge in `sync_worktree_with_base`.
- Implement developer tool whitelist and forbidden shell operator filtering in `safe_run_test_command`.
- Apply `shlex.quote` across all suggested PR and Git command strings.
