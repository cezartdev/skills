# ⚡ cezartdev / skills

<div align="center">

[![Release](https://img.shields.io/badge/release-v1.0.0-blue.svg?style=for-the-badge&logo=github)](https://github.com/cezartdev/skills/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![Package Manager](https://img.shields.io/badge/pnpm-11.x-orange.svg?style=for-the-badge&logo=pnpm)](https://pnpm.io)
[![Python](https://img.shields.io/badge/python-3.8+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Astral uv](https://img.shields.io/badge/uv-managed-DE5FE9.svg?style=for-the-badge&logo=astral)](https://astral.sh/uv)
[![Agent Skills](https://img.shields.io/badge/Agent_Skills-Compatible-00D084.svg?style=for-the-badge&logo=openai)](https://skills.sh)

<p align="center">
  <strong>A curated collection of deterministic, production-grade AI agent skills and automated developer toolkits.</strong>
</p>

<p align="center">
  Designed for autonomous agents (Antigravity, Claude Code, Cursor, Codex) and human developers seeking security gates, strict standardization, and reliable execution.
</p>

</div>

---

## 🧭 Table of Contents

- [Overview](#-overview)
- [📦 Skills Catalog](#-skills-catalog)
  - [Available Skills](#available-skills)
  - [Planned & In-Development Skills](#planned--in-development-skills)
- [🚀 Quick Start & Installation](#-quick-start--installation)
  - [Installing via `skills-cli`](#installing-via-skills-cli)
  - [Installing via Antigravity / Agent Interfaces](#installing-via-antigravity--agent-interfaces)
- [🏗️ Repository Architecture](#️-repository-architecture)
- [🛠️ Developer & Contributing Workflow](#️-developer--contributing-workflow)
  - [1. Creating a New Skill](#1-creating-a-new-skill)
  - [2. Versioning & Changesets](#2-versioning--changesets)
  - [3. Pre-Flight Validation & Commit](#3-pre-flight-validation--commit)
- [📄 License & Author](#-license--author)

---

## 🌟 Overview

As AI agents take on increasingly complex development tasks, deterministic guardrails and standardized workflows become critical. **`cezartdev/skills`** is a modular repository providing specialized, autonomous skills that equip agents with:

- 🛡️ **Zero-Trust Security & Hygiene Gates**: Active protection against leaking secrets, `.env` files, private keys, or broken merge markers.
- 📏 **Strict Syntax & Convention Enforcement**: Deterministic validation gates (such as 10-step Conventional Commits) eliminating sloppy diffs and non-standard outputs.
- ⚡ **Zero-Overhead Runtimes**: Standard-library lightweight Python engines (`>=3.8`) and `uv`/`pnpm` tooling for instantaneous cross-platform execution.
- 🤖 **Universal Agent Interoperability**: Compatible out-of-the-box with `skills.sh`, Antigravity CLI, Claude Code, Cursor, and custom agentic frameworks.

---

## 📦 Skills Catalog

### Available Skills

| Skill | Version | Description | Runtime | Documentation |
|---|---|---|---|---|
| [`git`](file:///home/cezartdev/Documents/cezartdev/professional/skills/skills/git) | `1.0.0` | **Deterministic Git Operations Suite**: Pre-commit security gate, 10-step Conventional Commits validation, retrospective history auditing (`/git audit`), atomic commits, and safe push workflows. | Python 3.8+ (Zero external deps) | [📖 `docs/git`](file:///home/cezartdev/Documents/cezartdev/professional/skills/docs/git/README.md) |

#### 🔍 `git` Skill Highlights
- **Subcommand Suite**: `/git commit`, `/git sync`, `/git status`, `/git branch`, `/git undo`, and `/git audit`.
- **Security Blocker (Tier 1)**: Intercepts dotenvs, certificates, AWS/private tokens, and `<<<<<<<` merge markers before any commit occurs.
- **Convention Gate (Tier 2)**: Enforces imperative verbs, proper casing, scope rules, and character boundaries.
- **Commit History Compliance (`/git audit`)**: Scans past commit logs, scores repository compliance, and suggests automated standardized rewrites.

---

### Planned & In-Development Skills

| Planned Skill | Target Engine | Purpose & Scope | Status |
|---|---|---|---|
| **`workflow`** | Python + LangGraph | Deterministic state-machine runner for multi-step agent tasks, checkpointing, and step transitions. | 🚧 In Design |
| **`testing`** | Node.js / Python | Automated test generation, snapshot validation, and coverage gatekeeper for autonomous PRs. | 📋 Planned |
| **`release`** | Node / Changesets | Automated changelog curation, release tag orchestrator, and semantic version reconciler. | 📋 Planned |

---

## 🚀 Quick Start & Installation

### Installing via `skills-cli`

You can install any skill directly into your workspace using the standard `skills-cli`:

```bash
# Install the Git skill
npx skills add cezartdev/skills --skill git

# Check available skills in the repository
npx skills list cezartdev/skills
```

> [!IMPORTANT]
> Always provide the mandatory `--skill <name>` argument to ensure `skills-cli` loads the exact skill path rather than resolving against git branch names.

---

### Installing via Antigravity / Agent Interfaces

Skills follow the standard `skills/<skill-name>/SKILL.md` specification. In your agent workspace or configuration:

1. Clone or submodule this repository:
   ```bash
   git clone https://github.com/cezartdev/skills.git
   ```
2. Reference the skill path in your agent settings or invoke directly:
   ```bash
   python3 skills/git/scripts/git_helper.py check-env
   ```

---

## 🏗️ Repository Architecture

The project follows a clean, modular structure where each skill is isolated and self-contained:

```text
skills/
├── .agents/skills/           # Global agent skill symlinks / registrations
├── .changeset/               # Semantic versioning changesets & configuration
├── .github/workflows/        # Automated release and CI verification pipelines
├── docs/                     # Comprehensive developer and agent documentation
│   └── git/
│       └── README.md         # Full command reference, troubleshooting & examples
├── scripts/
│   └── sync-versions.mjs     # Version synchronization engine across docs & manifests
├── skills/                   # Core skills directory
│   └── git/
│       ├── SKILL.md          # Skill instruction specification & agent contract
│       ├── pyproject.toml    # Python environment & metadata specification
│       └── scripts/
│           └── git_helper.py # Deterministic Git CLI helper & validation engine
├── AGENTS.md                 # Agent operating standards, rules & release workflows
├── CHANGELOG.md              # Automated semantic release notes
├── package.json              # Root workspace manifest & version source of truth
└── pnpm-lock.yaml            # pnpm lockfile
```

---

## 🛠️ Developer & Contributing Workflow

We maintain rigorous standards for code quality, dependency management, and releases. Please review [AGENTS.md](file:///home/cezartdev/Documents/cezartdev/professional/skills/AGENTS.md) for full operating guidelines.

### 1. Creating a New Skill

1. Create the skill directory under `skills/<skill-name>/`:
   - `skills/<skill-name>/SKILL.md`: Mandatory YAML frontmatter (`name`, `description`) + markdown instructions.
   - `skills/<skill-name>/scripts/`: Helper scripts (Python or Node.js).
   - `skills/<skill-name>/pyproject.toml` (if using Python) or `package.json` (if using Node.js).
2. Create complete documentation under `docs/<skill-name>/README.md`.
3. Add the skill to the catalog in this `README.md`.

### 2. Versioning & Changesets

This repository uses **Changesets** for automated semantic versioning and release notes:

```bash
# Option A: Interactive CLI (Human developers)
pnpm changeset

# Option B: Headless Agent declaration (write to .changeset/<slug>.md)
---
"cezartdev-skills": minor
---

Add new deterministic workflow runner skill
```

### 3. Pre-Flight Validation & Commit

Use the built-in `git` helper to validate compliance and commit:

```bash
python3 skills/git/scripts/git_helper.py commit \
  -t feat \
  -s workflow \
  -m "implement deterministic state machine runner" \
  -b "add LangGraph execution engine for structured multi-step tasks"
```

Verify version synchronization:
```bash
pnpm check-version
```

---

## 📄 License & Author

- **Author**: [Cezar (@cezartdev)](https://github.com/cezartdev)
- **License**: [MIT](LICENSE) — free for use in open-source and commercial agent systems.
