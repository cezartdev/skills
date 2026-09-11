---
name: git
description: Deterministic Git suite for AI agents and developers. Pure native Bash and PowerShell scripts with pre-commit security gates (secret, sensitive file with .env.example allowance & conflict marker blocker), 10-step Conventional Commits validation, commit history compliance auditing (/git audit), safe atomic commits, sync/push, and branch management without Python.
---

# Git Suite Skill Specification

## 1. Prerequisites & Environment (Cross-Platform: Linux, Windows, macOS)

- **Pure Native Execution**: Built entirely in **Bash** (`git_helper.sh`) and **PowerShell** (`git_helper.ps1`). **No Python, uv, or virtual environments required.**
- **Supported Platforms**:
  - **Linux & macOS**: `bash skills/git/scripts/git_helper.sh <subcommand>` (or directly `./skills/git/scripts/git_helper.sh`)
  - **Windows (PowerShell)**: `pwsh skills/git/scripts/git_helper.ps1 <subcommand>` (or `powershell skills/git/scripts/git_helper.ps1`)
  - **Windows (Git Bash / MSYS2 / WSL)**: `bash skills/git/scripts/git_helper.sh <subcommand>`
- **Environment Diagnostic**: Run `check-env` to test Git setup and runtime availability:
  ```bash
  bash skills/git/scripts/git_helper.sh check-env
  # or on Windows:
  pwsh skills/git/scripts/git_helper.ps1 check-env
  ```

---

## 2. Directory Layout

```text
skills/git/
├── SKILL.md              # [REQUIRED] Skill specification & agent prompt instructions
└── scripts/
    ├── git_helper.sh     # Linux / macOS / Git Bash native script runner
    └── git_helper.ps1    # Windows native PowerShell script runner
```

---

## 3. Subcommand Trigger Routing & Everyday Ergonomics

| Trigger / User Request | Command | Workflow | Remote Action |
|---|---|---|---|
| `/git` or `/git sync` / `/git push` | `bash git_helper.sh "<message>"` | Security Scan $\rightarrow$ 10-step validation $\rightarrow$ Commit $\rightarrow$ Safe push | ✅ Remote push |
| `/git commit` | `bash git_helper.sh commit "<message>"` | Security Scan $\rightarrow$ 10-step message validation $\rightarrow$ Atomic commit | ❌ Local only |
| `/git audit [N]` | `bash git_helper.sh audit [-n 10]` | Evaluates past $N$ commits for Conventional Commits compliance & proposes standardized rewrites | ❌ None |
| `/git status` | `bash git_helper.sh status` | Formatted working tree overview, unpushed commits, branch tracking, and security status | ❌ None |
| `/git draft` | `bash git_helper.sh draft` | Working tree status, security scan, and smart commit scope/type inference | ❌ None |
| `/git branch <name>` | `bash git_helper.sh branch <name>` | Creates conventional branch enforcing prefixes (`feat/`, `fix/`, `chore/`, `docs/`, `refactor/`, `test/`) | ❌ None |
| `/git undo` | `bash git_helper.sh undo` | Reverts last commit safely (`git reset --soft HEAD~1`) preserving files in staging | ❌ None |
| `/git check-env` | `bash git_helper.sh check-env` | Verifies Git executable, author configuration, and shell environment | ❌ None |

> [!TIP]
> **Flexible Argument Passing**:
> You can pass the commit message directly as a string or use flags:
> ```bash
> # Direct message string:
> bash skills/git/scripts/git_helper.sh "feat(git): add native bash script runner"
> 
> # With flags and bullets:
> bash skills/git/scripts/git_helper.sh commit \
>   -t feat -s git -m "add native bash script runner" \
>   -b "Migrate from python helper to pure bash and powershell"
> ```

---

## 4. Agent Cognitive Process & Reflection Protocol

When executing git tasks, the AI agent MUST follow this structured chain of thought:

