---
name: workflow
description: Deterministic state-machine workflow runner, Spec-Driven Development (SDD), Test-Driven Development (TDD), OWASP Top 10 cybersecurity auditor, streamlined project memory (coding preferences, project context, indexed docs), codebase exploration with tech drift detection, Anti-Zombie multi-daemon physical Git Worktree isolation, and Quality Gatekeeper.
compatibility: Requires Python 3.10+, Git, Astral uv, and GitHub CLI (gh). Works across Linux, Windows (PowerShell/CMD), and macOS. Supports Python, Rust, Go, TypeScript/JavaScript, Java, and .NET.
metadata:
  author: cezartdev
  version: "1.3.0"
---

# Workflow Suite Skill Specification

## 1. Prerequisites & Polyglot Environment (Linux, Windows, macOS)

- **Python Core**: Version **3.10+** executes `scripts/workflow_runner.py`.
- **Git Core**: Version **2.25+** for version control and physical worktree isolation.
- **Astral `uv`**: Ultra-fast Python package manager for virtual environments and runner dependencies (`langgraph`, `langchain-core`, `pydantic`). If `langgraph` is not yet installed, a pure-Python standard library fallback runner executes automatically.
- **GitHub CLI (`gh`)**: Required for reading GitHub issues, opening pull requests (`/workflow quality --create-pr`), and repository automation. Authenticate via `gh auth login` with necessary scopes (`repo`, `workflow`, `read:org`, `read:project`). Verify with `gh auth status` or `/workflow check-env`.
- **Polyglot Stacks Supported**: Automatically adapts to Python (`uv`/`pytest`), Rust (`cargo`), Go (`go test`), TypeScript/JavaScript (`pnpm`/`bun`/`npm`), Java (`maven`/`gradle`), and C# (`dotnet`).
- **Encapsulated Architecture**: All project artifacts reside in the target project's **`.workflow/`** directory (`specs/`, `memory/`, `prs/`, `worktrees/`, `logs/`).
- **Universal Execution (Tier 1 — Recommended across Linux, Windows, macOS)**:
  ```bash
  uv run skills/workflow/scripts/workflow_runner.py <subcommand>
  ```
- **Fallback Execution (Tier 2 — Minimal environments without uv)**:
  - **Linux / macOS**: `python3 skills/workflow/scripts/workflow_runner.py <subcommand>`
  - **Windows**: `python skills/workflow/scripts/workflow_runner.py <subcommand>`

