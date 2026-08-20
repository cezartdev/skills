---
"cezartdev-skills": patch
---

Implement automatic `.gitkeep` lifecycle reconciliation (`reconcile_all_gitkeeps`): automatically deletes `.gitkeep` placeholders whenever real files or subdirectories exist in `.workflow/` catalogs, and restores them only when folders are completely empty.
