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
    get_default_branch,
    run_git,
)
from scaffolder import get_workflow_root, sanitize_identifier, atomic_write_json
from graph.engine import WorkflowEngine


import socket
import getpass
import platform


def get_machine_identity() -> Dict[str, str]:
    """Returns stable host and machine metadata for multi-developer team collaboration."""
    try:
        user = getpass.getuser()
    except Exception:
        user = "developer"
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = "local-machine"

    os_name = platform.system().lower()
    host_tag = f"{user}@{hostname}"

    return {
        "user": user,
        "hostname": hostname,
        "os": os_name,
        "host_tag": host_tag,
    }


def get_daemon_registry_path(target_dir: str = ".") -> str:
    """Returns absolute path to .workflow/daemons.json."""
    wf_root = get_workflow_root(target_dir)
    return os.path.join(wf_root, "daemons.json")


def is_workflow_process(pid: Optional[int]) -> bool:
    """Verifies whether a PID is genuinely alive AND belongs to a workflow/python process (PID Recycling Defense)."""
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False

    # Check Linux /proc/<pid>/cmdline
    proc_cmdline = f"/proc/{pid}/cmdline"
    if os.path.exists(proc_cmdline):
        try:
            with open(proc_cmdline, "r", encoding="utf-8", errors="ignore") as f:
                cmdline = f.read().lower()
                return "python" in cmdline or "workflow" in cmdline or "uv" in cmdline
        except Exception:
            return False

    # Fallback for macOS/POSIX using ps
    try:
        ps_res = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True, check=False)
        if ps_res.returncode == 0:
            cmd = ps_res.stdout.strip().lower()
            return "python" in cmd or "workflow" in cmd or "uv" in cmd
    except Exception:
        pass

    return True


def reconcile_daemon_registry(target_dir: str = ".") -> Dict[str, Any]:
    """Post-Reboot Self-Healing & Zombie State Reconciler with Multi-Machine Host Affinity.
    
    Validates all registered daemons belonging to the current host. If the local machine was rebooted
    or processes crashed, reconciles stale RUNNING states to STOPPED. Daemons hosted on other machines
    are respected and not erroneously killed or terminated.
    """
    target_dir = os.path.abspath(target_dir)
    registry = load_daemon_registry(target_dir)
    recovered = []
    current_host = get_machine_identity()["host_tag"]

    for name, entry in list(registry.get("daemons", {}).items()):
        status = entry.get("status")
        pid = entry.get("pid")
        entry_host = entry.get("host")

        # Multi-Machine Protection: Only audit local PIDs for daemons started on this machine
        if entry_host and entry_host != current_host:
            continue

        # Reconcile stale is_busy execution locks
        if entry.get("is_busy"):
            run_pid = entry.get("current_run_pid")
            if not is_workflow_process(run_pid):
                entry["is_busy"] = False
                entry["current_run_pid"] = None

        if status in ["RUNNING", "PAUSED"]:
            if not is_workflow_process(pid):
                entry["status"] = "STOPPED"
                entry["is_busy"] = False
                entry["reconciled_at"] = datetime.now().isoformat()
                entry["recovery_reason"] = "STALE_PROCESS_OR_SYSTEM_REBOOT_RECOVERED"
                force_purge_worktree(name, repo_dir=target_dir)
                recovered.append(name)

    if recovered:
        save_daemon_registry(registry, target_dir)
        prune_worktrees(target_dir)

    return {
        "status": "RECONCILED",
        "recovered_count": len(recovered),
        "recovered_daemons": recovered,
        "host": current_host,
    }


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
    atomic_write_json(path, registry)


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


def save_workflow_config(config: Dict[str, Any], target_dir: str = ".") -> str:
    """Saves workflow configuration atomically to .workflow/workflow.json."""
    target_dir = os.path.abspath(target_dir)
    wf_root = get_workflow_root(target_dir)
    os.makedirs(wf_root, exist_ok=True)
    cfg_path = os.path.join(wf_root, "workflow.json")
    atomic_write_json(cfg_path, config)
    return cfg_path