> [!IMPORTANT]
> **MANDATORY AGENT EXECUTION DIRECTIVES**:
> 1. **Deterministic Tool Invocation (NEVER Manual Creation)**: AI Agents MUST ALWAYS invoke workflow commands using `uv run` (e.g. `uv run skills/workflow/scripts/workflow_runner.py <subcommand>` or `uv run .agents/skills/workflow/scripts/workflow_runner.py <subcommand>`). NEVER invoke `python3` or `python` directly, and NEVER attempt to manually write or reconstruct the `.workflow/` directory tree or memory files by hand. Running `workflow init` deterministically creates `.workflow/specs/active/`, `.workflow/specs/archive/`, `.workflow/prs/active/`, `.workflow/prs/archive/`, `.workflow/memory/docs/`, `.workflow/memory/workflow_methodology.md`, analyzes the codebase to generate `.workflow/memory/project_context.md` and `.workflow/memory/coding_preferences.md`, configures `.gitignore`, and updates `AGENTS.md` automatical> 2. **GitHub Spec-Kit SDD Foundation**: The workflow implements 5 deterministic specification stages prior to code execution:
>    - **`specify`** (`/workflow specify <name>`): Author functional `spec.md` focusing strictly on **WHAT** and **WHY** (user stories, scenarios, edge cases, acceptance criteria) without technical implementation details.
>    - **`clarify`** (`/workflow clarify <name>`): Ambiguity Checkpoint detecting omissions and conducting a 1-by-1 Socratic interview using `ask_question`, writing an ADR in `.workflow/specs/active/<name>/adrs/ADR_<timestamp>_clarifications.md`.
>    - **`plan`** (`/workflow plan <name>`): Convert approved `spec.md` into technical design (`plan.md`) defining data models, DB schemas, interfaces, library selection, and architecture.
>    - **`tasks`** (`/workflow tasks <name>`): Decompose `plan.md` into ordered atomic tasks in `tasks.md` and individual issue files under `.workflow/specs/active/<name>/issues/`.
>    - **`analyze`** (`/workflow analyze <name>`): Static consistency audit comparing Constitution/Memory, `spec.md`, `plan.md`, and `tasks.md`, scoring 0-100 before code execution.
> 3. **Deterministic 7-Stage Multi-Subagent Pipeline**: When triggering `/workflow run <spec>`, the AI Agent MUST NOT execute all stages in a single monolithic turn. Instead, the AI Agent MUST:
>    - First run `uv run skills/workflow/scripts/workflow_runner.py run <spec>` to initialize and sync the physical worktree (`.workflow/worktrees/<spec>/worker/`).
>    - Define the 7 specialized subagent types using `define_subagent` (reading their system prompts from `skills/workflow/references/prompts/`):
>      * `workflow-implement-worker` (System prompt: `references/prompts/implement.prompt.md`, `enable_write_tools=True`)
>      * `workflow-fix-worker` (System prompt: `references/prompts/fix.prompt.md`, `enable_write_tools=True`)
>      * `workflow-refactor-worker` (System prompt: `references/prompts/refactor.prompt.md`, `enable_write_tools=True`)
>      * `workflow-security-worker` (System prompt: `references/prompts/security_worker.prompt.md`, `enable_write_tools=True`)
>      * `workflow-quality-worker` (System prompt: `references/prompts/quality.prompt.md`, `enable_write_tools=True`)
>      * `workflow-doc-worker` (System prompt: `references/prompts/doc_sync.prompt.md`, `enable_write_tools=True`)
>      * `workflow-git-worker` (System prompt: `references/prompts/git_worker.prompt.md`, `enable_write_tools=True`)
>    - Sequentially invoke each subagent using `invoke_subagent` so each worker appears distinctly in the agent UI:
>      1. **Stage 1 (Implementer)**: `invoke_subagent(Subagents=[{'TypeName': 'workflow-implement-worker', 'Role': 'Implementer Specialist', 'Prompt': 'Build out spec requirements and task issues for <spec> in .workflow/worktrees/<spec>/worker/. Follow TDD Red-Green cycle and zero-comments policy.'}])`
>      2. **Stage 2 (Fix-Worker)**: `invoke_subagent(Subagents=[{'TypeName': 'workflow-fix-worker', 'Role': 'Fix-Worker Specialist', 'Prompt': 'Diagnose and stabilize tests in .workflow/worktrees/<spec>/worker/'}])`
>      3. **Stage 3 (Refactor-Worker)**: `invoke_subagent(Subagents=[{'TypeName': 'workflow-refactor-worker', 'Role': 'Refactor-Worker Specialist', 'Prompt': 'Refactor modular code and strip redundant comments in worktree while keeping tests green.'}])`
>      4. **Stage 4 (Security-Worker)**: `invoke_subagent(Subagents=[{'TypeName': 'workflow-security-worker', 'Role': 'Cybersecurity Specialist', 'Prompt': 'Audit OWASP Top 10 SAST patterns, secret leaks, and dependency CVEs in worktree.'}])`
>      5. **Stage 5 (Quality-Worker)**: `invoke_subagent(Subagents=[{'TypeName': 'workflow-quality-worker', 'Role': 'Quality Specialist', 'Prompt': 'Audit holistic quality gates (100/100, zero comments, OWASP clearance) and compile ADR in .workflow/specs/active/<spec>/adrs/.'}])`
>         * If Quality-Worker returns `NEEDS_FIX` or `NEEDS_REFACTOR`, loop back to that subagent (up to `max_revisions: 3`).
>      6. **Stage 6 (Doc-Worker)**: `invoke_subagent(Subagents=[{'TypeName': 'workflow-doc-worker', 'Role': 'Doc-Worker Specialist', 'Prompt': 'Sync markdown docs and verify spec acceptance criteria in worktree.'}])`
>      7. **Stage 7 (Git-Worker)**: `invoke_subagent(Subagents=[{'TypeName': 'workflow-git-worker', 'Role': 'Git-Worker Specialist', 'Prompt': 'Conduct interactive Grilling Session confirmation via ask_question with developer. Default Security: Commit locally and do NOT push to remote unless --push flag is passed or explicitly authorized.'}])`
> 4. **Immediate Stop & Timer Cancellation**: When triggering `/workflow stop [spec|--all]`, the AI Agent MUST:
>    - Execute `uv run skills/workflow/scripts/workflow_runner.py stop [spec]`.
>    - Cancel background schedule cron timers with `manage_task(Action="kill")`.
>    - Terminate active subagents with `manage_subagents(Action="kill", ConversationIds=[...])`.
> 5. **Interactive Test Runner Selection**: When `/workflow init` or `/workflow explore` indicates that no explicit test script is defined in project manifests, the AI Agent MUST prompt the developer using `ask_question` in English to pick from the detected ecosystem candidates (e.g. `pnpm test`, `vitest run`, `jest`).
> 6. **Cross-Platform Compatibility**: All scripts support Windows (PowerShell / `uv run`), Linux, and macOS (POSIX shell / `uv run`) using standard library path normalization and pure Python file operations.
> 7. **Cross-Harness Interoperability**: Compatible with all major AI coding agent CLIs and harnesses (Antigravity, Claude Desktop, Cursor, Codex, OpenDevin, Aider, Gemini CLI) complying with the Agent Skills specification (`skills.sh` / `agentskills.io`).
> 8. **Strict Hierarchical Worktrees & Worker Branch Scoping (`.workflow/worktrees/<spec>/worker/`)**: Every physical worktree is **strictly dependent on and scoped to a specification and its designated subagent**:
>    - **Feature / Developer Branch**: Primary implementation takes place directly on `<spec-name>` (e.g. `user-login`) or `feat/<spec-name>`.
>    - **Staging Branch**: Autonomous subagents operate on dedicated staging branch `<spec-name>-worker` inside `.workflow/worktrees/<spec-name>/worker/`.
>    - **Auto-Merge Scope**: Automatic merges rebase and target the spec's associated branch (`feat/<spec-name>` or `<spec-name>`), never solely `main`.
> 9. **Interactive Grilling for Branch Selection**: When creating a spec interactively, the AI Agent MUST initiate a question round using `ask_question` allowing the developer to confirm or select their preferred branch name format (`(Recommended) feat/<name>`, `<name>`, `fix/<name>`, `refactor/<name>`, or custom), ensuring alignment before disk operations occur.
> 10. **Strict Zero-Comments Code Policy**: When writing, editing, or refactoring code in this workflow (across all subagent phases: Implementer, Fix-Worker, Refactor-Worker), AI Agents MUST produce 100% clean, self-documenting code with **ZERO comments**. Inline comments (`//`, `#`), block comments (`/* */`), and unrequested docstrings (`""" """`) are **strictly prohibited**, with the sole exception being when the user explicitly requests comments or documentation annotations.
> 11. **Protected Branch Gate & Grilling on `main`/`master`**: When `/workflow run <spec>` is executed while the active branch is `main` or `master` (or protected branches), direct commits or pushes to `main` are **deterministically blocked**. The pipeline automatically creates and isolates the feature branch `feat/<spec>`. The AI Agent MUST conduct a grilling session using `ask_question` asking the developer to confirm their desired feature branch before any remote push or merge.
> 12. **100% Self-Contained Skill & Zero External Skill Dependency**: The `workflow` skill is completely independent and contains internal tools for Git operations (`git_ops.py`), security scanning (`security_auditor.py`), and PR synthesis. AI Agents MUST NEVER invoke external skills (e.g. `skills/git/`) from within the workflow harness.
> 13. **Default Security Gate (Local Commits by Default)**: By default, all pipeline runs stop after the local commit inside the worktree. Autonomous subagents and CLI commands MUST NOT push to remote `origin` or open public PRs unless the explicit `--push` flag was provided (e.g. `/workflow run <spec> --push`) or the human developer explicitly authorizes remote push during the interactive grilling session.
> 14. **Clean Slash Command Suggestions (`/workflow <subcommand>`)**: When displaying suggested next steps or recommending follow-up actions to the developer in chat or CLI output, AI Agents MUST ALWAYS format them as clean slash commands (e.g., `/workflow explore`, `/workflow new <spec-name>`, `/workflow specify <spec-name>`, `/workflow clarify <spec-name>`, `/workflow plan <spec-name>`, `/workflow tasks <spec-name>`, `/workflow analyze <spec-name>`, `/workflow run <spec-name>`). Never present raw internal script paths as suggested user steps.

