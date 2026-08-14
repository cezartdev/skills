# Project Master Context & Architectural Invariants

**Project Name**: `{{PROJECT_NAME}}`  
**Last Updated**: `{{DATE}}`  
**Manifest Fingerprint**: `{{MANIFEST_HASH}}`

---

## 1. Technology Stack & Runtimes
- **Primary Language(s)**: `{{PRIMARY_LANGUAGES}}`
- **Framework(s)**: `{{FRAMEWORKS}}`
- **Package Manager**: `{{PACKAGE_MANAGER}}`
- **Test Runner & Suite**: `{{TEST_RUNNER}}`
- **Linter & Formatter**: `{{LINTER}}`

---

## 2. Core Architectural Invariants & Rules
1. **Spec-Driven Architecture**: All significant changes are declared in `specs/` and executed via TDD issues.
2. **Worktree Isolation**: Background workers run strictly inside dedicated `.worktrees/` instances.
3. **Quality Gate Compliance**: Tests must pass 100% with no security gate violations prior to merging.

---

## 3. Cumulative Decisions & Historical Rollup Log
<!-- Compacted historical rollup of major technical decisions across archetypes -->

| Date | Archetype | Decision / Milestone | Summary & Impact |
|---|---|---|---|
| {{DATE}} | `explorer` | Initial Stack Survey | Initialized project context and test runner configuration. |
