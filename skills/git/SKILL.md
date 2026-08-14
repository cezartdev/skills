---
name: git
description: Deterministic Git suite for AI agents and developers. Includes pre-commit security gates (secret, sensitive file & conflict marker blocker), 10-step Conventional Commits validation, commit history compliance auditing (/git audit), safe atomic commits, sync/push, branch management, and cross-platform runners.
---

# Git Suite Skill Specification

## 1. Prerequisites & Environment (Cross-Platform: Linux, Windows, macOS)

- **Python**: Version **3.8+** is required to execute `scripts/git_helper.py`.
- **Dependencies**: Built entirely on Python standard library modules (`argparse`, `json`, `os`, `re`, `subprocess`, `sys`, `typing`). No external pip dependencies are needed.
- **Dependency Specification**: Declared in [`pyproject.toml`](file:///home/cezartdev/Documents/cezartdev/professional/skills/skills/git/pyproject.toml) (`requires-python = ">=3.8"`).
- **Universal CLI Runners**:
  - **Tier 1 (Universal — Recommended across Linux, macOS, Windows)**:
    ```bash
    uv run skills/git/scripts/git_helper.py <subcommand>
    ```
  - **Tier 2 (Native Platform Launchers)**:
    - **Linux / macOS**: `bash skills/git/scripts/git_helper.sh <subcommand>`
    - **Windows (PowerShell)**: `pwsh skills/git/scripts/git_helper.ps1 <subcommand>`
  - **Tier 3 (Fallback for minimal environments without uv)**:
    - **Linux / macOS**: `python3 skills/git/scripts/git_helper.py <subcommand>`
    - **Windows**: `python skills/git/scripts/git_helper.py <subcommand>`
- **Environment Diagnostic**: Run `check-env` to test Python runtime, Git setup, and uv availability:
  ```bash
  uv run skills/git/scripts/git_helper.py check-env
  ```

> [!IMPORTANT]
> **MANDATORY AGENT EXECUTION DIRECTIVE**:
> AI Agents MUST ALWAYS execute Git commands via `uv run` (e.g. `uv run skills/git/scripts/git_helper.py <subcommand>` or `uv run .agents/skills/git/scripts/git_helper.py <subcommand>`).
> NEVER invoke `python3` or `python` directly unless running in a restricted sandbox where `uv` is unavailable.

---

## 2. Directory Layout

```text
skills/git/
├── SKILL.md              # [REQUIRED] Skill specification & agent prompt instructions
├── pyproject.toml        # [OPTIONAL] Python manifest (name="git", requires-python=">=3.8")
└── scripts/
    ├── git_helper.py     # Deterministic CLI runner with security gates, validator, audit & JSON mode
    ├── git_helper.sh     # Linux / macOS POSIX launcher with auto-uv resolution
    └── git_helper.ps1    # Windows PowerShell launcher with auto-uv resolution
```

---

## 3. Subcommand Trigger Routing

| Trigger / User Request | Subcommand | Workflow | Remote Action |
|---|---|---|---|
| `/git commit` | `commit` | Inspect status $\rightarrow$ Security Scan $\rightarrow$ 10-step message validation $\rightarrow$ Atomic commit | ❌ Local only |
| `/git` or `/git sync` / `/git push` | `sync` | Security Scan $\rightarrow$ 10-step validation $\rightarrow$ Commit $\rightarrow$ Verify upstream $\rightarrow$ Safe push | ✅ Remote push |
| `/git audit [N]` | `audit` | Evaluates past $N$ commits for Conventional Commits compliance & proposes standardized rewrites | ❌ None |
| `/git status` | `status` | Formatted working tree overview, unpushed commits, branch tracking, and suggested scopes | ❌ None |
| `/git branch <name>` | `branch` | Creates conventional branch enforcing prefixes (`feat/`, `fix/`, `chore/`, `docs/`, `refactor/`, `test/`) | ❌ None |
| `/git undo` | `undo` | Reverts last commit safely (`git reset --soft HEAD~1`) without losing working code | ❌ None |
| `/git check-env` | `check-env` | Verifies Python $\ge 3.8$, Git version, author configuration, and Astral `uv` | ❌ None |

---

## 4. Agent Cognitive Process & Reflection Protocol

When executing git tasks, the AI agent MUST follow this structured chain of thought:

```text
[Agent Reflection & Execution Steps]:
1. Check Status & Draft:
   Run 'uv run skills/git/scripts/git_helper.py draft' to inspect staged files and suggested scopes.
2. Security & Hygiene Review:
   Confirm that NO sensitive files (.env, .pem, .key, credentials) or merge conflict markers (<<<<<<<) are staged.
3. Select Type & Scope:
   - Type: Choose strictly from [feat, fix, docs, refactor, chore, test].
   - Scope: Choose a concise lowercase kebab-case module name (e.g., 'git', 'auth', 'workflow', 'deps').
4. Formulate Imperative Subject:
   - Must begin with an approved English imperative verb in present tense (e.g., 'add', 'implement', 'fix', 'refactor', 'enforce').
   - First letter lowercase, no period at the end, 10-120 total chars.
5. Execute via Helper Script:
   Execute 'uv run skills/git/scripts/git_helper.py commit' (or 'sync') with explicit arguments.
```

---

## 5. Security & Hygiene Gate (Tier 1)

`git_helper.py` automatically blocks commits if any of the following are detected:

1. **Sensitive Files**: `.env*`, `*.pem`, `*.key`, `*.pfx`, `*.p12`, `id_rsa*`, `id_ed25519*`, `credentials.json`, `service-account*.json`, `*.sqlite`, `*.db`.
2. **Secret Content in Diffs**: `-----BEGIN PRIVATE KEY-----`, `AKIA[0-9A-Z]{16}`, API tokens / keys.
3. **Merge Conflict Markers**: `<<<<<<<`, `=======`, `>>>>>>>`.
4. **Large Files Warning**: Files $> 10\text{ MB}$ or binary archives (`.zip`, `.tar.gz`, `.iso`).

---

## 6. Conventional Commits 10-Step Validation Gate (Tier 2)

All commit messages are strictly validated against 10 rules:
1. `validate_structure`: `<type>(<scope>): <description>` or `<type>(<scope>)!: <description>`.
2. `validate_type`: Must be one of `feat`, `fix`, `docs`, `refactor`, `chore`, `test`.
3. `validate_scope`: Lowercase alphanumeric or kebab-case.
4. `validate_header_length`: Max 120 characters.
5. `validate_description_length`: Min 10 characters.
6. `validate_no_trailing_period`: No trailing period `.` in subject.
7. `validate_english_imperative_verb`: Verified English present-tense action verb (e.g. `add`, `update`, `fix`).
8. `validate_casing_and_spacing`: Lowercase start, clean single spaces.
9. `validate_body_bullets`: Non-empty body lines must be bullet points (`- ...`) under 120 chars each.
10. `validate_breaking_change`: Valid `BREAKING CHANGE:` footer format when applicable.

---

## 7. CLI Command Reference & Examples

### Safe Local Commit (`/git commit`)
```bash
uv run skills/git/scripts/git_helper.py commit \
  -t feat \
  -s git \
  -m "add security gates and commit history audit engine" \
  -b "- Block sensitive files, credentials, and unresolved conflict markers." \
  -b "- Implement /git audit command to score legacy commits and propose rewrites."
```

### Commit & Push Sync (`/git` or `/git sync`)
```bash
uv run skills/git/scripts/git_helper.py sync \
  -t fix \
  -s release \
  -m "enforce pnpm run version in github release action workflow" \
  -b "- Prevent ERR_PNPM_INVALID_VERSION_BUMP in automated release pipeline."
```

### Audit Historical Commits (`/git audit`)
```bash
# Audit the last 10 commits
uv run skills/git/scripts/git_helper.py audit -n 10

# Audit with machine-readable JSON
uv run skills/git/scripts/git_helper.py audit -n 10 --json
```

### Repository Status & Branch Creation
```bash
# Rich overview of working tree, unpushed commits, and security
uv run skills/git/scripts/git_helper.py status

# Create a standardized branch
uv run skills/git/scripts/git_helper.py branch feat/audit-engine

# Undo the last commit safely (preserves working files in staging area)
uv run skills/git/scripts/git_helper.py undo
```
