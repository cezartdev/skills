---
"cezartdev-skills": patch
---

fix(workflow): enforce strict skill immutability and isolate code formatters

- Update `formatter_manager.py` to strictly discover and format only application source files, ignoring `.agents/`, `skills/`, and `.workflow/`.
- Add self-healing rollback in `git_ops.py` (`execute_atomic_commit`) to revert any accidental modifications in `.agents/` before staging.
- Add Skill Immutability & Scope Isolation directives across all subagent prompts.
- Establish rule 16 in `SKILL.md` enforcing zero self-modification of skills during pipeline runs.