---

## 2. Directory Layout (AgentSkills.io Standard)

```text
skills/workflow/
├── SKILL.md                          # [REQUIRED] Skill specification & agent prompt instructions
├── pyproject.toml                    # [OPTIONAL] Python dependencies managed via uv
├── scripts/                          # [OPTIONAL] Executable automation code & runners
│   ├── workflow_runner.py            # Central CLI entry point with Smart Path Resolver
│   ├── pipeline.py                   # Deterministic 7-stage Quality pipeline runner
│   ├── security_auditor.py           # Deterministic OWASP Top 10 SAST, secret scanner & dependency CVE auditor
│   ├── quality.py                    # Quality Gatekeeper, holistic evaluator & ADR generator
│   ├── git_ops.py                    # Self-contained Git engine, security gates & Conventional Commits
│   ├── scaffolder.py                 # Scaffolds .workflow/ structure & specs from assets/
│   ├── explorer.py                   # Polyglot codebase stack & test runner scanner
│   ├── drift_detector.py             # Manifest checksums & tech drift anomaly detector
│   ├── memory_manager.py             # Hierarchical memory manager & indexed docs catalog
│   ├── worktree_manager.py           # Physical Git Worktree lifecycle manager with cross-platform lock clearing
│   ├── quality_auditor.py            # Deterministic Pre-Execution Static Consistency Auditor & Quality Gate
│   └── graph/
│       └── pipeline_graph.py         # Deterministic 7-stage pipeline state machine
├── references/                       # [OPTIONAL] Reference documentation & system prompts read on-demand
│   ├── ARCHITECTURE.md               # In-depth technical architecture guide
│   ├── owasp_top_10.md               # OWASP Top 10 taxonomy & polyglot anti-pattern guide
│   └── prompts/                      # Dedicated archetype system prompts
│       ├── specify.prompt.md         # Functional spec scribe prompt (what & why)
│       ├── clarify.prompt.md         # Ambiguity checkpoint & Socratic griller prompt
│       ├── plan.prompt.md            # Technical design engineer prompt (plan.md)
│       ├── tasks.prompt.md           # Task breakdown specialist prompt (tasks.md & issues/)
│       ├── analyze.prompt.md         # Static consistency auditor prompt
│       ├── implement.prompt.md       # Feature & SDD/TDD Engineer prompt (implement-worker)
│       ├── explorer.prompt.md        # Codebase discovery scout prompt
│       ├── fix.prompt.md             # BugFix & Auto-Heal prompt (fix-worker)
│       ├── refactor.prompt.md        # Architecture & code health prompt (refactor-worker)
│       ├── security_worker.prompt.md # Cybersecurity & OWASP Top 10 audit prompt (security-worker)
│       ├── quality.prompt.md         # Quality Assurance Gatekeeper prompt (quality-worker)
│       ├── doc_sync.prompt.md        # Documentation synchronizer prompt (doc-worker)
│       ├── git_worker.prompt.md      # Deterministic Git & GitHub release prompt (git-worker)
│       └── context.prompt.md         # Business & application domain context curator prompt
└── assets/                           # [OPTIONAL] Templates, schemas, and static resources
    ├── spec.template.md              # Functional Spec template (what & why)
    ├── plan.template.md              # Technical Design Plan template (architecture & schemas)
    ├── tasks.template.md             # Atomic Task Breakdown template
    ├── issue.template.md             # Atomic TDD Issue template (Red -> Green -> Refactor)
    ├── memory_00.template.md         # Initial master context template
    └── workflow_methodology.template.md # Methodology guide template
```

