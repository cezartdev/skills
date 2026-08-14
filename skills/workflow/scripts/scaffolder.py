"""Scaffolder module: initializes target project structure and creates new specs inside .workflow/."""

import os
import json
import shutil
from typing import Optional, Dict, Any, List
from datetime import datetime


def get_skill_assets_dir() -> str:
    """Returns the absolute path to skills/workflow/assets."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(script_dir, "..", "assets"))


def get_workflow_root(target_dir: str = ".") -> str:
    """Returns the absolute path to the encapsulated .workflow directory in target project."""
    target_dir = os.path.abspath(target_dir)
    # If target_dir is already inside .workflow, return it
    if os.path.basename(target_dir) == ".workflow":
        return target_dir
    return os.path.join(target_dir, ".workflow")


def scaffold_init(target_dir: str = ".", test_runner_cmd: Optional[str] = None) -> Dict[str, Any]:
    """Initializes encapsulated .workflow structure in target directory."""
    target_dir = os.path.abspath(target_dir)
    wf_root = get_workflow_root(target_dir)
    assets_dir = get_skill_assets_dir()

    # 1. Create .workflow/specs/ namespaces (features, bugs, refactor, docs, archive)
    specs_dir = os.path.join(wf_root, "specs")
    os.makedirs(os.path.join(specs_dir, "features"), exist_ok=True)
    os.makedirs(os.path.join(specs_dir, "bugs"), exist_ok=True)
    os.makedirs(os.path.join(specs_dir, "refactor"), exist_ok=True)
    os.makedirs(os.path.join(specs_dir, "docs"), exist_ok=True)
    os.makedirs(os.path.join(specs_dir, "archive"), exist_ok=True)

    # 2. Create hierarchical .workflow/memory/ directories
    memory_dir = os.path.join(wf_root, "memory")
    os.makedirs(memory_dir, exist_ok=True)
    os.makedirs(os.path.join(memory_dir, "fix"), exist_ok=True)
    os.makedirs(os.path.join(memory_dir, "refactor"), exist_ok=True)
    os.makedirs(os.path.join(memory_dir, "implement"), exist_ok=True)
    os.makedirs(os.path.join(memory_dir, "doc_sync"), exist_ok=True)

    # 3. Create .workflow/worktrees/ placeholder
    worktrees_dir = os.path.join(wf_root, "worktrees")
    os.makedirs(worktrees_dir, exist_ok=True)

    # 4. Scaffold .workflow/workflow.json if not present
    config_file = os.path.join(wf_root, "workflow.json")
    config_created = False
    test_cmd = test_runner_cmd or "pnpm test"
    
    if not os.path.exists(config_file):
        template_config = os.path.join(assets_dir, "workflow.config.json")
        if os.path.exists(template_config):
            with open(template_config, "r", encoding="utf-8") as f:
                content = f.read().replace("{{TEST_COMMAND}}", test_cmd)
            with open(config_file, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            default_conf = {
                "version": "1.0",
                "test_runner": {"command": test_cmd, "args": ["--run"]},
                "memory": {"directory": ".workflow/memory"},
                "worktrees": {"directory": ".workflow/worktrees", "auto_clean_on_merge": True}
            }
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(default_conf, f, indent=2)
        config_created = True

    # 5. Add .workflow/worktrees/ to .gitignore in project root
    gitignore_file = os.path.join(target_dir, ".gitignore")
    gitignore_updated = False
    worktree_entry = ".workflow/worktrees/"
    if os.path.exists(gitignore_file):
        with open(gitignore_file, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        if worktree_entry not in lines and ".workflow/worktrees" not in lines:
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
        "workflow_dir": wf_root,
        "specs_dir": specs_dir,
        "memory_dir": memory_dir,
        "config_file": config_file,
        "config_created": config_created,
        "gitignore_updated": gitignore_updated,
    }


def scaffold_new_spec(
    spec_name: str,
    archetype: str = "features",
    target_dir: str = "."
) -> Dict[str, Any]:
    """Creates a new spec directory under .workflow/specs/<namespace>/<spec_name>/."""
    wf_root = get_workflow_root(target_dir)
    assets_dir = get_skill_assets_dir()

    # Normalize archetype aliases (defaults to features/implement)
    arch = (archetype or "feat").lower()
    if arch in ["fix", "bug", "bugs"]:
        parent_folder = "bugs"
        norm_archetype = "fix"
    elif arch in ["refactor", "refactoring"]:
        parent_folder = "refactor"
        norm_archetype = "refactor"
    elif arch in ["doc", "docs", "doc_sync"]:
        parent_folder = "docs"
        norm_archetype = "doc_sync"
    else:  # feat, feature, features, implement
        parent_folder = "features"
        norm_archetype = "implement"

    spec_dir = os.path.join(wf_root, "specs", parent_folder, spec_name)
    issues_dir = os.path.join(spec_dir, "issues")
    os.makedirs(issues_dir, exist_ok=True)

    # 1. Create spec.md from assets/spec.template.md
    spec_file = os.path.join(spec_dir, "spec.md")
    template_spec = os.path.join(assets_dir, "spec.template.md")
    if os.path.exists(template_spec):
        with open(template_spec, "r", encoding="utf-8") as f:
            spec_content = f.read().replace("{{SPEC_NAME}}", spec_name)
    else:
        spec_content = f"# Spec: {spec_name}\n\n## 1. Overview\n\n## 5. Acceptance Criteria\n"
    
    with open(spec_file, "w", encoding="utf-8") as f:
        f.write(spec_content)

    # 2. Create initial issue 001_initial_task.md from assets/issue.template.md
    issue_file = os.path.join(issues_dir, "001_initial_task.md")
    template_issue = os.path.join(assets_dir, "issue.template.md")
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
        "archetype": norm_archetype,
        "daemon_name": None,
        "worktree_path": None,
        "branch_name": f"workflow/{parent_folder}-{spec_name}",
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
        "archetype": norm_archetype,
        "namespace": parent_folder,
        "spec_dir": spec_dir,
        "spec_file": spec_file,
        "state_file": state_file,
    }


def archive_spec(spec_name: str, target_dir: str = ".") -> Dict[str, Any]:
    """Moves a completed spec folder into .workflow/specs/archive/<year>/<spec_name>/."""
    wf_root = get_workflow_root(target_dir)
    specs_root = os.path.join(wf_root, "specs")
    
    # Search for spec in features, bugs, refactor, docs
    found_src = None
    for folder in ["features", "bugs", "refactor", "docs"]:
        candidate = os.path.join(specs_root, folder, spec_name)
        if os.path.exists(candidate) and os.path.isdir(candidate):
            found_src = candidate
            break

    if not found_src:
        # Also check if spec_name is a direct directory path
        if os.path.exists(spec_name) and os.path.isdir(spec_name):
            found_src = os.path.abspath(spec_name)
            spec_name = os.path.basename(found_src)
        else:
            return {"status": "ERROR", "message": f"Spec '{spec_name}' not found under .workflow/specs/features, bugs, refactor, or docs."}

    year = str(datetime.now().year)
    archive_dest = os.path.join(specs_root, "archive", year, spec_name)
    os.makedirs(os.path.dirname(archive_dest), exist_ok=True)

    if os.path.exists(archive_dest):
        shutil.rmtree(archive_dest)

    shutil.move(found_src, archive_dest)

    return {
        "status": "ARCHIVED",
        "spec_name": spec_name,
        "source_path": found_src,
        "archive_path": archive_dest,
    }
