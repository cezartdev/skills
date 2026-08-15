"""Scaffolder module: initializes target project structure and creates new specs inside .workflow/."""

import os
import json
import shutil
import re
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from .explorer import scan_codebase
except ImportError:
    from explorer import scan_codebase


def sanitize_identifier(name: str) -> str:
    """Sanitizes an identifier (spec, daemon, worktree) against path traversal and invalid chars."""
    if not name:
        return "unnamed"
    cleaned = os.path.basename(name.replace("\\", "/"))
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", cleaned).strip("-._")
    return cleaned.lower() or "unnamed"


def atomic_write_json(file_path: str, data: Dict[str, Any]) -> None:
    """Safely writes a JSON dictionary atomically to disk using a temporary file and os.replace."""
    file_path = os.path.abspath(file_path)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    temp_path = f"{file_path}.tmp.{os.getpid()}_{int(time.time()*1000)}"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, file_path)
    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        raise e


def get_skill_assets_dir() -> str:
    """Returns the absolute path to skills/workflow/assets."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(script_dir, "..", "assets"))


def get_workflow_root(target_dir: str = ".") -> str:
    """Returns the absolute path to the encapsulated .workflow directory in target project."""
    target_dir = os.path.abspath(target_dir)
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

    # 3. Create .workflow/prs/ catalog (active, archive)
    prs_dir = os.path.join(wf_root, "prs")
    os.makedirs(os.path.join(prs_dir, "active"), exist_ok=True)
    os.makedirs(os.path.join(prs_dir, "archive"), exist_ok=True)

    # 4. Create .workflow/worktrees/ placeholder
    worktrees_dir = os.path.join(wf_root, "worktrees")
    os.makedirs(worktrees_dir, exist_ok=True)

    # 5. Determine test runner dynamically via polyglot scan
    if not test_runner_cmd:
        scan = scan_codebase(target_dir)
        test_cmd = scan.get("test_runner", "pytest")
    else:
        test_cmd = test_runner_cmd

    # 6. Scaffold .workflow/workflow.json if not present
    config_file = os.path.join(wf_root, "workflow.json")
    config_created = False
    if not os.path.exists(config_file):
        template_config = os.path.join(assets_dir, "workflow.config.json")
        if os.path.exists(template_config):
            with open(template_config, "r", encoding="utf-8") as f:
                cfg_data = json.load(f)
            cfg_data.setdefault("test_runner", {})["command"] = test_cmd
            atomic_write_json(config_file, cfg_data)
        else:
            atomic_write_json(config_file, {
                "version": "1.0.0",
                "test_runner": {"command": test_cmd},
                "daemons": {
                    "auto-fixer": {"archetype": "fix", "schedule": {"interval_minutes": 10}},
                    "refactor-worker": {"archetype": "refactor", "schedule": {"interval_minutes": 15}},
                    "doc-sync": {"archetype": "doc_sync", "schedule": {"interval_minutes": 30}}
                }
            })
        config_created = True

    # 7. Add .workflow/worktrees to .gitignore if not present
    gitignore_path = os.path.join(target_dir, ".gitignore")
    gitignore_updated = False
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as f:
            content = f.read()
        needed_entries = [".workflow/worktrees/", ".workflow/logs/"]
        to_add = [e for e in needed_entries if e not in content]
        if to_add:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                f.write("\n# Workflow Ephemeral Artifacts\n" + "\n".join(to_add) + "\n")
            gitignore_updated = True
    else:
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write("# Workflow Ephemeral Artifacts\n.workflow/worktrees/\n.workflow/logs/\n")
        gitignore_updated = True

    return {
        "status": "INITIALIZED",
        "target_dir": target_dir,
        "workflow_dir": wf_root,
        "specs_dir": specs_dir,
        "memory_dir": memory_dir,
        "prs_dir": prs_dir,
        "config_file": config_file,
        "test_runner": test_cmd,
        "config_created": config_created,
        "gitignore_updated": gitignore_updated,
    }


def scaffold_new_spec(
    spec_name: str,
    archetype: str = "features",
    target_dir: str = "."
) -> Dict[str, Any]:
    """Creates a new spec directory under .workflow/specs/<namespace>/<spec_name>/."""
    target_dir = os.path.abspath(target_dir)
    wf_root = get_workflow_root(target_dir)
    assets_dir = get_skill_assets_dir()

    clean_name = sanitize_identifier(spec_name)

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

    spec_dir = os.path.join(wf_root, "specs", parent_folder, clean_name)
    issues_dir = os.path.join(spec_dir, "issues")
    os.makedirs(issues_dir, exist_ok=True)

    # 1. Create spec.md from assets/spec.template.md
    spec_file = os.path.join(spec_dir, "spec.md")
    template_spec = os.path.join(assets_dir, "spec.template.md")
    if os.path.exists(template_spec):
        with open(template_spec, "r", encoding="utf-8") as f:
            spec_content = f.read().replace("{{SPEC_NAME}}", clean_name)
    else:
        spec_content = f"# Spec: {clean_name}\n\n## 1. Overview\n\n## 5. Acceptance Criteria\n"
    
    with open(spec_file, "w", encoding="utf-8") as f:
        f.write(spec_content)

    # 2. Create initial state.json with clean empty issues list (tasks generated during /workflow plan)
    state_file = os.path.join(spec_dir, "state.json")
    initial_state = {
        "spec_name": clean_name,
        "spec_path": spec_dir,
        "archetype": norm_archetype,
        "daemon_name": None,
        "worktree_path": None,
        "branch_name": f"workflow/{parent_folder}-{clean_name}",
        "current_issue_index": 0,
        "issues": [],
        "dag_step": "NEW_SPEC_INITIALIZED",
        "checkpoint_history": [],
        "quality_gate_passed": False,
        "user_confirmed": False,
        "all_tests_passing": False,
        "spec_verified": False,
        "can_auto_merge": False,
        "memory_logged": False,
    }
    atomic_write_json(state_file, initial_state)

    return {
        "status": "SUCCESS",
        "spec_name": clean_name,
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
    clean_name = sanitize_identifier(spec_name)
    
    # Search for spec in features, bugs, refactor, docs
    found_src = None
    for folder in ["features", "bugs", "refactor", "docs"]:
        candidate = os.path.join(specs_root, folder, clean_name)
        if os.path.exists(candidate) and os.path.isdir(candidate):
            found_src = candidate
            break

    if not found_src:
        if os.path.exists(spec_name) and os.path.isdir(spec_name):
            found_src = os.path.abspath(spec_name)
            clean_name = sanitize_identifier(os.path.basename(found_src))
        else:
            return {"status": "ERROR", "message": f"Spec '{spec_name}' not found under .workflow/specs/features, bugs, refactor, or docs."}

    year = str(datetime.now().year)
    archive_dest = os.path.join(specs_root, "archive", year, clean_name)
    os.makedirs(os.path.dirname(archive_dest), exist_ok=True)

    if os.path.exists(archive_dest):
        shutil.rmtree(archive_dest)

    shutil.move(found_src, archive_dest)

    return {
        "status": "ARCHIVED",
        "spec_name": clean_name,
        "source_path": found_src,
        "archive_path": archive_dest,
    }
