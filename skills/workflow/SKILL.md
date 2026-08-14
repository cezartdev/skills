---
name: workflow
description: Deterministic state-machine workflow runner, Spec-Driven Development (SDD), Test-Driven Development (TDD), hierarchical markdown memory with 00-10 compaction, autonomous codebase exploration with tech drift detection, and multi-daemon physical Git Worktree isolation.
compatibility: Requires Python 3.10+, Git, and Astral uv. Works across Linux, Windows (PowerShell/CMD), and macOS.
metadata:
  author: cezartdev
  version: "1.0.0"
---

# Workflow Suite Skill Specification

## 1. Prerequisites & Environment (Cross-Platform: Linux, Windows, macOS)

- **Python**: Version **3.10+** is required to execute `scripts/workflow_runner.py`.
- **Dependencies**: Managed via Astral `uv` (`langgraph`, `langchain-core`, `pydantic`). If `langgraph` is not yet installed, a pure-Python standard library fallback runner automatically executes with an identical contract.
- **Universal CLI Runners**:
  - **Linux / macOS**:
    ```bash
    bash skills/workflow/scripts/workflow.sh <subcommand>
    # Or directly with Python / uv:
    python3 skills/workflow/scripts/workflow_runner.py <subcommand>
    ```
  - **Windows (PowerShell, CMD, Git Bash)**:
    ```powershell
    pwsh skills/workflow/scripts/workflow.ps1 <subcommand>
    # Or using py / python:
    python skills/workflow/scripts/workflow_runner.py <subcommand>
    ```
- **Environment Diagnostic**:
  ```bash
  python3 skills/workflow/scripts/workflow_runner.py check-env
  ```

---

## 2. Directory Layout (AgentSkills.io Standard)

```text
skills/workflow/
├── SKILL.md                          # [REQUIRED] Skill specification & agent prompt instructions
├── pyproject.toml                    # [OPTIONAL] Python dependencies managed via uv
├── scripts/                          # [OPTIONAL] Executable automation code & launchers
│   ├── workflow_runner.py            # Central CLI entry point (init, explore, drift, memory, new, check, run, daemon, archive, worktree)
│   ├── workflow.ps1                  # Windows PowerShell launcher with auto-bootstrap
│   ├── workflow.sh                   # Linux/macOS POSIX shell launcher
│   ├── scaffolder.py                 # Scaffolds workflow.json & specs from assets/ templates
│   ├── explorer.py                   # Language-agnostic codebase stack scanner
│   ├── drift_detector.py             # Manifest checksums & tech drift anomaly detector
│   ├── memory_manager.py             # Hierarchical 00-10 memory sliding window & compaction engine
│   ├── worktree_manager.py           # Physical Git Worktree lifecycle manager with self-healing prune
│   ├── quality_auditor.py            # Pre-execution Quality Gate for spec.md and issues
│   ├── orchestrator.py               # Hybrid orchestrator for Subagents and background processes
│   ├── daemon_manager.py             # Multi-daemon runner with scheduled cycles & auto-merge
│   └── graph/
│       ├── state.py                  # LangGraph TypedDict state definitions
│       ├── nodes.py                  # LangGraph node transitions (RED, GREEN, REFACTOR, GATES)
│       └── engine.py                 # LangGraph StateGraph builder, checkpointer & runner
├── references/                       # [OPTIONAL] Reference documentation & system prompts read on-demand
│   ├── ARCHITECTURE.md               # In-depth technical architecture guide
│   └── prompts/                      # Dedicated archetype system prompts
│       ├── explorer.prompt.md        # Codebase discovery scout prompt
│       ├── fix.prompt.md             # BugFix & Auto-Heal prompt
│       ├── refactor.prompt.md        # Architecture & code health prompt
│       ├── implement.prompt.md       # Feature builder prompt
│       └── doc_sync.prompt.md        # Documentation synchronizer prompt
└── assets/                           # [OPTIONAL] Templates, schemas, and static resources
    ├── spec.template.md              # Matt Pocock-inspired Spec template
    ├── issue.template.md             # Atomic TDD Issue template (Red -> Green -> Refactor)
    ├── memory_00.template.md         # Initial master context template
    └── workflow.config.json          # Default workflow.json scaffold template
```

