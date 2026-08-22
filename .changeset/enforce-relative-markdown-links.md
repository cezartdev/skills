---
"cezartdev-skills": patch
---

fix(workflow): enforce relative markdown paths in project context and documentation

- Compute relative paths from `.workflow/memory/` to root files in `explorer.py` to prevent machine-specific absolute `file:///` URLs.
- Replace local absolute links in `README.md` and `skills/git/SKILL.md` with portable repository-relative markdown paths.
