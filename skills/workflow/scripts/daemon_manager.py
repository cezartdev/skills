"""Multi-daemon manager, Anti-Zombie lifecycle engine, and background scheduler."""

import os
import json
import signal
import subprocess
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from worktree_manager import create_worktree, remove_worktree, force_purge_worktree, prune_worktrees
from quality_auditor import audit_spec
from graph.engine import WorkflowEngine


def get_workflow_root(target_dir: str = ".") -> str:
    """Returns absolute path to .workflow directory."""
    target_dir = os.path.abspath(target_dir)
    if os.path.basename(target_dir) == ".workflow":
        return target_dir
    return os.path.join(target_dir, ".workflow")


def get_daemon_registry_path(target_dir: str = ".") -> str:
    """Returns path to .workflow/daemons.json."""
    return os.path.join(get_workflow_root(target_dir), "daemons.json")


def load_daemon_registry(target_dir: str = ".") -> Dict[str, Any]:
    """Loads active daemon registry from .workflow/daemons.json."""
    reg_path = get_daemon_registry_path(target_dir)
    if os.path.exists(reg_path):
        try:
            with open(reg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"daemons": {}}


def save_daemon_registry(registry: Dict[str, Any], target_dir: str = ".") -> None:
    """Saves daemon registry to .workflow/daemons.json."""
    reg_path = get_daemon_registry_path(target_dir)
    os.makedirs(os.path.dirname(reg_path), exist_ok=True)
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)


def load_workflow_config(root_dir: str = ".") -> Dict[str, Any]:
    """Loads .workflow/workflow.json or returns default configuration."""
    root_dir = os.path.abspath(root_dir)
    wf_root = get_workflow_root(root_dir)
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


def start_daemon(
    daemon_name: str,
    interval_minutes: int = 10,
    archetype: Optional[str] = None,
    target_dir: str = "."
) -> Dict[str, Any]:
    """Starts a daemon, runs pre-flight healing, and generates subagent dispatch directive."""
    target_dir = os.path.abspath(target_dir)
    wf_root = get_workflow_root(target_dir)
    config = load_workflow_config(target_dir)
    daemon_conf = config.get("daemons", {}).get(daemon_name, {})

    arch = archetype or daemon_conf.get("archetype", "fix" if "fix" in daemon_name else "refactor")
    interval = interval_minutes or daemon_conf.get("schedule", {}).get("interval_minutes", 10)
    cron_expr = f"*/{interval} * * * *"

    # 1. Pre-Flight Self-Healing: purge any prior zombie or stale worktree of this daemon
    force_purge_worktree(daemon_name, repo_dir=target_dir)

    worktree_path = os.path.join(wf_root, "worktrees", daemon_name)
    now = datetime.now().isoformat()

    # 2. Register active daemon in .workflow/daemons.json
    registry = load_daemon_registry(target_dir)
    registry["daemons"][daemon_name] = {
        "name": daemon_name,
        "status": "RUNNING",
        "archetype": arch,
        "cron_expression": cron_expr,
        "interval_minutes": interval,
        "worktree_path": worktree_path,
        "started_at": now,
        "last_run_at": None,
        "last_result": "INITIALIZED",
        "pid": os.getpid(),
    }
    save_daemon_registry(registry, target_dir)

    # 3. Build Universal Subagent Dispatch Directive
    system_prompt_file = f"skills/workflow/references/prompts/{arch}.prompt.md"
    task_prompt = (
        f"Execute background TDD cycle for daemon '{daemon_name}' (archetype: {arch}) "
        f"inside isolated Git Worktree at '{worktree_path}'. "
        f"Check .workflow/specs/{'bugs' if arch == 'fix' else 'refactor'}/ for pending issues, "
        f"run unit tests, implement surgical patches, and trigger safe auto-merge to main on 100% test pass."
    )

    return {
        "status": "STARTED",
        "daemon_name": daemon_name,
        "archetype": arch,
        "interval_minutes": interval,
        "cron_expression": cron_expr,
        "worktree_path": worktree_path,
        "subagent_directive": {
            "action": "INVOKE_SUBAGENT",
            "role": f"{daemon_name.title()} Daemon Specialist",
            "working_directory": worktree_path,
            "system_prompt_file": system_prompt_file,
            "schedule": {
                "type": "recurring_cron",
                "cron_expression": cron_expr,
                "interval_minutes": interval,
            },
            "task_prompt": task_prompt,
        },
    }


def stop_daemon(daemon_name: str, target_dir: str = ".", force: bool = False) -> Dict[str, Any]:
    """Anti-Zombie 3-Phase Deep Cleanup: stops daemon, kills process, purges worktree and locks."""
    target_dir = os.path.abspath(target_dir)
    registry = load_daemon_registry(target_dir)

    if daemon_name not in registry["daemons"]:
        # Attempt physical cleanup even if not in registry
        force_purge_worktree(daemon_name, repo_dir=target_dir)
        return {"status": "NOT_FOUND_BUT_PURGED", "daemon_name": daemon_name}

    entry = registry["daemons"][daemon_name]
    pid = entry.get("pid")

    # Phase 1: Process & Task Termination
    if pid and pid != os.getpid():
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.5)
            # If still alive, send SIGKILL
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        except OSError:
            pass  # Process already dead

    # Phase 2: Worktree & Git Reference Deep Purge
    force_purge_worktree(daemon_name, repo_dir=target_dir)

    # Phase 3: Registry Reconcile
    entry["status"] = "STOPPED"
    entry["stopped_at"] = datetime.now().isoformat()
    save_daemon_registry(registry, target_dir)

    return {
        "status": "STOPPED",
        "daemon_name": daemon_name,
        "worktree_purged": True,
        "process_terminated": bool(pid),
    }


