# 📦 `workflow` — Deterministic State Machine Runner, SDD/TDD Engine, Multi-Daemon & Release Curator

> **Author**: `cezartdev`  
> **Version**: `1.2.0`  
> **Status**: `Active`  
> **Interface**: AI Agent Skill & Universal Cross-Platform CLI Runner

---

## 🎯 Purpose & Overview

The **`workflow`** skill provides a deterministic, state-machine driven development suite for software projects. Encapsulated inside a single modular **`.workflow/`** directory in target repositories, it is fully standardized according to the **[Agent Skills Specification](https://agentskills.io/specification)** and integrates best practices from **[GitHub Spec-Kit](https://github.com/github/spec-kit)** and **[Fission-AI OpenSpec](https://github.com/Fission-AI/OpenSpec)**:

- **Encapsulated `.workflow/` Architecture**: Centralizes all specifications (`.workflow/specs/`), memory (`.workflow/memory/`), configurations (`.workflow/workflow.json`), active daemons (`.workflow/daemons.json`), and worktrees (`.workflow/worktrees/`).
- **Spec-Kit Debate & Refinement (`/workflow specify`)**: Interactive Socratic interview session to co-author and refine `spec.md` data models, error handling, and acceptance criteria before writing code.
- **Autonomous Background Daemons (`/workflow daemon`)**: Dispatches subagents on recurring **cron schedules** (e.g. every 10 minutes) inside isolated physical Git Worktrees, with instant idle detection and conditional auto-merge to `main`.
- **Anti-Zombie & Deep Cleanup Protocol**: 3-phase shutdown guarantees zero orphaned background processes, zero zombie tasks, and zero dangling Git lockfiles (`.git/index.lock`).
- **Release Curator Subagent (`/workflow curate`)**: Aggregates all memory decisions (fixes, refactors, features), verifies test suite health, and compiles executive-level Pull Requests (`.workflow/PR_SUMMARY.md` / `gh pr create`).
- **Universal Cross-CLI Subagent Dispatch**: Seamlessly generates directives for **Antigravity, Claude Code, Cursor, Codex, and Headless CI**.

---

## 🚀 CLI Command Reference

### 1. View Universal Catalog & Cheat-Sheet
```bash
python3 skills/workflow/scripts/workflow_runner.py list
```

### 2. Freeform Brainstorming
```bash
python3 skills/workflow/scripts/workflow_runner.py chat
```

### 3. Initialize Target Project
```bash
python3 skills/workflow/scripts/workflow_runner.py init --test-runner "uv run pytest"
```

### 4. Spec-Driven Development (SDD) Cycle
```bash
# Scaffold new feature spec (defaults to feat)
python3 skills/workflow/scripts/workflow_runner.py new 001-payment-gateway

# Socratic debate & co-authoring (Spec-Kit style)
python3 skills/workflow/scripts/workflow_runner.py specify 001-payment-gateway

# Decompose into atomic TDD task issues
python3 skills/workflow/scripts/workflow_runner.py plan 001-payment-gateway

# Quality Gate audit
python3 skills/workflow/scripts/workflow_runner.py check 001-payment-gateway

# Execute LangGraph TDD state machine (RED -> GREEN -> REFACTOR)
python3 skills/workflow/scripts/workflow_runner.py run 001-payment-gateway

# Archive completed spec
python3 skills/workflow/scripts/workflow_runner.py archive 001-payment-gateway
```

### 5. Autonomous Background Daemons & Cron Jobs
```bash
# Start auto-fixer subagent every 10 minutes
python3 skills/workflow/scripts/workflow_runner.py daemon start auto-fixer --interval 10

# Start refactor worker subagent every 30 minutes
python3 skills/workflow/scripts/workflow_runner.py daemon start refactor-worker --interval 30

# View active daemon status table & health metrics
python3 skills/workflow/scripts/workflow_runner.py daemon status

# Stop a specific daemon with Anti-Zombie purge
python3 skills/workflow/scripts/workflow_runner.py daemon stop auto-fixer

# Stop ALL running daemons simultaneously
python3 skills/workflow/scripts/workflow_runner.py daemon stop --all

# Clean all dead PIDs and stale worktree locks
python3 skills/workflow/scripts/workflow_runner.py daemon clean
```

### 6. Release Curation & Automated Pull Requests
```bash
# Compile PR summary from all recent memory logs
python3 skills/workflow/scripts/workflow_runner.py curate

# Compile summary and open GitHub Pull Request directly
python3 skills/workflow/scripts/workflow_runner.py curate --create-pr --target-branch main
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
