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
> 3. **Native Subagent & Recurring Scheduler Dispatch**: When triggering `/workflow daemon start <name>`, the AI Agent MUST:
>    - Execute `uv run skills/workflow/scripts/workflow_runner.py daemon start <name>`.
>    - Register the recurring cron trigger using the native `schedule` tool (passing `CronExpression: res.cron_expression`, e.g. `*/2 * * * *` or `*/10 * * * *`, and `Prompt: "Execute recurring daemon cycle for <name> inside .workflow/worktrees/<name>/"`) to guarantee that recurring cycles are continuously triggered every interval without stopping.
>    - Invoke the native subagent (`invoke_subagent`) passing `TypeName: "self"`, `Role: "<Name> Daemon Specialist"`, and the continuous task prompt targeting `.workflow/worktrees/<name>/`.
> 4. **Immediate Daemon Stop & Timer Cancellation**: When triggering `/workflow daemon stop [name|--all]`, the AI Agent MUST:
>    - Execute `uv run skills/workflow/scripts/workflow_runner.py daemon stop <name>`.
>    - Check active background tasks via `manage_task(Action="list")` and cancel the scheduled cron timer (`manage_task(Action="kill", TaskId=...)`) immediately.
>    - Terminate any active subagent conversation for that daemon (`manage_subagents(Action="kill", ConversationIds=[...])`).
>    - If a scheduled wakeup prompt is received while `.workflow/daemons.json` marks the daemon as `STOPPED` or `PAUSED`, the agent MUST abort immediately without performing any worktree operations, tests, or code changes.
> 5. **Interactive Test Runner Selection**: When `/workflow init` or `/workflow explore` indicates that no explicit test script is defined in project manifests, the AI Agent MUST prompt the developer using `ask_question` in English to pick from the detected ecosystem candidates (e.g. `pnpm test`, `vitest run`, `jest`).
> 6. **Daemon Blueprint Creation & Configuration Grilling**: When triggering `/workflow daemon create` or `/workflow daemon set` without flags, the AI Agent MUST conduct an interactive Grilling Session using `ask_question` asking sequentially:
>    - Daemon Name (e.g. `security-auditor`, `perf-monitor`).
>    - Archetype persona (`fix`, `refactor`, `implement`, `doc_sync`).
>    - Execution interval in minutes (`5`, `10`, `15`, `30`, `60`).
>    - Max iterations cap (`Unlimited`, `5`, `10`, `20`, `50`).
>    - Responsibilities description.
>    - Then execute `uv run skills/workflow/scripts/workflow_runner.py daemon create ...` or `daemon set ...` with atomic updates to `.workflow/workflow.json`.
> 7. **Multi-Machine Host Affinity**: All daemons register their machine fingerprint (`host: user@hostname`). AI Agents and scripts on other machines MUST respect remote workers and NEVER send local OS kill signals or corrupt worktrees belonging to other team members.
> 8. **Fixed-Delay & Zero-Overlap Concurrency Lock**: Daemon intervals operate strictly under a **Fixed-Delay** model (i.e. $N$ minutes counting **after the previous execution finishes**, NEVER overlapping concurrent agents):
>    - Gate 0B rejects overlapping executions if a cycle is actively running (`is_busy: true`).
>    - Gate 0C enforces cooldown until the full $N$ minutes interval has elapsed since `last_completed_at`.
>    - Subagents and host agents complete their current cycle, record `last_completed_at`, and schedule the next cycle using `schedule(DurationSeconds=interval_minutes * 60, Prompt="...")`.
> 9. **Strict Hierarchical Worktrees & Worker Branch Scoping (`.workflow/worktrees/<spec>/<worker>/`)**: Every physical worktree is **strictly dependent on and scoped to a specification and its assigned subagent**:
>    - **Feature / Developer Branch**: Primary implementation takes place directly on `<spec-name>` (e.g. `user-login`).
>    - **Worker Branches**: Autonomous subagents operate on dedicated worker branches `<spec-name>-<worker-name>` (e.g. `user-login-fix-worker`, `user-login-refactor-worker`, `user-login-doc-worker`, `user-login-curator-worker`).
>    - **Worktree Directory**: Nested format `.workflow/worktrees/<spec-name>/<worker-name>/` (e.g. `.workflow/worktrees/user-login/fix-worker/`, `.workflow/worktrees/user-login/curator-worker/`).
>    - **Auto-Merge Scope**: Automatic merges rebase and target the spec's associated branch (`<spec-name>`), never solely `main`.
>    - **Curator Unification & PR**: The Curator (`workflow curate --spec <spec>`) runs in `.workflow/worktrees/<spec>/curator-worker/` on branch `<spec>-curator-worker`, unifies and orders all worker contributions, executes test gates, and suggests a Pull Request to merge `<spec>-curator-worker` into `<spec-name>`.
> 10. **Interactive Grilling for Branch Selection**: When creating a spec, worktree, or daemon interactively, the AI Agent MUST initiate a question round using `ask_question` allowing the developer to confirm or select their preferred branch name format (`<name>`, `feat/<name>`, `fix/<name>`, `refactor/<name>`, `docs/<name>`, or custom), ensuring alignment before disk operations occur.

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
│       ├── fix.prompt.md             # BugFix & Auto-Heal prompt (fix-worker)
│       ├── refactor.prompt.md        # Architecture & code health prompt (refactor-worker)
│       ├── implement.prompt.md       # Feature builder prompt (feat-worker)
│       ├── doc_sync.prompt.md        # Documentation synchronizer prompt (doc-worker)
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
| `/workflow explore` | `workflow explore [dir]` | Survey polyglot stack & extract style preferences (`00_coding_preferences.md`) |
| `/workflow new` | `workflow new <name> [--archetype <type>]` | Scaffold a new spec under `.workflow/specs/` (default: feat) |
| `/workflow specify` | `workflow specify <name>` | Interactive 1-by-1 Grilling Session to co-author `spec.md` |
| `/workflow plan` | `workflow plan <name>` | Decompose refined spec into atomic TDD task issues |
| `/workflow check` | `workflow check <name>` | Audit spec against deterministic Quality Gate (100/100) |
| `/workflow run` | `workflow run <name>` | Execute deterministic LangGraph TDD DAG (Red -> Green -> Refactor) |
| `/workflow archive` | `workflow archive <name>` | Move completed spec to `.workflow/specs/archive/<year>/` |
| `/workflow drift` | `workflow drift [--sync]` | Detect manifest checksum drift & sync tech context |
| `/workflow memory` | `workflow memory <action>` | Manage episodic memory sliding window & 00-10 compaction |
| `/workflow daemon list` | `workflow daemon list` | Display catalog of configured daemon blueprints & multi-machine status |
| `/workflow daemon create` | `workflow daemon create <name>` | Create a new daemon blueprint in `workflow.json` via interactive Grilling |
| `/workflow daemon set` | `workflow daemon set <name> [--interval <m>]` | Modify daemon schedule interval, max iterations, or archetype |
| `/workflow daemon start` | `workflow daemon start [name]` | Start background daemon subagent (`fix-worker`, `refactor-worker`, `doc-worker`) |
| `/workflow daemon pause` | `workflow daemon pause [name]` | Pause background worker without deleting worktree |
| `/workflow daemon resume` | `workflow daemon resume [name]` | Resume paused background worker execution |
| `/workflow daemon stop` | `workflow daemon stop [name\|--all]` | Terminate background worker & execute Anti-Zombie purge |
| `/workflow daemon status` | `workflow daemon status` | View active daemon health table, host affinity & execution metrics |
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
   Run '/workflow new <name> [--archetype feat|bug|refactor|doc]' under '.workflow/specs/'.
3. Socratic Co-Authoring & Branch Selection (Spec-Kit Style):
   Run '/workflow specify <name>' and confirm branch name via grilling session before planning.
4. Deterministic TDD Execution:
   Run '/workflow run <name>'. Python strictly validates exit codes (RED != 0, GREEN == 0).
5. Background Daemons:
   Run '/workflow daemon start fix-worker --interval 10' for isolated worktree auto-healing.
6. Multi-PR Release Curation:
   Pause workers with '/workflow daemon pause --all' and run '/workflow curate --archetype fix' or '/workflow curate --all --create-pr' to generate scoped pull requests in '.workflow/prs/active/'.
```
