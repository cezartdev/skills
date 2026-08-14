#!/usr/bin/env python3
"""Workflow Suite: Deterministic State Machine Runner, SDD/TDD Engine, Multi-Daemon & Multi-PR Curator."""

import argparse
import json
import os
import sys
import subprocess
from typing import Dict, Any, List, Optional

from scaffolder import scaffold_init, scaffold_new_spec, archive_spec, get_workflow_root
from explorer import scan_codebase, generate_master_context
from drift_detector import check_drift, sync_drift
from memory_manager import log_decision, compact_archetype_memory, get_memory_status
from worktree_manager import list_worktrees, create_worktree, remove_worktree, force_purge_worktree, prune_worktrees
from quality_auditor import audit_spec
from daemon_manager import (
    start_daemon,
    stop_daemon,
    pause_daemon,
    resume_daemon,
    stop_all_daemons,
    clean_orphaned_daemons,
    get_daemon_status_table,
    run_daemon_cycle,
    load_workflow_config
)
from curator import compile_scoped_pr_summary, create_curator_pr, archive_merged_pr
from orchestrator import prepare_subagent_dispatch, generate_subagent_directive, get_archetype_prompt
from graph.engine import WorkflowEngine


def resolve_spec_path(spec_arg: str, target_dir: str = ".") -> str:
    """Smart Path Resolver: resolves spec path from shorthand name or direct path."""
    target_dir = os.path.abspath(target_dir)
    if os.path.exists(spec_arg):
        return os.path.abspath(spec_arg)

    wf_root = get_workflow_root(target_dir)
    specs_root = os.path.join(wf_root, "specs")

    for folder in ["features", "bugs", "refactor", "docs"]:
        candidate = os.path.join(specs_root, folder, spec_arg)
        if os.path.exists(candidate):
            return candidate

    legacy_specs = os.path.join(target_dir, "specs")
    for folder in ["features", "bugs", "refactor", "docs"]:
        candidate = os.path.join(legacy_specs, folder, spec_arg)
        if os.path.exists(candidate):
            return candidate

    return os.path.abspath(os.path.join(specs_root, "features", spec_arg))


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
    """Scaffolds encapsulated .workflow directory structure in target repository."""
    scan = scan_codebase(args.target_dir)
    selected_test_runner = args.test_runner or scan.get("test_runner", "pytest")

    result = scaffold_init(args.target_dir, test_runner_cmd=selected_test_runner)
    master_file = generate_master_context(args.target_dir)
    result["master_memory"] = master_file
    result["test_runner"] = selected_test_runner
    result["detected_candidates"] = scan.get("test_candidates", [])

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"✅ Encapsulated .workflow initialized in '{result['target_dir']}':")
        print(f"  • Module Root:  {result['workflow_dir']}")
        print(f"  • Config:       {result['config_file']}")
        print(f"  • Test Runner:  {selected_test_runner}")
        print(f"  • Specs Dir:    {result['specs_dir']} (features, bugs, refactor, docs, archive)")
        print(f"  • Memory Dir:   {result['memory_dir']}")
        print(f"  • PRs Catalog:  {result['prs_dir']} (active, archive)")
        print(f"  • Master Doc:   {master_file}")
    return 0


def cmd_explore(args: argparse.Namespace) -> int:
    """Runs codebase explorer scanner and updates .workflow/memory/00_project_context.md."""
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
        print(f"  • Master Context:  {master_file}")
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
    """Manages hierarchical memory namespaces under .workflow/memory/."""
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
    """Creates a new spec directory under .workflow/specs/<namespace>/<spec_name>/."""
    res = scaffold_new_spec(args.spec_name, archetype=args.archetype, target_dir=args.target_dir)
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"✨ Created new spec '{args.spec_name}' [Namespace: .workflow/specs/{res.get('namespace')}]:")
        print(f"  • Spec Document:    {res['spec_file']}")
        print(f"  • State Checkpoint: {res['state_file']}")
    return 0


