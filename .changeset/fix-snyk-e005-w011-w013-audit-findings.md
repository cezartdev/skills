---
"cezartdev-skills": patch
---

fix(workflow): resolve Snyk audit findings E005, W011, and W013 for skills.sh compliance

- Remove external installer URLs in launcher scripts and documentation (E005).
- Strengthen multi-layer prompt injection filtering and HTML sanitization on ingested markdown files (W011).
- Neutralize process and service terminology in SKILL.md and documentation to clarify safe local repository scoping (W013).
