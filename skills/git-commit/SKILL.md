---
name: git-commit
description: Inspects working tree changes, drafts standardized Conventional Commits in English (strictly feat, fix, docs, refactor, chore, test), runs modular pre-flight validation gates (10-120 chars, imperative verbs, bullet body), and executes safe commits.
---

# Git Commit Skill (`git-commit`)

This skill provides an automated, deterministic workflow for creating standardized **Conventional Commits** in English. It enforces strict type whitelisting, length bounds, imperative English verb checks, and pre-flight validation before executing any commit.

---

## 1. Prerequisites & Environment (Cross-Platform: Linux, Windows, macOS)

- **Python**: Version **3.8+** is required to execute the pre-flight validation and commit runner script (`scripts/commit_helper.py`).
- **Dependencies**: Uses Python standard library modules exclusively (`argparse`, `re`, `subprocess`, `sys`). No external pip dependencies are needed.
- **Dependency Specification**: Declared in [`pyproject.toml`](file:///home/cezartdev/Documents/cezartdev/professional/skills/skills/git-commit/pyproject.toml) (`requires-python = ">=3.8"`).
- **Universal CLI Runners**:
  - **Linux / macOS**:
    ```bash
    python3 skills/git-commit/scripts/commit_helper.py <command>
    # Or using uv (auto-manages Python if not installed):
    uv run skills/git-commit/scripts/commit_helper.py <command>
    ```
  - **Windows (PowerShell, CMD, Git Bash)**:
    ```powershell
    python skills/git-commit/scripts/commit_helper.py <command>
    # Or using py launcher:
    py skills/git-commit/scripts/commit_helper.py <command>
    # Or using uv (auto-manages Python if not installed):
    uv run skills/git-commit/scripts/commit_helper.py <command>
    ```
- **Environment Diagnostic**: Run `check-env` to test Python version, Git setup, and uv availability:
  ```bash
  python3 skills/git-commit/scripts/commit_helper.py check-env
  ```
- **Troubleshooting & Missing Dependencies**:
  - **Option A: Astral `uv` (Recommended - Automatically manages Python versions)**:
    - **Windows (PowerShell)**:
      ```powershell
      powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
      # Or via WinGet:
      winget install --id=astral-sh.uv -e
      ```
    - **Linux / macOS**:
      ```bash
      curl -LsSf https://astral.sh/uv/install.sh | sh
      ```
  - **Option B: Manual Python & Git Installation**:
    - **Windows (WinGet)**:
      ```powershell
      winget install -e --id Python.Python.3.12
      winget install -e --id Git.Git
      ```
    - **Linux (Fedora / RHEL)**: `sudo dnf install -y python3 git`
    - **Linux (Ubuntu / Debian)**: `sudo apt update && sudo apt install -y python3 git`
    - **macOS**: `brew install python git`

---

## 2. Directory Layout

```text
skills/git-commit/
├── SKILL.md                 # Complete agent instructions and specifications
├── pyproject.toml           # Python version requirements and metadata
└── scripts/
    └── commit_helper.py     # Python CLI validator & safe commit runner
```

---

## 3. Commit Format Standards

Every commit generated or validated by this skill MUST strictly follow this structure:

```text
<type>(<scope>): <imperative_verb> <description>

- <concise bullet point explaining rationale or context>
- <concise bullet point explaining impact>
```

### Strict Rules:

1. **Type Whitelist (Strictly 6 Types)**:
   - `feat`: A new feature, skill, or functional enhancement.
   - `fix`: A bug fix or correction.
   - `docs`: Documentation only (e.g., `README.md`, `AGENTS.md`, `SKILL.md`).
   - `refactor`: Restructuring code/scripts without changing functionality.
   - `chore`: Dependency updates (`package.json`, `pyproject.toml`), configs, build tasks.
   - `test`: Adding, updating, or fixing tests.
   *Any other type is strictly rejected.*

2. **Scope**:
   - Lowercase alphanumeric or kebab-case (e.g., `workflow`, `git-commit`, `agents`, `deps`, `auth`).
   - No spaces or uppercase characters.

3. **Description**:
   - **Language**: Strictly **English**.
   - **Imperative Present Tense**: Must begin with a lowercase English action verb (e.g., `add`, `update`, `fix`, `implement`, `refactor`, `remove`, `configure`, `create`, `ensure`, `handle`, `enforce`, `resolve`, `support`, `document`).
   - **Casing & Spacing**: Lowercase sentence, single spaces only. No accidental `snake_case` in general prose.
   - **No Trailing Period**: Never end the subject line with a period (`.`).
   - **Length Limits**:
     - Description length: **$\ge 10$ characters**.
     - Full header line: **$\le 120$ characters**.

4. **Body (Optional)**:
   - When additional context is needed, format lines as concise bullet points (`- ...`).
   - Each bullet point must be in English and under 120 characters.

---

## 4. Step-by-Step Execution Workflow

Follow this sequence to inspect, draft, validate, and execute commits:

```mermaid
graph TD
    A[Step 1: Inspect Status & Diff] --> B[Step 2: Stage Target Files]
    B --> C[Step 3: Draft Commit Message]
    C --> D[Step 4: Pre-Flight Validation Gate]
    D -- "Failed (Auto-Adjust)" --> C
    D -- "Passed 100%" --> E[Step 5: Safe Commit Execution]
    E --> F[Step 6: Confirm with git log]
```

### Step 1: Inspect Changes & Check for Clean Tree
Run git commands to understand what changed:
```bash
git status -s
git diff
```

> [!IMPORTANT]
> **No-Changes Protocol**: If `git status -s` produces no output (working tree is clean), there are no changes to commit. 
> The agent MUST NOT attempt to run `git commit` or validate empty strings. Instead, terminate the task early and report:
> `"No changes detected in working tree. No commit was executed."`

### Step 2: Stage Target Files
Stage only intentional changes (avoid staging unrelated temporary files):
```bash
git add <path/to/file1> <path/to/file2>
```

### Step 3: Draft Candidate Message
Formulate the message adhering to the whitelisted types, scope, and English imperative verb.

### Step 4: Run Pre-Flight Validation Gate
Validate the message using the helper script before committing:
```bash
python skills/git-commit/scripts/commit_helper.py validate "<proposed_commit_message>"
```

If validation fails, read the failing step in the report and adjust the message until all steps pass.

### Step 5: Execute Safe Commit
Run the atomic commit command through the helper or standard git:
```bash
python skills/git-commit/scripts/commit_helper.py commit -t <type> -s <scope> -m "<description>" [-b "<bullet1>"] [-b "<bullet2>"]
```
*Or directly via git once validated:*
```bash
git commit -m "<validated_header>" [-m "- <bullet1>"]
```

### Step 6: Verify Commit
Confirm the commit was recorded cleanly:
```bash
git log -1 --stat
```

---

## 5. Pre-Flight Validation Functions

The validation pipeline runs 8 modular checks:

| # | Function | Rule Enforced |
|---|---|---|
| 1 | `validate_structure` | Matches `<type>(<scope>): <description>` structure |
| 2 | `validate_type` | Type is one of: `feat`, `fix`, `docs`, `refactor`, `chore`, `test` |
| 3 | `validate_scope` | Scope is lowercase kebab-case / alphanumeric |
| 4 | `validate_header_length` | Total header length is $\le 120$ characters |
| 5 | `validate_description_length` | Description part is $\ge 10$ characters |
| 6 | `validate_no_trailing_period` | Header does not end with `.` |
| 7 | `validate_english_imperative_verb`| First word is an approved English imperative verb |
| 8 | `validate_casing_and_spacing` | Lowercase start, clean single spaces, no snake_case prose |

---

## 6. Examples

### ✅ Valid Examples
```bash
# Feature addition
feat(git-commit): implement modular step validation pipeline

# Documentation update
docs(agents): update commit conventions and add length limits

# Bug fix with bullet body
fix(git-commit): handle empty diff output in commit helper

- check for empty git status before attempting to parse files
- return friendly error message when working tree is clean

# Dependency update
chore(deps): update pnpm packages to latest patch versions
```

### ❌ Invalid Examples & Why They Fail
| Invalid Message | Why it Fails |
|---|---|
| `git-commit: add helper` | Missing type and parenthesis around scope |
| `feat(git-commit): añadido validador` | Non-English description & verb |
| `feat(git-commit): added helper.` | Past tense verb (`added`) and trailing period (`.`) |
| `feat(git-commit): fix` | Description is under 10 characters |
| `custom(workflow): create state graph` | `custom` is not in the strict type whitelist |
| `feat(git-commit): add_helper_script` | Uses snake_case in description instead of standard English prose |
