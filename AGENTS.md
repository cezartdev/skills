# Agent Operating Guidelines & Standards

This document establishes the mandatory operating standards, execution workflow, and rules of engagement for all AI agents working on `skills`.

---

## 1. Agent Operational Rules & Tooling

- **Repository & JS/TS Package Manager**: Use `pnpm` exclusively for all JavaScript/TypeScript package management commands, script executions, and root repository configuration.
- **Python Environment & Package Manager**: Use `uv` exclusively for Python virtual environments, dependency management (`uv pip`, `uv add`, `uv run`), and script execution.
- **Documentation & APIs**: Always use `context7` tools when looking up library documentation or modern API syntax.
- **Default Language**: All code, docstrings, git commit messages, READMEs, skill descriptions, and technical documentation MUST be written in English.

---

## 2. Git Commit Standards & Examples

All git commit messages MUST adhere to the **Conventional Commits** specification and MUST be written in English.

### Format
```text
<type>(<scope>): <short description in present tense>

[optional body giving contextual reasoning]
```

### Commit Types
- `feat`: A new feature or skill functionality.
- `fix`: A bug fix in a script, skill, or configuration.
- `docs`: Documentation updates (e.g., `AGENTS.md`, `README.md`, skill documentation).
- `refactor`: Code restructuring without changing functionality.
- `chore`: Maintenance tasks, updating dependencies (`package.json`, `pyproject.toml`), config files.
- `test`: Adding or updating tests.

### Commit Rules
1. Use imperative present tense ("add", "update", "fix", not "added", "updated", "fixes").
2. Keep the first line under 120 characters.
3. No period `.` at the end of the subject line.
4. Scope should indicate the specific skill or subsystem (e.g., `workflow`, `commits`, `agents`, `deps`).

### Examples of Valid Commits

```bash
# Adding a new skill feature
git commit -m "feat(workflow): implement langgraph state graph runner for deterministic steps"

# Documenting agent guidelines
git commit -m "docs(agents): define git commit conventions and python dependency rules"

# Fixing a script bug in a skill
git commit -m "fix(commits): handle empty staged diffs gracefully in commit generator"

# Updating dependencies
git commit -m "chore(deps): add langgraph and langchain-core via uv"

# Refactoring skill scripts
git commit -m "refactor(workflow): decouple state serialization from graph execution"
```

---

## 3. Skill Architecture & Standards

Skills created in this repository must follow a clean, modular structure compatible with standard AI agent skill interfaces (e.g., `skills.sh` / Agent Skills specification).

### Skill Directory Layout
Each skill resides under `skills/<skill-name>/`. Only `SKILL.md` is mandatory; all other files and subdirectories are optional and should only be added when strictly needed:

```text
skills/<skill-name>/
├── SKILL.md              # [REQUIRED] Skill specification & instructions (YAML frontmatter + markdown)
├── pyproject.toml        # [OPTIONAL] Python dependencies managed via uv (if skill uses Python packages)
├── package.json          # [OPTIONAL] Node.js dependencies managed via pnpm (if skill uses Node packages)
├── scripts/              # [OPTIONAL] Helper scripts (Python or Node) for automation/execution
├── references/           # [OPTIONAL] Additional reference docs read on-demand by agents
└── resources/            # [OPTIONAL] Static templates, assets, or schemas
```

### Skill Guidelines
- **Self-Contained & Minimalist**: Every skill must have a valid `SKILL.md` with frontmatter (`name`, `description`). Avoid creating empty folders (`resources/`, `references/`, `scripts/`) unless they are actively utilized.
- **Documentation (`docs/<skill-name>/`)**: Every skill created MUST have a corresponding documentation file in `docs/<skill-name>/README.md` containing:
  - Skill metadata (Author: `cezartdev`, Version, Status).
  - Purpose, feature list, and prerequisites.
  - Usage instructions for agents and human developers.
  - Complete CLI command reference and example workflows.
- **Dependencies**: If a skill uses Python scripts with external libraries, manage them via `uv` within the skill directory or workspace environment. If using Node.js scripts, use `pnpm`.
- **Interoperability**: Structure `SKILL.md` so it is fully compatible with standard AI agent skill interfaces (e.g., `skills.sh`, Antigravity, Claude Desktop, Cursor, etc.).

---

## 4. Planned Skills Roadmap

1. **`workflow` (Deterministic Agent Workflow)**:
   - **Engine**: Python + LangGraph.
   - **Purpose**: Provides a deterministic, state-machine driven workflow runner for multi-step tasks across any repository. Ensures agent execution state is logged, verifiable, and strictly bound to step transitions.
2. **`git-commit` (Automated Standardized Commits)**:
   - **Engine**: Node.js / Python CLI helper.
   - **Purpose**: Analyzes git status and staged diffs to draft, validate, and execute Conventional Commit messages following repository standards automatically.