def create_daemon_blueprint(
    name: str,
    archetype: str = "fix",
    interval_minutes: int = 10,
    max_iterations: Optional[int] = None,
    description: Optional[str] = None,
    target_spec_dir: Optional[str] = None,
    target_dir: str = "."
) -> Dict[str, Any]:
    """Creates a new daemon blueprint entry in .workflow/workflow.json without manual editing."""
    target_dir = os.path.abspath(target_dir)
    clean_name = sanitize_identifier(name)
    config = load_workflow_config(target_dir)

    if "daemons" not in config:
        config["daemons"] = {}

    default_descriptions = {
        "fix": f"Autonomous bug fixer & regression hunter for {clean_name}",
        "refactor": f"Architectural cleanup & code smell refactorer for {clean_name}",
        "implement": f"Autonomous feature implementer for {clean_name}",
        "doc_sync": f"Documentation synchronizer & README updater for {clean_name}",
    }
    desc = description or default_descriptions.get(archetype, f"Background worker for {clean_name}")

    spec_folder_map = {
        "fix": ".workflow/specs/bugs",
        "refactor": ".workflow/specs/refactor",
        "doc_sync": ".workflow/specs/docs",
        "implement": ".workflow/specs/features",
    }
    spec_dir = target_spec_dir or spec_folder_map.get(archetype, ".workflow/specs/features")

    schedule_payload: Dict[str, Any] = {"interval_minutes": int(interval_minutes)}
    if max_iterations is not None and max_iterations > 0:
        schedule_payload["max_iterations"] = int(max_iterations)

    config["daemons"][clean_name] = {
        "archetype": archetype,
        "description": desc,
        "schedule": schedule_payload,
        "target_spec_dir": spec_dir,
        "worktree": f".workflow/worktrees/{clean_name}",
    }

    save_workflow_config(config, target_dir)
    return {
        "status": "CREATED",
        "daemon_name": clean_name,
        "archetype": archetype,
        "interval_minutes": int(interval_minutes),
        "max_iterations": max_iterations,
        "description": desc,
        "target_spec_dir": spec_dir,
    }


def update_daemon_config(
    name: str,
    interval_minutes: Optional[int] = None,
    max_iterations: Optional[int] = None,
    archetype: Optional[str] = None,
    description: Optional[str] = None,
    target_dir: str = "."
) -> Dict[str, Any]:
    """Updates an existing daemon blueprint in .workflow/workflow.json and synchronizes daemons.json."""
    target_dir = os.path.abspath(target_dir)
    clean_name = sanitize_identifier(name)
    config = load_workflow_config(target_dir)

    if "daemons" not in config or clean_name not in config["daemons"]:
        return {"status": "NOT_FOUND", "daemon_name": clean_name}

    daemon_entry = config["daemons"][clean_name]
    if "schedule" not in daemon_entry:
        daemon_entry["schedule"] = {}

    if interval_minutes is not None and interval_minutes > 0:
        daemon_entry["schedule"]["interval_minutes"] = int(interval_minutes)
    if max_iterations is not None:
        if max_iterations > 0:
            daemon_entry["schedule"]["max_iterations"] = int(max_iterations)
        elif "max_iterations" in daemon_entry["schedule"]:
            del daemon_entry["schedule"]["max_iterations"]
    if archetype:
        daemon_entry["archetype"] = archetype
    if description:
        daemon_entry["description"] = description

    save_workflow_config(config, target_dir)

    # Synchronize active registry in daemons.json
    registry = load_daemon_registry(target_dir)
    if clean_name in registry.get("daemons", {}):
        active_d = registry["daemons"][clean_name]
        if interval_minutes is not None and interval_minutes > 0:
            active_d["interval_minutes"] = int(interval_minutes)
            active_d["cron_expression"] = f"*/{interval_minutes} * * * *"
        if max_iterations is not None:
            active_d["max_iterations"] = max_iterations if max_iterations > 0 else None
        if archetype:
            active_d["archetype"] = archetype
        save_daemon_registry(registry, target_dir)

    return {
        "status": "UPDATED",
        "daemon_name": clean_name,
        "config": daemon_entry,
    }


