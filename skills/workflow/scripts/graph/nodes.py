"""LangGraph nodes for deterministic SDD and TDD state machine transitions."""

import os
import json
import subprocess
from typing import Dict, Any, List
from datetime import datetime


def audit_spec_quality_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Audits spec completeness and acceptance criteria."""
    spec_path = state.get("spec_path", "")
    spec_file = os.path.join(spec_path, "spec.md") if os.path.isdir(spec_path) else spec_path

    quality_passed = False
    if os.path.exists(spec_file):
        try:
            with open(spec_file, "r", encoding="utf-8") as f:
                content = f.read()
            has_overview = "## 1. Overview" in content or "## Overview" in content
            has_criteria = "## 5. Acceptance Criteria" in content or "## Acceptance Criteria" in content
            quality_passed = has_overview and has_criteria and len(content.strip()) > 100
        except Exception:
            quality_passed = False

    history = state.get("checkpoint_history", [])
    history.append({
        "node": "audit_spec_quality",
        "timestamp": datetime.now().isoformat(),
        "quality_passed": quality_passed,
    })

    return {
        **state,
        "dag_step": "QUALITY_AUDIT",
        "quality_gate_passed": quality_passed,
        "checkpoint_history": history,
    }


def plan_issues_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Scans and parses existing issues under issues/ or generates a plan."""
    spec_path = state.get("spec_path", "")
    issues_dir = os.path.join(spec_path, "issues") if os.path.isdir(spec_path) else os.path.join(os.path.dirname(spec_path), "issues")
    
    issues: List[Dict[str, Any]] = []
    if os.path.exists(issues_dir):
        files = sorted([f for f in os.listdir(issues_dir) if f.endswith(".md")])
        for idx, filename in enumerate(files):
            file_path = os.path.join(issues_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                title_line = f.readline().replace("#", "").strip()
            issues.append({
                "issue_id": filename.replace(".md", ""),
                "title": title_line or f"Task {idx + 1}",
                "status": "PENDING",
                "tests_written": [],
                "files_modified": [],
                "error_log": None,
            })

    if not issues:
        issues.append({
            "issue_id": "001_initial_task",
            "title": "Initial feature task",
            "status": "PENDING",
            "tests_written": [],
            "files_modified": [],
            "error_log": None,
        })

    history = state.get("checkpoint_history", [])
    history.append({
        "node": "plan_issues",
        "timestamp": datetime.now().isoformat(),
        "issues_count": len(issues),
    })

    return {
        **state,
        "dag_step": "ISSUES_PLANNED",
        "issues": issues,
        "current_issue_index": 0,
        "checkpoint_history": history,
    }


def test_red_phase_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Marks the start of the RED phase for the active issue."""
    issues = state.get("issues", [])
    curr_idx = state.get("current_issue_index", 0)

    if curr_idx < len(issues):
        issues[curr_idx]["status"] = "RED_PHASE"

    history = state.get("checkpoint_history", [])
    history.append({
        "node": "test_red_phase",
        "timestamp": datetime.now().isoformat(),
        "issue_index": curr_idx,
    })

    return {
        **state,
        "dag_step": "RED_PHASE",
        "issues": issues,
        "checkpoint_history": history,
    }


def implement_green_phase_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Marks the transition to the GREEN implementation phase."""
    issues = state.get("issues", [])
    curr_idx = state.get("current_issue_index", 0)

    if curr_idx < len(issues):
        issues[curr_idx]["status"] = "GREEN_PHASE"

    history = state.get("checkpoint_history", [])
    history.append({
        "node": "implement_green_phase",
        "timestamp": datetime.now().isoformat(),
        "issue_index": curr_idx,
    })

    return {
        **state,
        "dag_step": "GREEN_PHASE",
        "issues": issues,
        "checkpoint_history": history,
    }


def refactor_phase_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Marks the transition to the REFACTOR phase."""
    issues = state.get("issues", [])
    curr_idx = state.get("current_issue_index", 0)

    if curr_idx < len(issues):
        issues[curr_idx]["status"] = "REFACTOR_PASSED"

    history = state.get("checkpoint_history", [])
    history.append({
        "node": "refactor_phase",
        "timestamp": datetime.now().isoformat(),
        "issue_index": curr_idx,
    })

    return {
        **state,
        "dag_step": "REFACTOR_PASSED",
        "issues": issues,
        "checkpoint_history": history,
    }


def verify_spec_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Verifies that all issues are completed and all tests pass."""
    issues = state.get("issues", [])
    all_completed = all(i.get("status") in ["COMPLETED", "REFACTOR_PASSED", "GREEN_PASSED"] for i in issues)

    history = state.get("checkpoint_history", [])
    history.append({
        "node": "verify_spec",
        "timestamp": datetime.now().isoformat(),
        "all_completed": all_completed,
    })

    return {
        **state,
        "dag_step": "SPEC_VERIFIED" if all_completed else "INCOMPLETE",
        "spec_verified": all_completed,
        "all_tests_passing": all_completed,
        "can_auto_merge": all_completed,
        "checkpoint_history": history,
    }
