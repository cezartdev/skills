# cezartdev-skills

## 1.0.0

### Major Changes

- [`1d2baae`](https://github.com/cezartdev/skills/commit/1d2baaea5aebcb519f5b2ab558cc55b6a17be37e) Thanks [@cezartdev](https://github.com/cezartdev)! - Release `git` skill suite v1.0.0 (renamed and evolved from `git-commit`):
  
  - **Modular Subcommand Suite**: Introduces `/git commit` (local atomic commit), `/git` / `/git sync` (commit & push), `/git status` (repository health), `/git branch` (conventional branch creator), `/git undo` (safe soft reset), `/git audit` (commit history compliance scoring & rewrites), and `/git check-env`.
  - **Pre-Commit Security & Hygiene Gate (Tier 1)**: Automatically scans and blocks commits containing dotenv files (`.env*`), private keys (`*.pem`, `*.key`), credentials, raw tokens in staged diffs, and unresolved merge conflict markers (`<<<<<<<`).
  - **10-Step Conventional Commits Validation Gate (Tier 2)**: Enforces strict Conventional Commits structure, imperative English present-tense verbs, scope formatting, and bullet limits.
  - **Retrospective Commit History Auditor (`/git audit`)**: Analyzes past $N$ commits, scores repository compliance against Conventional Commits standards, and proposes standardized rewrite suggestions.
  - **Cross-Platform & Headless Support**: Zero third-party dependencies (Python standard library $\ge 3.8$), compatible with Linux, Windows (PowerShell/CMD), macOS, and Astral `uv`, with `--json` output across all subcommands.

## 0.2.0

### Minor Changes

- [`86d4c47`](https://github.com/cezartdev/skills/commit/86d4c470cf0fc92abe1979d903dc4f30ba56ad86) Thanks [@cezartdev](https://github.com/cezartdev)! - Release `git-commit` skill with cross-platform Windows/Linux/macOS support, Python runtime dependencies, and environment diagnostics:
  
  - Add `pyproject.toml` specification declaring Python `>=3.8` requirements and metadata.
  - Implement UTF-8 standard stream reconfigure (`setup_terminal_encoding`) for Windows PowerShell and Command Prompt.
  - Add `check-env` diagnostic CLI command to check Python versions, Git availability, author configurations, and Astral `uv` detection.
  - Provide comprehensive cross-platform installation and troubleshooting documentation for Windows (WinGet, PowerShell), Linux (Fedora `dnf`, Ubuntu/Debian `apt`), and macOS (`brew`).
  - Document Astral `uv` automatic Python version download and isolated execution workflow.
  - Update `scripts/sync-versions.mjs` to automatically synchronize version numbers in `skills/*/pyproject.toml` alongside `docs/*/README.md`.
