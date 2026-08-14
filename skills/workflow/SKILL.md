---
name: workflow
description: Deterministic state-machine workflow runner, Spec-Driven Development (SDD), Test-Driven Development (TDD), hierarchical markdown memory with 00-10 compaction, autonomous codebase exploration with tech drift detection, Anti-Zombie multi-daemon physical Git Worktree isolation, and automated Release Curator for Pull Requests.
compatibility: Requires Python 3.10+, Git, and Astral uv. Works across Linux, Windows (PowerShell/CMD), and macOS.
metadata:
  author: cezartdev
  version: "1.2.0"
---

# Workflow Suite Skill Specification

## 1. Prerequisites & Environment (Cross-Platform: Linux, Windows, macOS)

- **Python**: Version **3.10+** is required to execute `scripts/workflow_runner.py`.
- **Dependencies**: Managed via Astral `uv` (`langgraph`, `langchain-core`, `pydantic`). If `langgraph` is not yet installed, a pure-Python standard library fallback runner automatically executes with an identical contract.
- **Encapsulated Architecture**: All project artifacts reside in the target project's **`.workflow/`** directory (`.workflow/workflow.json`, `.workflow/daemons.json`, `.workflow/specs/`, `.workflow/memory/`, `.workflow/worktrees/`, `.workflow/PR_SUMMARY.md`).
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
│   ├── workflow_runner.py            # Central CLI entry point with Smart Path Resolver
│   ├── workflow.ps1                  # Windows PowerShell launcher with auto-bootstrap
│   ├── workflow.sh                   # Linux/macOS POSIX shell launcher
│   ├── scaffolder.py                 # Scaffolds .workflow/ structure & specs from assets/
│   ├── explorer.py                   # Language-agnostic codebase stack scanner
│   ├── drift_detector.py             # Manifest checksums & tech drift anomaly detector
│   ├── memory_manager.py             # Hierarchical 00-10 memory sliding window & compaction engine
│   ├── worktree_manager.py           # Physical Git Worktree lifecycle manager with Anti-Zombie force purge
│   ├── quality_auditor.py            # Pre-execution Quality Gate for spec.md and issues
│   ├── orchestrator.py               # Universal Subagent Dispatch engine
│   ├── daemon_manager.py             # Multi-daemon scheduler with cron & Anti-Zombie cleanup
│   ├── curator.py                    # Release Curator & automated PR synthesizer
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
│       ├── doc_sync.prompt.md        # Documentation synchronizer prompt
│       ├── specify.prompt.md         # Spec Scribe & Socratic Co-Author prompt (Spec-Kit style)
│       ├── chat.prompt.md            # Macro project advisor & brainstorming prompt
│       └── curator.prompt.md         # Release Curator & PR Integrator prompt
└── assets/                           # [OPTIONAL] Templates, schemas, and static resources
    ├── spec.template.md              # Matt Pocock-inspired Spec template
    ├── issue.template.md             # Atomic TDD Issue template (Red -> Green -> Refactor)
    ├── memory_00.template.md         # Initial master context template
    └── workflow.config.json          # Default workflow.json scaffold template
```

---

## 3. Subcommand Trigger Routing

| Trigger / User Request | Subcommand | Workflow Action | Path in Target Project |
|---|---|---|---|
| `/workflow list` | `list [--json]` | Displays universal command catalog and cheat-sheet | Terminal / Chat |
| `/workflow chat [spec]` | `chat` | Freeform project brainstorming (or scoped spec debate) | `.workflow/memory/` |
| `/workflow init` | `init [--test-runner <cmd>]` | Scaffolds `.workflow/`, `.workflow/specs/`, `.workflow/memory/`, `.workflow/workflow.json` | `.workflow/` |
| `/workflow explore` | `explore` | Scans codebase languages, frameworks, test suites & updates `.workflow/memory/00_project_context.md` | `.workflow/memory/` |
| `/workflow drift` | `drift [--sync]` | Detects manifest hash drift; reconciles `.workflow/workflow.json` with framework changes | `.workflow/memory/` |
| `/workflow new <name> [--archetype feat|bug|refactor|doc]` | `new` | Creates new spec folder (defaults to feat $\rightarrow$ `.workflow/specs/features/<name>/`) | `.workflow/specs/` |
| `/workflow specify <spec>` | `specify` | Socratic debate & interactive interview to co-author `spec.md` (GitHub Spec-Kit style) | `.workflow/specs/` |
| `/workflow plan <spec>` | `plan` | Decomposes refined `spec.md` into atomic TDD tasks in `issues/*.md` | `.workflow/specs/` |
| `/workflow check <spec>` | `check` | Pre-Execution Quality Gate: verifies acceptance criteria and edge cases | `.workflow/specs/` |
| `/workflow run <spec>` | `run` | Executes LangGraph DAG state machine (RED $\rightarrow$ GREEN $\rightarrow$ REFACTOR) | `.workflow/specs/` |
| `/workflow archive <name>` | `archive` | Moves completed & merged spec folder to `.workflow/specs/archive/<year>/` | `.workflow/specs/archive/` |
| `/workflow memory <action>` | `memory` | Manages hierarchical memory namespaces (`compact`, `log`, `status`) | `.workflow/memory/<arch>/` |
| `/workflow daemon start <name>` | `daemon start` | Schedules background daemon subagent with cron interval in worktree | `.workflow/worktrees/<name>/` |
| `/workflow daemon stop [name]` | `daemon stop` | Anti-Zombie shutdown: terminates subagent, purges worktrees & locks | `.workflow/worktrees/` |
| `/workflow daemon status` | `daemon status` | Displays active daemon status table, intervals, PIDs, and last results | `.workflow/daemons.json` |
| `/workflow daemon clean` | `daemon clean` | Forcefully purges stale worktrees, dead PIDs, and dangling lockfiles | `.workflow/worktrees/` |
| `/workflow curate` | `curate` | Curator Subagent: consolidates memory decisions, tests, and opens PR | `.workflow/PR_SUMMARY.md` |
| `/workflow worktree <action>` | `worktree` | Manages physical Git Worktrees (`list`, `add`, `clean`, `prune`) | `.workflow/worktrees/` |
| `/workflow check-env` | `check-env` | Diagnostic check of Python $\ge 3.10$, Git, uv, and LangGraph status | None |

---

## 4. Agent Cognitive Process & Execution Protocol

```text
[8-Step Agent Execution Chain]:
1. Explore or Chat:
   Invoke '/workflow chat' to explore architectural options, or '/workflow explore' to survey the stack.
2. Scaffold Spec (SDD):
   Run '/workflow new <name> [--archetype feat|bug|refactor]' to initialize the spec in '.workflow/specs/<namespace>/<name>/'.
3. Debate & Refine Spec (Spec-Kit Style):
   Run '/workflow specify <name>' to conduct Socratic co-authoring on data schemas and acceptance criteria.
4. Plan Atomic Tasks:
   Run '/workflow plan <name>' to generate testable subtasks in 'issues/*.md'.
5. Quality Gate Audit:
   Run '/workflow check <name>' to ensure score reaches 100/100.
6. Deterministic TDD Execution:
   Run '/workflow run <name>' (RED -> GREEN -> REFACTOR).
7. Autonomous Background Daemons:
   Run '/workflow daemon start auto-fixer --interval 10' to resolve bugs asynchronously in isolated worktrees.
8. Release Curation:
   Run '/workflow curate --create-pr' to aggregate all fixes and refactorings into a consolidated Pull Request.
```
