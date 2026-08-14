# Technical Architecture & Reference Guide: `workflow`

This document serves as an in-depth reference for the internal architecture, state machine, and isolation protocols of the **`workflow`** skill.

---

## 1. Specification Lifecycle & Hierarchical Namespaces

Specifications are strictly organized by archetype/intent under `specs/`:

```text
specs/
├── features/     # Feature & capability specifications (implement archetype)
├── bugs/         # Bug fixes and surgical patches (fix archetype)
├── refactor/     # Code health & refactoring (refactor archetype)
├── docs/         # Documentation & OpenAPI syncs (doc-sync archetype)
└── archive/      # Completed & merged specifications (organized by year)
```

Each active specification directory contains:
- `spec.md`: User stories, technical architecture, error handling, and acceptance criteria.
- `state.json`: Deterministic state checkpoint tracking current issue, step, and history.
- `issues/`: Ordered atomic task files (`001_xxx.md`, `002_xxx.md`) following the TDD cycle.

---

## 2. Deterministic LangGraph State Machine

The workflow engine executes a Directed Acyclic Graph (DAG) state machine:

```text
[START]
   │
   ▼
audit_spec_quality   ──► Evaluates acceptance criteria and edge cases
   │
   ▼
plan_issues          ──► Parses or creates ordered atomic tasks in issues/
   │
   ▼
test_red_phase       ──► Writes failing test asserting expected behavior
   │
   ▼
implement_green_phase──► Implements minimal code to make tests pass
   │
   ▼
refactor_phase       ──► Cleans code, lints, ensures 100% tests stay green
   │
   ▼
verify_spec          ──► Validates full suite against spec acceptance criteria
   │
   ▼
[END / COMMIT GATE]
```

---

## 3. Physical Git Worktree Concurrency Model

- **Physical Isolation**: Each background worker operates inside `.worktrees/<daemon-name>/`.
- **Private Index**: Dedicated staging index (`.git/worktrees/<name>/index`) prevents `index.lock` collisions.
- **Dedicated Branch**: Branches use unique names (`workflow/worktree-<name>-<timestamp>`), never checking out `main` directly.
- **Safe Auto-Merge**: Auto-merge to `main` requires 100% test pass and zero security gate violations.

---

## 4. Observable Markdown Memory with 00-10 Compaction

- **`memory/00_project_context.md`**: Master context containing tech stack, invariants, and historical rollup.
- **`memory/<archetype>/01..10_*.md`**: Isolated episodic decision logs per worker.
- **Compaction**: When 10 episodic files accumulate in a namespace, the compaction engine rolls them up into `memory/<archetype>/00_<archetype>_context.md` and safely removes `01..10`.
