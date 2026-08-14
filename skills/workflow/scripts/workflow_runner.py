#!/usr/bin/env python3
"""Workflow Suite: Deterministic State Machine Runner & SDD/TDD Engine for AI Agents."""

import argparse
import json
import os
import sys
import subprocess
from typing import Dict, Any

from scaffolder import scaffold_init, scaffold_new_spec, archive_spec
from explorer import scan_codebase, generate_master_context
from drift_detector import check_drift, sync_drift
from memory_manager import log_decision, compact_archetype_memory, get_memory_status
from worktree_manager import list_worktrees, create_worktree, remove_worktree, prune_worktrees
from quality_auditor import audit_spec
from daemon_manager import run_daemon_cycle, load_workflow_config
from orchestrator import prepare_subagent_dispatch
from graph.engine import WorkflowEngine


def cmd_check_env(args: argparse.Namespace) -> int:
    """Verifies runtime environment: Python version, Git setup, uv, and dependencies."""
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 10)

    git_res = subprocess.run(["git", "--version"], capture_output=True, text=True, check=False)
    git_ok = git_res.returncode == 0
    git_ver = git_res.stdout.strip() if git_ok else "Not installed"

    uv_res = subprocess.run(["uv", "--version"], capture_output=True, text=True, check=False)
    uv_ok = uv_res.returncode == 0
    uv_ver = uv_res.stdout.strip() if uv_ok else "Not installed"

    try:
        import langgraph
        langgraph_ver = getattr(langgraph, "__version__", "Installed")
        lg_ok = True
    except ImportError:
        langgraph_ver = "Not installed (pure-Python fallback available)"
        lg_ok = False

    data = {
        "status": "PASS" if py_ok and git_ok else "FAIL",
        "python": {"version": py_version, "compatible": py_ok, "required": ">=3.10"},
        "git": {"version": git_ver, "available": git_ok},
        "uv": {"version": uv_ver, "available": uv_ok},
        "langgraph": {"version": langgraph_ver, "available": lg_ok},
    }

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print("⚡ Workflow Environment Diagnostic:")
        print(f"  • Python:    {py_version} [{'PASS' if py_ok else 'FAIL: requires >=3.10'}]")
        print(f"  • Git:       {git_ver} [{'PASS' if git_ok else 'FAIL'}]")
        print(f"  • Astral uv: {uv_ver} [{'PASS' if uv_ok else 'OPTIONAL'}]")
        print(f"  • LangGraph: {langgraph_ver} [{'PASS' if lg_ok else 'FALLBACK_ACTIVE'}]")

    return 0 if py_ok and git_ok else 1


def cmd_init(args: argparse.Namespace) -> int:
    """Scaffolds workflow directory structure in target repository with agnostic test runner selection."""
    scan = scan_codebase(args.target_dir)
    selected_test_runner = args.test_runner or scan.get("test_runner", "pnpm test")

    result = scaffold_init(args.target_dir, test_runner_cmd=selected_test_runner)
    master_file = generate_master_context(args.target_dir)
    result["master_memory"] = master_file
    result["test_runner"] = selected_test_runner
    result["detected_candidates"] = scan.get("test_candidates", [])

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"✅ Workflow initialized successfully in '{result['target_dir']}':")
        print(f"  • Config:       {result['config_file']}")
        print(f"  • Test Runner:  {selected_test_runner}")
        print(f"  • Specs Dir:    {result['specs_dir']} (features, bugs, refactor, docs, archive)")
        print(f"  • Memory Dir:   {result['memory_dir']}")
        print(f"  • Master Doc:   {master_file}")
    return 0


def cmd_explore(args: argparse.Namespace) -> int:
    """Runs codebase explorer scanner and generates/updates master context."""
    master_file = generate_master_context(args.target_dir)
    scan = scan_codebase(args.target_dir)

    if args.json:
        print(json.dumps({"status": "SUCCESS", "master_file": master_file, "scan": scan}, indent=2))
    else:
        print(f"🔍 Codebase Explorer Survey Complete:")
        print(f"  • Project:         {scan['project_name']}")
        print(f"  • Languages:       {scan['languages']}")
        print(f"  • Frameworks:      {scan['frameworks']}")
        print(f"  • Packages:        {scan['package_manager']}")
        print(f"  • Test Runner:     {scan['test_runner']}")
        print(f"  • Candidates:      {', '.join(scan.get('test_candidates', []))}")
        print(f"  • Master Doc:      {master_file}")
    return 0


