---
"cezartdev-skills": patch
---

feat(workflow): standardize Pull Request format, branch hierarchy, and hierarchical PR storage

- Standardize automated PR title and body requested by Workflow Agent (`Git-Worker`) targeting `feat/<spec>` from `feat/<spec>-worker`.
- Organize active Pull Request summaries hierarchically under `.workflow/prs/active/<spec-name>/` and archives under `.workflow/prs/archive/<year>/<spec-name>/`.
- Extract and include specification purpose and functional overview in the standardized PR body.
