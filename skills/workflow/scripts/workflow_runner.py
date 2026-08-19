#!/usr/bin/env python3
"""Workflow Suite: Deterministic State Machine Runner, SDD/TDD Engine, Multi-Daemon & Multi-PR Curator."""

import argparse
import json
import os
import sys
import subprocess
from typing import Dict, Any, List, Optional

from scaffolder import (
    scaffold_init,
    scaffold_new_spec,
    archive_spec,
    get_workflow_root,
    sanitize_identifier,
    reconcile_gitkeep,
)
from explorer import scan_codebase, generate_master_context
from drift_detector import check_drift, sync_drift
from memory_manager import (
    add_memory_doc,
    list_memory_catalog,
    read_memory_doc,
)
from worktree_manager import list_worktrees, create_worktree, remove_worktree, force_purge_worktree, prune_worktrees, ensure_git_repository
from quality_auditor import audit_spec
from daemon_manager import (
    start_daemon,
    stop_daemon,
    pause_daemon,
    resume_daemon,
    stop_all_daemons,
    clean_orphaned_daemons,
    get_daemon_status_table,
    get_daemon_catalog,
    run_daemon_cycle,
    load_workflow_config,
    reconcile_daemon_registry,
    create_daemon_blueprint,
    update_daemon_config,
)
from curator import compile_scoped_pr_summary, create_curator_pr, archive_merged_pr
from orchestrator import prepare_subagent_dispatch, generate_subagent_directive, get_archetype_prompt
from pipeline import PipelineRunner
from graph.engine import WorkflowEngine


def print_next_steps(suggestions: List[Dict[str, str]]) -> None:
    """Renders actionable subsequent CLI commands in a styled border box."""
    if not suggestions:
        return
    print("\n💡 SUGGESTED NEXT STEPS")
    print("-" * 110)
    for s in suggestions:
        print(f"  👉 {s['cmd']:<70} │ {s['desc']}")
    print("=" * 110)


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
    """Performs cross-platform diagnostic check of Python >=3.10, Git, uv, and dependencies."""
    py_ver = sys.version_info
    py_ok = (py_ver.major == 3 and py_ver.minor >= 10)
    
    git_ok = False
    git_ver = "Not found"
    try:
        res = subprocess.run(["git", "--version"], capture_output=True, text=True, check=False)
        if res.returncode == 0:
            git_ok = True
            git_ver = res.stdout.strip()
    except Exception:
        pass

    uv_ok = False
    uv_ver = "Not found"
    try:
        res = subprocess.run(["uv", "--version"], capture_output=True, text=True, check=False)
        if res.returncode == 0:
            uv_ok = True
            uv_ver = res.stdout.strip()
    except Exception:
        pass

    langgraph_ok = False
    try:
        import langgraph
        langgraph_ok = True
    except ImportError:
        pass

    all_passed = py_ok and git_ok and uv_ok

    report = {
        "status": "PASS" if all_passed else "FAIL",
        "python": {
            "version": f"{py_ver.major}.{py_ver.minor}.{py_ver.micro}",
            "passed": py_ok,
            "required": ">=3.10",
        },
        "git": {
            "version": git_ver,
            "passed": git_ok,
        },
        "uv": {
            "version": uv_ver,
            "passed": uv_ok,
        },
        "langgraph_installed": langgraph_ok,
    }

    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if all_passed else 1

    print("=" * 110)
    print(" 🛠️  WORKFLOW RUNTIME DIAGNOSTIC REPORT")
    print("=" * 110)
    print(f"{'COMPONENT':<20} │ {'STATUS':<10} │ {'VERSION':<30} │ DETAILS")
    print("-" * 110)
    print(f"{'Python':<20} │ {'[PASS]' if py_ok else '[FAIL]':<10} │ {report['python']['version']:<30} │ Required >= 3.10")
    print(f"{'Git':<20} │ {'[PASS]' if git_ok else '[FAIL]':<10} │ {git_ver:<30} │ Standard version control")
    print(f"{'Astral uv':<20} │ {'[PASS]' if uv_ok else '[FAIL]':<10} │ {uv_ver:<30} │ Fast Python package manager")
    print(f"{'LangGraph':<20} │ {'[PASS]' if langgraph_ok else '[INFO]':<10} │ {'Installed' if langgraph_ok else 'Fallback Active':<30} │ Deterministic State Graph Engine")
    print("=" * 110)
    print(f"OVERALL SYSTEM STATUS: {report['status']}")
    print("=" * 110)

    return 0 if all_passed else 1


def cmd_init(args: argparse.Namespace) -> int:
    """Initializes encapsulated .workflow/ structure in target directory."""
    res = scaffold_init(target_dir=args.target_dir, test_runner_cmd=args.test_runner)
    if args.json:
        print(json.dumps(res, indent=2))
        return 0

    print("=" * 110)
    print(f" ✅ WORKFLOW MODULE INITIALIZED ({args.target_dir})")
    print("=" * 110)
    print(f"{'PROPERTY':<24} │ VALUE")
    print("-" * 110)
    print(f"{'Workflow Root':<24} │ {res['workflow_dir']}")
    print(f"{'Configuration':<24} │ {res['config_file']}")
    print(f"{'Test Runner':<24} │ {res['test_runner']}")
    print(f"{'Specs Directory':<24} │ {res['specs_dir']} (features, bugs, refactor, docs, archive)")
    print(f"{'Memory Catalog':<24} │ {res['memory_dir']} (coding_preferences.md, project_context.md, docs/)")
    print(f"{'PRs Catalog':<24} │ {res['prs_dir']} (active, archive)")
    print("=" * 110)

    print("\nℹ️  AI Agent Interactive Question Directive:")
    print("   No explicit test script in manifest. Ask developer with ask_question to choose test runner:")
    print("   Candidates: pytest, cargo test, go test ./..., pnpm test")

    print_next_steps([
        {"cmd": "uv run skills/workflow/scripts/workflow_runner.py explore", "desc": "Survey polyglot stack & update context"},
        {"cmd": "uv run skills/workflow/scripts/workflow_runner.py new <spec-name>", "desc": "Scaffold your first feature specification"},
        {"cmd": "uv run skills/workflow/scripts/workflow_runner.py run <spec-name>", "desc": "Run 4-stage sequential subagent pipeline"},
    ])
    return 0


def cmd_explore(args: argparse.Namespace) -> int:
    """Scans codebase polyglot stack and generates master context in .workflow/memory/."""
    master_path = generate_master_context(args.target_dir)
    scan = scan_codebase(args.target_dir)

    if args.json:
        print(json.dumps(scan, indent=2))
        return 0

    print("=" * 110)
    print(f" 🔭 CODEBASE EXPLORATION COMPLETE: '{scan['project_name']}'")
    print("=" * 110)
    print(f"{'PROPERTY':<24} │ VALUE")
    print("-" * 110)
    print(f"{'Primary Language':<24} │ {scan['languages']}")
    print(f"{'Frameworks':<24} │ {scan['frameworks']}")
    print(f"{'Package Manager':<24} │ {scan['package_manager']}")
    print(f"{'Test Runner':<24} │ {scan['test_runner']}")
    print(f"{'Linters / Tools':<24} │ {scan['linters']['tools']}")
    print(f"{'Master Context':<24} │ {master_path}")
    print("=" * 110)

    print_next_steps([
        {"cmd": "uv run skills/workflow/scripts/workflow_runner.py memory list", "desc": "Inspect generated coding preferences & project context"},
        {"cmd": "uv run skills/workflow/scripts/workflow_runner.py new <spec-name>", "desc": "Scaffold a new feature specification"},
    ])
    return 0


