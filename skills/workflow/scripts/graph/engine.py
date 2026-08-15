"""Deterministic LangGraph state machine builder and runner with JSON checkpointing."""

import os
import json
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from .nodes import (
        audit_spec_quality_node,
        plan_issues_node,
        test_red_phase_node,
        implement_green_phase_node,
        refactor_phase_node,
        verify_spec_node,
    )
except ImportError:
    from graph.nodes import (
        audit_spec_quality_node,
        plan_issues_node,
        test_red_phase_node,
        implement_green_phase_node,
        refactor_phase_node,
        verify_spec_node,
    )

try:
    from scaffolder import atomic_write_json
except ImportError:
    from ..scaffolder import atomic_write_json


def create_workflow_graph():
    """Builds the StateGraph using LangGraph if available, or returns state runner."""
    try:
        from langgraph.graph import StateGraph, START, END
        
        builder = StateGraph(dict)
        builder.add_node("audit_spec_quality", audit_spec_quality_node)
        builder.add_node("plan_issues", plan_issues_node)
        builder.add_node("test_red_phase", test_red_phase_node)
        builder.add_node("implement_green_phase", implement_green_phase_node)
        builder.add_node("refactor_phase", refactor_phase_node)
        builder.add_node("verify_spec", verify_spec_node)

        builder.add_edge(START, "audit_spec_quality")
        builder.add_edge("audit_spec_quality", "plan_issues")
        builder.add_edge("plan_issues", "test_red_phase")
        builder.add_edge("test_red_phase", "implement_green_phase")
        builder.add_edge("implement_green_phase", "refactor_phase")
        builder.add_edge("refactor_phase", "verify_spec")
        builder.add_edge("verify_spec", END)

        return builder.compile()
    except ImportError:
        # Fallback deterministic sequential runner matching identical graph transitions
        return FallbackStateRunner()


class FallbackStateRunner:
    """Pure-Python deterministic DAG runner mimicking LangGraph transitions."""

    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        curr = audit_spec_quality_node(state)
        curr = plan_issues_node(curr)
        curr = test_red_phase_node(curr)
        curr = implement_green_phase_node(curr)
        curr = refactor_phase_node(curr)
        curr = verify_spec_node(curr)
        return curr


class WorkflowEngine:
    """High-level runner managing LangGraph execution and state.json persistence."""

    def __init__(self, spec_dir: str):
        self.spec_dir = os.path.abspath(spec_dir)
        self.state_file = os.path.join(self.spec_dir, "state.json")
        self.graph = create_workflow_graph()

    def load_state(self) -> Dict[str, Any]:
        """Loads state from state.json or initializes default state."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        spec_name = os.path.basename(self.spec_dir.rstrip("/\\"))
        return {
            "spec_name": spec_name,
            "spec_path": self.spec_dir,
            "archetype": "implement",
            "daemon_name": None,
            "worktree_path": None,
            "branch_name": f"workflow/{spec_name}",
            "current_issue_index": 0,
            "issues": [],
            "dag_step": "INITIALIZED",
            "checkpoint_history": [],
            "quality_gate_passed": False,
            "user_confirmed": False,
            "all_tests_passing": False,
            "spec_verified": False,
            "can_auto_merge": False,
            "memory_logged": False,
            "updated_at": datetime.now().isoformat(),
        }

    def save_state(self, state: Dict[str, Any]):
        """Persists state atomically to state.json."""
        state["updated_at"] = datetime.now().isoformat()
        os.makedirs(self.spec_dir, exist_ok=True)
        try:
            atomic_write_json(self.state_file, state)
        except Exception:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

    def run_step(self, step_name: Optional[str] = None) -> Dict[str, Any]:
        """Executes a graph step and saves checkpoint."""
        state = self.load_state()
        new_state = self.graph.invoke(state)
        self.save_state(new_state)
        return new_state