```text
[Agent Reflection & Execution Steps]:
1. Check Status & Draft:
   Run 'bash skills/git/scripts/git_helper.sh draft' to inspect staged files and suggested scopes.
2. Security & Hygiene Review:
   Confirm that NO real sensitive files (.env, .env.local, .pem, .key, credentials) or merge conflict markers (<<<<<<<) are staged.
   (Note: .env.example, .env.sample, .env.template, .env.dist are explicitly permitted).
3. Select Type & Scope:
   - Type: Choose strictly from [feat, fix, docs, refactor, chore, test].
   - Scope: Choose a concise lowercase kebab-case module name (e.g., 'git', 'auth', 'workflow', 'deps').
4. Formulate Imperative Subject:
   - Must begin with an approved English imperative verb in present tense (e.g., 'add', 'implement', 'fix', 'refactor', 'enforce').
   - First letter lowercase, no period at the end, 10-120 total chars.
5. Execute via Helper Script:
   Execute 'bash skills/git/scripts/git_helper.sh "<message>"' (or 'commit' for local-only) with validated arguments.
```

---

## 5. Security & Hygiene Gate (Tier 1)

The helper script automatically blocks commits if any of the following are detected:

1. **Sensitive Files**:
   - `.env*` files are strictly blocked **UNLESS** they are templates: `.env.example`, `.env.sample`, `.env.template`, `.env.dist`, `.env.ci`.
   - `*.pem`, `*.key`, `*.pfx`, `*.p12`, `*.keystore`.
   - `id_rsa*`, `id_ed25519*`.
   - `*credential*.json`, `*service-account*.json`, `*client_secret*.json`.
   - `*.sqlite`, `*.db`.
2. **Secret Content in Diffs**:
   - `-----BEGIN [RSA/EC/OPENSSH/PGP/DSA]? PRIVATE KEY-----`.
   - AWS Access Key IDs (`AKIA...`, `ASIA...`, etc.).
   - Generic API tokens/secrets (`api_key=...`, `secret_key=...`).
3. **Merge Conflict Markers**:
   - `<<<<<<<`, `=======`, `>>>>>>>`.
4. **Large Files Warning**:
   - Files $> 10\text{ MB}$ or binary archives (`.zip`, `.tar.gz`, `.iso`, `.exe`).

---

## 6. Conventional Commits 10-Step Validation Gate (Tier 2)

All commit messages are strictly validated against 10 rules:
1. `validate_structure`: `<type>(<scope>): <description>` or `<type>(<scope>)!: <description>`.
2. `validate_type`: Must be one of `feat`, `fix`, `docs`, `refactor`, `chore`, `test`.
3. `validate_scope`: Lowercase alphanumeric or kebab-case (`^[a-z0-9]+(-[a-z0-9]+)*$`).
4. `validate_header_length`: Max 120 characters.
5. `validate_description_length`: Min 10 characters.
6. `validate_no_trailing_period`: No trailing period `.` in subject line.
7. `validate_english_imperative_verb`: Verified English present-tense action verb (e.g. `add`, `update`, `fix`). Gerunds (`-ing`), past tenses (`-ed`), and 3rd-person singulars (`-s`, `-es`) are rejected.
8. `validate_casing_and_spacing`: Lowercase start (acronyms like JWT, CLI permitted), single spaces, no snake_case.
9. `validate_body_bullets`: Non-empty body lines must be bullet points (`- ...`) under 120 chars each.
10. `validate_breaking_change`: Valid `BREAKING CHANGE:` footer format when applicable.

---

## 7. CLI Command Reference & Examples

### Everyday Commit & Push (`/git`)
```bash
# Push directly to current branch upstream
bash skills/git/scripts/git_helper.sh "feat(auth): add google oauth provider"
```

### Local Commit Only (`/git commit`)
```bash
# Commit locally without pushing
bash skills/git/scripts/git_helper.sh commit "feat(git): add native bash script runner"
```

### With Explanatory Body Bullets
```bash
bash skills/git/scripts/git_helper.sh commit \
  -t feat \
  -s git \
  -m "add native bash and powershell runners" \
  -b "Eliminate python runtime dependency for deterministic git operations." \
  -b "Support .env.example in pre-commit security scan."
```

### Audit Historical Commits (`/git audit`)
```bash
# Audit the last 10 commits
bash skills/git/scripts/git_helper.sh audit -n 10

# Audit with machine-readable JSON
bash skills/git/scripts/git_helper.sh audit -n 10 --json
```

### Repository Status & Branch Creation
```bash
# Overview of working tree, unpushed commits, and security scan
bash skills/git/scripts/git_helper.sh status

# Create a standardized branch
bash skills/git/scripts/git_helper.sh branch feat/audit-engine

# Undo the last commit safely (preserves working files in staging area)
bash skills/git/scripts/git_helper.sh undo
```