---

## 3. Subcommand Trigger Routing & List Template

When `/workflow list` is requested by the user, the AI Agent MUST respond with this exact concise reference table without verbose conversational filler:

| Slash Command | CLI Syntax | Description |
|---|---|---|
| `/workflow init` | `workflow init [dir]` | Initialize encapsulated `.workflow/` structure & memory |
| `/workflow explore` | `workflow explore [dir]` | Survey polyglot stack & extract style preferences (`coding_preferences.md`) |
| `/workflow new` | `workflow new <spec>` | Scaffold a new feature spec directly under `.workflow/specs/active/<spec>/` |
| `/workflow specify` | `workflow specify <spec>` | Draft functional `spec.md` focusing strictly on what and why |
| `/workflow clarify` | `workflow clarify <spec> [--generate-adr]` | Ambiguity Checkpoint: Socratic Q&A to close specification gaps & generate ADR |
| `/workflow plan` | `workflow plan <spec>` | Convert approved `spec.md` into technical design (`plan.md`) |
| `/workflow tasks` | `workflow tasks <spec>` | Decompose technical plan into atomic tasks (`tasks.md` & `issues/`) |
| `/workflow analyze` | `workflow analyze <spec>` | Auditoría previa: static consistency audit across spec, plan & tasks |
| `/workflow security` | `workflow security [spec] [--json]` | Run OWASP Top 10 SAST, secret leak & dependency CVE audit |
| `/workflow audit-deps` | `workflow audit-deps [dir]` | Audit project package manifests for known CVEs |
| `/workflow quality` | `workflow quality [spec] [--create-pr]` | Quality Gatekeeper: audit quality score & OWASP report, generate ADR |
| `/workflow run` | `workflow run <spec> [--push] [--schedule <m>]` | **Primary Engine**: Run 7-stage subagent pipeline (Implement -> Fix -> Refactor -> Security -> Quality -> Doc -> Git) |
| `/workflow commit` | `workflow commit -t <type> -s <spec> -m <msg>` | Git-Worker deterministic Conventional Commit with pre-commit security gates |
| `/workflow pr` | `workflow pr --spec <spec> [--push]` | Git-Worker deterministic GitHub PR creation via gh CLI (Default: no push; add `--push`) |
| `/workflow status` | `workflow status [spec]` | View active pipeline status, worktrees & security audits |
| `/workflow stop` | `workflow stop [spec]` | Terminate background pipeline subagents and cancel timers |
| `/workflow clean` | `workflow clean` | Deep Anti-Zombie cleanup of orphaned worktrees, locks & dead PIDs |
| `/workflow archive` | `workflow archive <spec>` | Move completed spec to `.workflow/specs/archive/<year>/` |
| `/workflow drift` | `workflow drift [--sync]` | Detect manifest checksum drift & sync tech context |
| `/workflow memory` | `workflow memory [list|add|show]` | Manage methodology, coding preferences, project context & indexed docs |
| `/workflow context` | `workflow context [text]` | Add or view business domain context in `project_context.md` |
| `/workflow check-env` | `workflow check-env` | Diagnostic check of Python $\ge 3.10$, Git, uv, gh CLI, and dependencies |
| `/workflow list` | `workflow list` | Display this concise command reference table |

