# 📦 `workflow` — Deterministic State Machine Runner & SDD/TDD Engine for AI Agents

> **Author**: `cezartdev`  
> **Version**: `1.0.0`  
> **Status**: `Active`  
> **Interface**: AI Agent Skill & Universal CLI Runner

---

## 🎯 Purpose & Overview

The **`workflow`** skill provides a deterministic, state-machine driven development suite for software projects. Inspired by Matt Pocock's Spec-Driven Development (SDD) and Test-Driven Development (TDD) patterns, it equips AI agents and developers with:

- **Spec-Driven Architecture**: Structured specifications in `specs/<spec-name>/spec.md` decomposed into atomic TDD tasks under `issues/`.
- **Deterministic LangGraph State Engine**: Verifiable state transitions (RED $\rightarrow$ GREEN $\rightarrow$ REFACTOR $\rightarrow$ VERIFY) with checkpointing in `state.json`.
- **Physical Git Worktree Concurrency**: Multi-daemon execution in isolated physical disk directories (`.worktrees/`) preventing file collisions and git index locks.
- **Observable Hierarchical Memory (00-10 Compaction)**: Git-trackable architectural memory (`memory/<archetype>/`) with automatic 10-file sliding window compaction into `00_project_context.md`.
- **Autonomous Codebase Exploration & Tech Drift Detection**: Language-agnostic stack scanner that detects framework migrations (e.g. FastAPI $\rightarrow$ NestJS) and auto-syncs project configuration.

---

## ✨ Features

- 🏗️ **Centralized Skill Templates**: All spec and issue templates are packaged within the skill (`skills/workflow/resources/templates/`), keeping user projects 100% clean of template clutter.
- 🚦 **Pre-Execution Quality Gate (Human-in-the-Loop)**: Audits specs for completeness, acceptance criteria, and edge cases before implementation, offering actionable recommendations.
- 🌲 **Physical Git Worktree Manager**: Full lifecycle management of isolated worktrees with self-healing prune routines to recover from aborted processes.
- 🤖 **Predefined Archetypes & Specialized System Prompts**:
  - `fix`: Surgical bug fixer & auto-healer (`specs/bugs/`, prompt: `fix.prompt.md`).
  - `refactor`: Architecture & code health specialist (`specs/refactor/`, prompt: `refactor.prompt.md`).
  - `implement`: Feature builder (`specs/<feature>/`, prompt: `implement.prompt.md`).
  - `doc-sync`: Documentation & spec synchronizer (`specs/docs/`, prompt: `doc_sync.prompt.md`).
  - `explorer`: Codebase survey scout (`memory/`, prompt: `explorer.prompt.md`).
- 🔄 **Hybrid Orchestration Engine**: Supports both native AI Subagent dispatching and detached background processes/terminals with cron scheduling and safe auto-merge gates.
- ⚙️ **Visible Root Configuration (`workflow.json`)**: Centralized configuration for test commands, daemon schedules, scope limits, and auto-merge policies.

---

## 📥 Installation

Install this skill into your workspace using the standard `skills-cli`:

```bash
npx skills add cezartdev/skills --skill workflow
```

> [!IMPORTANT]
> Always specify the mandatory `--skill workflow` flag when adding this skill to ensure `skills-cli` loads the exact skill path instead of attempting branch matching.

---

## 🛠️ Prerequisites & Environment Setup

- **Python**: Version **3.10+** is required.
- **Git**: Installed and configured.
- **Astral `uv`**: Recommended for dependency management (`langgraph`, `langchain-core`, `pydantic`).

### Environment Diagnostics
Run the diagnostic command to verify your setup:
```bash
python3 skills/workflow/scripts/workflow_runner.py check-env
```

---

## 🚀 CLI Command Reference & Workflows

### 1. Initialize a Project
Scaffold `specs/`, `memory/`, `.gitignore`, and `workflow.json`:
```bash
python3 skills/workflow/scripts/workflow_runner.py init
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

### 4. Create a New Spec
Generate a new spec from embedded templates under the appropriate archetype folder:
```bash
python3 skills/workflow/scripts/workflow_runner.py new 001-payment-gateway --archetype implement
```

### 5. Run Quality Gate Audit
Audit `spec.md` completeness before implementation:
```bash
python3 skills/workflow/scripts/workflow_runner.py check specs/001-payment-gateway
```

### 6. Execute LangGraph TDD DAG
Run the deterministic state machine for a spec:
```bash
python3 skills/workflow/scripts/workflow_runner.py run specs/001-payment-gateway
```

### 7. Run a Background Daemon in an Isolated Worktree
Execute a daemon worker with optional auto-merge into `main`:
```bash
python3 skills/workflow/scripts/workflow_runner.py daemon auto-fixer --auto-merge
```

### 8. Manage Hierarchical Memory
Check memory status or force compaction:
```bash
python3 skills/workflow/scripts/workflow_runner.py memory status
python3 skills/workflow/scripts/workflow_runner.py memory compact --archetype fix
```

---

## 🤖 AI Agent Cognitive Protocol

When invoked via `/workflow`, agents follow this structured execution loop:

```text
1. Read Context: Check 'memory/00_project_context.md' or run 'explore'.
2. Quality Check: Run 'check <spec_path>' and verify acceptance criteria.
3. Worktree Isolation: Run background tasks in '.worktrees/<daemon-name>/'.
4. TDD Cycle:
   - RED: Write failing test.
   - GREEN: Implement minimal code.
   - REFACTOR: Clean code & verify 100% tests pass.
5. Record Memory: Log decision in 'memory/<archetype>/' and compact on threshold.
```
