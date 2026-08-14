"""Scaffolder module: initializes target project structure and creates new specs from embedded templates."""

import os
import json
import shutil
from typing import Optional, Dict, Any


def get_skill_resource_dir() -> str:
    """Returns the absolute path to skills/workflow/resources."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(script_dir, "..", "resources"))


def scaffold_init(target_dir: str = ".") -> Dict[str, Any]:
    """Initializes workflow structure in target directory."""
    target_dir = os.path.abspath(target_dir)
    res_dir = get_skill_resource_dir()
    templates_dir = os.path.join(res_dir, "templates")

    # 1. Create specs/ and memory/ directories
    specs_dir = os.path.join(target_dir, "specs")
    memory_dir = os.path.join(target_dir, "memory")
    os.makedirs(specs_dir, exist_ok=True)
    os.makedirs(memory_dir, exist_ok=True)
    os.makedirs(os.path.join(memory_dir, "fix"), exist_ok=True)
    os.makedirs(os.path.join(memory_dir, "refactor"), exist_ok=True)
    os.makedirs(os.path.join(memory_dir, "implement"), exist_ok=True)
    os.makedirs(os.path.join(memory_dir, "doc_sync"), exist_ok=True)

    # 2. Scaffold root workflow.json if not present
    config_file = os.path.join(target_dir, "workflow.json")
    config_created = False
    if not os.path.exists(config_file):
        template_config = os.path.join(templates_dir, "workflow.config.json")
        if os.path.exists(template_config):
            with open(template_config, "r", encoding="utf-8") as f:
                content = f.read().replace("{{TEST_COMMAND}}", "pnpm test")
            with open(config_file, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            default_conf = {
                "version": "1.0",
                "test_runner": {"command": "pnpm test", "args": ["--run"]},
                "worktrees": {"directory": ".worktrees", "auto_clean_on_merge": True}
            }
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(default_conf, f, indent=2)
        config_created = True

    # 3. Add .worktrees/ to .gitignore
    gitignore_file = os.path.join(target_dir, ".gitignore")
    gitignore_updated = False
    worktree_entry = ".worktrees/"
    if os.path.exists(gitignore_file):
        with open(gitignore_file, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        if worktree_entry not in lines and ".worktrees" not in lines:
            with open(gitignore_file, "a", encoding="utf-8") as f:
                f.write(f"\n# Git Worktree isolation for workflow daemons\n{worktree_entry}\n")
            gitignore_updated = True
    else:
        with open(gitignore_file, "w", encoding="utf-8") as f:
            f.write(f"# Git Worktree isolation for workflow daemons\n{worktree_entry}\n")
        gitignore_updated = True

    return {
        "status": "SUCCESS",
        "target_dir": target_dir,
        "specs_dir": specs_dir,
        "memory_dir": memory_dir,
        "config_file": config_file,
        "config_created": config_created,
        "gitignore_updated": gitignore_updated,
    }


def scaffold_new_spec(
    spec_name: str,
    archetype: str = "implement",
    target_dir: str = "."
) -> Dict[str, Any]:
    """Creates a new spec directory from embedded skill templates."""
    target_dir = os.path.abspath(target_dir)
    res_dir = get_skill_resource_dir()
    templates_dir = os.path.join(res_dir, "templates")

    # Determine destination folder based on archetype
    if archetype == "fix":
        spec_parent = os.path.join(target_dir, "specs", "bugs")
    elif archetype == "refactor":
        spec_parent = os.path.join(target_dir, "specs", "refactor")
    else:
        spec_parent = os.path.join(target_dir, "specs")

    spec_dir = os.path.join(spec_parent, spec_name)
    issues_dir = os.path.join(spec_dir, "issues")
    os.makedirs(issues_dir, exist_ok=True)

    # 1. Create spec.md
    spec_file = os.path.join(spec_dir, "spec.md")
    template_spec = os.path.join(templates_dir, "spec.template.md")
    if os.path.exists(template_spec):
        with open(template_spec, "r", encoding="utf-8") as f:
            spec_content = f.read().replace("{{SPEC_NAME}}", spec_name)
    else:
        spec_content = f"# Spec: {spec_name}\n\n## 1. Overview\n\n## 5. Acceptance Criteria\n"
    
    with open(spec_file, "w", encoding="utf-8") as f:
        f.write(spec_content)

    # 2. Create initial issue 001_initial_task.md
    issue_file = os.path.join(issues_dir, "001_initial_task.md")
    template_issue = os.path.join(templates_dir, "issue.template.md")
    if os.path.exists(template_issue):
        with open(template_issue, "r", encoding="utf-8") as f:
            issue_content = (
                f.read()
                .replace("{{ISSUE_ID}}", "001")
                .replace("{{ISSUE_TITLE}}", "Initial Implementation Task")
                .replace("{{SPEC_NAME}}", spec_name)
                .replace("{{TEST_COMMAND}}", "pnpm test")
            )
    else:
        issue_content = f"# Issue 001: Initial task for {spec_name}\n"

    with open(issue_file, "w", encoding="utf-8") as f:
        f.write(issue_content)

    # 3. Create initial state.json
    state_file = os.path.join(spec_dir, "state.json")
    initial_state = {
        "spec_name": spec_name,
        "spec_path": spec_dir,
        "archetype": archetype,
        "daemon_name": None,
        "worktree_path": None,
        "branch_name": f"workflow/{spec_name}",
        "current_issue_index": 0,
        "issues": [
            {
                "issue_id": "001_initial_task",
                "title": "Initial Implementation Task",
                "status": "PENDING",
                "tests_written": [],
                "files_modified": [],
                "error_log": None,
            }
        ],
        "dag_step": "INITIALIZED",
        "checkpoint_history": [],
        "quality_gate_passed": False,
        "user_confirmed": False,
        "all_tests_passing": False,
        "spec_verified": False,
        "can_auto_merge": False,
        "memory_logged": False,
    }
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(initial_state, f, indent=2)

    return {
        "status": "SUCCESS",
        "spec_name": spec_name,
        "archetype": archetype,
        "spec_dir": spec_dir,
        "spec_file": spec_file,
        "state_file": state_file,
    }
