---
"cezartdev-skills": patch
---

refactor(workflow): remove --schedule parameter from run command

- Remove `--schedule` and `--interval` flags and daemon registration from `workflow_runner.py run`.
- Update `pipeline.py`, command catalog tables, help reference, and documentation to reflect clean pipeline execution flags.
