# 📦 `workflow` — Deterministic State Machine Runner, Multi-Daemon & Multi-PR Release Curator

> **Author**: `cezartdev`  
> **Version**: `1.3.0`  
> **Status**: `Active`  
> **Interface**: AI Agent Skill & Universal Cross-Platform CLI Runner  
> **Ecosystems Supported**: Python (`uv`/`pytest`), Rust (`cargo`), Go (`go test`), TypeScript/JavaScript (`pnpm`/`bun`/`npm`), Java (`maven`/`gradle`), C# (`dotnet`)

---

## 🎯 Purpose & Overview

The **`workflow`** skill provides a deterministic, state-machine driven development suite for software projects. Encapsulated inside a single modular **`.workflow/`** directory in target repositories, it is fully standardized according to the **[Agent Skills Specification](https://agentskills.io/specification)** and integrates best practices from **[GitHub Spec-Kit](https://github.com/github/spec-kit)** and **[Fission-AI OpenSpec](https://github.com/Fission-AI/OpenSpec)**:

- **Encapsulated `.workflow/` Architecture**: Centralizes all specifications (`.workflow/specs/`), memory (`.workflow/memory/`), configurations (`.workflow/workflow.json`), active daemons (`.workflow/daemons.json`), PRs catalog (`.workflow/prs/`), and worktrees (`.workflow/worktrees/`).
- **Multi-PR Catalog (`.workflow/prs/`)**: Scoped PR generation per archetype (`fix`, `refactor`, `implement`), spec-specific PRs, or unified batch releases stored in `.workflow/prs/active/` and archived to `.workflow/prs/archive/<year>/`.
- **Universal Polyglot Engine (Zero Bias)**: Automatically detects and adapts to Python, Rust, Go, Node, Java, and .NET test runners.
- **Pure-Deterministic Pipelines in Python**: Separates strict logical rules (quality score regex, exit code evaluation, worktree locks) from LLM reasoning to guarantee zero hallucinations in critical logic.
- **Strict Zero-Comments Code Policy**: All autonomous subagents produce 100% clean, self-documenting code without extraneous inline or block comments (`//`, `#`, `/* */`, `""" """`) unless explicitly requested by the developer.
- **Protected Branch Gate & Deterministic Main/Master Isolation**: Automatically intercepts executions triggered while on `main` or `master`, isolates work to a dedicated feature branch, and blocks direct pushes or commits to protected branches.
- **Autonomous Background Daemons (`/workflow daemon`)**: Dispatches subagents on recurring **cron schedules** inside isolated Git Worktrees, with pause, resume, status, and Anti-Zombie cleanup.

---

## 🛠️ Universal Execution Hierarchy

- **Tier 1 (Universal Recommended — Linux, Windows, macOS)**:
  ```bash
  uv run skills/workflow/scripts/workflow_runner.py <subcommand>
  ```
- **Tier 2 (Native Platform Launchers)**:
  - **Linux & macOS (Bash / Zsh)**: `bash skills/workflow/scripts/workflow.sh <subcommand>`
  - **Windows (PowerShell)**: `pwsh skills/workflow/scripts/workflow.ps1 <subcommand>`
- **Tier 3 (Fallback for minimal environments without uv)**:
  - **Linux / macOS**: `python3 skills/workflow/scripts/workflow_runner.py <subcommand>`
  - **Windows**: `python skills/workflow/scripts/workflow_runner.py <subcommand>`

---

## 🚀 CLI Command Reference

### 1. View Universal Catalog & Cheat-Sheet
```bash
uv run skills/workflow/scripts/workflow_runner.py list
```

### 2. Polyglot Initialization & Codebase Exploration
```bash
# Auto-detects stack, test runners, and generates coding_preferences.md and project_context.md
uv run skills/workflow/scripts/workflow_runner.py explore

# Initialize .workflow/ module
uv run skills/workflow/scripts/workflow_runner.py init
```

### 3. Streamlined Project Memory & Indexed Docs
```bash
# View memory catalog (coding_preferences.md, project_context.md, and docs/)
uv run skills/workflow/scripts/workflow_runner.py memory list

# Add a new indexed guideline / documentation note into .workflow/memory/docs/
uv run skills/workflow/scripts/workflow_runner.py memory add auth-rules --content "JWT tokens expire in 15m; use refresh tokens in HttpOnly cookies."
# => Creates: .workflow/memory/docs/01_auth_rules.md

# View a recorded memory note
uv run skills/workflow/scripts/workflow_runner.py memory show 01
```

### 4. Freeform Brainstorming
```bash
uv run skills/workflow/scripts/workflow_runner.py chat
```

### 5. Spec-Driven Development (SDD) & Sequential Pipeline
```bash
# Scaffold new feature spec (defaults to feat)
uv run skills/workflow/scripts/workflow_runner.py new user-login

# Interactive Grilling Session & Socratic co-authoring (Matt Pocock / Spec-Kit style)
uv run skills/workflow/scripts/workflow_runner.py specify user-login

# Decompose into atomic TDD task issues
uv run skills/workflow/scripts/workflow_runner.py plan user-login

# Deterministic Quality Gate audit (100/100 score)
uv run skills/workflow/scripts/workflow_runner.py check user-login

# Primary Engine: Execute deterministic 4-stage sequential subagent pipeline (Fix -> Refactor -> Doc -> Curator)
uv run skills/workflow/scripts/workflow_runner.py run user-login

# Opt-In Recurring Background Execution (runs every 30m with Fixed-Delay):
uv run skills/workflow/scripts/workflow_runner.py run user-login --schedule 30

# Check active pipeline status and worktree metrics:
uv run skills/workflow/scripts/workflow_runner.py status

# Stop active background schedulers & terminate subagents:
uv run skills/workflow/scripts/workflow_runner.py stop user-login

# Deep Anti-Zombie cleanup (purges orphaned worktrees, dangling locks & dead PIDs):
uv run skills/workflow/scripts/workflow_runner.py clean

# Archive completed spec when merged:
uv run skills/workflow/scripts/workflow_runner.py archive user-login
```

### 5. Architectural Decision Records (ADRs) & PR Curation
The Curator subagent (`workflow curate <spec>`) unifies worker contributions on `<spec>-worker` inside `.workflow/worktrees/<spec>/worker/`, verifies test gates, writes a formal **Architectural Decision Record (ADR)** in `.workflow/specs/<namespace>/<spec>/adrs/`, and suggests opening a PR into the base feature branch (`<spec>`):

```bash
# Generate ADR and synthesize PR summary for user-login:
uv run skills/workflow/scripts/workflow_runner.py curate user-login

# Open Pull Request directly on GitHub via gh CLI:
uv run skills/workflow/scripts/workflow_runner.py curate user-login --create-pr

# Scoped Rollup PR: Compile exclusively bug fixes into .workflow/prs/active/
uv run skills/workflow/scripts/workflow_runner.py curate --archetype fix

# Archive a merged PR record:
uv run skills/workflow/scripts/workflow_runner.py curate --archive PR_spec_user_login_20260818_200000.md
```

### 6. Strict Hierarchical Worktrees & Subagent Branch Scoping
Every physical worktree is **strictly dependent on and scoped to a specification and its designated subagent**:
- **Feature / Developer Branch**: Primary implementation takes place directly on `<spec-name>` (e.g., `user-login`).
- **Staging Branch**: Autonomous subagents operate on dedicated staging branch `<spec-name>-worker` inside `.workflow/worktrees/<spec-name>/worker/`.
- **Auto-Merge Scope**: Auto-merge operations target the spec's associated branch (`user-login`), never solely `main`.
- **ADR Audit Trail**: Versioned ADRs stored in `.workflow/specs/<namespace>/<spec>/adrs/ADR_<timestamp>_pipeline_decisions.md`.

```bash
# Execute the full pipeline on-demand:
uv run skills/workflow/scripts/workflow_runner.py run user-login
# => Worktree: .workflow/worktrees/user-login/worker/ (Branch: user-login-worker)
# => Generates ADR in .workflow/specs/features/user-login/adrs/
# => Prepares PR: user-login-worker ➔ user-login
```
