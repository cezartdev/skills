# cezartdev-skills

## 1.10.0

### Minor Changes

- [`9057e69`](https://github.com/cezartdev/skills/commit/9057e6950e38d14c62d394daa069c86ffcadfda5) Thanks [@cezartdev](https://github.com/cezartdev)! - Generate Architectural Decision Records (ADRs) during specification grilling sessions (`/workflow specify`) to formally audit architecture, data schemas, and trade-offs co-authored in `spec.md`.

- [`dfa1136`](https://github.com/cezartdev/skills/commit/dfa1136816c08e8fe193913e02ff23466f622039) Thanks [@cezartdev](https://github.com/cezartdev)! - Introduce `.workflow/specs/active/` directory hierarchy for in-flight specifications, scaffold `.workflow/memory/workflow_methodology.md`, and add intelligent detection and injection of agent rule directives into `AGENTS.md` and related instruction files upon `workflow init`.

## 1.9.0

### Minor Changes

- [`e58e579`](https://github.com/cezartdev/skills/commit/e58e579c1c07be6ab9f0f18ada4b8acee4c701ab) Thanks [@cezartdev](https://github.com/cezartdev)! - Flatten `.workflow/specs/` directory layout by eliminating `bugs/`, `docs/`, `refactor/`, and `features/` namespaces; specifications now live directly in `.workflow/specs/<spec>/` as agnostic feature containers with co-located ADRs.

## 1.8.0

### Minor Changes

- [`e4de2d9`](https://github.com/cezartdev/skills/commit/e4de2d9940b65702c8d8de4b825527282f10feae) Thanks [@cezartdev](https://github.com/cezartdev)! - Implement deterministic LangGraph state machine pipeline runner (`pipeline_graph.py`), self-contained commit validator & security gate (`commit_validator.py`), and modernize `workflow.json` scaffold to Version 2.0.

- [`376766e`](https://github.com/cezartdev/skills/commit/376766ed8d1f1b8ecd8275e1be621107f5da994a) Thanks [@cezartdev](https://github.com/cezartdev)! - Streamline project memory structure to `coding_preferences.md`, `project_context.md`, and indexed sequential documentation notes in `.workflow/memory/docs/` (`workflow memory add`).

### Patch Changes

- [`af186fe`](https://github.com/cezartdev/skills/commit/af186fe068d1b57bf5505ce52000418b3f938f58) Thanks [@cezartdev](https://github.com/cezartdev)! - Add deterministic Protected Branch Gate (`main`/`master`) on `/workflow run`, preventing direct commits/pushes to production branches and mandating an interactive grilling session for feature branch confirmation.

- [`b8205ed`](https://github.com/cezartdev/skills/commit/b8205ed873c201707e50540960661ab20c193a5b) Thanks [@cezartdev](https://github.com/cezartdev)! - Enforce strict Zero-Comments code policy across all workflow subagent prompts and execution directives (no `//`, `#`, or `""" """` in generated code unless explicitly requested).

## 1.7.0

### Minor Changes

- [`0cba65c`](https://github.com/cezartdev/skills/commit/0cba65c15356c8eca9ca78cb3d42e654d3986bbc) Thanks [@cezartdev](https://github.com/cezartdev)! - Implement worker branch scoping (`<spec>-<worker>`), spec-based auto-merge targeting, and Curator subagent unification into `<spec>-curator-worker` with PR suggestions to `<spec>`.

- [`51e4e5e`](https://github.com/cezartdev/skills/commit/51e4e5edc58aff1e824e79de7555a2c921082e54) Thanks [@cezartdev](https://github.com/cezartdev)! - Enforce strict hierarchical worktree structure (`.workflow/worktrees/<branch-name>/<worker-name>/`) and align branch names directly with spec functionality.

- [`d722918`](https://github.com/cezartdev/skills/commit/d722918cd62ad7dc170d4f54e4c35f14563e7e51) Thanks [@cezartdev](https://github.com/cezartdev)! - Rename default daemon subagents to `fix-worker`, `refactor-worker`, and `doc-worker`, enforce spec-dependent worktrees, and add interactive branch grilling directives.

- [`91a016b`](https://github.com/cezartdev/skills/commit/91a016bc335f97bf7e609b6057d1ac6cacff2e52) Thanks [@cezartdev](https://github.com/cezartdev)! - Implement standardized semantic git branch creation (`feat/*`, `fix/*`, `refactor/*`, `docs/*`) automatically alongside physical Git Worktrees and specification scaffolding.

- [`08d7479`](https://github.com/cezartdev/skills/commit/08d7479321c4f300eeb22189b50fcaad53e779c4) Thanks [@cezartdev](https://github.com/cezartdev)! - Implement deterministic 4-stage sequential subagent pipeline runner (`workflow run <spec>`), automated MADR Architectural Decision Record generation, and streamlined positional CLI commands (`status`, `stop`, `clean`, `curate`).

## 1.6.0

### Minor Changes

- [`477fb54`](https://github.com/cezartdev/skills/commit/477fb544fee9a60e95205808c7ff436c12a07040) Thanks [@cezartdev](https://github.com/cezartdev)! - Implement fixed-delay execution model and zero-overlap concurrency locks for background daemons so execution intervals start counting strictly after cycle completion, preventing overlapping agents.

### Patch Changes

- [`544bad0`](https://github.com/cezartdev/skills/commit/544bad0d261453b0dadabfcc8f81f9a89f674566) Thanks [@cezartdev](https://github.com/cezartdev)! - Audit and harden `workflow` skill for cross-platform compatibility across Linux, macOS (Darwin), and Windows: add Windows `tasklist` and `taskkill` process management, robust `safe_rmtree` with read-only unlock handlers, atomic write retry on transient file locks, and fix `WorkflowEngine` class method scoping.

- [`afca071`](https://github.com/cezartdev/skills/commit/afca071d7ab82f286238cf2ffc09552339262b30) Thanks [@cezartdev](https://github.com/cezartdev)! - Normalize `worktree_path` in `daemons.json` and `spec_path` in `state.json` to clean project-relative paths (`.workflow/...`) to preserve user privacy and portability across machines.

## 1.5.1

### Patch Changes

- [`85fdc5c`](https://github.com/cezartdev/skills/commit/85fdc5c3d6efe2ec993296d62f2f68cb193a6e5e) Thanks [@cezartdev](https://github.com/cezartdev)! - Automatically generate `.gitkeep` placeholder files inside all base `.workflow/` scaffold directories (`specs/`, `memory/`, `prs/`, `issues/`) so Git preserves empty folder structures.

- [`f75bd15`](https://github.com/cezartdev/skills/commit/f75bd15a9a1eeaf59ac2b6d434d87e440858d87c) Thanks [@cezartdev](https://github.com/cezartdev)! - Automatically remove `.gitkeep` files as soon as real files or specifications are created inside `.workflow/` subdirectories, and reconcile placeholders if directories become empty.

## 1.5.0

### Minor Changes

- [`45f4502`](https://github.com/cezartdev/skills/commit/45f45027f42bbc4c4c944ac70dafede8138f2007) Thanks [@cezartdev](https://github.com/cezartdev)! - Add multi-machine host affinity tagging, interactive daemon blueprint creation (`workflow daemon create`), and dynamic schedule/iteration configuration modifier (`workflow daemon set`).

### Patch Changes

- [`7a2e8ef`](https://github.com/cezartdev/skills/commit/7a2e8ef12fe5d4d7d05ec24c0fdd89394c3dc5f3) Thanks [@cezartdev](https://github.com/cezartdev)! - Implement immediate stop gate in daemon cycle execution and direct background schedule timer cancellation on daemon stop.

## 1.4.1

### Patch Changes

- [`7f6f287`](https://github.com/cezartdev/skills/commit/7f6f2877e79612565ea8e45059e39e08d439d9ca) Thanks [@cezartdev](https://github.com/cezartdev)! - Harden git skill scripts and pattern definitions to eliminate Snyk SAST false-positives on secret scanning regexes and shell arguments.

## 1.4.0

### Minor Changes

- [`c538044`](https://github.com/cezartdev/skills/commit/c53804406a5692d78bd655c627038f9d4231a0d3) Thanks [@cezartdev](https://github.com/cezartdev)! - Enhance /workflow explore to automatically analyze codebase style conventions, linters, and generate 00_coding_preferences.md.

### Patch Changes

- [`d26b9c7`](https://github.com/cezartdev/skills/commit/d26b9c7b726bc3aa109d9be65faac864d78e6ec6) Thanks [@cezartdev](https://github.com/cezartdev)! - Fix daemon interval resolution to prioritize workflow.json settings and integrate native schedule cron tool for recurring cycles.

## 1.3.3

### Patch Changes

- [`6affdde`](https://github.com/cezartdev/skills/commit/6affddeb8b5af225354acaa361b24d43f5b6295f) Thanks [@cezartdev](https://github.com/cezartdev)! - Implement pre-cycle base branch synchronization (sync_worktree_with_base) and auto-merge gate across daemon cycles.

- [`a5e2e5e`](https://github.com/cezartdev/skills/commit/a5e2e5e754f4457b51c1476c447638c60acca5f2) Thanks [@cezartdev](https://github.com/cezartdev)! - Implement native subagent daemon continuous loop, git pre-flight auto-init, clean SDD planning, and /workflow daemon list blueprint catalog.

- [`51defeb`](https://github.com/cezartdev/skills/commit/51defeb94c8dda22faaa041602c5382dc60c2611) Thanks [@cezartdev](https://github.com/cezartdev)! - Implement post-reboot self-healing reconciliation, PID recycling defense, atomic JSON writing, path traversal sanitization, and dirty tree auto-merge protection.

## 1.3.2

### Patch Changes

- [`0ab14cd`](https://github.com/cezartdev/skills/commit/0ab14cd31932d3a5ee245f37d81c2613f24920f9) Thanks [@cezartdev](https://github.com/cezartdev)! - Add context-aware suggested next command prompts across all workflow runner subcommands.

- [`ab3b39f`](https://github.com/cezartdev/skills/commit/ab3b39fad79c64cbc531f8a4b9deedad3b43c813) Thanks [@cezartdev](https://github.com/cezartdev)! - Implement ecosystem-aware test runner fallbacks, native subagent dispatch protocol, and standardized token-efficient table outputs in English.

- [`a3bee32`](https://github.com/cezartdev/skills/commit/a3bee32a0ede8467002cd8428a06be0acd2e6d62) Thanks [@cezartdev](https://github.com/cezartdev)! - Standardize git skill execution to uv run with cross-platform native launchers.

- [`969beca`](https://github.com/cezartdev/skills/commit/969becaf1e1d8a29f95b15f0bdf6d7051d19ca66) Thanks [@cezartdev](https://github.com/cezartdev)! - Refine curator PR metadata handling for empty rollups and ignore .workflow runtime directories.

- [`bbc88b4`](https://github.com/cezartdev/skills/commit/bbc88b4483f39ae4d17db63566ec4ac3c5b82812) Thanks [@cezartdev](https://github.com/cezartdev)! - Standardize /workflow list output to a deterministic, concise command reference table.

## 1.3.1

### Patch Changes

- [`68d966f`](https://github.com/cezartdev/skills/commit/68d966fd71d9f85f6be39cbfa1ade677014d5a0a) Thanks [@cezartdev](https://github.com/cezartdev)! - Pre-configure auto-fixer, refactor-worker, and doc-sync base daemons in workflow.config.json and scaffolder.

- [`5eaa454`](https://github.com/cezartdev/skills/commit/5eaa454483c43c4056167b550bf4980a1d31a2c9) Thanks [@cezartdev](https://github.com/cezartdev)! - Implement interactive Grilling Session protocol in specify prompt, enforce English across all assets, and mandate uv run for AI agents.

## 1.3.0

### Minor Changes

- [`72a8950`](https://github.com/cezartdev/skills/commit/72a895018e999479ae9dcc5a9d1f162f53856602) Thanks [@cezartdev](https://github.com/cezartdev)! - Encapsulate workflow files inside .workflow/ directory, add /workflow specify for Spec-Kit co-authoring, /workflow chat for macro dialogue, /workflow list cheat-sheet, and Smart Path Resolver.

- [`f3337d6`](https://github.com/cezartdev/skills/commit/f3337d6848a63922531eaa97313641aa6a0b8d41) Thanks [@cezartdev](https://github.com/cezartdev)! - Implement autonomous background daemon subagents with cron scheduling, 3-phase Anti-Zombie cleanup, Universal Subagent Dispatch, and the Curator Subagent for release PR rollups.

- [`2de07a6`](https://github.com/cezartdev/skills/commit/2de07a6be7cc1de5d0c408ce73494c2167707509) Thanks [@cezartdev](https://github.com/cezartdev)! - Implement Multi-PR catalog in .workflow/prs/, polyglot test detection (Python, Rust, Go, Node, Java, .NET), and deterministic pipelines with daemon pause/resume controls.

### Patch Changes

- [`26052b4`](https://github.com/cezartdev/skills/commit/26052b4a7e7fb9d51f4cca0be63e924da6c6a0da) Thanks [@cezartdev](https://github.com/cezartdev)! - Standardize CLI execution documentation to prioritize uv run across Linux, Windows, and macOS.

## 1.2.0

### Minor Changes

- [`31e1c1f`](https://github.com/cezartdev/skills/commit/31e1c1fe531479cb78962ba70318e0ae1e9c418a) Thanks [@cezartdev](https://github.com/cezartdev)! - Standardize workflow skill structure to official AgentSkills.io specification (assets/ and references/), add specs/features/ hierarchy, agnostic test runner discovery, and cross-platform launchers (PowerShell/Bash).

## 1.1.0

### Minor Changes

- [`bdcca8b`](https://github.com/cezartdev/skills/commit/bdcca8b837ed6641c953b1037881769d54609502) Thanks [@cezartdev](https://github.com/cezartdev)! - Implement workflow skill: deterministic LangGraph state machine runner, Spec-Driven & Test-Driven Development (SDD/TDD), zero-collision hierarchical markdown memory with 00-10 compaction, autonomous codebase explorer with tech drift detection, and multi-daemon physical Git Worktree isolation.

### Patch Changes

- [`e27b9d4`](https://github.com/cezartdev/skills/commit/e27b9d482815e5e48803cfdbbb60b0953b9068fc) Thanks [@cezartdev](https://github.com/cezartdev)! - Add comprehensive repository README documenting skills catalog, installation, and architecture

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
