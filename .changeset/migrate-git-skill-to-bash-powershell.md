---
"cezartdev-skills": minor
---

Refactor git skill to native Bash and PowerShell scripts, eliminating Python runtime dependencies

- Replace `git_helper.py` with pure POSIX `git_helper.sh` (Linux, macOS, Git Bash) and native `git_helper.ps1` (Windows PowerShell).
- Streamline command ergonomics: default `/git` workflow executes commit + push sync, `/git commit` executes local-only commit, and accepts direct message arguments.
- Allow template environment files (`.env.example`, `.env.sample`, `.env.template`, `.env.dist`, `.env.ci`) in pre-commit security gates while strictly blocking real `.env` files.
- Preserve 100% of existing validation gates, Conventional Commits 10-step checks, audit command, status, undo, and branch management.