def get_daemon_catalog(target_dir: str = ".") -> Dict[str, Any]:
    """Returns catalog of all configured daemon blueprints from workflow.json alongside active status."""
    target_dir = os.path.abspath(target_dir)
    reconcile_daemon_registry(target_dir)
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
        sched = conf.get("schedule", {}) if isinstance(conf.get("schedule"), dict) else {}
        interval = (
            sched.get("interval_minutes")
            or conf.get("interval_minutes")
            or sched.get("interval")
            or conf.get("interval")
            or 10
        )
        max_iter = sched.get("max_iterations") or conf.get("max_iterations")
        desc = conf.get("description") or descriptions.get(name, f"Background worker for {arch}")
        active_entry = registry.get("daemons", {}).get(name, {})
        status = active_entry.get("status", "STOPPED")
        host = active_entry.get("host")

        catalog.append({
            "name": name,
            "archetype": arch,
            "default_interval_minutes": interval,
            "max_iterations": max_iter,
            "cron_expression": f"*/{interval} * * * *",
            "description": desc,
            "status": status,
            "host": host,
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
    interval_minutes: Optional[int] = None,
    max_iterations: Optional[int] = None,
    archetype: Optional[str] = None,
    target_dir: str = "."
) -> Dict[str, Any]:
    """Starts a daemon, runs pre-flight healing, and generates subagent dispatch directive."""
    target_dir = os.path.abspath(target_dir)
    ensure_git_repository(target_dir)
    reconcile_daemon_registry(target_dir)
    clean_name = sanitize_identifier(daemon_name)

    wf_root = get_workflow_root(target_dir)
    config = load_workflow_config(target_dir)
    daemon_conf = config.get("daemons", {}).get(clean_name, {})
    sched = daemon_conf.get("schedule", {}) if isinstance(daemon_conf.get("schedule"), dict) else {}

    # Resolve archetype
    if archetype:
        arch = archetype
    elif "archetype" in daemon_conf:
        arch = daemon_conf["archetype"]
    elif "fix" in clean_name or "bug" in clean_name:
        arch = "fix"
    elif "refactor" in clean_name:
        arch = "refactor"
    elif "doc" in clean_name:
        arch = "doc_sync"
    else:
        arch = "implement"

    # Resolve interval: CLI parameter > workflow.json schedule.interval_minutes / interval_minutes > fallback 10
    if interval_minutes is not None and interval_minutes > 0:
        interval = interval_minutes
    elif "schedule" in daemon_conf and "interval_minutes" in daemon_conf["schedule"]:
        interval = int(daemon_conf["schedule"]["interval_minutes"])
    elif "interval_minutes" in daemon_conf:
        interval = int(daemon_conf["interval_minutes"])
    elif "schedule" in daemon_conf and "interval" in daemon_conf["schedule"]:
        interval = int(daemon_conf["schedule"]["interval"])
    elif "interval" in daemon_conf:
        interval = int(daemon_conf["interval"])
    else:
        interval = 10

    # Resolve max iterations
    effective_max_iter = max_iterations if max_iterations is not None else sched.get("max_iterations")

    cron_expr = f"*/{interval} * * * *"

    # 1. Pre-Flight Self-Healing: purge any prior zombie or stale worktree of this daemon
    force_purge_worktree(clean_name, repo_dir=target_dir)

    worktree_path = os.path.join(wf_root, "worktrees", clean_name)
    now = datetime.now().isoformat()
    machine = get_machine_identity()

    # 2. Register active daemon in .workflow/daemons.json with multi-machine host tagging & Fixed-Delay fields
    registry = load_daemon_registry(target_dir)
    registry["daemons"][clean_name] = {
        "name": clean_name,
        "status": "RUNNING",
        "archetype": arch,
        "cron_expression": cron_expr,
        "interval_minutes": interval,
        "max_iterations": effective_max_iter,
        "iteration_count": 0,
        "is_busy": False,
        "current_run_pid": None,
        "current_run_started_at": None,
        "last_completed_at": None,
        "worktree_path": worktree_path,
        "started_at": now,
        "last_heartbeat": now,
        "last_run_at": None,
        "last_result": "INITIALIZED",
        "conversation_id": None,
        "pid": os.getpid(),
        "host": machine["host_tag"],
        "os": machine["os"],
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
        f"You are the long-running background daemon '{clean_name}' (archetype: {arch}). "
        f"Your working directory is locked to the isolated Git Worktree at '{worktree_path}'. "
        f"Execute continuous daemon cycles every {interval} minutes:\n"
        f"1. Pre-Cycle Sync: Synchronize your worktree branch with latest base branch.\n"
        f"2. Check .workflow/specs/{target_specs_folder}/ for pending tasks or run test suites to detect regressions.\n"
        f"3. Execute TDD fixes/updates, verifying 100% test passing.\n"
        f"4. Log decisions to .workflow/memory/{arch}/ and update heartbeat in .workflow/daemons.json.\n"
        f"5. If status in .workflow/daemons.json becomes 'STOPPED', summarize and exit cleanly."
    )

    return {
        "status": "STARTED",
        "daemon_name": clean_name,
        "archetype": arch,
        "interval_minutes": interval,
        "cron_expression": cron_expr,
        "worktree_path": worktree_path,
        "subagent_directive": {
            "action": "INVOKE_SUBAGENT",
            "role": f"{clean_name.title()} Daemon Specialist",
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
    clean_name = sanitize_identifier(daemon_name)
    registry = load_daemon_registry(target_dir)

    if clean_name not in registry["daemons"]:
        force_purge_worktree(clean_name, repo_dir=target_dir)
        return {"status": "NOT_FOUND_BUT_PURGED", "daemon_name": clean_name}

    entry = registry["daemons"][clean_name]
    conv_id = entry.get("conversation_id")
    pid = entry.get("pid")

    # Phase 1: Process & Task Termination (with PID recycling defense & Host Affinity)
    current_host = get_machine_identity()["host_tag"]
    entry_host = entry.get("host")
    if (not entry_host or entry_host == current_host) and pid and pid != os.getpid() and is_workflow_process(pid):
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
    force_purge_worktree(clean_name, repo_dir=target_dir)

    # Phase 3: Registry Synchronization
    entry["status"] = "STOPPED"
    entry["stopped_at"] = datetime.now().isoformat()
    save_daemon_registry(registry, target_dir)
    prune_worktrees(target_dir)

    return {
        "status": "STOPPED",
        "daemon_name": clean_name,
        "conversation_id": conv_id,
        "worktree_purged": True,
        "cleanup_directive": {
            "cancel_cron_action": "manage_task(Action='kill', TaskId=<daemon_schedule_task_id>)",
            "terminate_subagent_action": f"manage_subagents(Action='kill', ConversationIds=['{conv_id}'])" if conv_id else "None",
        },
    }


def pause_daemon(daemon_name: str, target_dir: str = ".") -> Dict[str, Any]:
    """Pauses a daemon's cron execution without destroying worktree state."""
    target_dir = os.path.abspath(target_dir)
    clean_name = sanitize_identifier(daemon_name)
    registry = load_daemon_registry(target_dir)

    if clean_name in registry["daemons"]:
        registry["daemons"][clean_name]["status"] = "PAUSED"
        registry["daemons"][clean_name]["paused_at"] = datetime.now().isoformat()
        save_daemon_registry(registry, target_dir)
        return {"status": "PAUSED", "daemon_name": clean_name}

    return {"status": "NOT_FOUND", "daemon_name": clean_name}


def resume_daemon(daemon_name: str, target_dir: str = ".") -> Dict[str, Any]:
    """Resumes a paused daemon's cron execution."""
    target_dir = os.path.abspath(target_dir)
    clean_name = sanitize_identifier(daemon_name)
    registry = load_daemon_registry(target_dir)

    if clean_name in registry["daemons"]:
        registry["daemons"][clean_name]["status"] = "RUNNING"
        registry["daemons"][clean_name]["resumed_at"] = datetime.now().isoformat()
        registry["daemons"][clean_name]["last_heartbeat"] = datetime.now().isoformat()
        save_daemon_registry(registry, target_dir)
        return {"status": "RESUMED", "daemon_name": clean_name}

    return {"status": "NOT_FOUND", "daemon_name": clean_name}


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
    reconcile_daemon_registry(target_dir)
    registry = load_daemon_registry(target_dir)
    cleaned = []

    for name, entry in list(registry.get("daemons", {}).items()):
        pid = entry.get("pid")
        is_alive = is_workflow_process(pid)

        if not is_alive or entry.get("status") == "STOPPED":
            force_purge_worktree(name, repo_dir=target_dir)
            entry["status"] = "STOPPED"
            cleaned.append(name)

    save_daemon_registry(registry, target_dir)
    prune_worktrees(target_dir)
    return {"status": "CLEANED", "purged_daemons": cleaned}


def get_daemon_status_table(target_dir: str = ".") -> Dict[str, Any]:
    """Returns structured table of active daemons, schedules, host affinity, and health metrics."""
    target_dir = os.path.abspath(target_dir)
    reconcile_daemon_registry(target_dir)
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
            "max_iterations": entry.get("max_iterations"),
            "iteration_count": entry.get("iteration_count", 0),
            "host": entry.get("host", "local"),
            "os": entry.get("os", "unknown"),
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
    clean_name = sanitize_identifier(daemon_name)
    wf_root = get_workflow_root(root_dir)
    config = load_workflow_config(root_dir)
    
    daemon_conf = config.get("daemons", {}).get(clean_name, {})
    archetype = archetype or daemon_conf.get("archetype", "fix")
    worktree_name = worktree_name or daemon_conf.get("worktree", f".workflow/worktrees/{clean_name}").replace(".workflow/worktrees/", "").replace(".worktrees/", "")
    worktree_name = sanitize_identifier(worktree_name)
    
    if not spec_dir:
        spec_dir = daemon_conf.get("target_spec_dir", os.path.join(".workflow", "specs", "bugs" if archetype == "fix" else "refactor"))
    
    spec_dir = os.path.abspath(os.path.join(root_dir, spec_dir))
    target_base = get_default_branch(root_dir)

    # 0. Anti-Zombie / Immediate Stop Gate: Check if daemon is STOPPED or PAUSED
    registry = load_daemon_registry(root_dir)
    daemon_entry = registry.get("daemons", {}).get(clean_name)
    if not daemon_entry or daemon_entry.get("status") in ["STOPPED", "PAUSED"]:
        status_label = daemon_entry.get("status") if daemon_entry else "STOPPED"
        return {
            "status": "ABORTED",
            "daemon_name": clean_name,
            "reason": f"Daemon '{clean_name}' is currently {status_label}. Execution terminated immediately with zero work performed.",
        }

    # 0B. Concurrency Lock & Anti-Overlap Gate: Prevent concurrent cycles on the same worktree
    if daemon_entry.get("is_busy"):
        busy_pid = daemon_entry.get("current_run_pid")
        if is_workflow_process(busy_pid):
            return {
                "status": "SKIPPED_ALREADY_BUSY",
                "daemon_name": clean_name,
                "reason": f"Daemon '{clean_name}' has an ongoing cycle currently executing (PID: {busy_pid}). Overlap prevented to preserve worktree isolation.",
            }
        else:
            # Stale lock from dead or recycled process
            daemon_entry["is_busy"] = False

    # 0C. Fixed-Delay Cooldown Gate: Enforce delay interval from previous cycle's completion
    last_completed = daemon_entry.get("last_completed_at")
    interval_mins = daemon_entry.get("interval_minutes", 10)
    if last_completed:
        try:
            last_dt = datetime.fromisoformat(last_completed)
            elapsed_seconds = (datetime.now() - last_dt).total_seconds()
            required_delay = interval_mins * 60
            if elapsed_seconds < required_delay:
                remaining = int(required_delay - elapsed_seconds)
                return {
                    "status": "SKIPPED_COOLDOWN_ACTIVE",
                    "daemon_name": clean_name,
                    "reason": f"Fixed-delay interval of {interval_mins}m has not elapsed yet since previous cycle finished ({remaining}s remaining). Overlap prevented.",
                    "seconds_remaining": remaining,
                }
        except Exception:
            pass

    # Acquire Execution Concurrency Lock
    daemon_entry["is_busy"] = True
    daemon_entry["current_run_started_at"] = datetime.now().isoformat()
    daemon_entry["current_run_pid"] = os.getpid()
    save_daemon_registry(registry, root_dir)

    cycle_result: Optional[Dict[str, Any]] = None
    try:
        # 1. Setup isolated physical worktree
        wt_result = create_worktree(worktree_name, base_branch=target_base, repo_dir=root_dir)
        if wt_result["status"] == "ERROR":
            cycle_result = {"status": "WORKTREE_ERROR", "details": wt_result}
            return cycle_result

        wt_path = wt_result["worktree_path"]
        branch_name = wt_result.get("branch_name", f"workflow/worktree-{clean_name}")

        # 2. Pre-Cycle Sync: Safely rebase worktree onto latest base branch
        sync_res = sync_worktree_with_base(wt_path, base_branch=target_base, repo_dir=root_dir)
        if sync_res.get("status") == "CONFLICT":
            cycle_result = {
                "status": "SYNC_CONFLICT",
                "message": f"Worktree branch has conflicts with latest '{target_base}'. Resolve manually or re-create worktree.",
                "details": sync_res,
                "worktree_path": wt_path,
            }
            return cycle_result

        # 3. Find pending spec or run test health check
        target_spec_path = None
        if os.path.exists(spec_dir):
            for item in os.listdir(spec_dir):
                candidate = os.path.join(spec_dir, item)
                if os.path.isdir(candidate):
                    target_spec_path = candidate
                    break

        if not target_spec_path:
            cycle_result = {
                "status": "IDLE",
                "message": f"No pending specs found in '{spec_dir}'. Daemon cycle complete with zero work required.",
                "worktree_path": wt_path,
            }
            return cycle_result

        # 4. Execute LangGraph DAG state machine on target spec
        engine = WorkflowEngine(target_spec_path)
        dag_result = engine.run_step()

        # 5. Safe Auto-Merge Gate with Dirty Working Tree Protection
        merge_status = "SKIPPED"
        if auto_merge and dag_result.get("all_tests_passing") and dag_result.get("spec_verified"):
            status_check = run_git(["status", "--porcelain"], cwd=root_dir)
            if status_check.stdout.strip():
                merge_status = "DIRTY_TREE_POSTPONED: Uncommitted changes present on base branch. Auto-merge postponed safely."
            else:
                merge_cmd = run_git(["merge", "--no-ff", branch_name, "-m", f"chore(workflow): auto-merge daemon '{clean_name}'"], cwd=root_dir)
                merge_status = "MERGED" if merge_cmd.returncode == 0 else f"MERGE_FAILED: {merge_cmd.stderr.strip()}"
                if merge_cmd.returncode == 0:
                    remove_worktree(worktree_name, repo_dir=root_dir, force=True)

        cycle_result = {
            "status": "COMPLETED",
            "daemon_name": clean_name,
            "archetype": archetype,
            "worktree_path": wt_path,
            "branch_name": branch_name,
            "dag_step": dag_result.get("dag_step"),
            "all_tests_passing": dag_result.get("all_tests_passing"),
            "spec_verified": dag_result.get("spec_verified"),
            "merge_status": merge_status,
        }
        return cycle_result
    finally:
        # Release Concurrency Lock & Record Completion Timestamp for Fixed Delay
        latest_reg = load_daemon_registry(root_dir)
        if clean_name in latest_reg.get("daemons", {}):
            entry = latest_reg["daemons"][clean_name]
            now_iso = datetime.now().isoformat()
            entry["is_busy"] = False
            entry["current_run_pid"] = None
            entry["last_completed_at"] = now_iso
            entry["last_heartbeat"] = now_iso
            entry["last_run_at"] = now_iso
            if cycle_result:
                entry["last_result"] = cycle_result.get("status", "COMPLETED")
            entry["iteration_count"] = entry.get("iteration_count", 0) + 1

            # Check Max Iterations Cap
            max_iter = entry.get("max_iterations")
            if max_iter and max_iter > 0 and entry["iteration_count"] >= max_iter:
                entry["status"] = "STOPPED"
                entry["stopped_at"] = now_iso
                entry["stopped_reason"] = f"MAX_ITERATIONS_REACHED ({entry['iteration_count']}/{max_iter})"
                force_purge_worktree(clean_name, repo_dir=root_dir)

            save_daemon_registry(latest_reg, root_dir)
