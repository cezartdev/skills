# cezartdev-skills

## 0.2.0

### Minor Changes

- [`86d4c47`](https://github.com/cezartdev/skills/commit/86d4c470cf0fc92abe1979d903dc4f30ba56ad86) Thanks [@cezartdev](https://github.com/cezartdev)! - Release `git-commit` skill with cross-platform Windows/Linux/macOS support, Python runtime dependencies, and environment diagnostics:
  
  - Add `pyproject.toml` specification declaring Python `>=3.8` requirements and metadata.
  - Implement UTF-8 standard stream reconfigure (`setup_terminal_encoding`) for Windows PowerShell and Command Prompt.
  - Add `check-env` diagnostic CLI command to check Python versions, Git availability, author configurations, and Astral `uv` detection.
  - Provide comprehensive cross-platform installation and troubleshooting documentation for Windows (WinGet, PowerShell), Linux (Fedora `dnf`, Ubuntu/Debian `apt`), and macOS (`brew`).
  - Document Astral `uv` automatic Python version download and isolated execution workflow.
  - Update `scripts/sync-versions.mjs` to automatically synchronize version numbers in `skills/*/pyproject.toml` alongside `docs/*/README.md`.
