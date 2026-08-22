---
"cezartdev-skills": patch
---

fix(workflow): support incremental Pull Request updates and automated PR directory archiving

- Automatically update existing open GitHub PRs via `gh pr edit` when repeated pipeline runs deliver new commits for the same specification.
- Archive `.workflow/prs/active/<spec>/` automatically to `.workflow/prs/archive/<year>/<spec>/` upon `/workflow archive <spec>`.
