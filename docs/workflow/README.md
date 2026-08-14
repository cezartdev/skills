# 📦 `workflow` — Deterministic State Machine Runner & SDD/TDD Engine for AI Agents

> **Author**: `cezartdev`  
> **Version**: `1.1.0`  
> **Status**: `Active`  
> **Interface**: AI Agent Skill & Universal Cross-Platform CLI Runner

---

## 🎯 Purpose & Overview

The **`workflow`** skill provides a deterministic, state-machine driven development suite for software projects. Encapsulated inside a single modular **`.workflow/`** directory in target repositories, it is fully standardized according to the **[Agent Skills Specification](https://agentskills.io/specification)** and integrates best practices from **[GitHub Spec-Kit](https://github.com/github/spec-kit)** and **[Fission-AI OpenSpec](https://github.com/Fission-AI/OpenSpec)**:

- **Encapsulated `.workflow/` Architecture**: Centralizes all specifications (`.workflow/specs/`), memory (`.workflow/memory/`), configurations (`.workflow/workflow.json`), and worktrees (`.workflow/worktrees/`) in one place.
- **Hierarchical Spec Architecture**: Categorized specifications under `features/`, `bugs/`, `refactor/`, `docs/`, and `archive/`.
- **Spec-Kit Debate & Refinement (`/workflow specify`)**: Interactive Socratic interview session to co-author and refine `spec.md` data models, error handling, and acceptance criteria before writing code.
- **Freeform Architectural Advisor (`/workflow chat`)**: Contextual project brainstorming and scoped spec debate.
- **Universal Cheat-Sheet (`/workflow list`)**: Terminal command catalog and cheat-sheet.
- **Deterministic LangGraph State Engine**: Verifiable TDD state transitions (RED $\rightarrow$ GREEN $\rightarrow$ REFACTOR $\rightarrow$ VERIFY) with checkpointing in `state.json`.
- **Physical Git Worktree Concurrency**: Multi-daemon execution in isolated physical disk directories (`.workflow/worktrees/`) preventing file collisions and git index locks.
- **Observable Hierarchical Memory (00-10 Compaction)**: Git-trackable architectural memory (`.workflow/memory/<archetype>/`) with automatic 10-file sliding window compaction.
- **Autonomous Codebase Exploration & Tech Drift Detection**: Language-agnostic stack scanner with automatic context sync.
- **Cross-Platform Runtime Resilience (Windows, Linux, macOS)**: Native PowerShell (`workflow.ps1`) and POSIX shell (`workflow.sh`) launchers with zero-dependency pure-Python fallback.

---

## ✨ Features

- 🏗️ **Zero Workspace Clutter**: Encapsulates all generated files in `.workflow/` while automatically updating `.gitignore` for `.workflow/worktrees/`.
- 🔍 **Smart Path Resolver**: Commands accept short spec names (e.g. `workflow check 001-payment`) or direct paths interchangeably.
- 📝 **Spec-Kit Co-Authoring (`specify`)**: Audits spec completeness and conducts an interactive interview to achieve a 100/100 Quality Gate score.
- 💬 **Macro Advisor (`chat`)**: Discusses architectural trade-offs, technology choices, and ideas freely before creating specs.
- 📋 **Universal Command Catalog (`list`)**: Instant cheat-sheet of all commands with descriptions and syntax.
- 🌲 **Physical Git Worktree Isolation**: Full lifecycle management with self-healing prune routines to recover from aborted processes.
- 🤖 **Predefined Archetypes & Specialized System Prompts**:
  - `feat` / `implement`: Feature builder (`.workflow/specs/features/`, prompt: `references/prompts/implement.prompt.md`).
  - `fix`: Surgical bug fixer & auto-healer (`.workflow/specs/bugs/`, prompt: `references/prompts/fix.prompt.md`).
  - `refactor`: Architecture & code health specialist (`.workflow/specs/refactor/`, prompt: `references/prompts/refactor.prompt.md`).
  - `doc-sync`: Documentation & spec synchronizer (`.workflow/specs/docs/`, prompt: `references/prompts/doc_sync.prompt.md`).
  - `specify`: Spec Scribe & Co-Author (`.workflow/specs/`, prompt: `references/prompts/specify.prompt.md`).
  - `chat`: Project Advisor & Brainstormer (prompt: `references/prompts/chat.prompt.md`).

---

## 📥 Installation

Install this skill into your workspace using the standard `skills-cli`:

```bash
npx skills add cezartdev/skills --skill workflow
```

> [!IMPORTANT]
> Always specify the mandatory `--skill workflow` flag when adding this skill to ensure `skills-cli` loads the exact skill path instead of attempting branch matching.

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

---

## 🚀 CLI Command Reference & 7-Step Workflow

### 1. View All Commands
```bash
python3 skills/workflow/scripts/workflow_runner.py list
```

### 2. Brainstorm Ideas Freely
```bash
python3 skills/workflow/scripts/workflow_runner.py chat
```

### 3. Initialize Target Project
```bash
python3 skills/workflow/scripts/workflow_runner.py init --test-runner "uv run pytest"
```

### 4. Create a New Spec (Defaults to Feature)
```bash
python3 skills/workflow/scripts/workflow_runner.py new 001-payment-gateway
# Or specify archetype:
python3 skills/workflow/scripts/workflow_runner.py new auth-timeout --archetype bug
```

### 5. Debate & Co-Author Spec Details (Spec-Kit Style)
```bash
python3 skills/workflow/scripts/workflow_runner.py specify 001-payment-gateway
```

### 6. Decompose Tasks into Issues
```bash
python3 skills/workflow/scripts/workflow_runner.py plan 001-payment-gateway
```

### 7. Run Quality Gate Audit
```bash
python3 skills/workflow/scripts/workflow_runner.py check 001-payment-gateway
```

### 8. Execute LangGraph TDD Engine
```bash
python3 skills/workflow/scripts/workflow_runner.py run 001-payment-gateway
```

### 9. Archive Completed Spec
```bash
python3 skills/workflow/scripts/workflow_runner.py archive 001-payment-gateway
```
