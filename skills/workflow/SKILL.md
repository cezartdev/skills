---
name: workflow
description: Deterministic state-machine workflow runner, Spec-Driven Development (SDD), Test-Driven Development (TDD), hierarchical markdown memory with 00-10 compaction, autonomous codebase exploration with tech drift detection, and multi-daemon physical Git Worktree isolation.
---

# Workflow Suite Skill Specification

## 1. Prerequisites & Environment (Cross-Platform: Linux, Windows, macOS)

- **Python**: Version **3.10+** is required to execute `scripts/workflow_runner.py`.
- **Dependencies**: Managed via Astral `uv` (`langgraph`, `langchain-core`, `pydantic`). If `langgraph` is not yet installed, a pure-Python deterministic state runner with an identical contract automatically acts as a zero-dependency fallback.
- **Universal CLI Runners**:
  - **Linux / macOS**:
    ```bash
    python3 skills/workflow/scripts/workflow_runner.py <subcommand>
    # Or using uv:
    uv run skills/workflow/scripts/workflow_runner.py <subcommand>
    ```
  - **Windows (PowerShell, CMD, Git Bash)**:
    ```powershell
    python skills/workflow/scripts/workflow_runner.py <subcommand>
    # Or using uv:
    uv run skills/workflow/scripts/workflow_runner.py <subcommand>
    ```
- **Environment Diagnostic**:
  ```bash
  python3 skills/workflow/scripts/workflow_runner.py check-env
  ```

---

## 2. Directory Layout

```text
skills/workflow/
├── SKILL.md                          # [REQUIRED] Skill specification & agent prompt instructions
├── pyproject.toml                    # [OPTIONAL] Python dependencies managed via uv
├── scripts/
│   ├── workflow_runner.py            # Central CLI entry point (init, explore, drift, memory, new, check, run, daemon, worktree)
│   ├── scaffolder.py                 # Scaffolds workflow.json & specs from skill templates
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
└── resources/
    ├── templates/                    # [CENTRALIZED EMBEDDED TEMPLATES]
    │   ├── spec.template.md          # Matt Pocock-inspired Spec template
    │   ├── issue.template.md         # Atomic TDD Issue template (Red -> Green -> Refactor)
    │   ├── memory_00.template.md     # Initial master context template
    │   └── workflow.config.json      # Default workflow.json scaffold template
    └── prompts/                      # [SPECIALIZED ARCHETYPE SYSTEM PROMPTS]
        ├── explorer.prompt.md        # System prompt for 'explorer' subagent
        ├── fix.prompt.md             # System prompt for 'fix' archetype
        ├── refactor.prompt.md        # System prompt for 'refactor' archetype
        ├── implement.prompt.md       # System prompt for 'implement' archetype
        └── doc_sync.prompt.md        # System prompt for 'doc-sync' archetype
```

---

## 3. Subcommand Trigger Routing

| Trigger / User Request | Subcommand | Workflow Action | Worktree Isolation |
|---|---|---|---|
| `/workflow init` | `init` | Scaffolds `specs/`, `memory/`, `workflow.json`, and runs stack explorer | ❌ Main Workspace |
| `/workflow explore` | `explore` | Scans codebase languages, frameworks, test suites & updates `memory/00_project_context.md` | ❌ Main Workspace |
| `/workflow drift` | `drift [--sync]` | Detects manifest hash drift; reconciles `workflow.json` with framework changes | ❌ Main Workspace |
| `/workflow new <name>` | `new` | Creates new spec folder `specs/<name>/` directly from embedded skill templates | ❌ Main Workspace |
| `/workflow check <spec>` | `check` | Pre-Execution Quality Gate: verifies acceptance criteria and edge cases | ❌ None |
| `/workflow run <spec>` | `run` | Executes LangGraph DAG state machine (RED $\rightarrow$ GREEN $\rightarrow$ REFACTOR) | Optional / Yes |
| `/workflow daemon <name>` | `daemon` | Runs background worker in physical worktree with archetype prompt & auto-merge | ✅ `.worktrees/` |
| `/workflow memory <action>` | `memory` | Manages hierarchical memory namespaces (`compact`, `log`, `status`) | ❌ / ✅ Scoped |
| `/workflow worktree <action>` | `worktree` | Manages physical Git Worktrees (`list`, `add`, `clean`, `prune`) | ✅ `.worktrees/` |
| `/workflow check-env` | `check-env` | Diagnostic check of Python $\ge 3.10$, Git, uv, and LangGraph status | ❌ None |

---

## 4. Agent Cognitive Process & Protocol

When managing workflows and tasks, the AI agent MUST follow this structured chain of thought:

```text
[Agent Reflection & Execution Steps]:
1. Check Memory & Stack Context:
   Inspect 'memory/00_project_context.md'. If absent or drifted, execute 'workflow_runner.py explore' to survey the stack.
2. Pre-Execution Quality Audit & Confirmation:
   Run 'workflow_runner.py check <spec_dir>' to ensure acceptance criteria, edge cases, and architecture contracts are defined.
   Prompt user for confirmation or offer recommendations if quality score < 80.
3. Select Execution Strategy & Worktree Isolation:
   - Interactive Task: Execute LangGraph DAG directly or in a worktree.
   - Background Daemon / Multi-Agent: Dispatch dedicated subagents pointing Cwd to '.worktrees/<daemon-name>/'.
4. Enforce Deterministic TDD Transitions:
   - RED: Write failing test, verify failure.
   - GREEN: Implement minimal surgical code to make test pass.
   - REFACTOR: Polish structure, lint, verify 100% tests stay green.
5. Record Decision & Compact Memory:
   Log technical decision in 'memory/<archetype>/XX_<decision>.md'. If 10 files accumulate, trigger automatic compaction.
```

---

## 5. Multi-Daemon Physical Worktree Architecture

To achieve zero-collision concurrency, background agents run strictly inside **physical disk directories** created via `git worktree add`:

- **Dedicated Directory**: `.worktrees/<daemon-name>/` (added to `.gitignore`).
- **Independent Index**: Private staging index eliminates `index.lock` collisions.
- **Dedicated Archetypes & Prompts**:
  - `fix`: BugFix specialist (`specs/bugs/`, prompt: `fix.prompt.md`).
  - `refactor`: Architecture specialist (`specs/refactor/`, prompt: `refactor.prompt.md`).
  - `implement`: Feature builder (`specs/<feature>/`, prompt: `implement.prompt.md`).
  - `doc-sync`: Documentation keeper (`specs/docs/`, prompt: `doc_sync.prompt.md`).

---

## 6. Hierarchical Markdown Memory & Compaction Protocol

- **Global Master**: `memory/00_project_context.md` stores tech stack, invariants, and high-level rollup.
- **Archetype Namespaces**: `memory/<archetype>/01..10_*.md` records isolated episodic decisions per worker.
- **Compaction**: When 10 episodic files accumulate, the engine synthesizes them into `memory/<archetype>/00_<archetype>_context.md` and safely prunes episodic files.
