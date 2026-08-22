---
"cezartdev-skills": patch
---

refactor(workflow): unify pipeline delivery flags into clean `--pr` parameter

- Standardize `/workflow run <spec>` delivery flag to `--pr` to open or update GitHub Pull Requests targeting `feat/<spec>`.
- Gracefully alias `--push` and `--create-pr` to `--pr`.
- Update prompt references, command catalog tables, and documentation.
