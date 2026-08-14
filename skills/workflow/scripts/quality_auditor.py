"""Pre-execution quality gate for spec and issue validation."""

import os
from typing import Dict, Any, List


def audit_spec(spec_path: str) -> Dict[str, Any]:
    """Audits spec.md completeness against core quality criteria."""
    spec_dir = os.path.abspath(spec_path)
    spec_file = os.path.join(spec_dir, "spec.md") if os.path.isdir(spec_dir) else spec_dir

    if not os.path.exists(spec_file):
        return {
            "status": "ERROR",
            "passed": False,
            "score": 0,
            "errors": [f"Spec file not found at {spec_file}"],
            "recommendations": ["Create spec.md using /workflow new <name>"],
        }

    with open(spec_file, "r", encoding="utf-8") as f:
        content = f.read()

    errors: List[str] = []
    recommendations: List[str] = []
    checks = {
        "overview": "## 1. Overview" in content or "## Overview" in content,
        "goals": "## 2. User Stories" in content or "## Goals" in content or "User Stories" in content,
        "architecture": "## 3. Technical Architecture" in content or "## Architecture" in content,
        "edge_cases": "## 4. Edge Cases" in content or "## Edge Cases" in content,
        "acceptance_criteria": "## 5. Acceptance Criteria" in content or "## Acceptance Criteria" in content,
    }

    score = sum(20 for k, passed in checks.items() if passed)

    if not checks["overview"]:
        errors.append("Missing Overview & Problem Statement section.")
        recommendations.append("Add '## 1. Overview & Problem Statement' describing the business context.")

    if not checks["edge_cases"]:
        recommendations.append("Explicitly specify error scenarios and boundary conditions under '## 4. Edge Cases'.")

    if not checks["acceptance_criteria"]:
        errors.append("Missing Acceptance Criteria.")
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