def cmd_drift(args: argparse.Namespace) -> int:
    """Detects or synchronizes tech drift and manifest changes."""
    if args.sync:
        res = sync_drift(args.target_dir)
        if args.json:
            print(json.dumps(res, indent=2))
            return 0
        print("=" * 110)
        print(" 🔄 TECH DRIFT SYNCHRONIZED")
        print("=" * 110)
        print(f"Status: {res['status']} | {res['message']}")
        print("=" * 110)
        return 0

    drift_detected, info = check_drift(args.target_dir)
    if args.json:
        print(json.dumps(info, indent=2))
        return 0

    print("=" * 110)
    print(" 📡 TECH DRIFT AUDIT REPORT")
    print("=" * 110)
    print(f"Drift Detected: {'YES (Action Required)' if drift_detected else 'NO (Synchronized)'}")
    if drift_detected:
        print("-" * 110)
        for manifest, reason in info.get("details", {}).items():
            print(f"  ⚠️  {manifest}: {reason}")
    print("=" * 110)

    print_next_steps([
        {"cmd": "uv run skills/workflow/scripts/workflow_runner.py drift --sync", "desc": "Reconcile drift and update project context"},
    ])
    return 0


def cmd_memory(args: argparse.Namespace) -> int:
    """Manages project memory: coding_preferences.md, project_context.md, and docs/*.md."""
    action = getattr(args, "action", "list") or "list"
    target_dir = getattr(args, "target_dir", ".") or "."

    # Handle directory argument when action is list/status and title is passed as target_dir
    if action in ["status", "list"] and getattr(args, "title", None):
        if os.path.isdir(args.title) or args.title.startswith("/") or args.title.startswith("."):
            target_dir = args.title
            args.title = None

    target_dir = os.path.abspath(target_dir)

    if action in ["list", "status"]:
        res = list_memory_catalog(target_dir)
        if args.json:
            print(json.dumps(res, indent=2))
            return 0

        print("=" * 110)
        print(" 🧠 WORKFLOW MEMORY CATALOG (.workflow/memory/)")
        print("=" * 110)
        print(f"{'ARTIFACT':<26} │ {'STATUS':<12} │ PATH")
        print("-" * 110)
        p_status = "Present" if res["coding_preferences"]["exists"] else "Missing"
        print(f"{'coding_preferences.md':<26} │ {p_status:<12} │ {res['coding_preferences']['path']}")
        c_status = "Present" if res["project_context"]["exists"] else "Missing"
        print(f"{'project_context.md':<26} │ {c_status:<12} │ {res['project_context']['path']}")
        print("=" * 110)

        docs = res.get("docs", [])
        if docs:
            print("\n 📚 DOCUMENTATION NOTES (.workflow/memory/docs/)")
            print("=" * 110)
            print(f"{'INDEX':<8} │ {'FILENAME':<30} │ TITLE")
            print("-" * 110)
            for d in docs:
                print(f"{d['index']:<8} │ {d['filename']:<30} │ {d['title']}")
            print("=" * 110)
        else:
            print("\nℹ️  No custom memory documentation notes found under .workflow/memory/docs/.")

        print_next_steps([
            {"cmd": "uv run skills/workflow/scripts/workflow_runner.py memory add <title> --content \"...\"", "desc": "Add indexed note to memory/docs/"},
            {"cmd": "uv run skills/workflow/scripts/workflow_runner.py explore", "desc": "Re-survey stack and update project context"},
        ])
        return 0

    elif action in ["add", "log"]:
        title = getattr(args, "title", None) or getattr(args, "message", None)
        if not title:
            print("Error: Document title is required. Example: workflow memory add auth-rules --content 'JWT guidelines'", file=sys.stderr)
            return 1

        content = getattr(args, "content", None) or title
        res = add_memory_doc(title=title, content=content, target_dir=target_dir)

        if args.json:
            print(json.dumps(res, indent=2))
            return 0

        print("=" * 110)
        print(f" 📝 MEMORY NOTE RECORDED: '{res['filename']}'")
        print("=" * 110)
        print(f"{'Index':<12} │ {res['index']:02d}")
        print(f"{'Title':<12} │ {res['title']}")
        print(f"{'File Path':<12} │ {res['path']}")
        print("=" * 110)
        print_next_steps([
            {"cmd": f"uv run skills/workflow/scripts/workflow_runner.py memory show {res['index']:02d}", "desc": "View recorded memory note"},
            {"cmd": "uv run skills/workflow/scripts/workflow_runner.py memory list", "desc": "View full memory catalog"},
        ])
        return 0

    elif action in ["show", "view", "read"]:
        identifier = getattr(args, "title", None) or getattr(args, "message", None) or "project_context"
        res = read_memory_doc(identifier, target_dir=target_dir)
        if not res:
            print(f"Error: Memory document '{identifier}' not found.", file=sys.stderr)
            return 1

        if args.json:
            print(json.dumps(res, indent=2))
            return 0

        print("=" * 110)
        print(f" 📄 MEMORY DOCUMENT: {res['filename']}")
        print("=" * 110)
        print(res["content"].strip())
        print("=" * 110)
        return 0

    return 0


