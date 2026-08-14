"""Daemon manager: coordinates background daemon iterations, worktree isolation, and safe auto-merge."""

import os
import json
import time
import subprocess
from typing import Dict, Any, Optional
from datetime import datetime
try:
    from .worktree_manager import create_worktree, remove_worktree, run_git
    from .graph.engine import WorkflowEngine
except ImportError:
    from worktree_manager import create_worktree, remove_worktree, run_git
    from graph.engine import WorkflowEngine


def load_workflow_config(root_dir: str = ".") -> Dict[str, Any]:
    """Loads .workflow/workflow.json or returns default configuration."""
    root_dir = os.path.abspath(root_dir)
    wf_root = os.path.join(root_dir, ".workflow") if os.path.basename(root_dir) != ".workflow" else root_dir
    cfg_path = os.path.join(wf_root, "workflow.json")
    if not os.path.exists(cfg_path):
        legacy_cfg = os.path.join(root_dir, "workflow.json")
        if os.path.exists(legacy_cfg):
            cfg_path = legacy_cfg

    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"daemons": {}, "test_runner": {"command": "pnpm test"}}


def run_daemon_cycle(
    daemon_name: str,
    archetype: str = "fix",
    spec_dir: Optional[str] = None,
    worktree_name: Optional[str] = None,
    auto_merge: bool = False,
    root_dir: str = "."
) -> Dict[str, Any]:
    """Executes a single daemon cycle inside an isolated physical worktree."""
    root_dir = os.path.abspath(root_dir)
    wf_root = os.path.join(root_dir, ".workflow") if os.path.basename(root_dir) != ".workflow" else root_dir
    config = load_workflow_config(root_dir)
    
    daemon_conf = config.get("daemons", {}).get(daemon_name, {})
    archetype = archetype or daemon_conf.get("archetype", "fix")
    worktree_name = worktree_name or daemon_conf.get("worktree", f".workflow/worktrees/{daemon_name}").replace(".workflow/worktrees/", "").replace(".worktrees/", "")
    
    if not spec_dir:
        spec_dir = daemon_conf.get("target_spec_dir", os.path.join(".workflow", "specs", "bugs" if archetype == "fix" else "refactor"))
    
    spec_dir = os.path.abspath(os.path.join(root_dir, spec_dir))

    # 1. Setup isolated physical worktree
    wt_result = create_worktree(worktree_name, repo_dir=root_dir)
    if wt_result["status"] == "ERROR":
        return {"status": "WORKTREE_ERROR", "details": wt_result}

    wt_path = wt_result["worktree_path"]
    branch_name = wt_result["branch_name"]

    # 2. Execute LangGraph DAG
    engine = WorkflowEngine(spec_dir)
    dag_state = engine.run_step()

    # 3. Check Auto-Merge Conditions
    merge_status = "SKIPPED"
    if auto_merge or daemon_conf.get("auto_merge", {}).get("enabled", False):
        if dag_state.get("all_tests_passing", False) and dag_state.get("spec_verified", False):
            # Perform safe merge to main
            merge_res = run_git(["merge", branch_name, "--no-ff", "-m", f"chore(workflow): auto-merge daemon '{daemon_name}'"], cwd=root_dir)
            if merge_res.returncode == 0:
                merge_status = "MERGED"
                if config.get("worktrees", {}).get("auto_clean_on_merge", True):
                    remove_worktree(worktree_name, repo_dir=root_dir)
            else:
                merge_status = f"MERGE_FAILED: {merge_res.stderr.strip()}"

    return {
        "status": "COMPLETED",
        "daemon_name": daemon_name,
        "archetype": archetype,
        "worktree_path": wt_path,
        "branch_name": branch_name,
        "dag_step": dag_state.get("dag_step"),
        "merge_status": merge_status,
        "timestamp": datetime.now().isoformat(),
    }
