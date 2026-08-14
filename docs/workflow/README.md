# 📦 `workflow` — Deterministic State Machine Runner & SDD/TDD Engine for AI Agents

> **Author**: `cezartdev`  
> **Version**: `1.0.0`  
> **Status**: `Active`  
> **Interface**: AI Agent Skill & Universal Cross-Platform CLI Runner

---

## 🎯 Purpose & Overview

The **`workflow`** skill provides a deterministic, state-machine driven development suite for software projects. Fully standardized according to the **[Agent Skills Specification](https://agentskills.io/specification)**, it draws best practices from **[GitHub Spec-Kit](https://github.com/github/spec-kit)** and **[Fission-AI OpenSpec](https://github.com/Fission-AI/OpenSpec)** to equip AI agents and developers with:

- **Hierarchical Spec Architecture**: Categorized specifications under `specs/features/`, `specs/bugs/`, `specs/refactor/`, `specs/docs/`, and `specs/archive/`.
- **Deterministic LangGraph State Engine**: Verifiable TDD state transitions (RED $\rightarrow$ GREEN $\rightarrow$ REFACTOR $\rightarrow$ VERIFY) with checkpointing in `state.json`.
- **Physical Git Worktree Concurrency**: Multi-daemon execution in isolated physical disk directories (`.worktrees/`) preventing file collisions and git index locks.
- **Observable Hierarchical Memory (00-10 Compaction)**: Git-trackable architectural memory (`memory/<archetype>/`) with automatic 10-file sliding window compaction into `00_project_context.md`.
- **Autonomous Codebase Exploration & Tech Drift Detection**: Language-agnostic stack scanner that detects framework migrations (e.g. FastAPI $\rightarrow$ NestJS) and auto-syncs project configuration.
- **Cross-Platform Runtime Resilience (Windows, Linux, macOS)**: Native PowerShell (`workflow.ps1`) and POSIX shell (`workflow.sh`) launchers with zero-dependency pure-Python fallback.

---

## ✨ Features

- 🏗️ **AgentSkills.io Standard Layout**: Centralized assets in `assets/` (templates) and documentation/prompts in `references/`, keeping user workspaces completely uncluttered.
- 🚦 **Pre-Execution Quality Gate (Human-in-the-Loop)**: Audits specs for completeness, acceptance criteria, and edge cases before implementation, offering actionable recommendations.
- 🌲 **Physical Git Worktree Manager**: Full lifecycle management of isolated worktrees with self-healing prune routines to recover from aborted processes.
- 🤖 **Predefined Archetypes & Specialized System Prompts**:
  - `feat` / `implement`: Feature builder (`specs/features/`, prompt: `references/prompts/implement.prompt.md`).
  - `fix`: Surgical bug fixer & auto-healer (`specs/bugs/`, prompt: `references/prompts/fix.prompt.md`).
  - `refactor`: Architecture & code health specialist (`specs/refactor/`, prompt: `references/prompts/refactor.prompt.md`).
  - `doc-sync`: Documentation & spec synchronizer (`specs/docs/`, prompt: `references/prompts/doc_sync.prompt.md`).
  - `explorer`: Codebase survey scout (`memory/`, prompt: `references/prompts/explorer.prompt.md`).
- 🔄 **Hybrid Orchestration Engine**: Supports both native AI Subagent dispatching and detached background processes/terminals with cron scheduling and safe auto-merge gates.
- 📦 **Specification Archival Lifecycle**: Safely moves completed and merged specs to `specs/archive/<year>/` to maintain an organized active workspace.

---

## 📥 Installation

Install this skill into your workspace using the standard `skills-cli`:

```bash
npx skills add cezartdev/skills --skill workflow
```

> [!IMPORTANT]
> Always specify the mandatory `--skill workflow` flag when adding this skill to ensure `skills-cli` loads the exact skill path instead of attempting branch matching.

---

## 🛠️ Prerequisites & Cross-Platform Launchers

- **Python**: Version **3.10+** (pure stdlib fallback runner built-in; no required pip installs).
- **Git**: Installed and configured.
- **Astral `uv`**: Recommended for automatic Python & dependency management.

### Universal Launchers:
- **Windows (PowerShell)**:
  ```powershell
  pwsh skills/workflow/scripts/workflow.ps1 check-env
  ```
- **Linux & macOS (Bash / Zsh)**:
  ```bash
  bash skills/workflow/scripts/workflow.sh check-env
  ```
- **Direct Python**:
  ```bash
  python3 skills/workflow/scripts/workflow_runner.py check-env
  ```

---

## 🚀 CLI Command Reference & Workflows

### 1. Initialize a Project
Scaffold `specs/` namespaces, `memory/`, `.gitignore`, and `workflow.json`:
```bash
python3 skills/workflow/scripts/workflow_runner.py init --test-runner "uv run pytest"
```

### 2. Survey Codebase & Stack
Scan project languages, frameworks, and test runners to generate `memory/00_project_context.md`:
```bash
python3 skills/workflow/scripts/workflow_runner.py explore
```

### 3. Check for Tech Stack Drift
Verify whether manifest files have changed and sync context:
```bash
python3 skills/workflow/scripts/workflow_runner.py drift --sync
```

### 4. Create a New Feature Spec
Generate a new spec from embedded templates under `specs/features/<name>/`:
```bash
python3 skills/workflow/scripts/workflow_runner.py new 001-payment-gateway --archetype feat
```

### 5. Run Quality Gate Audit
Audit `spec.md` completeness before implementation:
```bash
python3 skills/workflow/scripts/workflow_runner.py check specs/features/001-payment-gateway
```

### 6. Execute LangGraph TDD DAG
Run the deterministic state machine for a spec:
```bash
python3 skills/workflow/scripts/workflow_runner.py run specs/features/001-payment-gateway
```

### 7. Run a Background Daemon in an Isolated Worktree
Execute a daemon worker with optional auto-merge into `main`:
```bash
python3 skills/workflow/scripts/workflow_runner.py daemon auto-fixer --auto-merge
```

### 8. Archive a Completed Spec
Move a completed and verified spec to `specs/archive/<year>/`:
```bash
python3 skills/workflow/scripts/workflow_runner.py archive 001-payment-gateway
```

### 9. Manage Hierarchical Memory
Check memory status or force compaction:
```bash
python3 skills/workflow/scripts/workflow_runner.py memory status
python3 skills/workflow/scripts/workflow_runner.py memory compact --archetype fix
```