def stop_all_daemons(target_dir: str = ".") -> Dict[str, Any]:
    """Stops all active daemons and executes Anti-Zombie purge across all registered workers."""
    target_dir = os.path.abspath(target_dir)
    registry = load_daemon_registry(target_dir)
    results = {}

    for name in list(registry["daemons"].keys()):
        results[name] = stop_daemon(name, target_dir=target_dir, force=True)

    # Prune any dangling worktrees in .workflow/worktrees/
    wf_root = get_workflow_root(target_dir)
    wt_root = os.path.join(wf_root, "worktrees")
    if os.path.exists(wt_root):
        for item in os.listdir(wt_root):
            force_purge_worktree(item, repo_dir=target_dir)

    prune_worktrees(target_dir)
    return {"status": "ALL_STOPPED", "daemons": results}


def clean_orphaned_daemons(target_dir: str = ".") -> Dict[str, Any]:
    """Scans and purges dead PIDs, orphaned worktree folders, and stale lockfiles."""
    target_dir = os.path.abspath(target_dir)
    registry = load_daemon_registry(target_dir)
    cleaned = []

    for name, entry in list(registry["daemons"].items()):
        pid = entry.get("pid")
        is_alive = False
        if pid:
            try:
                os.kill(pid, 0)
                is_alive = True
            except OSError:
                is_alive = False

        if not is_alive or entry.get("status") == "STOPPED":
            force_purge_worktree(name, repo_dir=target_dir)
            entry["status"] = "STOPPED"
            cleaned.append(name)

    save_daemon_registry(registry, target_dir)
    prune_worktrees(target_dir)
    return {"status": "CLEANED", "purged_daemons": cleaned}


def get_daemon_status_table(target_dir: str = ".") -> Dict[str, Any]:
    """Returns structured table of active daemons, schedules, and health metrics."""
    target_dir = os.path.abspath(target_dir)
    registry = load_daemon_registry(target_dir)
    config = load_workflow_config(target_dir)

    daemons = []
    for name, entry in registry.get("daemons", {}).items():
        pid = entry.get("pid")
        is_alive = False
        if pid:
            try:
                os.kill(pid, 0)
                is_alive = True
            except OSError:
                is_alive = False

        daemons.append({
            "name": name,
            "status": "RUNNING" if is_alive and entry.get("status") == "RUNNING" else "STOPPED",
            "archetype": entry.get("archetype", "fix"),
            "cron_expression": entry.get("cron_expression", "N/A"),
            "interval_minutes": entry.get("interval_minutes", 10),
            "started_at": entry.get("started_at"),
            "last_run_at": entry.get("last_run_at"),
            "last_result": entry.get("last_result"),
            "worktree_path": entry.get("worktree_path"),
            "alive": is_alive,
        })

    return {
        "status": "SUCCESS",
        "active_count": sum(1 for d in daemons if d["status"] == "RUNNING"),
        "daemons": daemons,
        "configured_in_config": list(config.get("daemons", {}).keys()),
    }


def run_daemon_cycle(
    daemon_name: str,
    archetype: str = "fix",
    spec_dir: Optional[str] = None,
    worktree_name: Optional[str] = None,
    auto_merge: bool = False,
    root_dir: str = "."
) -> Dict[str, Any]:
    """Executes a single one-shot daemon cycle inside an isolated physical worktree."""
    root_dir = os.path.abspath(root_dir)
    wf_root = get_workflow_root(root_dir)
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
    branch_name = wt_result.get("branch_name", f"workflow/worktree-{daemon_name}")

    # 2. Find pending spec or run test health check
    target_spec_path = None
    if os.path.exists(spec_dir):
        for item in os.listdir(spec_dir):
            candidate = os.path.join(spec_dir, item)
            if os.path.isdir(candidate):
                target_spec_path = candidate
                break

    if not target_spec_path:
        # Check if any unit tests are failing
        return {
            "status": "IDLE",
            "message": f"No pending specs found in '{spec_dir}'. Daemon cycle complete with zero work required.",
            "worktree_path": wt_path,
        }

    # 3. Execute LangGraph DAG state machine on target spec
    engine = WorkflowEngine(target_spec_path)
    dag_result = engine.run_step()

    # 4. Safe Auto-Merge Gate
    merge_status = "SKIPPED"
    if auto_merge and dag_result.get("all_tests_passing") and dag_result.get("spec_verified"):
        merge_cmd = subprocess.run(
            ["git", "merge", "--no-ff", branch_name, "-m", f"chore(workflow): auto-merge daemon '{daemon_name}'"],
            cwd=root_dir,
            capture_output=True,
            text=True,
            check=False
        )
        merge_status = "MERGED" if merge_cmd.returncode == 0 else f"MERGE_FAILED: {merge_cmd.stderr.strip()}"
        if merge_cmd.returncode == 0:
            remove_worktree(worktree_name, repo_dir=root_dir, force=True)

    return {
        "status": "COMPLETED",
        "daemon_name": daemon_name,
        "archetype": archetype,
        "worktree_path": wt_path,
        "branch_name": branch_name,
        "dag_step": dag_result.get("dag_step"),
        "all_tests_passing": dag_result.get("all_tests_passing"),
        "spec_verified": dag_result.get("spec_verified"),
        "merge_status": merge_status,
    }
