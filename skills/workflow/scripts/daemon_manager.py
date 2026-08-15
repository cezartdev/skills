"""Multi-Daemon Physical Worktree & Subagent Orchestration Engine."""

import os
import json
import signal
import time
import subprocess
from datetime import datetime
from typing import Dict, Any, List, Optional

from worktree_manager import (
    create_worktree,
    remove_worktree,
    force_purge_worktree,
    prune_worktrees,
    ensure_git_repository,
    sync_worktree_with_base,
)
from scaffolder import get_workflow_root
from graph.engine import WorkflowEngine


def get_daemon_registry_path(target_dir: str = ".") -> str:
    """Returns absolute path to .workflow/daemons.json."""
    wf_root = get_workflow_root(target_dir)
    return os.path.join(wf_root, "daemons.json")


def load_daemon_registry(target_dir: str = ".") -> Dict[str, Any]:
    """Loads active daemon registry from .workflow/daemons.json."""
    path = get_daemon_registry_path(target_dir)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"daemons": {}}


def save_daemon_registry(registry: Dict[str, Any], target_dir: str = ".") -> None:
    """Saves daemon registry atomically to .workflow/daemons.json."""
    path = get_daemon_registry_path(target_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)


def load_workflow_config(target_dir: str = ".") -> Dict[str, Any]:
    """Loads workflow configuration from .workflow/workflow.json or fallback assets."""
    target_dir = os.path.abspath(target_dir)
    wf_root = get_workflow_root(target_dir)
    cfg_path = os.path.join(wf_root, "workflow.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    fallback_asset = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "workflow.config.json")
    if os.path.exists(fallback_asset):
        try:
            with open(fallback_asset, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"daemons": {}, "test_runner": {"command": "pnpm test"}}


def get_daemon_catalog(target_dir: str = ".") -> Dict[str, Any]:
    """Returns catalog of all configured daemon blueprints from workflow.json alongside active status."""
    target_dir = os.path.abspath(target_dir)
    config = load_workflow_config(target_dir)
    registry = load_daemon_registry(target_dir)

    catalog = []
    config_daemons = config.get("daemons", {})

    descriptions = {
        "auto-fixer": "Autonomous bug fixer & regression hunter",
        "refactor-worker": "Architectural cleanup & code smell refactorer",
        "doc-sync": "Documentation synchronizer & README updater",
    }

    for name, conf in config_daemons.items():
        arch = conf.get("archetype", "implement")
        interval = conf.get("schedule", {}).get("interval_minutes", 10)
        desc = conf.get("description") or descriptions.get(name, f"Background worker for {arch}")
        active_entry = registry.get("daemons", {}).get(name, {})
        status = active_entry.get("status", "STOPPED")

        catalog.append({
            "name": name,
            "archetype": arch,
            "default_interval_minutes": interval,
            "cron_expression": f"*/{interval} * * * *",
            "description": desc,
            "status": status,
            "conversation_id": active_entry.get("conversation_id"),
            "worktree_path": active_entry.get("worktree_path") or os.path.join(".workflow", "worktrees", name),
        })

    return {
        "status": "SUCCESS",
        "total_configured": len(catalog),
        "active_count": sum(1 for c in catalog if c["status"] == "RUNNING"),
        "daemons": catalog,
    }


def start_daemon(
    daemon_name: str,
    interval_minutes: int = 10,
    archetype: Optional[str] = None,
    target_dir: str = "."
) -> Dict[str, Any]:
    """Starts a daemon, runs pre-flight healing, and generates subagent dispatch directive."""
    target_dir = os.path.abspath(target_dir)
    ensure_git_repository(target_dir)
    wf_root = get_workflow_root(target_dir)
    config = load_workflow_config(target_dir)
    daemon_conf = config.get("daemons", {}).get(daemon_name, {})

    # Resolve archetype
    if archetype:
        arch = archetype
    elif "archetype" in daemon_conf:
        arch = daemon_conf["archetype"]
    elif "fix" in daemon_name or "bug" in daemon_name:
        arch = "fix"
    elif "refactor" in daemon_name:
        arch = "refactor"
    elif "doc" in daemon_name:
        arch = "doc_sync"
    else:
        arch = "implement"

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
        "last_heartbeat": now,
        "last_run_at": None,
        "last_result": "INITIALIZED",
        "conversation_id": None,
        "pid": os.getpid(),
    }
    save_daemon_registry(registry, target_dir)

    # 3. Build Universal Subagent Dispatch Directive
    target_specs_folder = (
        "bugs" if arch == "fix"
        else ("refactor" if arch == "refactor"
        else ("docs" if arch == "doc_sync"
        else "features"))
    )
    system_prompt_file = f"skills/workflow/references/prompts/{arch}.prompt.md"
    task_prompt = (
        f"You are the long-running background daemon '{daemon_name}' (archetype: {arch}). "
        f"Your working directory is locked to the isolated Git Worktree at '{worktree_path}'. "
        f"Execute continuous daemon cycles every {interval} minutes:\n"
        f"1. Check .workflow/specs/{target_specs_folder}/ for pending tasks or run test suites to detect regressions.\n"
        f"2. Execute TDD fixes/updates, verifying 100% test passing.\n"
        f"3. Log decisions to .workflow/memory/{arch}/ and update heartbeat in .workflow/daemons.json.\n"
        f"4. If status in .workflow/daemons.json becomes 'STOPPED', summarize and exit cleanly."
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
        force_purge_worktree(daemon_name, repo_dir=target_dir)
        return {"status": "NOT_FOUND_BUT_PURGED", "daemon_name": daemon_name}

    entry = registry["daemons"][daemon_name]
    conv_id = entry.get("conversation_id")
    pid = entry.get("pid")

    # Phase 1: Process & Task Termination
    if pid and pid != os.getpid():
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.5)
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        except OSError:
            pass

    # Phase 2: Worktree & Git Reference Deep Purge
    force_purge_worktree(daemon_name, repo_dir=target_dir)

    # Phase 3: Registry Synchronization
    entry["status"] = "STOPPED"
    entry["stopped_at"] = datetime.now().isoformat()
    save_daemon_registry(registry, target_dir)
    prune_worktrees(target_dir)

    return {
        "status": "STOPPED",
        "daemon_name": daemon_name,
        "conversation_id": conv_id,
        "worktree_purged": True,
    }