def cmd_new(args: argparse.Namespace) -> int:
    """Creates a new spec directory under .workflow/specs/<namespace>/<spec_name>/."""
    res = scaffold_new_spec(args.spec_name, archetype=args.archetype, target_dir=args.target_dir)
    if args.json:
        print(json.dumps(res, indent=2))
        return 0

    spec_clean = res.get("spec_name", args.spec_name)
    ns = res.get("namespace", "features")
    prefix = "feat" if ns == "features" else ("fix" if ns == "bugs" else ("refactor" if ns == "refactor" else ("docs" if ns == "docs" else "feat")))

    print("=" * 110)
    print(f" ✨ SPECIFICATION SCAFFOLDED: '{args.spec_name}'")
    print("=" * 110)
    print(f"{'PROPERTY':<24} │ VALUE")
    print("-" * 110)
    print(f"{'Namespace':<24} │ .workflow/specs/{res.get('namespace')}/")
    print(f"{'Spec Document':<24} │ {res['spec_file']}")
    print(f"{'Issues Directory':<24} │ {os.path.join(os.path.dirname(res['spec_file']), 'issues')} (Clean, ready for /workflow plan)")
    print(f"{'State Checkpoint':<24} │ {res['state_file']}")
    print(f"{'Default Branch':<24} │ {spec_clean}")
    print(f"{'Hierarchical Worktree':<24} │ .workflow/worktrees/{spec_clean}/<worker-name>")
    print("=" * 110)

    print("\nℹ️  AI Agent Interactive Grilling & Branch Selection Directive:")
    print(f"   Ask developer with ask_question to confirm or customize the target git branch:")
    print(f"   Candidates: (Recommended) {spec_clean} | feat/{spec_clean} | fix/{spec_clean} | refactor/{spec_clean} | docs/{spec_clean}")

    print_next_steps([
        {"cmd": f"uv run skills/workflow/scripts/workflow_runner.py specify {args.spec_name}", "desc": "Interactive Grilling Session to co-author spec"},
        {"cmd": f"uv run skills/workflow/scripts/workflow_runner.py plan {args.spec_name}", "desc": "Decompose spec into atomic TDD task issues"},
    ])
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
        return 0

    print("=" * 110)
    print(f" 📝 SPECIFY SESSION: {spec_name} (Current Quality Score: {audit['score']}/100)")
    print("=" * 110)
    print(f"Target Document: {spec_file}\n")
    print("Architectural Co-Authoring Prompts:")
    for idx, q in enumerate(questions, 1):
        print(f"  {idx}. {q}")
    print("=" * 110)

    print_next_steps([
        {"cmd": f"uv run skills/workflow/scripts/workflow_runner.py check {spec_name}", "desc": "Verify 100/100 Quality Gate score"},
        {"cmd": f"uv run skills/workflow/scripts/workflow_runner.py plan {spec_name}", "desc": "Decompose refined spec into task issues"},
    ])
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    """Decomposes a refined spec into atomic TDD task issues."""
    resolved_path = resolve_spec_path(args.spec_name, target_dir=args.target_dir)
    issues_dir = os.path.join(resolved_path, "issues") if os.path.isdir(resolved_path) else os.path.join(os.path.dirname(resolved_path), "issues")
    os.makedirs(issues_dir, exist_ok=True)

    spec_name = os.path.basename(resolved_path.rstrip("/\\"))
    spec_file = os.path.join(resolved_path, "spec.md")

    # If issues folder is empty, decompose spec.md into structured atomic tasks
    existing_issues = sorted([f for f in os.listdir(issues_dir) if f.endswith(".md")])
    if not existing_issues:
        tasks = [
            ("001_domain_models.md", "Domain Models & Schema Setup"),
            ("002_core_logic.md", "Core Implementation & Unit Tests"),
            ("003_integration_verification.md", "Integration Verification & Quality Gate"),
        ]
        for filename, title in tasks:
            task_path = os.path.join(issues_dir, filename)
            content = f"# Issue: {title}\n\nTarget Spec: `{spec_name}`\n\n## Tasks\n- [ ] Implement required data structures.\n- [ ] Run test suite and ensure 100% green build.\n"
            with open(task_path, "w", encoding="utf-8") as f:
                f.write(content)
        existing_issues = sorted([f for f in os.listdir(issues_dir) if f.endswith(".md")])
        reconcile_gitkeep(issues_dir)

        # Update state.json with parsed issues
        state_file = os.path.join(resolved_path, "state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    st = json.load(f)
                st["issues"] = [
                    {"issue_id": f.replace(".md", ""), "title": f.replace(".md", "").replace("_", " ").title(), "status": "PENDING", "tests_written": [], "files_modified": []}
                    for f in existing_issues
                ]
                st["dag_step"] = "ISSUES_PLANNED"
                with open(state_file, "w", encoding="utf-8") as f:
                    json.dump(st, f, indent=2)
            except Exception:
                pass

    data = {
        "status": "SUCCESS",
        "spec_name": spec_name,
        "spec_path": resolved_path,
        "issues_dir": issues_dir,
        "existing_issues": existing_issues,
        "count": len(existing_issues),
    }

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    print("=" * 110)
    print(f" 📋 SPEC TASK PLAN: {data['spec_name']} ({len(existing_issues)} tasks planned)")
    print("=" * 110)
    print(f"{'ISSUE FILE':<36} │ DIRECTORY")
    print("-" * 110)
    for iss in existing_issues:
        print(f"{iss:<36} │ {issues_dir}")
    print("=" * 110)

    print_next_steps([
        {"cmd": f"uv run skills/workflow/scripts/workflow_runner.py check {data['spec_name']}", "desc": "Audit spec against Quality Gate"},
        {"cmd": f"uv run skills/workflow/scripts/workflow_runner.py run {data['spec_name']}", "desc": "Execute LangGraph TDD DAG (Red -> Green -> Refactor)"},
    ])
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Runs the Pre-Execution Quality Gate on a spec."""
    resolved_path = resolve_spec_path(args.spec_dir, target_dir=args.target_dir if hasattr(args, "target_dir") else ".")
    res = audit_spec(resolved_path)
    spec_name = os.path.basename(resolved_path.rstrip("/\\"))

    if args.json:
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1

    status_label = "PASS" if res["passed"] else "NEEDS_REFINEMENT"
    print("=" * 110)
    print(f" 📋 SPEC QUALITY AUDIT: {spec_name} (Score: {res['score']}/100 — {status_label})")
    print("=" * 110)
    print(f"{'QUALITY CRITERION':<28} │ {'STATUS':<10} │ DETAILS")
    print("-" * 110)
    checks = res.get("checks", {})
    print(f"{'Overview & Problem':<28} │ {'PASS' if checks.get('overview') else 'FAIL':<10} │ Business context & user stories defined")
    print(f"{'Architecture & Contracts':<28} │ {'PASS' if checks.get('architecture') else 'FAIL':<10} │ Type signatures & schemas specified")
    print(f"{'Edge Cases & Errors':<28} │ {'PASS' if checks.get('edge_cases') else 'FAIL':<10} │ Boundary conditions & error matrix documented")
    print(f"{'Acceptance Criteria':<28} │ {'PASS' if checks.get('acceptance_criteria') else 'FAIL':<10} │ Testable checkboxes verified")
    print("=" * 110)

    if res["passed"]:
        print_next_steps([
            {"cmd": f"uv run skills/workflow/scripts/workflow_runner.py run {spec_name}", "desc": "Execute deterministic LangGraph TDD runner"},
        ])
    else:
        print_next_steps([
            {"cmd": f"uv run skills/workflow/scripts/workflow_runner.py specify {spec_name}", "desc": "Refine missing criteria & edge cases"},
        ])
    return 0 if res["passed"] else 1


def cmd_run(args: argparse.Namespace) -> int:
    """Executes the deterministic 4-stage sequential subagent pipeline for a spec."""
    target_dir = os.path.abspath(getattr(args, "target_dir", ".") or ".")
    spec_name = getattr(args, "spec_name", None) or getattr(args, "spec", None) or getattr(args, "spec_dir", None)

    if not spec_name:
        print("Error: Specification name is required. Example: workflow run user-login", file=sys.stderr)
        return 1

    schedule_minutes = getattr(args, "schedule", None) or getattr(args, "interval", None)
    auto_merge = getattr(args, "auto_merge", False)
    create_pr = getattr(args, "create_pr", False)

    runner = PipelineRunner(target_dir=target_dir)
    res = runner.run_pipeline(
        spec_name=spec_name,
        schedule_minutes=schedule_minutes,
        auto_merge=auto_merge,
        create_pr=create_pr,
    )

    if getattr(args, "json", False):
        print(json.dumps(res, indent=2))
        return 0

    print("=" * 110)
    print(f" 🚀 PIPELINE COMPLETED: '{res['spec_name']}' ({res['elapsed_seconds']}s)")
    print("=" * 110)
    print(f"{'STAGE':<24} │ {'STATUS':<24} │ SUBAGENT SPECIALIST")
    print("-" * 110)
    for st in res["stages"]:
        print(f"{st['stage']:<24} │ {st['status']:<24} │ {st['subagent_role']}")
    print("=" * 110)
    print(f"{'Staging Branch':<24} │ {res['staging_branch']}")
    print(f"{'Target Base Branch':<24} │ {res['target_base']}")
    print(f"{'Worktree Path':<24} │ {res['worktree_path']}")
    if res.get("adr") and res["adr"].get("adr_file"):
        print(f"{'ADR Record':<24} │ {res['adr']['adr_file']}")
    if res.get("pr_summary") and res["pr_summary"].get("pr_file"):
        print(f"{'PR Summary':<24} │ {res['pr_summary']['pr_file']}")
    print("=" * 110)

    print("\nℹ️  AI Agent Native Subagent Dispatch Directives:")
    for d in res["subagent_directives"]:
        print(f"   - {d['stage']} ({d['role']}): {d['action']}")

    print("\n💡 Suggested PR & Integration Commands:")
    print(f"   👉 GitHub PR: {res.get('suggested_gh_command')}")
    print(f"   👉 Git Merge: {res.get('suggested_git_merge')}")

    if res.get("scheduled_interval"):
        print(f"\n⏰ Opt-In Recurring Daemon Registered: Runs every {res['scheduled_interval']}m (Fixed-Delay)")
        print(f"   To stop: uv run skills/workflow/scripts/workflow_runner.py stop {res['spec_name']}")

    print_next_steps([
        {"cmd": f"uv run skills/workflow/scripts/workflow_runner.py curate {res['spec_name']} --create-pr", "desc": "Open pull request directly on GitHub via gh CLI"},
        {"cmd": "uv run skills/workflow/scripts/workflow_runner.py status", "desc": "Check active pipeline status & worktrees"},
        {"cmd": f"uv run skills/workflow/scripts/workflow_runner.py archive {res['spec_name']}", "desc": "Archive completed specification when merged"},
    ])
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Displays active specifications, pipeline worktrees, and running daemons."""
    setattr(args, "action", "status")
    return cmd_daemon(args)


def cmd_stop(args: argparse.Namespace) -> int:
    """Stops active background pipeline schedulers and cleans processes."""
    setattr(args, "action", "stop")
    return cmd_daemon(args)


def cmd_clean(args: argparse.Namespace) -> int:
    """Performs anti-zombie cleanup of orphaned worktrees, dangling locks, and dead PIDs."""
    setattr(args, "action", "clean")
    return cmd_daemon(args)


def cmd_archive(args: argparse.Namespace) -> int:
    """Archives a completed spec folder into .workflow/specs/archive/<year>/."""
    res = archive_spec(args.spec_name, target_dir=args.target_dir)
    if args.json:
        print(json.dumps(res, indent=2))
        return 0 if res.get("status") == "ARCHIVED" else 1

    print("=" * 110)
    if res.get("status") == "ARCHIVED":
        print(f" 📦 SPEC ARCHIVED CLEANLY: {res.get('spec_name')}")
        print("=" * 110)
        print(f"{'PROPERTY':<24} │ PATH")
        print("-" * 110)
        print(f"{'Source Path':<24} │ {res.get('source_path')}")
        print(f"{'Archive Destination':<24} │ {res.get('archive_path')}")
        print("=" * 110)

        print_next_steps([
            {"cmd": "uv run skills/workflow/scripts/workflow_runner.py curate", "desc": "Compile memory decisions into release PR"},
            {"cmd": "uv run skills/workflow/scripts/workflow_runner.py new <next-spec>", "desc": "Scaffold your next specification"},
        ])
    else:
        print(f"❌ Archive Error: {res.get('message')}")
        print("=" * 110)
    return 0 if res.get("status") == "ARCHIVED" else 1


def cmd_chat(args: argparse.Namespace) -> int:
    """Gathers project context snapshot and launches freeform architectural dialogue."""
    target_dir = os.path.abspath(args.target_dir)
    wf_root = get_workflow_root(target_dir)
    master_file = os.path.join(wf_root, "memory", "00_project_context.md")

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
        return 0

    print("=" * 110)
    print(" 💬 WORKFLOW CHAT & ARCHITECTURAL ADVISOR")
    print("=" * 110)
    if scoped_spec:
        print(f"📌 Scoped Focus: Spec '{scoped_spec['name']}' at {scoped_spec['path']}")
    else:
        print("🌐 Scope: Global Project Architecture & Brainstorming")
    print(f"📦 Active Specifications: {sum(len(v) for v in active_specs.values())} in flight")
    print("=" * 110)

    print_next_steps([
        {"cmd": "uv run skills/workflow/scripts/workflow_runner.py new <name> --archetype feat", "desc": "Turn brainstormed idea into a feature spec"},
        {"cmd": "uv run skills/workflow/scripts/workflow_runner.py specify <name>", "desc": "Refine architectural decisions into spec.md"},
    ])
    return 0


def cmd_curate(args: argparse.Namespace) -> int:
    """Executes the Curator Subagent: generates ADR, manages multi-PR catalog and compiles scoped PR summaries."""
    target_dir = os.path.abspath(args.target_dir if hasattr(args, "target_dir") and args.target_dir else ".")
    spec_name = getattr(args, "spec_name", None) or getattr(args, "spec", None) or getattr(args, "flag_spec", None)
    target_branch = getattr(args, "target_branch", None)
    if not target_branch:
        target_branch = spec_name if spec_name else "main"
    create_pr = getattr(args, "create_pr", False)
    archetype = getattr(args, "archetype", None)

    if getattr(args, "archive", None):
        res = archive_merged_pr(args.archive, target_dir=target_dir)
        if args.json:
            print(json.dumps(res, indent=2))
            return 0
        print("=" * 110)
        print(f" 📦 ARCHIVED PR SUMMARY: {args.archive}")
        print("=" * 110)
        print(f"{'Archive Destination':<24} │ {res.get('destination', res.get('message'))}")
        print("=" * 110)
        print_next_steps([
            {"cmd": "uv run skills/workflow/scripts/workflow_runner.py new <next-spec>", "desc": "Scaffold your next specification"},
        ])
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

    file_slug = res.get("file_slug") or "PR_summary.md"
    head_branch = res.get("head_branch", f"{spec_name}-worker" if spec_name else "curator-worker")
    base_branch = res.get("base_branch", target_branch)
    print("=" * 110)
    print(f" 🚀 WORKFLOW CURATOR SUMMARY (.workflow/prs/active/{file_slug})")
    print("=" * 110)
    print(f"{'PROPERTY':<24} │ VALUE")
    print("-" * 110)
    print(f"{'Integration Branch':<24} │ {head_branch}")
    print(f"{'Target Base Branch':<24} │ {base_branch}")
    print(f"{'PR Document':<24} │ {res.get('pr_file')}")
    print(f"{'Total Integrated':<24} │ {res.get('total_changes', 0)} changes verified")
    integration = res.get("integration", {})
    if integration.get("merged_branches"):
        print(f"{'Merged Worker Branches':<24} │ {', '.join(integration['merged_branches'])}")
    print("=" * 110)

    if res.get("status") == "PR_CREATED":
        print(f"\n✅ Pull Request Opened: {res.get('pr_url')}")
    else:
        print("\n💡 Suggested PR & Integration Commands:")
        print(f"   👉 GitHub PR: {res.get('suggested_gh_command')}")
        print(f"   👉 Git Merge: {res.get('suggested_git_merge')}")

    print_next_steps([
        {"cmd": f"uv run skills/workflow/scripts/workflow_runner.py curate {spec_name or '<spec>'} --create-pr", "desc": "Open pull request directly on GitHub via gh CLI"},
        {"cmd": f"uv run skills/workflow/scripts/workflow_runner.py curate --archive {file_slug}", "desc": "Archive merged PR summary to history"},
    ])
    return 0


def cmd_daemon(args: argparse.Namespace) -> int:
    """Manages background daemon subagents, cron scheduling, and Anti-Zombie lifecycle."""
    action = getattr(args, "action", "status") or "status"
    target_dir = getattr(args, "target_dir", ".") or "."
    name = getattr(args, "spec_name", None) or getattr(args, "name", None)

    # If action doesn't require a daemon name (status, list, clean) and name is a directory path
    if action in ["status", "list", "clean"] and name:
        if os.path.isdir(name) or name.startswith("/") or name.startswith("."):
            target_dir = name
            name = None

    target_dir = os.path.abspath(target_dir)

    if action == "list":
        res = get_daemon_catalog(target_dir=target_dir)
        if args.json:
            print(json.dumps(res, indent=2))
            return 0

        print("=" * 110)
        print(" 🤖 AVAILABLE WORKFLOW DAEMONS (.workflow/workflow.json)")
        print("=" * 110)
        print(f"{'NAME':<18} │ {'ARCHETYPE':<10} │ {'CRON':<12} │ {'MAX ITER':<10} │ {'STATUS':<10} │ {'HOST':<20} │ DESCRIPTION")
        print("-" * 110)
        for d in res.get("daemons", []):
            max_it = str(d.get("max_iterations") or "Unlimited")
            host_str = str(d.get("host") or "-")
            print(f"{d['name']:<18} │ {d['archetype']:<10} │ every {d['default_interval_minutes']}m    │ {max_it:<10} │ {d['status']:<10} │ {host_str:<20} │ {d['description']}")
        print("=" * 110)

        print_next_steps([
            {"cmd": "uv run skills/workflow/scripts/workflow_runner.py daemon create <name>", "desc": "Create a new custom daemon blueprint"},
            {"cmd": "uv run skills/workflow/scripts/workflow_runner.py daemon set <name> --interval <m>", "desc": "Configure daemon schedule or iterations"},
            {"cmd": "uv run skills/workflow/scripts/workflow_runner.py daemon start fix-worker", "desc": "Start background daemon subagent"},
            {"cmd": "uv run skills/workflow/scripts/workflow_runner.py daemon status", "desc": "View active daemon health table"},
        ])
        return 0

    elif action in ["create", "add"]:
        if not getattr(args, "name", None):
            print("Error: Daemon name is required for daemon create. Example: workflow daemon create perf-monitor --archetype refactor", file=sys.stderr)
            return 1

        name = args.name
        archetype = args.archetype or "fix"
        interval = getattr(args, "interval", None) or 10
        max_iter = getattr(args, "max_iterations", None)
        desc = getattr(args, "description", None)
        target_spec = getattr(args, "target_spec_dir", None)

        res = create_daemon_blueprint(
            name=name,
            archetype=archetype,
            interval_minutes=interval,
            max_iterations=max_iter,
            description=desc,
            target_spec_dir=target_spec,
            target_dir=target_dir
        )

        if args.json:
            print(json.dumps(res, indent=2))
            return 0

        print("=" * 110)
        print(f" ✨ DAEMON BLUEPRINT CREATED: '{res['daemon_name']}' (.workflow/workflow.json)")
        print("=" * 110)
        print(f"{'PROPERTY':<24} │ VALUE")
        print("-" * 110)
        print(f"{'Archetype':<24} │ {res['archetype']}")
        print(f"{'Execution Interval':<24} │ every {res['interval_minutes']}m (cron: */{res['interval_minutes']} * * * *)")
        print(f"{'Max Iterations':<24} │ {res['max_iterations'] if res['max_iterations'] else 'Unlimited (Continuous)'}")
        print(f"{'Description':<24} │ {res['description']}")
        print(f"{'Target Spec Dir':<24} │ {res['target_spec_dir']}")
        print(f"{'Isolated Worktree':<24} │ .workflow/worktrees/{res['daemon_name']}")
        print("=" * 110)

        print_next_steps([
            {"cmd": f"uv run skills/workflow/scripts/workflow_runner.py daemon start {res['daemon_name']}", "desc": "Launch this new daemon background worker"},
            {"cmd": "uv run skills/workflow/scripts/workflow_runner.py daemon list", "desc": "Inspect all registered daemon blueprints"},
        ])
        return 0

    elif action in ["set", "edit", "config"]:
        if not getattr(args, "name", None):
            print("Error: Daemon name is required for daemon set. Example: workflow daemon set fix-worker --interval 5 --max-iterations 10", file=sys.stderr)
            return 1

        name = args.name
        interval = getattr(args, "interval", None)
        max_iter = getattr(args, "max_iterations", None)
        archetype = args.archetype
        desc = getattr(args, "description", None)

        res = update_daemon_config(
            name=name,
            interval_minutes=interval,
            max_iterations=max_iter,
            archetype=archetype,
            description=desc,
            target_dir=target_dir
        )

        if res.get("status") == "NOT_FOUND":
            print(f"Error: Daemon '{name}' not found in .workflow/workflow.json. Use 'workflow daemon create {name}' first.", file=sys.stderr)
            return 1

        if args.json:
            print(json.dumps(res, indent=2))
            return 0

        cfg = res.get("config", {})
        sched = cfg.get("schedule", {})
        print("=" * 110)
        print(f" ⚙️  DAEMON CONFIGURATION UPDATED: '{name}' (.workflow/workflow.json)")
        print("=" * 110)
        print(f"{'PROPERTY':<24} │ VALUE")
        print("-" * 110)
        print(f"{'Archetype':<24} │ {cfg.get('archetype')}")
        print(f"{'Execution Interval':<24} │ every {sched.get('interval_minutes', 10)}m")
        print(f"{'Max Iterations':<24} │ {sched.get('max_iterations', 'Unlimited (Continuous)')}")
        print(f"{'Description':<24} │ {cfg.get('description')}")
        print("=" * 110)

        print_next_steps([
            {"cmd": f"uv run skills/workflow/scripts/workflow_runner.py daemon start {name}", "desc": "Launch daemon with updated schedule configuration"},
            {"cmd": "uv run skills/workflow/scripts/workflow_runner.py daemon list", "desc": "Inspect daemon blueprints catalog"},
        ])
        return 0

    elif action == "start":
        name = args.name or "fix-worker"
        interval = getattr(args, "interval", None)
        max_iter = getattr(args, "max_iterations", None)
        spec_target = getattr(args, "spec", None)
        res = start_daemon(daemon_name=name, interval_minutes=interval, max_iterations=max_iter, archetype=args.archetype, spec_name=spec_target, target_dir=target_dir)
        if args.json:
            print(json.dumps(res, indent=2))
            return 0

        actual_interval = res.get("interval_minutes", 10)
        print("=" * 110)
        print(f" 🤖 DAEMON STARTED: '{name}' (Schedule: every {actual_interval}m)")
        print("=" * 110)
        print(f"{'PROPERTY':<24} │ VALUE")
        print("-" * 110)
        print(f"{'Worktree Path':<24} │ {res['worktree_path']}")
        print(f"{'Cron Expression':<24} │ {res['cron_expression']}")
        print(f"{'Subagent Role':<24} │ {res['subagent_directive']['role']}")
        print("=" * 110)

        print("\nℹ️  AI Agent Native Subagent Dispatch Directive:")
        print(f"   Invoke subagent tool (invoke_subagent) with Role='{res['subagent_directive']['role']}'")
        print(f"   Working Directory: {res['worktree_path']}")

        print_next_steps([
            {"cmd": "uv run skills/workflow/scripts/workflow_runner.py daemon status", "desc": "Check active daemon health & metrics"},
            {"cmd": "uv run skills/workflow/scripts/workflow_runner.py new <spec-name>", "desc": "Scaffold a feature spec while worker runs"},
            {"cmd": f"uv run skills/workflow/scripts/workflow_runner.py daemon pause {name}", "desc": "Freeze worker before release curation"},
            {"cmd": f"uv run skills/workflow/scripts/workflow_runner.py daemon stop {name}", "desc": "Stop background worker when finished"},
        ])
        return 0

    elif action == "pause":
        name = args.name or "fix-worker"
        res = pause_daemon(name, target_dir=target_dir)
        if args.json:
            print(json.dumps(res, indent=2))
            return 0

        print("=" * 110)
        print(f" ⏸️  DAEMON PAUSED: '{name}' (Cron cycles suspended without destroying worktree)")
        print("=" * 110)
        print_next_steps([
            {"cmd": "uv run skills/workflow/scripts/workflow_runner.py curate", "desc": "Review and compile memory while workers are paused"},
            {"cmd": f"uv run skills/workflow/scripts/workflow_runner.py daemon resume {name}", "desc": "Resume background worker execution"},
        ])
        return 0

    elif action == "resume":
        name = args.name or "fix-worker"
        res = resume_daemon(name, target_dir=target_dir)
        if args.json:
            print(json.dumps(res, indent=2))
            return 0

        print("=" * 110)
        print(f" ▶️  DAEMON RESUMED: '{name}' (Active cron execution resumed)")
        print("=" * 110)
        print_next_steps([
            {"cmd": "uv run skills/workflow/scripts/workflow_runner.py daemon status", "desc": "Inspect resumed worker status & metrics"},
        ])
        return 0

    elif action == "stop":
        if getattr(args, "all", False) or not name:
            res = stop_all_daemons(target_dir=target_dir)
            if args.json:
                print(json.dumps(res, indent=2))
                return 0

            print("=" * 110)
            print(" 🛑 ALL DAEMONS STOPPED & WORKTREES PURGED (Anti-Zombie Clean)")
            print("=" * 110)
            print("\nℹ️  AI Agent Stop & Cleanup Directive:")
            print("   - Cancel all background schedule cron timers with manage_task(Action='kill')")
            print("   - Terminate all daemon subagents with manage_subagents(Action='kill_all')")
            print_next_steps([
                {"cmd": "uv run skills/workflow/scripts/workflow_runner.py curate", "desc": "Compile completed worker patches into PR summary"},
                {"cmd": "uv run skills/workflow/scripts/workflow_runner.py daemon clean", "desc": "Ensure zero orphaned processes or locks remain"},
            ])
        else:
            res = stop_daemon(name, target_dir=target_dir, force=getattr(args, "force", False))
            if args.json:
                print(json.dumps(res, indent=2))
                return 0

            print("=" * 110)
            print(f" 🛑 DAEMON STOPPED: '{name}' (Worktree, process & scheduled timers purged)")
            print("=" * 110)
            print("\nℹ️  AI Agent Stop & Cleanup Directive:")
            print(f"   - Check running cron tasks with manage_task(Action='list') and cancel matching schedule task with manage_task(Action='kill', TaskId=...)")
            conv_id = res.get("conversation_id")
            if conv_id:
                print(f"   - Terminate subagent conversation with manage_subagents(Action='kill', ConversationIds=['{conv_id}'])")
            print_next_steps([
                {"cmd": "uv run skills/workflow/scripts/workflow_runner.py curate", "desc": "Compile completed worker patches into PR summary"},
                {"cmd": "uv run skills/workflow/scripts/workflow_runner.py daemon status", "desc": "Verify remaining daemon status"},
            ])
        return 0

    elif action == "clean":
        res = clean_orphaned_daemons(target_dir=target_dir)
        if args.json:
            print(json.dumps(res, indent=2))
            return 0

        print("=" * 110)
        print(f" 🧹 ANTI-ZOMBIE CLEAN COMPLETE (Purged: {len(res.get('purged_daemons', []))} items)")
        print("=" * 110)
        print_next_steps([
            {"cmd": "uv run skills/workflow/scripts/workflow_runner.py daemon status", "desc": "Inspect clean daemon table"},
        ])
        return 0

    elif action in ["status"]:
        res = get_daemon_status_table(target_dir=target_dir)
        if args.json:
            print(json.dumps(res, indent=2))
            return 0

        print("=" * 110)
        print(" 🤖 WORKFLOW DAEMONS STATUS (.workflow/daemons.json)")
        print("=" * 110)
        print(f"{'DAEMON':<18} │ {'STATUS':<9} │ {'SCHEDULE':<10} │ {'BRANCH':<22} │ {'HOST':<18} │ WORKTREE")
        print("-" * 110)
        if not res["daemons"]:
            print(f"{'fix-worker':<18} │ {'STOPPED':<9} │ {'every 10m':<10} │ {'fix-worker':<22} │ {'-':<18} │ .workflow/worktrees/general/fix-worker")
            print(f"{'refactor-worker':<18} │ {'STOPPED':<9} │ {'every 15m':<10} │ {'refactor-worker':<22} │ {'-':<18} │ .workflow/worktrees/general/refactor-worker")
            print(f"{'doc-worker':<18} │ {'STOPPED':<9} │ {'every 30m':<10} │ {'doc-worker':<22} │ {'-':<18} │ .workflow/worktrees/general/doc-worker")
        else:
            for d in res["daemons"]:
                status_str = d["status"]
                branch_str = str(d.get("branch_name") or d["name"])
                host_str = str(d.get("host") or "-")
                print(f"{d['name']:<18} │ {status_str:<9} │ every {d['interval_minutes']}m   │ {branch_str:<22} │ {host_str:<18} │ {d['worktree_path']}")
        print("=" * 110)

        print_next_steps([
            {"cmd": "uv run skills/workflow/scripts/workflow_runner.py daemon start fix-worker", "desc": "Launch fix-worker background worker"},
            {"cmd": "uv run skills/workflow/scripts/workflow_runner.py daemon create <name>", "desc": "Create a new custom daemon blueprint"},
            {"cmd": "uv run skills/workflow/scripts/workflow_runner.py daemon pause --all", "desc": "Freeze all workers for release curation"},
        ])
        return 0

    elif action == "run":
        name = args.name or "fix-worker"
        res = run_daemon_cycle(
            daemon_name=name,
            archetype=args.archetype,
            auto_merge=getattr(args, "auto_merge", False),
            root_dir=target_dir
        )
        if args.json:
            print(json.dumps(res, indent=2))
            return 0

        print("=" * 110)
        print(f" 🤖 ONE-SHOT DAEMON EXECUTION [{name}]")
        print("=" * 110)
        print(f"{'PROPERTY':<24} │ VALUE")
        print("-" * 110)
        print(f"{'Status':<24} │ {res.get('status')}")
        print(f"{'Worktree':<24} │ {res.get('worktree_path')}")
        print(f"{'Branch':<24} │ {res.get('branch_name')}")
        print(f"{'DAG Step':<24} │ {res.get('dag_step')}")
        print(f"{'Tests Passing':<24} │ {res.get('all_tests_passing')}")
        print(f"{'Merge Status':<24} │ {res.get('merge_status')}")
        print("=" * 110)

        print_next_steps([
            {"cmd": "uv run skills/workflow/scripts/workflow_runner.py curate", "desc": "Compile results into release PR"},
        ])
        return 0

    return 0


def cmd_worktree(args: argparse.Namespace) -> int:
    """Manages physical git worktree directories under .workflow/worktrees/."""
    name = args.name or getattr(args, "flag_name", None)
    if args.action == "list":
        wt = list_worktrees(args.target_dir)
        res = {"worktrees": wt}
    elif args.action == "add":
        if not name:
            print("Error: worktree name required for worktree add", file=sys.stderr)
            return 1
        res = create_worktree(
            name,
            repo_dir=args.target_dir,
            branch_name=getattr(args, "branch", None),
            archetype=getattr(args, "archetype", None),
            spec_name=getattr(args, "spec", None),
        )
    elif args.action == "clean":
        if not name:
            print("Error: worktree name required for worktree clean", file=sys.stderr)
            return 1
        res = force_purge_worktree(name, repo_dir=args.target_dir)
    elif args.action == "prune":
        ok = prune_worktrees(args.target_dir)
        res = {"status": "PRUNED" if ok else "ERROR"}
    else:
        res = {"status": "ERROR", "message": "Unknown worktree action"}

    if args.json:
        print(json.dumps(res, indent=2))
        return 0

    print("=" * 110)
    print(f" 🌲 WORKTREE OPERATION: {args.action.upper()}")
    print("=" * 110)
    print(f"Result: {json.dumps(res, indent=2)}")
    print("=" * 110)

    if args.action == "add":
        print("\nℹ️  AI Agent Worktree & Spec Isolation Directive:")
        print("   Worktrees in .workflow/worktrees/ are strictly scoped to specifications.")
        print(f"   Created physical worktree '{res.get('worktree_path')}' on branch '{res.get('branch_name')}'.")
        print("   Subagents dispatched to this worktree MUST execute exclusively within this isolated directory.")

    print_next_steps([
        {"cmd": "uv run skills/workflow/scripts/workflow_runner.py daemon status", "desc": "Check active daemon worktrees"},
    ])
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """Displays the concise, fixed command reference table."""
    commands = [
        {"slash": "/workflow init", "syntax": "workflow init [dir]", "desc": "Initialize encapsulated .workflow/ structure & configs"},
        {"slash": "/workflow explore", "syntax": "workflow explore [dir]", "desc": "Survey polyglot stack & extract style preferences (00_coding_preferences.md)"},
        {"slash": "/workflow new", "syntax": "workflow new <name> [--archetype <type>]", "desc": "Scaffold a new spec under .workflow/specs/ (default: feat)"},
        {"slash": "/workflow specify", "syntax": "workflow specify <name>", "desc": "Interactive 1-by-1 Grilling Session to co-author spec.md"},
        {"slash": "/workflow plan", "syntax": "workflow plan <name>", "desc": "Decompose refined spec into atomic TDD task issues"},
        {"slash": "/workflow check", "syntax": "workflow check <name>", "desc": "Audit spec against deterministic Quality Gate (100/100)"},
        {"slash": "/workflow run", "syntax": "workflow run <spec> [--schedule <m>]", "desc": "Primary Engine: Run 4-stage sequential pipeline (Fix -> Refactor -> Doc -> Curator)"},
        {"slash": "/workflow curate", "syntax": "workflow curate [spec] [--create-pr]", "desc": "Generate ADR, compile PR summary & suggest Pull Request"},
        {"slash": "/workflow status", "syntax": "workflow status [spec]", "desc": "View active pipeline status, worktrees & scheduled timers"},
        {"slash": "/workflow stop", "syntax": "workflow stop [spec]", "desc": "Terminate background pipeline subagents and cancel timers"},
        {"slash": "/workflow clean", "syntax": "workflow clean", "desc": "Deep Anti-Zombie cleanup of orphaned worktrees, locks & dead PIDs"},
        {"slash": "/workflow archive", "syntax": "workflow archive <name>", "desc": "Move completed spec to .workflow/specs/archive/<year>/"},
        {"slash": "/workflow drift", "syntax": "workflow drift [--sync]", "desc": "Detect manifest checksum drift & sync tech context"},
        {"slash": "/workflow memory", "syntax": "workflow memory [list|add|show]", "desc": "Manage coding preferences, project context & indexed docs"},
        {"slash": "/workflow chat", "syntax": "workflow chat [spec]", "desc": "Macro architecture brainstorming & scoped spec debate"},
        {"slash": "/workflow check-env", "syntax": "workflow check-env", "desc": "Diagnostic check of Python >=3.10, Git, uv, and dependencies"},
        {"slash": "/workflow list", "syntax": "workflow list", "desc": "Display this concise command reference table"},
    ]

    if args.json:
        print(json.dumps(commands, indent=2))
        return 0

    print("=" * 110)
    print(" ⚡ WORKFLOW COMMANDS REFERENCE (.workflow/)")
    print("=" * 110)
    print(f"{'SLASH COMMAND':<24} │ {'CLI SYNTAX':<36} │ DESCRIPTION")
    print("-" * 110)
    for c in commands:
        print(f"{c['slash']:<24} │ {c['syntax']:<36} │ {c['desc']}")
    print("=" * 110)
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
    p_mem = subparsers.add_parser("memory", help="Manage coding preferences, project context, and indexed memory docs")
    p_mem.add_argument("action", nargs="?", choices=["list", "status", "add", "log", "show", "view"], default="list", help="Memory action (default: list)")
    p_mem.add_argument("title", nargs="?", help="Document title or identifier (e.g. auth-rules, 01, coding_preferences)")
    p_mem.add_argument("--content", help="Content details for the note")
    p_mem.add_argument("--message", dest="message", help="Alternative title flag for logging")
    p_mem.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # new
    p_new = subparsers.add_parser("new", help="Scaffold a new spec folder under .workflow/specs/features/ (default) or bugs/refactor/docs")
    p_new.add_argument("spec_name", help="Name of the new spec")
    p_new.add_argument("--archetype", choices=["feat", "feature", "implement", "fix", "bug", "refactor", "doc", "docs", "doc_sync"], default="feat", help="Target archetype (defaults to feat -> .workflow/specs/features/)")
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
    p_run = subparsers.add_parser("run", help="Run deterministic 4-stage sequential subagent pipeline (Fix -> Refactor -> Doc -> Curator)")
    p_run.add_argument("spec_name", help="Target specification name (e.g. user-login)")
    p_run.add_argument("--schedule", "--interval", dest="schedule", type=int, default=None, help="Opt-in recurring interval in minutes (e.g. 30 or 45)")
    p_run.add_argument("--auto-merge", action="store_true", help="Auto-merge pipeline branch into feature branch if tests pass")
    p_run.add_argument("--create-pr", action="store_true", help="Open GitHub PR directly via gh CLI")
    p_run.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # curate
    p_curate = subparsers.add_parser("curate", help="Curator Subagent: generate ADR and compile scoped PR summaries")
    p_curate.add_argument("spec_name", nargs="?", help="Target specification name (e.g. user-login)")
    p_curate.add_argument("--spec", dest="flag_spec", help="Target specification name (alternative flag)")
    p_curate.add_argument("--archetype", choices=["fix", "refactor", "implement", "doc_sync", "all"], help="Scope PR to specific archetype decisions")
    p_curate.add_argument("--archive", help="Archive a merged PR filename into .workflow/prs/archive/<year>/")
    p_curate.add_argument("--create-pr", action="store_true", help="Open GitHub PR directly via gh CLI")
    p_curate.add_argument("--target-branch", default=None, help="Target merge branch (defaults to spec branch or main)")
    p_curate.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # status
    p_status = subparsers.add_parser("status", help="Display active specifications, pipeline worktrees, and running daemons")
    p_status.add_argument("spec_name", nargs="?", help="Optional specification name to filter")
    p_status.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # stop
    p_stop = subparsers.add_parser("stop", help="Stop background pipeline schedulers and terminate subagents")
    p_stop.add_argument("spec_name", nargs="?", help="Optional specification name to stop (stops all if omitted)")
    p_stop.add_argument("--all", action="store_true", help="Stop all running daemons and timers")
    p_stop.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # clean
    p_clean = subparsers.add_parser("clean", help="Anti-Zombie cleanup of orphaned worktrees, dangling locks, and dead PIDs")
    p_clean.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # archive
    p_arc = subparsers.add_parser("archive", help="Move completed spec folder into .workflow/specs/archive/<year>/")
    p_arc.add_argument("spec_name", help="Name of the spec to archive")
    p_arc.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # chat
    p_chat = subparsers.add_parser("chat", help="Freeform project brainstorming or scoped spec debate session")
    p_chat.add_argument("spec_name", nargs="?", help="Optional spec name to scope debate")
    p_chat.add_argument("--target-dir", default=".", help="Target workspace directory")

    # daemon
    p_daemon = subparsers.add_parser("daemon", help="Manage background daemon subagents, cron scheduling, and Anti-Zombie lifecycle")
    p_daemon.add_argument("action", nargs="?", default="status", choices=["list", "create", "add", "set", "edit", "config", "start", "pause", "resume", "stop", "status", "clean", "run"], help="Daemon action")
    p_daemon.add_argument("name", nargs="?", help="Named daemon (e.g. fix-worker, refactor-worker, doc-worker)")
    p_daemon.add_argument("--interval", type=int, default=None, help="Cron interval in minutes (defaults to workflow.json setting or 10)")
    p_daemon.add_argument("--max-iterations", type=int, default=None, help="Maximum number of iterations before stopping (0/None for unlimited)")
    p_daemon.add_argument("--archetype", choices=["feat", "feature", "implement", "fix", "bug", "refactor", "doc", "docs", "doc_sync"], help="Archetype persona")
    p_daemon.add_argument("--spec", help="Target specification name to bind branch and hierarchical worktree (e.g. user-login)")
    p_daemon.add_argument("--description", help="Human-readable description of daemon responsibilities")
    p_daemon.add_argument("--target-spec-dir", help="Custom directory containing target specs")
    p_daemon.add_argument("--all", action="store_true", help="Apply stop/pause to all running daemons")
    p_daemon.add_argument("--force", action="store_true", help="Force terminate process and wipe worktree")
    p_daemon.add_argument("--auto-merge", action="store_true", help="Enable safe auto-merge into main on completion")
    p_daemon.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # worktree
    p_wt = subparsers.add_parser("worktree", help="Manage physical git worktrees under .workflow/worktrees/")
    p_wt.add_argument("action", choices=["list", "add", "clean", "prune"], help="Worktree action")
    p_wt.add_argument("name", nargs="?", help="Worktree identifier")
    p_wt.add_argument("--name", dest="flag_name", help="Worktree identifier (alternative flag)")
    p_wt.add_argument("--archetype", choices=["feat", "feature", "implement", "fix", "bug", "refactor", "doc", "docs", "doc_sync"], help="Archetype persona for semantic branch prefix")
    p_wt.add_argument("--spec", help="Spec name to bind the worktree and branch to")
    p_wt.add_argument("--branch", help="Explicit branch name for the worktree")
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

    # Automatic Post-Reboot Self-Healing Reconciliation
    try:
        target_dir = getattr(args, "target_dir", ".") or "."
        reconcile_daemon_registry(target_dir)
    except Exception:
        pass

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
        "curate": cmd_curate,
        "status": cmd_status,
        "stop": cmd_stop,
        "clean": cmd_clean,
        "archive": cmd_archive,
        "chat": cmd_chat,
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
