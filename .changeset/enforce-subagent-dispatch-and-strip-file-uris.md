---
"cezartdev-skills": patch
---

fix(workflow): enforce sequential subagent dispatch and strip machine-specific file URIs

- Neutralize local machine `file:///` URIs across `explorer.py` and `quality.py` markdown sanitizers to prevent non-portable links.
- Update `workflow_runner.py run` output to explicitly signal staging readiness and require orchestrator agents to sequentially spawn subagents via `define_subagent` and `invoke_subagent`.
- Filter `subagent_directives` strictly by active stages (`--from`, `--only`) so agents dispatch only relevant workers.