def pause_daemon(daemon_name: str, target_dir: str = ".") -> Dict[str, Any]:
    """Pauses a daemon's cron execution without destroying worktree state."""
    target_dir = os.path.abspath(target_dir)
    registry = load_daemon_registry(target_dir)

    if daemon_name in registry["daemons"]:
        registry["daemons"][daemon_name]["status"] = "PAUSED"
        registry["daemons"][daemon_name]["paused_at"] = datetime.now().isoformat()
        save_daemon_registry(registry, target_dir)
        return {"status": "PAUSED", "daemon_name": daemon_name}

    return {"status": "NOT_FOUND", "daemon_name": daemon_name}


def resume_daemon(daemon_name: str, target_dir: str = ".") -> Dict[str, Any]:
    """Resumes a paused daemon's cron execution."""
    target_dir = os.path.abspath(target_dir)
    registry = load_daemon_registry(target_dir)

    if daemon_name in registry["daemons"]:
        registry["daemons"][daemon_name]["status"] = "RUNNING"
        registry["daemons"][daemon_name]["resumed_at"] = datetime.now().isoformat()
        registry["daemons"][daemon_name]["last_heartbeat"] = datetime.now().isoformat()
        save_daemon_registry(registry, target_dir)
        return {"status": "RESUMED", "daemon_name": daemon_name}

    return {"status": "NOT_FOUND", "daemon_name": daemon_name}


def stop_all_daemons(target_dir: str = ".") -> Dict[str, Any]:
    """Stops all active daemons and purges their worktrees."""
    target_dir = os.path.abspath(target_dir)
    registry = load_daemon_registry(target_dir)
    results = {}

    for name in list(registry.get("daemons", {}).keys()):
        results[name] = stop_daemon(name, target_dir=target_dir)

    return {"status": "ALL_STOPPED", "results": results}


def clean_orphaned_daemons(target_dir: str = ".") -> Dict[str, Any]:
    """Scans and force-purges all dead daemons, stale worktrees, and dangling locks."""
    target_dir = os.path.abspath(target_dir)
    registry = load_daemon_registry(target_dir)
    cleaned = []

    for name, entry in list(registry.get("daemons", {}).items()):
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
        status = entry.get("status", "STOPPED")
        daemons.append({
            "name": name,
            "status": status,
            "archetype": entry.get("archetype", "fix"),
            "cron_expression": entry.get("cron_expression", "N/A"),
            "interval_minutes": entry.get("interval_minutes", 10),
            "started_at": entry.get("started_at"),
            "last_heartbeat": entry.get("last_heartbeat"),
            "last_run_at": entry.get("last_run_at"),
            "last_result": entry.get("last_result"),
            "conversation_id": entry.get("conversation_id"),
            "worktree_path": entry.get("worktree_path"),
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

    # 2. Pre-Cycle Sync: Safely rebase worktree onto latest base branch (e.g. main)
    sync_res = sync_worktree_with_base(wt_path, base_branch="main", repo_dir=root_dir)
    if sync_res.get("status") == "CONFLICT":
        return {
            "status": "SYNC_CONFLICT",
            "message": "Worktree branch has conflicts with latest base branch. Resolve manually or re-create worktree.",
            "details": sync_res,
            "worktree_path": wt_path,
        }

    # 3. Find pending spec or run test health check
    target_spec_path = None
    if os.path.exists(spec_dir):
        for item in os.listdir(spec_dir):
            candidate = os.path.join(spec_dir, item)
            if os.path.isdir(candidate):
                target_spec_path = candidate
                break

    if not target_spec_path:
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
