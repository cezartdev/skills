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
> 3. **Deterministic Sequential Subagent Pipeline**: When triggering `/workflow run <spec>`, the AI Agent MUST:
>    - Execute the deterministic 4-stage sequential pipeline in `.workflow/worktrees/<spec>/worker/` on branch `<spec>-worker`:
>      1. **Stage 1 (Fix-Worker)**: Stabilize codebase and guarantee 100% green tests.
>      2. **Stage 2 (Refactor-Worker)**: Clean code and optimize modularity over green tests.
>      3. **Stage 3 (Doc-Worker)**: Synchronize docstrings, OpenAPI schemas, and specifications.
>      4. **Stage 4 (Curator-Worker)**: Run quality gates, generate formal ADR in `.workflow/specs/<namespace>/<spec>/adrs/`, and compile PR summary.
>    - If `--schedule <minutes>` is passed (e.g. 30 or 45), register the Fixed-Delay background timer with the native `schedule` tool.
> 4. **Immediate Stop & Timer Cancellation**: When triggering `/workflow stop [spec|--all]`, the AI Agent MUST:
>    - Execute `uv run skills/workflow/scripts/workflow_runner.py stop [spec]`.
>    - Cancel background schedule cron timers with `manage_task(Action="kill")`.
>    - Terminate active subagents with `manage_subagents(Action="kill", ConversationIds=[...])`.
> 5. **Interactive Test Runner Selection**: When `/workflow init` or `/workflow explore` indicates that no explicit test script is defined in project manifests, the AI Agent MUST prompt the developer using `ask_question` in English to pick from the detected ecosystem candidates (e.g. `pnpm test`, `vitest run`, `jest`).
> 6. **Multi-Machine Host Affinity**: All daemons register their machine fingerprint (`host: user@hostname`). AI Agents and scripts on other machines MUST respect remote workers and NEVER send local OS kill signals or corrupt worktrees belonging to other team members.
> 7. **Fixed-Delay & Zero-Overlap Concurrency Lock**: Daemon intervals operate strictly under a **Fixed-Delay** model (i.e. $N$ minutes counting **after the previous execution finishes**, NEVER overlapping concurrent agents):
>    - Gate 0B rejects overlapping executions if a cycle is actively running (`is_busy: true`).
>    - Gate 0C enforces cooldown until the full $N$ minutes interval has elapsed since `last_completed_at`.
>    - Subagents and host agents complete their current cycle, record `last_completed_at`, and schedule the next cycle using `schedule(DurationSeconds=interval_minutes * 60, Prompt="...")`.
> 8. **Strict Hierarchical Worktrees & Worker Branch Scoping (`.workflow/worktrees/<spec>/worker/`)**: Every physical worktree is **strictly dependent on and scoped to a specification and its designated subagent**:
>    - **Feature / Developer Branch**: Primary implementation takes place directly on `<spec-name>` (e.g. `user-login`).
>    - **Staging Branch**: Autonomous subagents operate on dedicated staging branch `<spec-name>-worker` inside `.workflow/worktrees/<spec-name>/worker/`.
>    - **Auto-Merge Scope**: Automatic merges rebase and target the spec's associated branch (`<spec-name>`), never solely `main`.
>    - **Curator Unification & ADR**: The Curator generates formal Architectural Decision Records (ADRs) in `.workflow/specs/<namespace>/<spec>/adrs/` and suggests a Pull Request merging `<spec-name>-worker` into `<spec-name>`.
> 9. **Interactive Grilling for Branch Selection**: When creating a spec interactively, the AI Agent MUST initiate a question round using `ask_question` allowing the developer to confirm or select their preferred branch name format (`<name>`, `feat/<name>`, `fix/<name>`, `refactor/<name>`, `docs/<name>`, or custom), ensuring alignment before disk operations occur.

---

## 2. Directory Layout (AgentSkills.io Standard)

```text
skills/workflow/
├── SKILL.md                          # [REQUIRED] Skill specification & agent prompt instructions
├── pyproject.toml                    # [OPTIONAL] Python dependencies managed via uv
├── scripts/                          # [OPTIONAL] Executable automation code & launchers
│   ├── workflow_runner.py            # Central CLI entry point with Smart Path Resolver
│   ├── pipeline.py                   # Deterministic 4-stage sequential subagent pipeline runner
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
│   ├── curator.py                    # Multi-PR Curator, ADR generator & scoped release synthesizer
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
| `/workflow new` | `workflow new <spec> [--archetype <type>]` | Scaffold a new spec under `.workflow/specs/` (default: feat) |
| `/workflow specify` | `workflow specify <spec>` | Interactive 1-by-1 Grilling Session to co-author `spec.md` |
| `/workflow plan` | `workflow plan <spec>` | Decompose refined spec into atomic TDD task issues |
| `/workflow check` | `workflow check <spec>` | Audit spec against deterministic Quality Gate (100/100) |
| `/workflow run` | `workflow run <spec> [--schedule <m>]` | **Primary Engine**: Run 4-stage sequential pipeline (Fix -> Refactor -> Doc -> Curator) |
| `/workflow curate` | `workflow curate [spec] [--create-pr]` | Generate ADR, compile PR summary & suggest Pull Request |
| `/workflow status` | `workflow status [spec]` | View active pipeline status, worktrees & scheduled timers |
| `/workflow stop` | `workflow stop [spec]` | Terminate background pipeline subagents and cancel timers |
| `/workflow clean` | `workflow clean` | Deep Anti-Zombie cleanup of orphaned worktrees, locks & dead PIDs |
| `/workflow archive` | `workflow archive <spec>` | Move completed spec to `.workflow/specs/archive/<year>/` |
| `/workflow drift` | `workflow drift [--sync]` | Detect manifest checksum drift & sync tech context |
| `/workflow memory` | `workflow memory <action>` | Manage episodic memory sliding window & 00-10 compaction |
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
