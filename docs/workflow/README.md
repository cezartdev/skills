# 📦 `workflow` — Deterministic State Machine Runner, Cybersecurity Auditor & Quality Gatekeeper

> **Author**: `cezartdev`  
> **Version**: `1.3.0`  
> **Status**: `Active`  
> **Interface**: AI Agent Skill & Universal Cross-Platform CLI Runner  
> **Ecosystems Supported**: Python (`uv`/`pytest`), Rust (`cargo`), Go (`go test`), TypeScript/JavaScript (`pnpm`/`bun`/`npm`), Java (`maven`/`gradle`), C# (`dotnet`)

---

## 🎯 Purpose & Overview

The **`workflow`** skill provides a deterministic, state-machine driven development suite for software projects. Encapsulated inside a single modular **`.workflow/`** directory in target repositories, it is fully standardized according to the **[Agent Skills Specification](https://agentskills.io/specification)** and integrates best practices from **[GitHub Spec-Kit](https://github.com/github/spec-kit)** and **[Fission-AI OpenSpec](https://github.com/Fission-AI/OpenSpec)**:

- **Encapsulated `.workflow/` Architecture**: Centralizes all specifications (`.workflow/specs/`), memory (`.workflow/memory/`), PRs catalog (`.workflow/prs/`), and worktrees (`.workflow/worktrees/`).
- **Deterministic 7-Stage Subagent Pipeline**: Sequentially executes `Implement` $\rightarrow$ `Fix` $\rightarrow$ `Refactor` $\rightarrow$ `Security` $\rightarrow$ `Quality` $\rightarrow$ `Doc` $\rightarrow$ `Git-Worker` across isolated physical Git Worktrees.
- **OWASP Top 10 Cybersecurity & Vulnerability Auditor (`/workflow security`)**: Integrated SAST pattern scanner, secret leak detector, and polyglot dependency CVE auditor (`pnpm audit`, `pip-audit`, `cargo audit`).
- **Quality Gatekeeper (`/workflow quality`)**: Evaluates holistic quality score (100/100 tests, OWASP clearance, zero comments), authors formal **Architectural Decision Records (ADRs)**, and compiles pull requests.
- **Universal Polyglot Engine (Zero Bias)**: Automatically detects and adapts to Python, Rust, Go, Node, Java, and .NET test runners.
- **Strict Zero-Comments Code Policy**: All autonomous subagents produce 100% clean, self-documenting code without extraneous inline or block comments (`//`, `#`, `/* */`, `""" """`) unless explicitly requested by the developer.
- **Protected Branch Gate & Deterministic Main/Master Isolation**: Automatically intercepts executions triggered while on `main` or `master`, isolates work to a dedicated feature branch (`feat/<name>`), and blocks direct pushes or commits to protected branches.

---

## 📋 Prerequisites & Tooling

To use the full capabilities of the Workflow Suite, ensure the following core tools are installed on your system:

| Tool | Minimum Version | Purpose | Installation / Setup |
|---|---|---|---|
| **Python** | `3.10+` | Core state machine runner and deterministic validator engine. | Standard package manager (`brew`, `apt`, `winget`). |
| **Git** | `2.25+` | Physical worktree isolation, branch management, and atomic commits. | Standard package manager (`git-scm.com`). |
| **Astral `uv`** | Latest | Ultra-fast Python package and virtual environment runner. | `pip install uv` or `brew install uv` |
| **GitHub CLI (`gh`)** | `2.0+` | Reading remote issues, opening Pull Requests (`/workflow quality --create-pr`), and repository automation. | Standard package manager (`cli.github.com`). |

### 🔑 GitHub CLI Authentication & Permissions
The GitHub CLI (`gh`) is essential for agents and developers to interact with GitHub repositories directly from the terminal (reading issues, opening pull requests, and inspecting CI status).

1. **Authenticate**:
   ```bash
   gh auth login
   ```
2. **Required Permissions / Scopes**: Ensure your authenticated token includes scopes according to your needs:
   - `repo`: Full control of private/public repositories (read issues, push branches, create PRs).
   - `workflow`: Update GitHub Action workflows if modifying CI.
   - `read:org`: Read organization membership (if collaborating in an organization repository).
   - `read:project`: Access organization project boards (if tracking issues).
3. **Verify Environment**:
   ```bash
   # Check GitHub CLI authentication status and granted scopes:
   gh auth status
   ```

---

## 🛠️ Universal Execution Hierarchy

- **Tier 1 (Universal Recommended — Linux, Windows, macOS)**:
  ```bash
  uv run skills/workflow/scripts/workflow_runner.py <subcommand>
  ```
- **Tier 2 (Fallback for minimal environments without uv)**:
  - **Linux / macOS**: `python3 skills/workflow/scripts/workflow_runner.py <subcommand>`
  - **Windows**: `python skills/workflow/scripts/workflow_runner.py <subcommand>`

---

## 🚀 CLI Command Reference

### 1. View Universal Catalog & Cheat-Sheet
```bash
uv run skills/workflow/scripts/workflow_runner.py list
```

### 2. Polyglot Initialization & Codebase Exploration
```bash
# Auto-detects stack, test runners, and generates coding_preferences.md and project_context.md
uv run skills/workflow/scripts/workflow_runner.py explore

# Initialize .workflow/ module
uv run skills/workflow/scripts/workflow_runner.py init
```

### 3. Streamlined Project Memory & Indexed Docs
```bash
# View memory catalog (coding_preferences.md, project_context.md, and docs/)
uv run skills/workflow/scripts/workflow_runner.py memory list

# Add a new indexed guideline / documentation note into .workflow/memory/docs/
uv run skills/workflow/scripts/workflow_runner.py memory add auth-rules --content "JWT tokens expire in 15m; use refresh tokens in HttpOnly cookies."
# => Creates: .workflow/memory/docs/01_auth_rules.md

# View a recorded memory note
uv run skills/workflow/scripts/workflow_runner.py memory show 01
```

### 4. Business & Application Domain Context
```bash
# Add or append business domain and application context to .workflow/memory/project_context.md:
uv run skills/workflow/scripts/workflow_runner.py context "This application is an e-commerce platform for digital gaming assets with Stripe payments, Discord OAuth, and real-time inventory management."

# View currently registered business and application domain context:
uv run skills/workflow/scripts/workflow_runner.py context
```

### 5. Spec-Driven Development (SDD) & Subagent Pipeline
```bash
# 1. Scaffold new feature spec directly under .workflow/specs/active/<spec>/
uv run skills/workflow/scripts/workflow_runner.py new user-login

# 2. Functional Specification (Focus purely on WHAT and WHY without implementation details):
uv run skills/workflow/scripts/workflow_runner.py specify user-login

# 3. Ambiguity Checkpoint (Socratic Q&A to eliminate gaps + generate ADR):
uv run skills/workflow/scripts/workflow_runner.py clarify user-login --generate-adr

# 4. Technical Design (Convert approved spec into architecture, data schemas & contracts):
uv run skills/workflow/scripts/workflow_runner.py plan user-login

# 5. Tasks Breakdown (Decompose technical plan into ordered atomic tasks & issues/):
uv run skills/workflow/scripts/workflow_runner.py tasks user-login

# 6. Auditoría Previa (Static consistency audit across Constitution, spec, plan & tasks):
uv run skills/workflow/scripts/workflow_runner.py analyze user-login

# 7. Execute 7-Stage Quality Pipeline (Full Run):
uv run skills/workflow/scripts/workflow_runner.py run user-login

# Dry-run execution simulation (view preview without modifying files or launching workers):
uv run skills/workflow/scripts/workflow_runner.py run user-login --dry-run

# Granular execution: Execute only a single stage (e.g. Security Audit):
uv run skills/workflow/scripts/workflow_runner.py run user-login --only security

# Resume pipeline from a specific stage onward (e.g. Quality Gatekeeper):
uv run skills/workflow/scripts/workflow_runner.py run user-login --from quality

# Automatic remote push to origin upon successful completion (Default is local commit only):
uv run skills/workflow/scripts/workflow_runner.py run user-login --push

# Force code auto-formatting during pipeline execution:
uv run skills/workflow/scripts/workflow_runner.py run user-login --format

# Opt-In Recurring Background Execution (runs every 30m with Fixed-Delay):
uv run skills/workflow/scripts/workflow_runner.py run user-login --schedule 30

# Stop active background schedulers & terminate subagents:
uv run skills/workflow/scripts/workflow_runner.py stop user-login

# Clean up completed worktrees and stale git directory locks:
uv run skills/workflow/scripts/workflow_runner.py clean

# Archive completed spec when merged:
uv run skills/workflow/scripts/workflow_runner.py archive user-login
```

### 6. Native Subagent Archetypes & Dedicated System Prompts
When `/workflow run <spec>` is executed, the AI Agent registers and launches 7 specialized subagents via native agent tools (`define_subagent` and `invoke_subagent`), each with its own role, function, and personality:

| Subagent Type | Subagent Role | System Prompt Reference | Key Function |
|---|---|---|---|
| `workflow-implement-worker` | **Implement Subagent** | `references/prompts/implement_worker.prompt.md` | Builds out core domain models, specifications, and initial test files following TDD Red-Green principles. |
| `workflow-fix-worker` | **Fix Subagent** | `references/prompts/fix_worker.prompt.md` | Diagnoses test failures, writes reproduction tests (Red Phase), and fixes bugs to 100% green tests. |
| `workflow-refactor-worker` | **Refactor Subagent** | `references/prompts/refactor_worker.prompt.md` | Eliminates code smells, reduces cognitive complexity, strips redundant comments, and preserves 100% green tests. |
| `workflow-security-worker` | **Security Subagent** | `references/prompts/security_worker.prompt.md` | Scans OWASP Top 10 SAST patterns, secret leaks, and dependency CVEs. |
| `workflow-quality-worker` | **Quality Subagent** | `references/prompts/quality_worker.prompt.md` | Evaluates holistic quality score (100/100, zero comments, security clearance), writes formal ADRs, and routes feedback loops. |
| `workflow-doc-worker` | **Doc Subagent** | `references/prompts/doc_worker.prompt.md` | Synchronizes markdown documentation, README files, API schemas, and `spec.md` acceptance criteria checkboxes. |
| `workflow-git-worker` | **Git Subagent** | `references/prompts/git_worker.prompt.md` | Conducts interactive Grilling Sessions (`ask_question`) with developer before commits/pushes, executing deterministic Conventional Commits and PRs. Local commits only by default unless `--push` is provided. |

### 7. Strict Hierarchical Worktrees & Subagent Branch Scoping
Every physical worktree is **strictly dependent on and scoped to a specification and its designated subagent**:
- **Feature / Developer Branch**: Primary implementation takes place directly on `feat/<spec-name>` (e.g., `feat/user-login`).
- **Staging Branch**: Autonomous subagents operate on dedicated staging branch `feat/<spec-name>-worker` inside `.workflow/worktrees/<spec-name>/worker/`.
- **Auto-Merge Scope**: Auto-merge operations target the spec's associated branch (`feat/user-login`), never solely `main`.
- **ADR Audit Trail**: Versioned ADRs stored in `.workflow/specs/active/<spec>/adrs/ADR_<timestamp>_pipeline_decisions.md`.

```bash
# Execute the full pipeline on-demand (local commit by default):
uv run skills/workflow/scripts/workflow_runner.py run user-login

# Or execute with automatic remote push:
uv run skills/workflow/scripts/workflow_runner.py run user-login --push
# => Worktree: .workflow/worktrees/user-login/worker/ (Branch: feat/user-login-worker)
# => Spawns Implementer -> Fix-Worker -> Refactor-Worker -> Security-Worker -> Quality-Worker -> Doc-Worker -> Git-Worker
# => Quality-Worker audits 100% tests, OWASP security clearance & zero comments
# => Generates ADR in .workflow/specs/active/user-login/adrs/
# => Git-Worker executes Grilling Session confirmation before commit & PR
```
