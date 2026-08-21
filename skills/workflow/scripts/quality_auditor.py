"""Pre-execution static consistency auditor and Spec-Kit quality gate."""

import os
import re
from typing import Dict, Any, List, Optional


def audit_spec(spec_path: str) -> Dict[str, Any]:
    """Audits spec.md completeness against functional requirements (what and why)."""
    spec_dir = os.path.abspath(spec_path)
    spec_file = os.path.join(spec_dir, "spec.md") if os.path.isdir(spec_dir) else spec_path

    if not os.path.exists(spec_file):
        return {
            "status": "ERROR",
            "passed": False,
            "score": 0,
            "errors": [f"Spec file not found at {spec_file}"],
            "recommendations": ["Create spec.md using /workflow new <name>"],
            "checks": {},
        }

    with open(spec_file, "r", encoding="utf-8") as f:
        content = f.read()

    errors: List[str] = []
    recommendations: List[str] = []
    checks = {
        "overview": bool(re.search(r"##\s*(\d+\.)?\s*(Overview|Problem Statement|Business Context)", content, re.IGNORECASE)),
        "user_stories": bool(re.search(r"##\s*(\d+\.)?\s*(User Stories|Goals)", content, re.IGNORECASE)),
        "requirements": bool(re.search(r"##\s*(\d+\.)?\s*(Functional Requirements|Scenarios|Requirements)", content, re.IGNORECASE)),
        "edge_cases": bool(re.search(r"##\s*(\d+\.)?\s*(Edge Cases|Error Handling|Error Scenarios)", content, re.IGNORECASE)),
        "acceptance_criteria": bool(re.search(r"##\s*(\d+\.)?\s*Acceptance Criteria", content, re.IGNORECASE)),
    }

    score = sum(20 for k, passed in checks.items() if passed)

    if not checks["overview"]:
        errors.append("Missing Overview & Business Context section in spec.md.")
        recommendations.append("Add '## 1. Overview & Business Context' describing what and why.")

    if not checks["user_stories"]:
        recommendations.append("Add '## 2. User Stories & Goals' with As a / I want / So that format.")

    if not checks["edge_cases"]:
        recommendations.append("Explicitly specify boundary conditions under '## 4. Edge Cases & Error Scenarios'.")

    if not checks["acceptance_criteria"]:
        errors.append("Missing Acceptance Criteria in spec.md.")
        recommendations.append("Define testable checkboxes under '## 5. Acceptance Criteria'.")

    passed = len(errors) == 0 and score >= 60

    return {
        "status": "SUCCESS",
        "spec_file": spec_file,
        "passed": passed,
        "score": score,
        "checks": checks,
        "errors": errors,
        "recommendations": recommendations,
    }


def audit_plan(spec_dir: str) -> Dict[str, Any]:
    """Audits plan.md completeness against technical design requirements."""
    spec_dir = os.path.abspath(spec_dir)
    plan_file = os.path.join(spec_dir, "plan.md")

    if not os.path.exists(plan_file):
        return {
            "status": "MISSING",
            "passed": False,
            "score": 0,
            "plan_file": plan_file,
            "errors": [f"Technical plan file not found at {plan_file}"],
            "recommendations": ["Generate technical design using /workflow plan <spec>"],
            "checks": {},
        }

    with open(plan_file, "r", encoding="utf-8") as f:
        content = f.read()

    errors: List[str] = []
    recommendations: List[str] = []
    checks = {
        "architecture": bool(re.search(r"##\s*(\d+\.)?\s*(Technical Architecture|Topology|Module Design)", content, re.IGNORECASE)),
        "data_models": bool(re.search(r"##\s*(\d+\.)?\s*(Data Models|Schemas|State Contracts)", content, re.IGNORECASE)),
        "interfaces": bool(re.search(r"##\s*(\d+\.)?\s*(Interfaces|Component Contracts|API Contracts)", content, re.IGNORECASE)),
        "dependencies": bool(re.search(r"##\s*(\d+\.)?\s*(Dependencies|Library Selection)", content, re.IGNORECASE)),
        "security_perf": bool(re.search(r"##\s*(\d+\.)?\s*(Security|Performance|Scalability)", content, re.IGNORECASE)),
    }

    score = sum(20 for k, passed in checks.items() if passed)

    if not checks["data_models"]:
        errors.append("Missing Data Models or Schema contracts in plan.md.")
        recommendations.append("Define explicit models and schemas under '## 2. Data Models, Schemas & State Contracts'.")

    if not checks["interfaces"]:
        recommendations.append("Document component interfaces and function signatures under '## 3. Interfaces & Component Contracts'.")

    passed = len(errors) == 0 and score >= 60

    return {
        "status": "SUCCESS",
        "plan_file": plan_file,
        "passed": passed,
        "score": score,
        "checks": checks,
        "errors": errors,
        "recommendations": recommendations,
    }


