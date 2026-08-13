# Git Commit Skill Documentation

> **Skill**: `git-commit`  
> **Author**: `cezartdev`  
> **Version**: `0.1.0`  
> **Status**: `Active`  
> **License**: `MIT`  

---

## 1. Overview

The **`git-commit`** skill provides an automated, deterministic workflow for creating standardized **Conventional Commits** in English.

It is designed for AI agents and human developers to eliminate non-standard commit messages, enforce strict length constraints, validate English imperative verbs, and guarantee pre-flight validation before any commit touches the repository history.

---

## 2. Key Features

- **Strict Type Whitelist**: Accepts only 6 semantic types (`feat`, `fix`, `docs`, `refactor`, `chore`, `test`).
- **Character Length Controls**:
  - Minimum description length: $\ge 10$ characters.
  - Maximum header length: $\le 120$ characters.
  - Maximum body bullet length: $\le 120$ characters.
- **English Imperative Verbs**: Requires the description to begin with a recognized lowercase English imperative verb (`add`, `update`, `fix`, `implement`, `refactor`, `remove`, `configure`, `create`, `ensure`, etc.). Non-English words (e.g. `añadir`) or past tenses (`added`) are rejected.
- **No Trailing Periods**: Enforces clean subject lines without trailing `.`.
- **Pre-Flight Validation Gate**: Analyzes the commit message string across 9 modular validation steps *before* executing `git commit`.
- **Safe Execution Runner**: Ensures zero invalid commits can be created.

---

## 3. Directory Layout

```text
skills/git-commit/
├── SKILL.md                 # Complete agent instructions and specifications
└── scripts/
    └── commit_helper.py     # Python CLI validator & safe commit runner
```

---

## 4. Prerequisites

- **Python 3.8+** (Uses standard library `argparse`, `re`, `subprocess`, `sys`).
- **Git** configured with `user.name` and `user.email`.

---

## 5. Installation & Consumption via `skills-cli`

You can install this skill into any target repository using the standard `skills-cli`:

### A. Install specific skill
```bash
npx skills add cezartdev/skills --skill git-commit
```
*(Or via full URL: `npx skills add https://github.com/cezartdev/skills --skill git-commit`)*

### B. List available skills in repository
```bash
npx skills add cezartdev/skills --list
```

### ⚠️ Common Syntax Pitfall & Troubleshooting
> [!WARNING]
> **Always use `--skill <name>` flag**: Do not pass the skill name as a positional argument (e.g. `npx skills add cezartdev/skills git-commit`). 
> 
> The CLI treats positional arguments as a **git branch or tag name** (e.g. `(git-commit)`), causing a `No valid skills found. Skills require a SKILL.md with name and description` error when that branch does not exist.

---

## 6. CLI Usage & Commands

The skill provides the `commit_helper.py` script with three primary commands:

### A. Draft Commit Messages (`draft`)
Inspects the current working tree, lists staged and unstaged files, and provides template suggestions:

```bash
python3 skills/git-commit/scripts/commit_helper.py draft
```

**Example Output**:
```text
======================================================================
 GIT STATUS SUMMARY & DRAFT SUGGESTIONS
======================================================================
Staged files (2):
  + skills/git-commit/SKILL.md
  + skills/git-commit/scripts/commit_helper.py

Unstaged/Untracked files (0):

Whitelisted Types: chore, docs, feat, fix, refactor, test
Template: <type>(<scope>): <imperative_verb> <description (10-120 chars)>
======================================================================
```

---

### B. Validate Commit Message Strings (`validate`)
Runs the full 9-step pre-flight validation pipeline on any candidate string and returns a detailed report:

```bash
python3 skills/git-commit/scripts/commit_helper.py validate "feat(git-commit): implement modular step validation pipeline"
```

**Validation Report**:
```text
======================================================================
 COMMIT MESSAGE PRE-FLIGHT VALIDATION REPORT
======================================================================
Candidate Header: feat(git-commit): implement modular step validation pipeline
----------------------------------------------------------------------
Step 1/9 validate_structure                  [PASS] : Structure parsed successfully: type='feat', scope='git-commit'
Step 2/9 validate_type                       [PASS] : Type 'feat' is whitelisted
Step 3/9 validate_scope                      [PASS] : Scope 'git-commit' is valid kebab-case
Step 4/9 validate_header_length              [PASS] : Header length (60/120 chars) within limit
Step 5/9 validate_description_length         [PASS] : Description (42 chars >= 10) is sufficiently detailed
Step 6/9 validate_no_trailing_period         [PASS] : No trailing period in header
Step 7/9 validate_english_imperative_verb    [PASS] : Leading verb 'implement' is an approved English imperative verb
Step 8/9 validate_casing_and_spacing         [PASS] : Casing and spacing format are clean
Step 9/9 validate_body_bullets               [PASS] : No body lines provided (optional)
======================================================================
>>> RESULT: 100% VALIDATED. Message is safe for git commit.
======================================================================
```

---

### C. Safe Commit Execution (`commit`)
Validates the message components first, ensures staged changes exist, and executes `git commit` atomically:

#### Single-line Commit:
```bash
python3 skills/git-commit/scripts/commit_helper.py commit \
  -t feat \
  -s git-commit \
  -m "implement modular step validation pipeline"
```

#### Multiline Commit with Bullet Points:
```bash
python3 skills/git-commit/scripts/commit_helper.py commit \
  -t feat \
  -s git-commit \
  -m "implement modular step validation pipeline" \
  -b "add 8 validation functions for types, lengths, and verbs" \
  -b "provide pre-flight validation report and safe commit runner"
```

#### Raw Message Commit:
```bash
python3 skills/git-commit/scripts/commit_helper.py commit \
  --raw "docs(git-commit): add comprehensive skill documentation"
```

---

## 7. Validation Rule Reference

| Step | Function | Allowed / Requirement |
|---|---|---|
| 1 | `validate_structure` | `<type>(<scope>): <description>` |
| 2 | `validate_type` | `feat`, `fix`, `docs`, `refactor`, `chore`, `test` |
| 3 | `validate_scope` | `^[a-z0-9]+(-[a-z0-9]+)*$` (lowercase alphanumeric/kebab-case) |
| 4 | `validate_header_length` | Total header $\le 120$ characters |
| 5 | `validate_description_length`| Description $\ge 10$ characters |
| 6 | `validate_no_trailing_period`| Must NOT end with `.` |
| 7 | `validate_english_imperative_verb`| First word in description must be an English imperative verb |
| 8 | `validate_casing_and_spacing`| Starts lowercase, single spaces, no snake_case prose |
| 9 | `validate_body_bullets`| Each body line must start with `- ` and be $\le 120$ characters |

---

## 8. AI Agent Execution Flow

When an AI agent is requested to create a commit:
1. Agent runs `git status -s` and stages intentional files (`git add <files>`).
2. Agent runs `python3 skills/git-commit/scripts/commit_helper.py draft` to review staged files and pick type/scope.
3. Agent prepares candidate header and bullets.
4. Agent runs `python3 skills/git-commit/scripts/commit_helper.py commit -t <type> -s <scope> -m "<description>" [-b "<bullet>"]`.
5. If any validation fails, the agent reads the report, adjusts the message accordingly, and re-submits until successful.