def cmd_drift(args: argparse.Namespace) -> int:
    """Checks or syncs tech drift and manifest anomalies."""
    if args.sync:
        res = sync_drift(args.target_dir)
    else:
        drift, info = check_drift(args.target_dir)
        res = {"status": "SUCCESS", "drift_detected": drift, "info": info}

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        if args.sync:
            print(f"🔄 Tech Drift Sync: {res.get('message')}")
        else:
            status_str = "⚠️ DRIFT DETECTED" if res.get("drift_detected") else "✅ SYNCHRONIZED"
            print(f"🛡️ Tech Drift Status: {status_str}")
            if res.get("drift_detected"):
                print(f"  Details: {res.get('info', {}).get('details')}")
                print("  Tip: Run '/workflow drift --sync' to re-survey.")
    return 0


def cmd_memory(args: argparse.Namespace) -> int:
    """Manages hierarchical memory namespaces and compaction."""
    if args.action == "status":
        res = get_memory_status(args.target_dir)
    elif args.action == "compact":
        archetype = args.archetype or "fix"
        res = compact_archetype_memory(args.target_dir, archetype)
    elif args.action == "log":
        if not args.message:
            print("Error: --message required for logging decision", file=sys.stderr)
            return 1
        archetype = args.archetype or "implement"
        file_path = log_decision(args.target_dir, archetype, args.message, args.content or args.message)
        res = {"status": "LOGGED", "file": file_path, "archetype": archetype}
    else:
        res = {"status": "ERROR", "message": "Unknown memory action"}

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"🧠 Memory Operation: {json.dumps(res, indent=2)}")
    return 0


def cmd_new(args: argparse.Namespace) -> int:
    """Creates a new spec directory under specs/features/, specs/bugs/, etc."""
    res = scaffold_new_spec(args.spec_name, archetype=args.archetype, target_dir=args.target_dir)
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"✨ Created new spec '{args.spec_name}' [Namespace: specs/{res.get('namespace')}]:")
        print(f"  • Spec Document:    {res['spec_file']}")
        print(f"  • State Checkpoint: {res['state_file']}")
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    """Archives a completed spec folder into specs/archive/<year>/."""
    res = archive_spec(args.spec_name, target_dir=args.target_dir)
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        if res.get("status") == "ARCHIVED":
            print(f"📦 Spec Archived Cleanly:")
            print(f"  • Source:  {res.get('source_path')}")
            print(f"  • Archive: {res.get('archive_path')}")
        else:
            print(f"❌ Archive Error: {res.get('message')}")
    return 0 if res.get("status") == "ARCHIVED" else 1


def cmd_check(args: argparse.Namespace) -> int:
    """Runs the Pre-Execution Quality Gate on a spec."""
    res = audit_spec(args.spec_dir)
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        status_label = "✅ PASS" if res["passed"] else "⚠️ NEEDS_REFINEMENT"
        print(f"📋 Spec Quality Audit: {status_label} (Score: {res['score']}/100)")
        if res.get("errors"):
            print("  Errors:")
            for e in res["errors"]:
                print(f"    - {e}")
        if res.get("recommendations"):
            print("  Recommendations:")
            for r in res["recommendations"]:
                print(f"    - {r}")
    return 0 if res["passed"] else 1


def cmd_run(args: argparse.Namespace) -> int:
    """Executes the LangGraph DAG state machine for a spec."""
    engine = WorkflowEngine(args.spec_dir)
    res = engine.run_step()
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"🚀 Executed Workflow DAG for '{res.get('spec_name')}':")
        print(f"  • Step:       {res.get('dag_step')}")
        print(f"  • Tests Pass: {res.get('all_tests_passing')}")
        print(f"  • Verified:   {res.get('spec_verified')}")
    return 0


def cmd_daemon(args: argparse.Namespace) -> int:
    """Executes a daemon cycle in an isolated worktree."""
    if args.action == "list":
        config = load_workflow_config(args.target_dir)
        worktrees = list_worktrees(args.target_dir)
        data = {"configured_daemons": config.get("daemons", {}), "active_worktrees": worktrees}
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print("🤖 Configured Daemons & Worktrees:")
            print(json.dumps(data, indent=2))
        return 0

    daemon_name = args.name or "auto-fixer"
    res = run_daemon_cycle(
        daemon_name=daemon_name,
        archetype=args.archetype,
        auto_merge=args.auto_merge,
        root_dir=args.target_dir,
    )
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"🤖 Daemon Execution [{daemon_name}]:")
        print(f"  • Worktree: {res.get('worktree_path')}")
        print(f"  • Branch:   {res.get('branch_name')}")
        print(f"  • DAG Step: {res.get('dag_step')}")
        print(f"  • Merge:    {res.get('merge_status')}")
    return 0


