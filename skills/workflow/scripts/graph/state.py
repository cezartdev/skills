"""State schema definitions for LangGraph-powered deterministic workflow engine."""

from typing import TypedDict, List, Optional, Dict, Any


class IssueState(TypedDict):
    issue_id: str
    title: str
    status: str  # PENDING | RED_PASSED | GREEN_PASSED | REFACTOR_PASSED | COMPLETED | FAILED
    tests_written: List[str]
    files_modified: List[str]
    error_log: Optional[str]


class WorkflowState(TypedDict):
    spec_name: str
    spec_path: str
    archetype: str  # fix | refactor | implement | doc_sync | explorer
    daemon_name: Optional[str]
    worktree_path: Optional[str]
    branch_name: Optional[str]
    current_issue_index: int
    issues: List[IssueState]
    dag_step: str
    checkpoint_history: List[Dict[str, Any]]
    quality_gate_passed: bool
    user_confirmed: bool
    all_tests_passing: bool
    spec_verified: bool
    can_auto_merge: bool
    memory_logged: bool
