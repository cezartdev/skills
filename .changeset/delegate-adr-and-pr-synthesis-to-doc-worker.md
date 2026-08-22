---
"cezartdev-skills": patch
---

refactor(workflow): delegate ADR consolidation and canonical PR summary synthesis exclusively to Doc-Worker

- Eliminate duplicate ADR and PR file generation across pipeline stages by establishing single canonical files (`ADR_decisions.md` and `PR_spec_<spec>.md`).
- Delegate complete documentation responsibility (canonical ADR consolidation, criteria checkboxes, and PR summary generation) to Doc-Worker (Stage 6).
- Streamline Quality-Worker (Stage 5) to pure QA evaluation and Git-Worker (Stage 7) to commit & PR delivery.
