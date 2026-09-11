# 🐙 `git` — Deterministic Git Suite for AI Agents & Developers

> **Author**: `cezartdev`  
> **Version**: `1.16.0`  
> **Status**: `Active`  
> **Interface**: AI Agent Skill & Universal CLI Runner

---

## 🎯 Purpose & Overview

The **`git`** skill provides a unified, deterministic, and security-hardened Git operations engine. It eliminates messy commit histories, prevents accidental secret leaks, validates Conventional Commits through a 10-step gate, provides a retrospective commit history auditor (`/git audit`), and automates safe commit-and-push workflows across Linux, Windows, and macOS.

**No Python required**: Built entirely in **pure Bash** and **native PowerShell**, ensuring zero runtime overhead and instant execution in any environment.

---

## ✨ Features

- 🛡️ **Pre-Commit Security & Hygiene Gates (Tier 1)**: Automatically blocks commits containing real dotenv files (`.env`, `.env.local`), private keys (`*.pem`, `*.key`), credentials, secret tokens in diffs, or unresolved merge conflict markers (`<<<<<<<`).
- 📄 **Explicit Support for `.env.example`**: Template files (`.env.example`, `.env.sample`, `.env.template`, `.env.dist`) are explicitly whitelisted and safe to commit.
- 🚦 **10-Step Conventional Commits Validation Gate (Tier 2)**: Enforces strict Conventional Commits syntax (`<type>(<scope>): <description>`), imperative present-tense English verbs, casing, and bullet formatting.
- 📊 **Commit History Audit & Compliance (`/git audit`)**: Analyzes past $N$ commits, scores repository compliance against Conventional Commits, and generates ready-to-use standardized rewrite proposals for legacy or messy commits.
- ⚡ **Streamlined High-Frequency Commands**:
  - `/git`: Validate, commit, and push directly to upstream remote in one step.
  - `/git commit`: Safe validated commit locally (without pushing).
  - `/git status`: Working tree overview, unpushed commits, and security scan.
  - `/git draft`: Inspect changes and get auto-inferred conventional scopes.
  - `/git undo`: Safe soft reset of the last commit (`git reset --soft HEAD~1`).
- 🤖 **Machine-Readable Mode (`--json`)**: Structured JSON output across all subcommands for autonomous agents.
- 🚀 **Zero Dependencies**: Pure Bash on POSIX (Linux/macOS/Git Bash) and native PowerShell on Windows.

---

## 📦 Installation

Install this skill into your workspace using the standard `skills-cli`:

```bash
npx skills add cezartdev/skills --skill git
```

> [!IMPORTANT]
> Always specify the mandatory `--skill git` flag when adding this skill to ensure `skills-cli` loads the exact skill path instead of attempting branch matching.

---

## 🛠️ Prerequisites & Multi-Platform Launchers

- **Git**: Installed and configured with `user.name` and `user.email`.
- **Runtime**:
  - **Linux & macOS (Bash / Zsh)**: `bash skills/git/scripts/git_helper.sh <subcommand>` (or `./skills/git/scripts/git_helper.sh`)
  - **Windows (PowerShell)**: `pwsh skills/git/scripts/git_helper.ps1 <subcommand>` (or `powershell skills/git/scripts/git_helper.ps1`)
  - **Windows (Git Bash / MSYS2 / WSL)**: `bash skills/git/scripts/git_helper.sh <subcommand>`

### Environment Diagnostics
Run the diagnostic command to check your setup:
```bash
# Linux / macOS / Git Bash
bash skills/git/scripts/git_helper.sh check-env

# Windows PowerShell
pwsh skills/git/scripts/git_helper.ps1 check-env
```

---

## 🚀 Command Reference & Workflows

### 1. Direct Commit & Push (`/git`)
Validates, commits, and pushes directly to the current remote branch:
```bash
# Direct string argument:
bash skills/git/scripts/git_helper.sh "feat(auth): implement oauth2 google login provider"

# Or with explicit subcmd / flags:
bash skills/git/scripts/git_helper.sh sync \
  -t feat \
  -s auth \
  -m "implement oauth2 google login provider" \
  -b "Add jwt validation middleware with rotating keys."
```

### 2. Safe Local Commit (`/git commit`)
Executes security checks, validates Conventional Commits format, and commits locally without pushing:
```bash
bash skills/git/scripts/git_helper.sh commit "feat(git): add native bash script runner"
```

### 3. Audit Commit History (`/git audit`)
Audits the last $N$ commits, scores compliance, and suggests standardized rewrites:
```bash
# Human-readable terminal report
bash skills/git/scripts/git_helper.sh audit -n 15

# Machine-readable JSON output for agents
bash skills/git/scripts/git_helper.sh audit -n 15 --json
```

### 4. Working Tree Status, Draft & Undo
```bash
# Rich overview of staged, unstaged, unpushed commits, and security scan
bash skills/git/scripts/git_helper.sh status

# Inspect changes and get auto-inferred commit scope & type
bash skills/git/scripts/git_helper.sh draft

# Create a standardized conventional branch
bash skills/git/scripts/git_helper.sh branch feat/audit-engine

# Undo last commit safely (changes remain staged)
bash skills/git/scripts/git_helper.sh undo
```

---

## 🛡️ Security Gate Specifications

The helper halts commits if any security rule is violated:

1. **Blocked Files**:
   - Real `.env*` files (`.env`, `.env.local`, `.env.production`).
   - *Exception*: Template files (`.env.example`, `.env.sample`, `.env.template`, `.env.dist`) are permitted.
   - `*.pem`, `*.key`, `*.pfx`, `*.p12`, `*.keystore`.
   - `id_rsa*`, `id_ed25519*`.
   - `*credential*.json`, `*service-account*.json`, `*client_secret*.json`.
   - `*.sqlite`, `*.db`.
2. **Blocked Diff Additions**: Private key blocks (`-----BEGIN PRIVATE KEY-----`), AWS Access Keys (`AKIA...`), and generic token assignments.
3. **Merge Conflict Markers**: `<<<<<<<`, `=======`, `>>>>>>>`.
4. **Large File Warning**: Files $> 10\text{ MB}$ or archive binaries (`.zip`, `.tar.gz`, `.iso`, `.exe`).

---

## 🚦 Conventional Commits 10-Step Validation Gate

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
