---
"cezartdev-skills": minor
---

feat(workflow): implement dedicated /workflow pr subcommand

- Add `/workflow pr <spec>` CLI command to directly create or update GitHub Pull Requests targeting `feat/<spec>` with canonical summary documents.
- Support `--title` and `--no-push` flags, with automated branch verification and `gh` readiness checks.
- Register `/workflow pr` in command catalog, help outputs, and documentation.
