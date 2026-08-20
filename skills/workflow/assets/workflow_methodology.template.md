# Workflow Methodology & Agent Architecture Guide

**Project Name**: `{{PROJECT_NAME}}`  
**Skill Reference**: `skills/workflow/SKILL.md` / `.agents/skills/workflow/SKILL.md`  
**Architecture Spec**: `skills/workflow/references/ARCHITECTURE.md`

---

## 1. Core Operating Philosophy

The project utilizes the **Deterministic Workflow Suite**, a structured harness combining:
1. **Spec-Driven Development (SDD)**: High-precision specifications co-authored via Socratic debate before any code is written.
2. **Test-Driven Development (TDD)**: Deterministic 🔴 RED $\rightarrow$ 🟢 GREEN $\rightarrow$ 🔵 REFACTOR cycles where exit codes govern state transitions.
3. **Deterministic 5-Stage Multi-Worker Pipeline**: Orchestrator-governed pipeline executing specialized roles sequentially with bounded feedback loops.
4. **Physical Git Worktree Isolation**: Staging workspaces isolated in `.workflow/worktrees/<spec>/worker/` protecting the primary repository branch.
5. **Architectural Decision Records (ADRs)**: Continuous, Git-trackable decision auditing co-located in `.workflow/specs/active/<spec>/adrs/`.
6. **Zero Direct Commits & Grilling Session Gates**: Zero unvetted commits or pushes; all releases are confirmed via interactive Grilling Sessions by the `Git-Worker`.
7. **Strict Zero-Comments Code Policy**: Clean, self-documenting code with zero unrequested inline comments, block comments, or docstrings.

---

## 2. Directory Topology & Lifecycle

```text
.workflow/
├── specs/
│   ├── active/                         # Active, in-flight specifications
│   │   └── <spec-name>/                # Feature container
│   │       ├── spec.md                 # Agnostic functional spec & contracts
│   │       ├── issues/                 # Atomic TDD task issues
│   │       ├── adrs/                   # Spec-scoped Architectural Decision Records
│   │       └── state.json              # State machine checkpoint & DAG state
│   └── archive/                        # Completed & merged specifications
│       └── <year>/
├── memory/                             # Persistent Git-trackable memory
│   ├── workflow_methodology.md         # This methodology & execution guide
│   ├── coding_preferences.md           # Linters, conventions & style invariants
│   ├── project_context.md              # Polyglot stack, frameworks & packages
│   └── docs/                           # Sequential indexed notes (01_title.md)
├── prs/
│   ├── active/                         # In-flight PR summaries
│   └── archive/                        # Merged PR records
└── worktrees/                          # Ephemeral staging worktrees (gitignored)
    └── <spec-name>/
        └── worker/                     # Staging workspace (<spec-name>-worker)
```

---

## 3. The 5-Stage Orchestrator-Governed Subagent Pipeline

When `/workflow run <spec>` is triggered, the pipeline executes 5 specialized stages inside `.workflow/worktrees/<spec>/worker/`:

| Stage | Specialist Role | Responsibility |
|---|---|---|
| **Stage 1 (Fix)** | `Fix-Worker Specialist` | Stabilize failing tests, apply surgical bug fixes, and guarantee 100% green builds. |
| **Stage 2 (Refactor)** | `Refactor-Worker Specialist` | Clean code, optimize modularity, reduce complexity, and enforce Zero-Comments policy. |
| **Stage 3 (Orchestrator)** | `Orchestrator Specialist` | Evaluate Quality Gate (100/100), route feedback loops (Fix vs Refactor), and generate ADR. |
| **Stage 4 (Doc)** | `Doc-Worker Specialist` | Synchronize documentation, OpenAPI schemas, and specifications. |
| **Stage 5 (Git-Worker)** | `Git-Worker Specialist` | Conduct Grilling Session confirmation with developer, then execute atomic Conventional Commit and PR. |

---

## 4. Mandatory Directives for AI Agents

1. **Memory Consultation**: Before implementing features or proposing changes, AI agents MUST inspect:
   - `.workflow/memory/project_context.md` for tech stack and runtime constraints.
   - `.workflow/memory/coding_preferences.md` for code style and conventions.
   - `.workflow/memory/docs/` for sequential architecture decisions.
2. **Specification First**: All non-trivial features must have an active specification under `.workflow/specs/active/<spec-name>/`.
3. **Zero-Comments Policy**: Source code must be 100% clean and self-documenting with **ZERO comments** (no `//`, `#`, or `""" """`), unless comments are explicitly requested by the user.
4. **Tool Execution**: Always invoke workflow scripts via `uv run`:
   - `uv run skills/workflow/scripts/workflow_runner.py <subcommand>`
   - `uv run .agents/skills/workflow/scripts/workflow_runner.py <subcommand>`
5. **Skill Instruction Reference**: Always refer to `.agents/skills/workflow/SKILL.md` (or `skills/workflow/SKILL.md`) for full command reference and advanced flags.