def cmd_worktree(args: argparse.Namespace) -> int:
    """Manages physical git worktree directories."""
    if args.action == "list":
        wt = list_worktrees(args.target_dir)
        res = {"worktrees": wt}
    elif args.action == "add":
        if not args.name:
            print("Error: --name required for worktree add", file=sys.stderr)
            return 1
        res = create_worktree(args.name, repo_dir=args.target_dir)
    elif args.clean:
        if not args.name:
            print("Error: --name required for worktree clean", file=sys.stderr)
            return 1
        res = remove_worktree(args.name, repo_dir=args.target_dir, force=args.force)
    elif args.action == "prune":
        ok = prune_worktrees(args.target_dir)
        res = {"status": "PRUNED" if ok else "ERROR"}
    else:
        res = {"status": "ERROR", "message": "Unknown worktree action"}

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"🌲 Worktree Manager: {json.dumps(res, indent=2)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Constructs CLI argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="workflow_runner.py",
        description="Deterministic State Machine Runner, SDD/TDD Engine & Multi-Daemon Worktree Manager",
    )
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # check-env
    subparsers.add_parser("check-env", help="Verify runtime environment, Python >=3.10, Git, and dependencies")

    # init
    p_init = subparsers.add_parser("init", help="Initialize specs/, memory/, and workflow.json in target repo")
    p_init.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")
    p_init.add_argument("--test-runner", help="Explicit test runner command to set in workflow.json")

    # explore
    p_exp = subparsers.add_parser("explore", help="Scan codebase tech stack and generate master context")
    p_exp.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # drift
    p_drift = subparsers.add_parser("drift", help="Detect or synchronize tech drift and manifest changes")
    p_drift.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")
    p_drift.add_argument("--sync", action="store_true", help="Re-survey and update context automatically")

    # memory
    p_mem = subparsers.add_parser("memory", help="Manage hierarchical memory and 00-10 compaction")
    p_mem.add_argument("action", choices=["status", "compact", "log"], help="Memory action")
    p_mem.add_argument("--archetype", choices=["fix", "refactor", "implement", "doc_sync"], help="Archetype namespace")
    p_mem.add_argument("--message", help="Decision title for logging")
    p_mem.add_argument("--content", help="Decision content details")
    p_mem.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # new
    p_new = subparsers.add_parser("new", help="Scaffold a new spec folder under specs/features/, specs/bugs/, etc.")
    p_new.add_argument("spec_name", help="Name of the new spec")
    p_new.add_argument("--archetype", choices=["feat", "feature", "fix", "bug", "refactor", "doc"], default="feat", help="Target archetype (feat creates under specs/features/)")
    p_new.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # archive
    p_arc = subparsers.add_parser("archive", help="Move completed spec folder into specs/archive/<year>/")
    p_arc.add_argument("spec_name", help="Name of the spec to archive")
    p_arc.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # check
    p_chk = subparsers.add_parser("check", help="Run the Pre-Execution Quality Gate on a spec")
    p_chk.add_argument("spec_dir", help="Path to the spec folder or spec.md")

    # run
    p_run = subparsers.add_parser("run", help="Execute the LangGraph DAG state machine for a spec")
    p_run.add_argument("spec_dir", help="Path to the spec folder")

    # daemon
    p_daemon = subparsers.add_parser("daemon", help="Run a daemon worker cycle in an isolated worktree")
    p_daemon.add_argument("name", nargs="?", help="Named daemon job in workflow.json")
    p_daemon.add_argument("--action", choices=["run", "list", "stop"], default="run", help="Daemon action")
    p_daemon.add_argument("--archetype", choices=["fix", "refactor", "implement", "doc_sync"], default="fix", help="Archetype persona")
    p_daemon.add_argument("--auto-merge", action="store_true", help="Enable safe auto-merge into main on completion")
    p_daemon.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # worktree
    p_wt = subparsers.add_parser("worktree", help="Manage physical git worktrees")
    p_wt.add_argument("action", choices=["list", "add", "clean", "prune"], help="Worktree action")
    p_wt.add_argument("--name", help="Worktree identifier")
    p_wt.add_argument("--force", action="store_true", help="Force remove worktree")
    p_wt.add_argument("target_dir", nargs="?", default=".", help="Target repository directory")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        return 0

    commands = {
        "check-env": cmd_check_env,
        "init": cmd_init,
        "explore": cmd_explore,
        "drift": cmd_drift,
        "memory": cmd_memory,
        "new": cmd_new,
        "archive": cmd_archive,
        "check": cmd_check,
        "run": cmd_run,
        "daemon": cmd_daemon,
        "worktree": cmd_worktree,
    }

    handler = commands.get(args.subcommand)
    if handler:
        return handler(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
