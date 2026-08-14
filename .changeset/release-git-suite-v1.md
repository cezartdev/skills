---
"cezartdev-skills": major
---

Release `git` skill suite v1.0.0 (renamed and evolved from `git-commit`):

- **Modular Subcommand Suite**: Introduces `/git commit` (local atomic commit), `/git` / `/git sync` (commit & push), `/git status` (repository health), `/git branch` (conventional branch creator), `/git undo` (safe soft reset), `/git audit` (commit history compliance scoring & rewrites), and `/git check-env`.
- **Pre-Commit Security & Hygiene Gate (Tier 1)**: Automatically scans and blocks commits containing dotenv files (`.env*`), private keys (`*.pem`, `*.key`), credentials, raw tokens in staged diffs, and unresolved merge conflict markers (`<<<<<<<`).
- **10-Step Conventional Commits Validation Gate (Tier 2)**: Enforces strict Conventional Commits structure, imperative English present-tense verbs, scope formatting, and bullet limits.
- **Retrospective Commit History Auditor (`/git audit`)**: Analyzes past $N$ commits, scores repository compliance against Conventional Commits standards, and proposes standardized rewrite suggestions.
- **Cross-Platform & Headless Support**: Zero third-party dependencies (Python standard library $\ge 3.8$), compatible with Linux, Windows (PowerShell/CMD), macOS, and Astral `uv`, with `--json` output across all subcommands.
