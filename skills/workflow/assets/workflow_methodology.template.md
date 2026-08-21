# Workflow Methodology & Agent Architecture Guide

**Project Name**: `{{PROJECT_NAME}}`  
**Skill Reference**: `skills/workflow/SKILL.md` / `.agents/skills/workflow/SKILL.md`  
**Architecture Spec**: `skills/workflow/references/ARCHITECTURE.md`

---

## 1. Core Operating Philosophy

The project utilizes the **Deterministic Workflow Suite**, a structured harness combining:
1. **GitHub Spec-Kit Phased Lifecycle**: 5 deterministic specification stages prior to code execution:
   - `specify`: Functional specification focusing strictly on WHAT and WHY.
   - `clarify`: Ambiguity Checkpoint & Socratic Q&A closing gaps with ADR records.
   - `plan`: Technical design (Architecture, Schemas & API contracts).
   - `tasks`: Atomic task decomposition (Dependency graphs & issues/).
   - `analyze`: Auditoría previa (Static consistency audit).
2. **Test-Driven Development (TDD)**: Deterministic 🔴 RED $\rightarrow$ 🟢 GREEN $\rightarrow$ 🔵 REFACTOR cycles where exit codes govern state transitions.
3. **Deterministic 7-Stage Multi-Worker Pipeline**: Quality-governed pipeline executing specialized roles sequentially with bounded feedback loops.
4. **OWASP Top 10 Cybersecurity Baseline**: Integrated SAST, secret leak scanner, and dependency vulnerability verification.
5. **Physical Git Worktree Isolation**: Staging workspaces isolated in `.workflow/worktrees/<spec>/worker/` protecting the primary repository branch.
6. **Architectural Decision Records (ADRs)**: Continuous, Git-trackable decision auditing co-located in `.workflow/specs/active/<spec>/adrs/`.
7. **Zero Direct Commits & Grilling Session Gates**: Zero unvetted commits or pushes; all releases are confirmed via interactive Grilling Sessions by the `Git-Worker`.
8. **Strict Zero-Comments Code Policy**: Clean, self-documenting code with zero unrequested inline comments, block comments, or docstrings.

---

## 2. Directory Topology & Lifecycle

```text
.workflow/
├── specs/
│   ├── active/                         # Active, in-flight specifications
│   │   └── <spec-name>/                # Feature container
│   │       ├── spec.md                 # Functional specification (What & Why)
│   │       ├── plan.md                 # Technical design (Architecture & Schemas)
│   │       ├── tasks.md                # Task breakdown & dependency graph
│   │       ├── issues/                 # Atomic TDD task issues
│   │       ├── adrs/                   # Spec-scoped Architectural Decision Records
│   │       └── security/               # OWASP Top 10 & dependency audit reports
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

## 3. The 7-Stage Quality-Governed Subagent Pipeline

When `/workflow run <spec>` is triggered, the pipeline executes 7 specialized stages inside `.workflow/worktrees/<spec>/worker/`:

| Stage | Specialist Role | Responsibility |
|---|---|---|
| **Stage 1 (Implement)** | `Implementer Specialist` | Build out core domain models, specifications, and initial test files following TDD Red-Green. |
| **Stage 2 (Fix)** | `Fix-Worker Specialist` | Stabilize failing tests, apply surgical bug fixes, and guarantee 100% green builds. |
| **Stage 3 (Refactor)** | `Refactor-Worker Specialist` | Clean code, optimize modularity, reduce complexity, and enforce Zero-Comments policy. |
| **Stage 4 (Security)** | `Cybersecurity Specialist` | Scan OWASP Top 10 SAST patterns, secret leaks, and ecosystem dependency CVEs. |
| **Stage 5 (Quality)** | `Quality Assurance Specialist` | Evaluate Quality Gate (100/100, zero comments, security clearance), route feedback, and generate ADR. |
| **Stage 6 (Doc)** | `Doc-Worker Specialist` | Synchronize documentation, OpenAPI schemas, and specifications. |
| **Stage 7 (Git-Worker)** | `Git-Worker Specialist` | Conduct Grilling Session confirmation with developer, then execute atomic Conventional Commit and PR. |

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
