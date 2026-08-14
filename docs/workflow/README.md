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
- **Autonomous Background Daemons (`/workflow daemon`)**: Dispatches subagents on recurring **cron schedules** inside isolated Git Worktrees, with pause, resume, status, and Anti-Zombie cleanup.

---

## 🚀 CLI Command Reference

### 1. View Universal Catalog & Cheat-Sheet
```bash
python3 skills/workflow/scripts/workflow_runner.py list
```

### 2. Polyglot Initialization & Codebase Exploration
```bash
# Auto-detects Python/uv, Rust, Go, Node, Java, or .NET
python3 skills/workflow/scripts/workflow_runner.py explore

# Initialize .workflow/ module
python3 skills/workflow/scripts/workflow_runner.py init
```

### 3. Spec-Driven Development (SDD) Cycle
```bash
# Scaffold new feature spec (defaults to feat)
python3 skills/workflow/scripts/workflow_runner.py new 001-payment-gateway

# Socratic debate & co-authoring (Spec-Kit style)
python3 skills/workflow/scripts/workflow_runner.py specify 001-payment-gateway

# Decompose into atomic TDD task issues
python3 skills/workflow/scripts/workflow_runner.py plan 001-payment-gateway

# Deterministic Quality Gate audit (100/100 score)
python3 skills/workflow/scripts/workflow_runner.py check 001-payment-gateway

# Execute LangGraph TDD state machine (RED -> GREEN -> REFACTOR)
python3 skills/workflow/scripts/workflow_runner.py run 001-payment-gateway

# Archive completed spec
python3 skills/workflow/scripts/workflow_runner.py archive 001-payment-gateway
```

### 4. Background Daemons & Scheduling
```bash
# Start auto-fixer subagent every 10 minutes
python3 skills/workflow/scripts/workflow_runner.py daemon start auto-fixer --interval 10

# Pause daemon cron execution without destroying worktree
python3 skills/workflow/scripts/workflow_runner.py daemon pause auto-fixer

# Resume daemon cron execution
python3 skills/workflow/scripts/workflow_runner.py daemon resume auto-fixer

# View active daemon status table & health metrics
python3 skills/workflow/scripts/workflow_runner.py daemon status

# Stop daemon with Anti-Zombie purge
python3 skills/workflow/scripts/workflow_runner.py daemon stop auto-fixer

# Clean dead PIDs and stale worktree locks
python3 skills/workflow/scripts/workflow_runner.py daemon clean
```

### 5. Multi-PR Release Curation & GitHub PRs
```bash
# Scoped PR: Compile exclusively bug fixes into .workflow/prs/active/
python3 skills/workflow/scripts/workflow_runner.py curate --archetype fix

# Scoped PR: Compile architectural refactorings
python3 skills/workflow/scripts/workflow_runner.py curate --archetype refactor

# Feature PR: Compile a specific spec delivery
python3 skills/workflow/scripts/workflow_runner.py curate --spec 001-payment-gateway

# Master Batch PR: Open directly on GitHub via gh CLI
python3 skills/workflow/scripts/workflow_runner.py curate --create-pr --target-branch main

# Archive a merged PR record
python3 skills/workflow/scripts/workflow_runner.py curate --archive PR_fix_rollup_20260814.md
```

---

## 🛠️ Universal Cross-Platform Launchers

- **Windows (PowerShell)**:
  ```powershell
  pwsh skills/workflow/scripts/workflow.ps1 list
  ```
- **Linux & macOS (Bash / Zsh)**:
  ```bash
  bash skills/workflow/scripts/workflow.sh list
  ```
- **Direct Python**:
  ```bash
  python3 skills/workflow/scripts/workflow_runner.py list
  ```