def cmd_specify(args: argparse.Namespace) -> int:
    """Interactive Spec Co-Authoring & Debate Session (GitHub Spec-Kit style)."""
    resolved_path = resolve_spec_path(args.spec_name, target_dir=args.target_dir)
    audit = audit_spec(resolved_path)

    spec_file = audit.get("spec_file", resolved_path)
    spec_name = os.path.basename(resolved_path.rstrip("/\\"))

    questions = []
    if not audit["checks"].get("architecture"):
        questions.append("What are the primary data models, schemas, or function interfaces involved?")
    if not audit["checks"].get("edge_cases"):
        questions.append("What boundary conditions, network timeouts, or error states must be handled?")
    if not audit["checks"].get("acceptance_criteria"):
        questions.append("What are the 3 to 5 measurable, testable acceptance criteria to verify completion?")
    if not questions:
        questions.append("Are there any third-party dependencies, security constraints, or performance targets to specify?")

    data = {
        "status": "READY_FOR_SPECIFY",
        "spec_name": spec_name,
        "spec_path": resolved_path,
        "spec_file": spec_file,
        "current_score": audit["score"],
        "checks": audit["checks"],
        "recommendations": audit.get("recommendations", []),
        "debate_questions": questions,
    }

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print("=" * 72)
        print(f" 📝 SPECIFY SESSION: {spec_name} (Current Quality Score: {audit['score']}/100)")
        print("=" * 72)
        print(f"Target File: {spec_file}\n")
        print("🔍 Socratic Debate Questions to Refine this Spec:")
        for idx, q in enumerate(questions, 1):
            print(f"  {idx}. {q}")
        if audit.get("recommendations"):
            print("\n💡 Quality Recommendations:")
            for r in audit["recommendations"]:
                print(f"  • {r}")
        print("\n👉 Next Steps & Interactive Grilling Directive:")
        print("  • AI Agent: Launch interactive question tool (e.g. ask_question) asking 1 question at a time with curated options.")
        print(f"  • Update '{spec_file}' iteratively as answers arrive.")
        print(f"  • Run 'uv run skills/workflow/scripts/workflow_runner.py check {spec_name}' to verify 100/100 Quality Gate.")
        print(f"  • Proceed to 'uv run skills/workflow/scripts/workflow_runner.py plan {spec_name}'.")
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    """Decomposes a refined spec into atomic TDD task issues."""
    resolved_path = resolve_spec_path(args.spec_name, target_dir=args.target_dir)
    issues_dir = os.path.join(resolved_path, "issues") if os.path.isdir(resolved_path) else os.path.join(os.path.dirname(resolved_path), "issues")
    os.makedirs(issues_dir, exist_ok=True)

    existing_issues = sorted([f for f in os.listdir(issues_dir) if f.endswith(".md")])
    data = {
        "status": "SUCCESS",
        "spec_name": os.path.basename(resolved_path.rstrip("/\\")),
        "spec_path": resolved_path,
        "issues_dir": issues_dir,
        "existing_issues": existing_issues,
        "count": len(existing_issues),
    }

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(f"📋 Spec Task Plan for '{data['spec_name']}':")
        print(f"  • Issues Directory: {issues_dir}")
        print(f"  • Active Issues:    {len(existing_issues)} tasks planned")
        for iss in existing_issues:
            print(f"    - {iss}")
        print(f"  Tip: Run '/workflow check {data['spec_name']}' then '/workflow run {data['spec_name']}'.")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Runs the Pre-Execution Quality Gate on a spec."""
    resolved_path = resolve_spec_path(args.spec_dir, target_dir=args.target_dir if hasattr(args, "target_dir") else ".")
    res = audit_spec(resolved_path)

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
    resolved_path = resolve_spec_path(args.spec_dir)
    engine = WorkflowEngine(resolved_path)
    res = engine.run_step()

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"🚀 Executed Workflow DAG for '{res.get('spec_name')}':")
        print(f"  • Step:       {res.get('dag_step')}")
        print(f"  • Tests Pass: {res.get('all_tests_passing')}")
        print(f"  • Verified:   {res.get('spec_verified')}")
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    """Archives a completed spec folder into .workflow/specs/archive/<year>/."""
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


def cmd_chat(args: argparse.Namespace) -> int:
    """Gathers project context snapshot and launches freeform architectural dialogue."""
    target_dir = os.path.abspath(args.target_dir)
    wf_root = get_workflow_root(target_dir)
    master_file = os.path.join(wf_root, "memory", "00_project_context.md")

    context_summary = "Not initialized (run /workflow init or explore)"
    if os.path.exists(master_file):
        with open(master_file, "r", encoding="utf-8") as f:
            context_summary = f.read()

    specs_root = os.path.join(wf_root, "specs")
    active_specs = {}
    if os.path.exists(specs_root):
        for sub in ["features", "bugs", "refactor", "docs"]:
            sub_dir = os.path.join(specs_root, sub)
            if os.path.exists(sub_dir):
                active_specs[sub] = [d for d in os.listdir(sub_dir) if os.path.isdir(os.path.join(sub_dir, d))]

    scoped_spec = None
    if args.spec_name:
        resolved = resolve_spec_path(args.spec_name, target_dir=target_dir)
        scoped_spec = {"name": os.path.basename(resolved), "path": resolved}

    data = {
        "status": "READY_FOR_CHAT",
        "project_root": target_dir,
        "workflow_root": wf_root,
        "active_specs": active_specs,
        "scoped_spec": scoped_spec,
        "master_context_available": os.path.exists(master_file),
    }

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print("=" * 72)
        print(" 💬 WORKFLOW CHAT & ARCHITECTURAL ADVISOR")
        print("=" * 72)
        if scoped_spec:
            print(f"📌 Scoped Focus: Spec '{scoped_spec['name']}' at {scoped_spec['path']}")
        else:
            print("🌐 Scope: Global Project Context & Brainstorming")
        print(f"📦 Active Specifications: {sum(len(v) for v in active_specs.values())} in flight")
        for k, v in active_specs.items():
            if v:
                print(f"  • {k}: {', '.join(v)}")
        print("\n✨ Ready to discuss architectural trade-offs, ideas, or stack questions.")
        print("Ask any question or propose an idea to explore!")
    return 0


def cmd_curate(args: argparse.Namespace) -> int:
    """Executes the Curator Subagent: manages multi-PR catalog and compiles scoped PR summaries."""
    target_dir = os.path.abspath(args.target_dir if hasattr(args, "target_dir") and args.target_dir else ".")
    target_branch = args.target_branch if hasattr(args, "target_branch") and args.target_branch else "main"
    create_pr = getattr(args, "create_pr", False)
    archetype = getattr(args, "archetype", None)
    spec_name = getattr(args, "spec", None)

    if getattr(args, "archive", None):
        res = archive_merged_pr(args.archive, target_dir=target_dir)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"📦 Archived PR Summary: {res.get('destination', res.get('message'))}")
        return 0

    res = create_curator_pr(
        target_dir=target_dir,
        archetype=archetype,
        spec_name=spec_name,
        target_branch=target_branch,
        create_pr=create_pr
    )

    if args.json:
        print(json.dumps(res, indent=2))
        return 0

    print("=" * 80)
    print(" 🚀 WORKFLOW CURATOR — MULTI-PR CATALOG & SUMMARY")
    print("=" * 80)
    print(f"Title: {res.get('title')}")
    print(f"PR Document: {res.get('pr_file')}\n")
    print("📊 Integrated Changes Breakdown:")
    counts = res.get("counts", {})
    for k, v in counts.items():
        print(f"  • {k.capitalize():<12}: {v} decisions integrated")
    print(f"  • Total Changes: {res.get('total_changes', 0)}")

    if res.get("status") == "PR_CREATED":
        print(f"\n✅ Pull Request Opened: {res.get('pr_url')}")
    elif create_pr and not res.get("gh_available"):
        print(f"\n💡 GitHub CLI ('gh') not authenticated. PR summary saved in {res.get('pr_file')}.")
    else:
        print(f"\n💡 Summary saved cleanly in .workflow/prs/active/. Run with '--create-pr' to open GitHub PR.")
    print("=" * 80)
    return 0


def cmd_daemon(args: argparse.Namespace) -> int:
    """Manages background daemon subagents, cron scheduling, and Anti-Zombie lifecycle."""
    action = args.action or "status"
    target_dir = os.path.abspath(args.target_dir if hasattr(args, "target_dir") and args.target_dir else ".")

    if action == "start":
        name = args.name or "auto-fixer"
        interval = args.interval or 10
        res = start_daemon(daemon_name=name, interval_minutes=interval, archetype=args.archetype, target_dir=target_dir)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print("=" * 72)
            print(f" 🤖 DAEMON STARTED: '{name}' (Schedule: every {interval} mins)")
            print("=" * 72)
            print(f"  • Worktree Path:   {res['worktree_path']}")
            print(f"  • Cron Expression: {res['cron_expression']}")
            print(f"  • Subagent Role:   {res['subagent_directive']['role']}")
            print("\n📋 Subagent Dispatch Directive Generated:")
            print(json.dumps(res["subagent_directive"], indent=2))
            print("\n👉 To stop this worker, run '/workflow daemon stop " + name + "'")
        return 0

    elif action == "pause":
        name = args.name or "auto-fixer"
        res = pause_daemon(name, target_dir=target_dir)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"⏸️ Daemon '{name}' paused. Cron cycles suspended without destroying worktree.")
        return 0

    elif action == "resume":
        name = args.name or "auto-fixer"
        res = resume_daemon(name, target_dir=target_dir)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"▶️ Daemon '{name}' resumed active cron execution.")
        return 0

    elif action == "stop":
        if getattr(args, "all", False) or not args.name:
            res = stop_all_daemons(target_dir=target_dir)
            if args.json:
                print(json.dumps(res, indent=2))
            else:
                print("🛑 All background daemons stopped and Anti-Zombie worktree purges executed.")
        else:
            res = stop_daemon(args.name, target_dir=target_dir, force=getattr(args, "force", False))
            if args.json:
                print(json.dumps(res, indent=2))
            else:
                print(f"🛑 Daemon '{args.name}' stopped successfully. Worktree and lockfiles purged.")
        return 0

    elif action == "clean":
        res = clean_orphaned_daemons(target_dir=target_dir)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"🧹 Anti-Zombie Clean Complete: Purged {len(res.get('purged_daemons', []))} stale daemons/worktrees.")
        return 0

    elif action in ["status", "list"]:
        res = get_daemon_status_table(target_dir=target_dir)
        if args.json:
            print(json.dumps(res, indent=2))
            return 0
        print("=" * 80)
        print(" 🤖 WORKFLOW DAEMONS & BACKGROUND SUBAGENTS STATUS")
        print("=" * 80)
        print(f"Active Daemons Running: {res['active_count']}\n")
        if not res["daemons"]:
            print("No daemons active. Start one using '/workflow daemon start auto-fixer --interval 10'.")
        else:
            print(f"{'NAME':<20} │ {'STATUS':<10} │ {'INTERVAL':<12} │ {'LAST RESULT':<18} │ WORKTREE")
            print("-" * 80)
            for d in res["daemons"]:
                status_str = "🟢 RUNNING" if d["status"] == "RUNNING" else ("⏸️ PAUSED" if d["status"] == "PAUSED" else "⚪ STOPPED")
                print(f"{d['name']:<20} │ {status_str:<10} │ every {d['interval_minutes']}m     │ {str(d.get('last_result')):<18} │ {d['worktree_path']}")
        print("=" * 80)
        return 0

    elif action == "run":
        name = args.name or "auto-fixer"
        res = run_daemon_cycle(
            daemon_name=name,
            archetype=args.archetype,
            auto_merge=getattr(args, "auto_merge", False),
            root_dir=target_dir
        )
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"🤖 One-Shot Daemon Execution [{name}]:")
            print(f"  • Status:     {res.get('status')}")
            print(f"  • Worktree:   {res.get('worktree_path')}")
            print(f"  • DAG Step:   {res.get('dag_step')}")
            print(f"  • Tests Pass: {res.get('all_tests_passing')}")
            print(f"  • Merge:      {res.get('merge_status')}")
        return 0

    return 0


def cmd_worktree(args: argparse.Namespace) -> int:
    """Manages physical git worktree directories under .workflow/worktrees/."""
    if args.action == "list":
        wt = list_worktrees(args.target_dir)
        res = {"worktrees": wt}
    elif args.action == "add":
        if not args.name:
            print("Error: --name required for worktree add", file=sys.stderr)
            return 1
        res = create_worktree(args.name, repo_dir=args.target_dir)
    elif args.action == "clean":
        if not args.name:
            print("Error: --name required for worktree clean", file=sys.stderr)
            return 1
        res = force_purge_worktree(args.name, repo_dir=args.target_dir)
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


def cmd_list(args: argparse.Namespace) -> int:
    """Displays the complete categorized command catalog and cheat-sheet."""
    catalog = {
        "Discovery & Setup (Polyglot)": [
            {"command": "/workflow init", "syntax": "workflow init [dir] [--test-runner <cmd>]", "desc": "Initialize encapsulated .workflow module, specs/, memory/, prs/, and workflow.json"},
            {"command": "/workflow explore", "syntax": "workflow explore [dir]", "desc": "Scan polyglot stack (Python/uv, Rust, Go, Node, Java, .NET) & update context"},
            {"command": "/workflow drift", "syntax": "workflow drift [--sync] [dir]", "desc": "Detect manifest checksum changes or framework migrations and sync context"},
            {"command": "/workflow check-env", "syntax": "workflow check-env", "desc": "Diagnostic check of Python >=3.10, Git, uv, and LangGraph availability"},
        ],
        "Spec-Driven Development (SDD)": [
            {"command": "/workflow new", "syntax": "workflow new <name> [--archetype feat|bug|refactor|doc]", "desc": "Scaffold a new spec (defaults to feat -> .workflow/specs/features/)"},
            {"command": "/workflow specify", "syntax": "workflow specify <name>", "desc": "Socratic debate & interactive interview to co-author spec.md details (Spec-Kit style)"},
            {"command": "/workflow plan", "syntax": "workflow plan <name>", "desc": "Decompose refined spec into atomic TDD task issues under issues/*.md"},
            {"command": "/workflow check", "syntax": "workflow check <name>", "desc": "Pre-Execution Quality Gate: deterministic regex audit of criteria, edge cases & score"},
            {"command": "/workflow archive", "syntax": "workflow archive <name>", "desc": "Move completed and verified spec folder to .workflow/specs/archive/<year>/"},
        ],
        "TDD Execution & Worktrees": [
            {"command": "/workflow run", "syntax": "workflow run <name>", "desc": "Execute deterministic LangGraph DAG state machine (RED -> GREEN -> REFACTOR)"},
            {"command": "/workflow worktree", "syntax": "workflow worktree <list|add|clean|prune>", "desc": "Manage physical Git Worktrees under .workflow/worktrees/ with auto-prune"},
        ],
        "Autonomous Background Daemons & Control": [
            {"command": "/workflow daemon start", "syntax": "workflow daemon start [name] [--interval 10]", "desc": "Schedule background daemon subagent with cron in isolated worktree"},
            {"command": "/workflow daemon pause", "syntax": "workflow daemon pause [name]", "desc": "Temporarily suspend daemon cron triggers without destroying worktree"},
            {"command": "/workflow daemon resume", "syntax": "workflow daemon resume [name]", "desc": "Resume scheduled cron execution for a paused daemon"},
            {"command": "/workflow daemon stop", "syntax": "workflow daemon stop [name] [--all]", "desc": "Anti-Zombie shutdown: terminate subagent task, purge worktrees and lockfiles"},
            {"command": "/workflow daemon status", "syntax": "workflow daemon status", "desc": "View active daemon health table, PIDs, and cron execution metrics"},
            {"command": "/workflow daemon clean", "syntax": "workflow daemon clean", "desc": "Scan and forcefully purge all stale worktree locks and dead daemon PIDs"},
        ],
        "Multi-PR Curator & Memory": [
            {"command": "/workflow curate", "syntax": "workflow curate [--archetype <arch>] [--spec <name>] [--create-pr]", "desc": "Curator Subagent: compile scoped PR in .workflow/prs/active/ & open GitHub PR"},
            {"command": "/workflow memory", "syntax": "workflow memory <status|log|compact> [--archetype <arch>]", "desc": "Manage hierarchical episodic memory and 00-10 compaction"},
            {"command": "/workflow chat", "syntax": "workflow chat [spec_name]", "desc": "Open freeform dialogue about project architecture or scoped spec debate"},
            {"command": "/workflow list", "syntax": "workflow list [--json]", "desc": "Display this universal command directory and cheat-sheet"},
        ]
    }

    if args.json:
        print(json.dumps(catalog, indent=2))
        return 0

    print("=" * 88)
    print(" ⚡ WORKFLOW SUITE — UNIVERSAL COMMAND CATALOG & CHEAT-SHEET (.workflow/)")
    print("=" * 88)

    for section, commands in catalog.items():
        print(f"\n📁 {section.upper()}")
        print("-" * 88)
        for cmd in commands:
            print(f"  • {cmd['syntax']:<52} │ {cmd['desc']}")

    print("\n" + "=" * 88)
    print(" 💡 Pro-Tip: Scoped PRs with '/workflow curate --archetype fix' or '--archetype refactor'.")
    print("=" * 88)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Constructs CLI argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="workflow_runner.py",
        description="Deterministic State Machine Runner, SDD/TDD Engine, Multi-Daemon Manager & Multi-PR Curator",
    )
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # check-env
    subparsers.add_parser("check-env", help="Verify runtime environment, Python >=3.10, Git, and dependencies")

    # init
    p_init = subparsers.add_parser("init", help="Initialize encapsulated .workflow/ structure in target repo")
    p_init.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")
    p_init.add_argument("--test-runner", help="Explicit test runner command to set in workflow.json")

    # explore
    p_exp = subparsers.add_parser("explore", help="Scan codebase polyglot stack and generate master context in .workflow/memory/")
    p_exp.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # drift
    p_drift = subparsers.add_parser("drift", help="Detect or synchronize tech drift and manifest changes")
    p_drift.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")
    p_drift.add_argument("--sync", action="store_true", help="Re-survey and update context automatically")

    # memory
    p_mem = subparsers.add_parser("memory", help="Manage hierarchical memory and 00-10 compaction under .workflow/memory/")
    p_mem.add_argument("action", choices=["status", "compact", "log"], help="Memory action")
    p_mem.add_argument("--archetype", choices=["fix", "refactor", "implement", "doc_sync"], help="Archetype namespace")
    p_mem.add_argument("--message", help="Decision title for logging")
    p_mem.add_argument("--content", help="Decision content details")
    p_mem.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # new
    p_new = subparsers.add_parser("new", help="Scaffold a new spec folder under .workflow/specs/features/ (default) or bugs/refactor/docs")
    p_new.add_argument("spec_name", help="Name of the new spec")
    p_new.add_argument("--archetype", choices=["feat", "feature", "fix", "bug", "refactor", "doc"], default="feat", help="Target archetype (defaults to feat -> .workflow/specs/features/)")
    p_new.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # specify
    p_spec = subparsers.add_parser("specify", help="Socratic debate & interactive interview to co-author spec.md (Spec-Kit style)")
    p_spec.add_argument("spec_name", help="Name or path of the spec to refine")
    p_spec.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # plan
    p_plan = subparsers.add_parser("plan", help="Decompose refined spec.md into atomic TDD tasks under issues/*.md")
    p_plan.add_argument("spec_name", help="Name or path of the spec to plan")
    p_plan.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # check
    p_chk = subparsers.add_parser("check", help="Run the Pre-Execution Quality Gate on a spec")
    p_chk.add_argument("spec_dir", help="Path or shorthand name of the spec")
    p_chk.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # run
    p_run = subparsers.add_parser("run", help="Execute the LangGraph DAG state machine for a spec")
    p_run.add_argument("spec_dir", help="Path or shorthand name of the spec")

    # archive
    p_arc = subparsers.add_parser("archive", help="Move completed spec folder into .workflow/specs/archive/<year>/")
    p_arc.add_argument("spec_name", help="Name of the spec to archive")
    p_arc.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # chat
    p_chat = subparsers.add_parser("chat", help="Freeform project brainstorming or scoped spec debate session")
    p_chat.add_argument("spec_name", nargs="?", help="Optional spec name to scope debate")
    p_chat.add_argument("--target-dir", default=".", help="Target workspace directory")

    # curate
    p_curate = subparsers.add_parser("curate", help="Curator Subagent: manage multi-PR catalog in .workflow/prs/active/, compile scoped PRs, and open release PRs")
    p_curate.add_argument("--archetype", choices=["fix", "refactor", "implement", "doc_sync", "all"], help="Scope PR to specific archetype decisions")
    p_curate.add_argument("--spec", help="Scope PR to a specific specification name")
    p_curate.add_argument("--archive", help="Archive a merged PR filename into .workflow/prs/archive/<year>/")
    p_curate.add_argument("--create-pr", action="store_true", help="Open GitHub PR directly via gh CLI")
    p_curate.add_argument("--target-branch", default="main", help="Target merge branch (default: main)")
    p_curate.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # daemon
    p_daemon = subparsers.add_parser("daemon", help="Manage background daemon subagents, cron scheduling, and Anti-Zombie lifecycle")
    p_daemon.add_argument("action", nargs="?", default="status", choices=["start", "pause", "resume", "stop", "status", "clean", "list", "run"], help="Daemon action")
    p_daemon.add_argument("name", nargs="?", help="Named daemon (e.g. auto-fixer, refactor-worker)")
    p_daemon.add_argument("--interval", type=int, default=10, help="Cron interval in minutes (default: 10)")
    p_daemon.add_argument("--archetype", choices=["fix", "refactor", "implement", "doc_sync"], help="Archetype persona")
    p_daemon.add_argument("--all", action="store_true", help="Apply stop/pause to all running daemons")
    p_daemon.add_argument("--force", action="store_true", help="Force terminate process and wipe worktree")
    p_daemon.add_argument("--auto-merge", action="store_true", help="Enable safe auto-merge into main on completion")
    p_daemon.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # worktree
    p_wt = subparsers.add_parser("worktree", help="Manage physical git worktrees under .workflow/worktrees/")
    p_wt.add_argument("action", choices=["list", "add", "clean", "prune"], help="Worktree action")
    p_wt.add_argument("--name", help="Worktree identifier")
    p_wt.add_argument("--force", action="store_true", help="Force remove worktree")
    p_wt.add_argument("target_dir", nargs="?", default=".", help="Target repository directory")

    # list
    subparsers.add_parser("list", help="Display universal command catalog and cheat-sheet")

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
        "specify": cmd_specify,
        "plan": cmd_plan,
        "check": cmd_check,
        "run": cmd_run,
        "archive": cmd_archive,
        "chat": cmd_chat,
        "curate": cmd_curate,
        "daemon": cmd_daemon,
        "worktree": cmd_worktree,
        "list": cmd_list,
    }

    handler = commands.get(args.subcommand)
    if handler:
        return handler(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
