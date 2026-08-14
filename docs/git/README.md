# 📦 `git` — Deterministic Git Suite for AI Agents & Developers

> **Author**: `cezartdev`  
> **Version**: `1.3.0`  
> **Status**: `Active`  
> **Interface**: AI Agent Skill & Universal CLI Runner

---

## 🎯 Purpose & Overview

The **`git`** skill provides a unified, deterministic, and security-hardened Git operations engine. It eliminates messy commit histories, prevents accidental secret leaks, validates Conventional Commits through a 10-step gate, provides a retrospective commit history auditor (`/git audit`), and automates safe commit-and-push workflows across Linux, Windows, and macOS.

---

## ✨ Features

- 🛡️ **Pre-Commit Security & Hygiene Gates (Tier 1)**: Automatically blocks commits containing sensitive dotenv files (`.env*`), private keys (`*.pem`, `*.key`), credentials, secret tokens in diffs, or unresolved merge conflict markers (`<<<<<<<`).
- 📏 **10-Step Conventional Commits Validation Gate (Tier 2)**: Enforces strict Conventional Commits syntax (`<type>(<scope>): <description>`), imperative present-tense English verbs, casing, and bullet formatting.
- 🔍 **Commit History Audit & Compliance (`/git audit`)**: Analyzes past $N$ commits, scores repository compliance against Conventional Commits, and generates ready-to-use standardized rewrite proposals for legacy or messy commits.
- 🚀 **Multi-Command Suite**:
  - `/git commit`: Safe commit only (local).
  - `/git` or `/git sync` / `/git push`: All-in-one validate, commit, and safe push to upstream remote.
  - `/git status`: Rich working tree overview, unpushed commits, and suggested scopes.
  - `/git branch <name>`: Conventional branch creator (`feat/`, `fix/`, `chore/`, etc.).
  - `/git undo`: Safe soft reset of the last commit (`git reset --soft HEAD~1`).
  - `/git check-env`: Cross-platform runtime diagnostics.
- 🤖 **Machine-Readable Mode (`--json`)**: Structured JSON output across all subcommands for autonomous agents.
- 🌐 **Zero External Dependencies**: Standard library Python (`>=3.8`) compatible with Astral `uv`, `python3`, `python`, and `py`.

---

## 📥 Installation

Install this skill into your workspace using the standard `skills-cli`:

```bash
npx skills add cezartdev/skills --skill git
```

> [!IMPORTANT]
> Always specify the mandatory `--skill git` flag when adding this skill to ensure `skills-cli` loads the exact skill path instead of attempting branch matching.

---

## 🛠️ Prerequisites & Multi-Platform Launchers

- **Python**: Version **3.8+** is required.
- **Git**: Installed and configured with `user.name` and `user.email`.

### Execution Modes
- **Tier 1 (Universal — Recommended across Linux, macOS, Windows)**:
  ```bash
  uv run skills/git/scripts/git_helper.py <subcommand>
  ```
- **Tier 2 (Native Platform Launchers)**:
  - **Linux & macOS (Bash / Zsh)**: `bash skills/git/scripts/git_helper.sh <subcommand>`
  - **Windows (PowerShell)**: `pwsh skills/git/scripts/git_helper.ps1 <subcommand>`
- **Tier 3 (Fallback for minimal environments without uv)**:
  - **Linux / macOS**: `python3 skills/git/scripts/git_helper.py <subcommand>`
  - **Windows**: `python skills/git/scripts/git_helper.py <subcommand>`

### Environment Diagnostics
Run the diagnostic command to check your setup:
```bash
uv run skills/git/scripts/git_helper.py check-env
```

---

## 📖 Command Reference & Workflows

### 1. Safe Local Commit (`/git commit`)
Executes security checks, validates conventional commit formatting, and commits staged files:
```bash
uv run skills/git/scripts/git_helper.py commit \
  -t feat \
  -s auth \
  -m "implement oauth2 google login provider" \
  -b "- Add jwt validation middleware with rotating keys." \
  -b "- Configure authentication redirects and session cookies."
```

### 2. Commit & Push Sync (`/git` or `/git sync`)
Validates, commits, and pushes directly to the current remote branch:
```bash
uv run skills/git/scripts/git_helper.py sync \
  -t fix \
  -s api \
  -m "handle null user profile responses gracefully" \
  -b "- Prevent 500 internal server error when profile is empty."
```

### 3. Audit Commit History (`/git audit`)
Audits the last $N$ commits, scores compliance, and suggests standardized rewrites:
```bash
# Terminal human-readable report
uv run skills/git/scripts/git_helper.py audit -n 15

# Machine-readable JSON output for agents
uv run skills/git/scripts/git_helper.py audit -n 15 --json
```

### 4. Working Tree Status & Branch Management
```bash
# Rich overview of staged, unstaged, unpushed commits, and security scan
uv run skills/git/scripts/git_helper.py status

# Create a conventional branch
uv run skills/git/scripts/git_helper.py branch feat/audit-engine

# Undo last commit safely (changes remain staged)
uv run skills/git/scripts/git_helper.py undo
```

---

## 🔒 Security Gate Specifications

`git_helper.py` halts commits if any security rule is violated:

1. **Blocked Files**: `.env*`, `*.pem`, `*.key`, `*.pfx`, `*.p12`, `id_rsa*`, `id_ed25519*`, `credentials.json`, `service-account*.json`, `*.sqlite`, `*.db`.
2. **Blocked Diff Additions**: Private key blocks (`-----BEGIN PRIVATE KEY-----`), AWS Access Keys (`AKIA...`), and generic token assignments.
3. **Merge Conflict Markers**: `<<<<<<<`, `=======`, `>>>>>>>`.
4. **Large File Warning**: Files $> 10\text{ MB}$ or archive binaries (`.zip`, `.tar.gz`, `.iso`).

---

## 📐 Conventional Commits 10-Step Validation Gate

| Step | Rule | Requirement | Example |
|---|---|---|---|
| **1** | Structure | `<type>(<scope>): <description>` | `feat(auth): add login form` |
| **2** | Type | Whitelist: `feat`, `fix`, `docs`, `refactor`, `chore`, `test` | `feat` |
| **3** | Scope | Lowercase alphanumeric / kebab-case | `git`, `oauth-service` |
| **4** | Header Length | Maximum 120 characters | 65 chars [PASS] |
| **5** | Description Length | Minimum 10 characters | 28 chars [PASS] |
| **6** | Trailing Period | No period at the end of subject | `add login form` (no `.`) |
| **7** | Imperative Verb | English present tense verb | `add`, `update`, `fix` |
| **8** | Casing & Spacing | Lowercase start, clean single spaces | `implement feature` |
| **9** | Body Bullets | Non-empty body lines must be `- ` bullets $\le 120$ chars | `- configure endpoints` |
| **10**| Breaking Changes| Format `BREAKING CHANGE: <description>` | `BREAKING CHANGE: drop v1 api` |