def audit_tasks(spec_dir: str) -> Dict[str, Any]:
    """Audits tasks breakdown and issues directory completeness."""
    spec_dir = os.path.abspath(spec_dir)
    tasks_file = os.path.join(spec_dir, "tasks.md")
    issues_dir = os.path.join(spec_dir, "issues")

    has_tasks_file = os.path.exists(tasks_file)
    has_issues = False
    issue_files = []

    if os.path.exists(issues_dir):
        issue_files = [f for f in sorted(os.listdir(issues_dir)) if f.endswith(".md") and f != ".gitkeep"]
        has_issues = len(issue_files) > 0

    errors: List[str] = []
    recommendations: List[str] = []

    if not has_tasks_file and not has_issues:
        errors.append("No tasks breakdown found. Run '/workflow tasks <spec>' to decompose plan.md into atomic tasks.")
        recommendations.append("Execute /workflow tasks <spec> to generate tasks.md and issues/*.md.")
        return {
            "status": "MISSING",
            "passed": False,
            "score": 0,
            "tasks_file": tasks_file,
            "issues_count": 0,
            "errors": errors,
            "recommendations": recommendations,
        }

    return {
        "status": "SUCCESS",
        "passed": True,
        "score": 100 if has_tasks_file and has_issues else 70,
        "tasks_file": tasks_file if has_tasks_file else None,
        "issues_count": len(issue_files),
        "issue_files": issue_files,
        "errors": [],
        "recommendations": [],
    }


def analyze_spec_consistency(spec_dir: str, target_dir: str = ".") -> Dict[str, Any]:
    """Statically verifies that no contradictions exist between Constitution, Spec, Plan, and Tasks."""
    spec_dir = os.path.abspath(spec_dir)
    target_dir = os.path.abspath(target_dir)
    spec_name = os.path.basename(spec_dir.rstrip("/\\"))

    spec_res = audit_spec(spec_dir)
    plan_res = audit_plan(spec_dir)
    tasks_res = audit_tasks(spec_dir)

    contradictions: List[str] = []
    warnings: List[str] = []

    # 1. Check Constitution & Memory alignment
    memory_dir = os.path.join(target_dir, ".workflow", "memory")
    coding_pref_file = os.path.join(memory_dir, "coding_preferences.md")
    proj_ctx_file = os.path.join(memory_dir, "project_context.md")

    has_methodology = os.path.exists(os.path.join(memory_dir, "workflow_methodology.md"))
    has_context = os.path.exists(proj_ctx_file)
    has_prefs = os.path.exists(coding_pref_file)

    # 2. Check if Spec has Acceptance Criteria
    spec_file = os.path.join(spec_dir, "spec.md")
    spec_content = ""
    if os.path.exists(spec_file):
        with open(spec_file, "r", encoding="utf-8") as f:
            spec_content = f.read()

    # 3. Check if Plan covers Acceptance Criteria
    plan_file = os.path.join(spec_dir, "plan.md")
    plan_content = ""
    if os.path.exists(plan_file):
        with open(plan_file, "r", encoding="utf-8") as f:
            plan_content = f.read()

    # 4. Check if Tasks cover Plan components
    tasks_file = os.path.join(spec_dir, "tasks.md")
    tasks_content = ""
    if os.path.exists(tasks_file):
        with open(tasks_file, "r", encoding="utf-8") as f:
            tasks_content = f.read()

    # Static Contradiction Checks
    if not spec_res["passed"]:
        contradictions.extend(spec_res["errors"])

    if plan_res["status"] == "MISSING":
        contradictions.append("Technical design 'plan.md' is missing. Run '/workflow plan <spec>' before analyzing.")
    elif not plan_res["passed"]:
        contradictions.extend(plan_res["errors"])

    if tasks_res["status"] == "MISSING":
        contradictions.append("Atomic tasks are missing. Run '/workflow tasks <spec>' before analyzing.")

    # Calculate overall consistency score (0 to 100)
    scores = [
        spec_res.get("score", 0) * 0.35,
        plan_res.get("score", 0) * 0.35,
        tasks_res.get("score", 0) * 0.30,
    ]
    total_score = int(sum(scores))
    passed = len(contradictions) == 0 and total_score >= 80

    return {
        "status": "PASS" if passed else "NEEDS_REFINEMENT",
        "spec_name": spec_name,
        "spec_dir": spec_dir,
        "score": total_score,
        "passed": passed,
        "spec_audit": spec_res,
        "plan_audit": plan_res,
        "tasks_audit": tasks_res,
        "contradictions": contradictions,
        "warnings": warnings,
        "memory_status": {
            "methodology": has_methodology,
            "project_context": has_context,
            "coding_preferences": has_prefs,
        },
    }