---

## 3. Subcommand Trigger Routing

| Trigger / User Request | Subcommand | Workflow Action | Spec Namespace / Directory |
|---|---|---|---|
| `/workflow init` | `init [--test-runner <cmd>]` | Scaffolds `specs/`, `memory/`, `workflow.json`, and runs stack explorer | `specs/` |
| `/workflow explore` | `explore` | Scans codebase languages, frameworks, test suites & updates `memory/00_project_context.md` | `memory/` |
| `/workflow drift` | `drift [--sync]` | Detects manifest hash drift; reconciles `workflow.json` with framework changes | `memory/` |
| `/workflow new <name> --archetype feat` | `new` | Creates new feature spec folder from embedded templates in [assets/spec.template.md](assets/spec.template.md) | `specs/features/<name>/` |
| `/workflow new <name> --archetype fix` | `new` | Creates new bug fix spec folder | `specs/bugs/<name>/` |
| `/workflow new <name> --archetype refactor` | `new` | Creates new refactoring spec folder | `specs/refactor/<name>/` |
| `/workflow check <spec>` | `check` | Pre-Execution Quality Gate: verifies acceptance criteria and edge cases | Scoped |
| `/workflow run <spec>` | `run` | Executes LangGraph DAG state machine (RED $\rightarrow$ GREEN $\rightarrow$ REFACTOR) | Scoped |
| `/workflow daemon <name>` | `daemon` | Runs background worker in physical worktree with archetype prompt & auto-merge | `.worktrees/` |
| `/workflow archive <name>` | `archive` | Moves completed & merged spec folder to `specs/archive/<year>/` | `specs/archive/` |
| `/workflow memory <action>` | `memory` | Manages hierarchical memory namespaces (`compact`, `log`, `status`) | `memory/<archetype>/` |
| `/workflow worktree <action>` | `worktree` | Manages physical Git Worktrees (`list`, `add`, `clean`, `prune`) | `.worktrees/` |
| `/workflow check-env` | `check-env` | Diagnostic check of Python $\ge 3.10$, Git, uv, and LangGraph status | None |

---

## 4. Agent Cognitive Process & Protocol

When managing workflows and tasks, the AI agent MUST follow this structured chain of thought:

```text
[Agent Reflection & Execution Steps]:
1. Check Memory & Stack Context:
   Inspect 'memory/00_project_context.md'. If absent or drifted, execute 'workflow_runner.py explore' to survey the stack.
2. Pre-Execution Quality Audit & Confirmation:
   Run 'workflow_runner.py check <spec_dir>' to ensure acceptance criteria, edge cases, and architecture contracts are defined.
   Prompt user for confirmation or offer recommendations if quality score < 80.
3. Select Execution Strategy & Worktree Isolation:
   - Interactive Task: Execute LangGraph DAG directly or in a worktree.
   - Background Daemon / Multi-Agent: Dispatch dedicated subagents pointing Cwd to '.worktrees/<daemon-name>/'.
4. Enforce Deterministic TDD Transitions:
   - RED: Write failing test, verify failure.
   - GREEN: Implement minimal surgical code to make test pass.
   - REFACTOR: Polish structure, lint, verify 100% tests stay green.
5. Record Decision & Compact Memory:
   Log technical decision in 'memory/<archetype>/XX_<decision>.md'. If 10 files accumulate, trigger automatic compaction.
6. Archive on Completion:
   Run '/workflow archive <name>' to move verified spec to 'specs/archive/<year>/'.
```

See [the architecture guide](references/ARCHITECTURE.md) for detailed state transitions and worktree lifecycle rules.
