---
name: workflow
description: Deterministic state-machine workflow runner, Spec-Driven Development (SDD), Test-Driven Development (TDD), hierarchical markdown memory with 00-10 compaction, polyglot codebase exploration with tech drift detection, Anti-Zombie multi-daemon physical Git Worktree isolation, and multi-PR Release Curator.
compatibility: Requires Python 3.10+, Git, and Astral uv. Works across Linux, Windows (PowerShell/CMD), and macOS. Supports Python, Rust, Go, TypeScript/JavaScript, Java, and .NET.
metadata:
  author: cezartdev
  version: "1.3.0"
---

# Workflow Suite Skill Specification

## 1. Prerequisites & Polyglot Environment (Linux, Windows, macOS)

- **Python Core**: Version **3.10+** executes `scripts/workflow_runner.py`.
- **Dependencies**: Managed via Astral `uv` (`langgraph`, `langchain-core`, `pydantic`). If `langgraph` is not yet installed, a pure-Python standard library fallback runner executes automatically.
- **Polyglot Stacks Supported**: Automatically adapts to Python (`uv`/`pytest`), Rust (`cargo`), Go (`go test`), TypeScript/JavaScript (`pnpm`/`bun`/`npm`), Java (`maven`/`gradle`), and C# (`dotnet`).
- **Encapsulated Architecture**: All project artifacts reside in the target project's **`.workflow/`** directory (`workflow.json`, `daemons.json`, `specs/`, `memory/`, `prs/`, `worktrees/`).
- **Universal CLI Runners**:
  - **Linux / macOS**:
    ```bash
    bash skills/workflow/scripts/workflow.sh <subcommand>
    # Or directly with Python:
    python3 skills/workflow/scripts/workflow_runner.py <subcommand>
    ```
  - **Windows (PowerShell, CMD, Git Bash)**:
    ```powershell
    pwsh skills/workflow/scripts/workflow.ps1 <subcommand>
    # Or using py / python:
    python skills/workflow/scripts/workflow_runner.py <subcommand>
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
│   ├── explorer.py                   # Polyglot codebase stack & test runner scanner
│   ├── drift_detector.py             # Manifest checksums & tech drift anomaly detector
│   ├── memory_manager.py             # Hierarchical 00-10 memory sliding window & compaction engine
│   ├── worktree_manager.py           # Physical Git Worktree lifecycle manager with Anti-Zombie force purge
│   ├── quality_auditor.py            # Deterministic Pre-Execution Quality Gate
│   ├── orchestrator.py               # Universal Subagent Dispatch engine
│   ├── daemon_manager.py             # Multi-daemon scheduler with cron, pause/resume & Anti-Zombie cleanup
│   ├── curator.py                    # Multi-PR Curator & scoped release synthesizer
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
│       └── curator.prompt.md         # Multi-PR Release Curator prompt
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
| `/workflow init` | `init [--test-runner <cmd>]` | Scaffolds `.workflow/` (specs, memory, prs, worktrees, config) | `.workflow/` |
| `/workflow explore` | `explore` | Scans polyglot stack (Python, Rust, Go, Node, Java, .NET) & updates memory | `.workflow/memory/` |
| `/workflow drift` | `drift [--sync]` | Detects manifest hash drift; reconciles `.workflow/workflow.json` | `.workflow/memory/` |
| `/workflow new <name> [--archetype feat|bug|refactor|doc]` | `new` | Creates new spec folder (defaults to feat $\rightarrow$ `.workflow/specs/features/<name>/`) | `.workflow/specs/` |
| `/workflow specify <spec>` | `specify` | Socratic debate & interactive interview to co-author `spec.md` (GitHub Spec-Kit style) | `.workflow/specs/` |
| `/workflow plan <spec>` | `plan` | Decomposes refined `spec.md` into atomic TDD tasks in `issues/*.md` | `.workflow/specs/` |
| `/workflow check <spec>` | `check` | Deterministic Quality Gate: regex audit of criteria, edge cases & score | `.workflow/specs/` |
| `/workflow run <spec>` | `run` | Executes deterministic LangGraph DAG state machine (RED $\rightarrow$ GREEN $\rightarrow$ REFACTOR) | `.workflow/specs/` |
| `/workflow archive <name>` | `archive` | Moves completed & merged spec folder to `.workflow/specs/archive/<year>/` | `.workflow/specs/archive/` |
| `/workflow memory <action>` | `memory` | Manages hierarchical memory namespaces (`compact`, `log`, `status`) | `.workflow/memory/<arch>/` |
| `/workflow daemon start <name>` | `daemon start` | Schedules background daemon subagent with cron interval in worktree | `.workflow/worktrees/<name>/` |
| `/workflow daemon pause [name]` | `daemon pause` | Suspends cron triggers without destroying worktree state | `.workflow/daemons.json` |
| `/workflow daemon resume [name]` | `daemon resume` | Resumes scheduled cron execution | `.workflow/daemons.json` |
| `/workflow daemon stop [name]` | `daemon stop` | Anti-Zombie shutdown: terminates subagent, purges worktrees & locks | `.workflow/worktrees/` |
| `/workflow daemon status` | `daemon status` | Displays active daemon status table, intervals, PIDs, and health metrics | `.workflow/daemons.json` |
| `/workflow daemon clean` | `daemon clean` | Forcefully purges stale worktrees, dead PIDs, and dangling lockfiles | `.workflow/worktrees/` |
| `/workflow curate` | `curate` | Multi-PR Curator: compiles scoped PR in `.workflow/prs/active/` | `.workflow/prs/active/` |
| `/workflow worktree <action>` | `worktree` | Manages physical Git Worktrees (`list`, `add`, `clean`, `prune`) | `.workflow/worktrees/` |
| `/workflow check-env` | `check-env` | Diagnostic check of Python $\ge 3.10$, Git, uv, and LangGraph status | None |

---

## 4. Agent Execution Protocol

```text
[Multi-PR & Polyglot Agent Lifecycle]:
1. Survey Stack:
   Run '/workflow explore' to detect Python, Rust, Go, Node, Java, or .NET test runners.
2. Scaffold Spec (SDD):
   Run '/workflow new <name> [--archetype feat|bug|refactor]' under '.workflow/specs/'.
3. Socratic Co-Authoring (Spec-Kit Style):
   Run '/workflow specify <name>' to refine data schemas, error handling, and acceptance criteria.
4. Deterministic TDD Execution:
   Run '/workflow run <name>'. Python strictly validates exit codes (RED != 0, GREEN == 0).
5. Background Daemons:
   Run '/workflow daemon start auto-fixer --interval 10' for isolated worktree auto-healing.
6. Multi-PR Release Curation:
   Pause workers with '/workflow daemon pause --all' and run '/workflow curate --archetype fix' or '/workflow curate --all --create-pr' to generate scoped pull requests in '.workflow/prs/active/'.
```
