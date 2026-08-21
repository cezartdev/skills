---
"cezartdev-skills": minor
---

feat(workflow): implement deterministic code auto-formatter, granular pipeline control, git checkpoints, and reactive task sync

- Add `formatter_manager.py` with polyglot support for Biome, Prettier, Ruff, rustfmt, and gofmt.
- Add `--only <stage>`, `--from <stage>`, and `--dry-run` simulation flags to `/workflow run`.
- Add ephemeral Git staging checkpoints and automated rollback in `worktree_manager.py`.
- Add real-time task and acceptance criteria checkbox synchronization in `quality_auditor.py`.
- Guarantee deterministic default branch `feat/<spec>` with zero grilling on `/workflow new`.
