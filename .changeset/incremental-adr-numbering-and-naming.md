---
"cezartdev-skills": patch
---

feat(workflow): implement incremental 4-digit zero-padded ADR filename format

- Format Architectural Decision Records as `0000_adr_<brief-decision-description>.md` sequentially under `.workflow/specs/active/<spec>/adrs/`.
- Maintain a single cumulative PR summary under `.workflow/prs/active/<spec>/PR_spec_<spec>.md` updated incrementally by Doc-Worker.
