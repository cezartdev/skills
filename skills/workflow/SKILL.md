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
- **Universal Execution (Tier 1 — Recommended across Linux, Windows, macOS)**:
  ```bash
  uv run skills/workflow/scripts/workflow_runner.py <subcommand>
  ```
- **Native Platform Launchers (Tier 2)**:
  - **Linux / macOS**: `bash skills/workflow/scripts/workflow.sh <subcommand>`
  - **Windows (PowerShell / CMD)**: `pwsh skills/workflow/scripts/workflow.ps1 <subcommand>`
- **Fallback Execution (Tier 3 — Minimal environments without uv)**:
  - **Linux / macOS**: `python3 skills/workflow/scripts/workflow_runner.py <subcommand>`
  - **Windows**: `python skills/workflow/scripts/workflow_runner.py <subcommand>`

> [!IMPORTANT]
> **MANDATORY AGENT EXECUTION DIRECTIVES**:
> 1. **Tool Invocation**: AI Agents MUST ALWAYS invoke workflow commands using `uv run` (e.g. `uv run skills/workflow/scripts/workflow_runner.py <subcommand>` or `uv run .agents/skills/workflow/scripts/workflow_runner.py <subcommand>`). NEVER invoke `python3` or `python` directly.
> 2. **Specify Grilling Session**: When triggering `/workflow specify <name>`, the AI Agent MUST conduct an interactive 1-by-1 Grilling Session using the interactive question tool (e.g., `ask_question`), asking questions sequentially with multiple-choice recommendations and updating `spec.md` in-place after each answer.
> 3. **Native Subagent Dispatch**: When triggering `/workflow daemon start <name>`, the AI Agent MUST immediately invoke its native subagent tool (`invoke_subagent`) passing `TypeName: "self"`, `Role: "<Name> Daemon Specialist"`, and the task prompt targeting `.workflow/worktrees/<name>/`.
> 4. **Interactive Test Runner Selection**: When `/workflow init` or `/workflow explore` indicates that no explicit test script is defined in project manifests, the AI Agent MUST prompt the developer using `ask_question` in English to pick from the detected ecosystem candidates (e.g. `pnpm test`, `vitest run`, `jest`).

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

## 3. Subcommand Trigger Routing & List Template

When `/workflow list` is requested by the user, the AI Agent MUST respond with this exact concise reference table without verbose conversational filler:

| Slash Command | CLI Syntax | Description |
|---|---|---|
| `/workflow init` | `workflow init [dir]` | Initialize encapsulated `.workflow/` structure & configs |
| `/workflow explore` | `workflow explore [dir]` | Survey polyglot stack (Python, Rust, Go, Node, Java, .NET) & update context |
| `/workflow new` | `workflow new <name> [--archetype <type>]` | Scaffold a new spec under `.workflow/specs/` (default: feat) |
| `/workflow specify` | `workflow specify <name>` | Interactive 1-by-1 Grilling Session to co-author `spec.md` |
| `/workflow plan` | `workflow plan <name>` | Decompose refined spec into atomic TDD task issues |
| `/workflow check` | `workflow check <name>` | Audit spec against deterministic Quality Gate (100/100) |
| `/workflow run` | `workflow run <name>` | Execute deterministic LangGraph TDD DAG (Red -> Green -> Refactor) |
| `/workflow archive` | `workflow archive <name>` | Move completed spec to `.workflow/specs/archive/<year>/` |
| `/workflow drift` | `workflow drift [--sync]` | Detect manifest checksum drift & sync tech context |
| `/workflow memory` | `workflow memory <action>` | Manage episodic memory sliding window & 00-10 compaction |
| `/workflow daemon start` | `workflow daemon start [name]` | Start background daemon subagent (`auto-fixer`, `refactor-worker`, `doc-sync`) |
| `/workflow daemon pause` | `workflow daemon pause [name]` | Pause background worker without deleting worktree |
| `/workflow daemon resume` | `workflow daemon resume [name]` | Resume paused background worker execution |
| `/workflow daemon stop` | `workflow daemon stop [name\|--all]` | Terminate background worker & execute Anti-Zombie purge |
| `/workflow daemon status` | `workflow daemon status` | View active daemon health table & execution metrics |
| `/workflow daemon clean` | `workflow daemon clean` | Force purge orphaned worktrees & dead worker PIDs |
| `/workflow curate` | `workflow curate [--archetype <type>]` | Compile scoped PR summary in `.workflow/prs/active/` & open PR |
| `/workflow chat` | `workflow chat [spec]` | Macro architecture brainstorming & scoped spec debate |
| `/workflow check-env` | `workflow check-env` | Diagnostic check of Python $\ge 3.10$, Git, uv, and dependencies |
| `/workflow list` | `workflow list` | Display this concise command reference table |

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
