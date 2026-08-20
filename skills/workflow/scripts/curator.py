"""Curator module (Backward compatibility alias for orchestrator.py)."""

try:
    from orchestrator import (
        evaluate_pipeline_quality,
        collect_memory_decisions,
        compile_scoped_pr_summary,
        generate_spec_adr,
        generate_specify_adr,
        get_workflow_root,
    )
except ImportError:
    from .orchestrator import (
        evaluate_pipeline_quality,
        collect_memory_decisions,
        compile_scoped_pr_summary,
        generate_spec_adr,
        generate_specify_adr,
        get_workflow_root,
    )
