---
"cezartdev-skills": patch
---

Audit and harden `workflow` skill for cross-platform compatibility across Linux, macOS (Darwin), and Windows: add Windows `tasklist` and `taskkill` process management, robust `safe_rmtree` with read-only unlock handlers, atomic write retry on transient file locks, and fix `WorkflowEngine` class method scoping.
