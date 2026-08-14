---
name: workflow
description: Deterministic state-machine workflow runner, Spec-Driven Development (SDD), Test-Driven Development (TDD), hierarchical markdown memory with 00-10 compaction, autonomous codebase exploration with tech drift detection, and multi-daemon physical Git Worktree isolation encapsulated in .workflow/.
compatibility: Requires Python 3.10+, Git, and Astral uv. Works across Linux, Windows (PowerShell/CMD), and macOS.
metadata:
  author: cezartdev
  version: "1.1.0"
---

# Workflow Suite Skill Specification

## 1. Prerequisites & Environment (Cross-Platform: Linux, Windows, macOS)

- **Python**: Version **3.10+** is required to execute `scripts/workflow_runner.py`.
- **Dependencies**: Managed via Astral `uv` (`langgraph`, `langchain-core`, `pydantic`). If `langgraph` is not yet installed, a pure-Python standard library fallback runner automatically executes with an identical contract.
- **Encapsulated Architecture**: All project artifacts reside in the target project's **`.workflow/`** directory (`.workflow/workflow.json`, `.workflow/specs/`, `.workflow/memory/`, `.workflow/worktrees/`).
- **Universal CLI Runners**:
  - **Linux / macOS**:
    ```bash
    bash skills/workflow/scripts/workflow.sh <subcommand>
    # Or directly with Python / uv:
    python3 skills/workflow/scripts/workflow_runner.py <subcommand>
    ```
  - **Windows (PowerShell, CMD, Git Bash)**:
    ```powershell
    pwsh skills/workflow/scripts/workflow.ps1 <subcommand>
    # Or using py / python:
    python skills/workflow/scripts/workflow_runner.py <subcommand>
    ```
- **Environment Diagnostic**:
  ```bash
  python3 skills/workflow/scripts/workflow_runner.py check-env
  ```

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
│   ├── explorer.py                   # Language-agnostic codebase stack scanner
│   ├── drift_detector.py             # Manifest checksums & tech drift anomaly detector
│   ├── memory_manager.py             # Hierarchical 00-10 memory sliding window & compaction engine
│   ├── worktree_manager.py           # Physical Git Worktree lifecycle manager with self-healing prune
│   ├── quality_auditor.py            # Pre-execution Quality Gate for spec.md and issues
│   ├── orchestrator.py               # Hybrid orchestrator for Subagents and background processes
│   ├── daemon_manager.py             # Multi-daemon runner with scheduled cycles & auto-merge
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
│       └── chat.prompt.md            # Macro project advisor & brainstorming prompt
└── assets/                           # [OPTIONAL] Templates, schemas, and static resources
    ├── spec.template.md              # Matt Pocock-inspired Spec template
    ├── issue.template.md             # Atomic TDD Issue template (Red -> Green -> Refactor)
    ├── memory_00.template.md         # Initial master context template
    └── workflow.config.json          # Default workflow.json scaffold template
```

---

## 3. Subcommand Trigger Routing

| Trigger / User Request | Subcommand | Workflow Action | Path in Target Project |
|---|---|---|---|
| `/workflow list` | `list [--json]` | Displays universal command catalog and cheat-sheet | Terminal / Chat |
| `/workflow chat [spec]` | `chat` | Freeform project brainstorming (or scoped spec debate) | `.workflow/memory/` |
| `/workflow init` | `init [--test-runner <cmd>]` | Scaffolds `.workflow/`, `.workflow/specs/`, `.workflow/memory/`, `.workflow/workflow.json` | `.workflow/` |
| `/workflow explore` | `explore` | Scans codebase languages, frameworks, test suites & updates `.workflow/memory/00_project_context.md` | `.workflow/memory/` |
| `/workflow drift` | `drift [--sync]` | Detects manifest hash drift; reconciles `.workflow/workflow.json` with framework changes | `.workflow/memory/` |
| `/workflow new <name> [--archetype feat|bug|refactor|doc]` | `new` | Creates new spec folder (defaults to feat $\rightarrow$ `.workflow/specs/features/<name>/`) | `.workflow/specs/` |
| `/workflow specify <spec>` | `specify` | Socratic debate & interactive interview to co-author `spec.md` (GitHub Spec-Kit style) | `.workflow/specs/` |
| `/workflow plan <spec>` | `plan` | Decomposes refined `spec.md` into atomic TDD tasks in `issues/*.md` | `.workflow/specs/` |
| `/workflow check <spec>` | `check` | Pre-Execution Quality Gate: verifies acceptance criteria and edge cases | `.workflow/specs/` |
| `/workflow run <spec>` | `run` | Executes LangGraph DAG state machine (RED $\rightarrow$ GREEN $\rightarrow$ REFACTOR) | `.workflow/specs/` |
| `/workflow daemon <name>` | `daemon` | Runs background worker in physical worktree with archetype prompt & auto-merge | `.workflow/worktrees/` |
| `/workflow archive <name>` | `archive` | Moves completed & merged spec folder to `.workflow/specs/archive/<year>/` | `.workflow/specs/archive/` |
| `/workflow memory <action>` | `memory` | Manages hierarchical memory namespaces (`compact`, `log`, `status`) | `.workflow/memory/<arch>/` |
| `/workflow worktree <action>` | `worktree` | Manages physical Git Worktrees (`list`, `add`, `clean`, `prune`) | `.workflow/worktrees/` |
| `/workflow check-env` | `check-env` | Diagnostic check of Python $\ge 3.10$, Git, uv, and LangGraph status | None |

---

## 4. Agent Cognitive Process & Protocol

When managing workflows and tasks, the AI agent MUST follow this structured chain of thought:

```text
[Agent Reflection & Execution Steps]:
1. Explore or Chat:
   If brainstorming, invoke '/workflow chat' to explore architectural options.
   If project context is absent, execute '/workflow explore' to survey the stack into '.workflow/memory/00_project_context.md'.
2. Scaffold Spec (SDD):
   Run '/workflow new <name> [--archetype feat|bug|refactor]' to initialize the spec in '.workflow/specs/<namespace>/<name>/'.
3. Debate & Refine Spec (Spec-Kit Style):
   Run '/workflow specify <name>' to interview the user on data schemas, error handling, and measurable acceptance criteria.
4. Plan Atomic Tasks:
   Run '/workflow plan <name>' to generate testable subtasks in 'issues/*.md'.
5. Quality Gate Audit:
   Run '/workflow check <name>'. Ensure quality score reaches 100/100 before writing implementation code.
6. Enforce Deterministic TDD Transitions:
   - RED: Write failing test, verify failure.
   - GREEN: Implement minimal surgical code to make test pass.
   - REFACTOR: Polish structure, lint, verify 100% tests stay green.
7. Record Decision & Compact Memory:
   Log technical decision in '.workflow/memory/<archetype>/XX_<decision>.md'. Trigger compaction when 10 files accumulate.
8. Archive Completed Spec:
   Run '/workflow archive <name>' to move verified spec to '.workflow/specs/archive/<year>/'.
```

See [the architecture guide](references/ARCHITECTURE.md) for detailed state transitions and worktree lifecycle rules.