---

## 4. Agent Execution Protocol

```text
[Multi-Worker & Polyglot Agent Lifecycle]:
1. Survey Stack:
   Run '/workflow explore' to detect Python, Rust, Go, Node, Java, or .NET test runners.
2. Scaffold Spec (SDD):
   Run '/workflow new <name>' directly under '.workflow/specs/active/<name>/'.
3. GitHub Spec-Kit Phased Lifecycle:
   a. Functional Spec: Run '/workflow specify <name>' to draft spec.md (what & why).
   b. Ambiguity Checkpoint: Run '/workflow clarify <name>' for Socratic Q&A and ADR authoring.
   c. Technical Design: Run '/workflow plan <name>' to author plan.md (contracts & schemas).
   d. Tasks Breakdown: Run '/workflow tasks <name>' to generate tasks.md and issues/*.md.
   e. Static Consistency Audit: Run '/workflow analyze <name>' to verify 0 contradictions.
4. Deterministic 7-Stage Quality Pipeline:
   Run '/workflow run <name>'. Implementer -> Fix -> Refactor -> Security -> Quality Gatekeeper -> Doc -> Git-Worker.
5. Interactive Grilling Gate for Release:
   Git-Worker conducts Grilling Session via ask_question with developer before any commit or push.
```stic 7-Stage Quality Pipeline:
   Run '/workflow run <name>'. Implementer -> Fix -> Refactor -> Security -> Quality Gatekeeper -> Doc -> Git-Worker.
5. Interactive Grilling Gate for Release:
   Git-Worker conducts Grilling Session via ask_question with developer before any commit or push.
6. Deterministic Commit & Pull Request:
   Git-Worker executes '/workflow commit' and '/workflow pr' via internal git_ops.py.
```
