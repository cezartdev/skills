#!/usr/bin/env python3
"""Workflow Suite: Deterministic State Machine Runner, SDD/TDD Engine, Cybersecurity Auditor & Quality Gatekeeper."""

import argparse
import json
import os
import sys
import subprocess
import shutil
from typing import Dict, Any, List, Optional, Tuple

from scaffolder import (
    scaffold_init,
    scaffold_new_spec,
    scaffold_spec_plan,
    scaffold_spec_tasks,
    archive_spec,
    get_workflow_root,
    sanitize_identifier,
    reconcile_gitkeep,
    reconcile_all_gitkeeps,
)
from explorer import scan_codebase, generate_master_context
from drift_detector import check_drift, sync_drift
from memory_manager import (
    add_memory_doc,
    list_memory_catalog,
    read_memory_doc,
)
from worktree_manager import list_worktrees, create_worktree, remove_worktree, force_purge_worktree, prune_worktrees, ensure_git_repository
from quality_auditor import audit_spec, audit_plan, audit_tasks, analyze_spec_consistency
from quality import (
    compile_scoped_pr_summary,
    generate_spec_adr,
    generate_specify_adr,
    evaluate_quality_gate,
    create_quality_pr,
    archive_merged_pr,
)
from security_auditor import (
    audit_codebase,
    audit_dependencies,
)
from git_ops import (
    execute_atomic_commit,
    create_github_pull_request,
    scan_pre_commit_security,
)
from pipeline import PipelineRunner


def print_next_steps(suggestions: List[Dict[str, str]]) -> None:
    """Renders actionable subsequent /workflow slash commands in a styled border box."""
    if not suggestions:
        return
    print("\n💡 SUGGESTED NEXT STEPS")
    print("-" * 110)
    for s in suggestions:
        cmd = s.get("cmd", "").strip()
        if "workflow_runner.py" in cmd:
            idx = cmd.find("workflow_runner.py")
            sub_part = cmd[idx + len("workflow_runner.py"):].strip()
            cmd = f"/workflow {sub_part}".strip()
        elif not cmd.startswith("/workflow"):
            if not cmd.startswith("git ") and not cmd.startswith("gh "):
                cmd = f"/workflow {cmd}".strip()
        print(f"  👉 {cmd:<70} │ {s['desc']}")
    print("=" * 110)


def resolve_spec_path(spec_arg: str, target_dir: str = ".") -> str:
    """Smart Path Resolver: resolves spec path from shorthand name or direct path."""
    target_dir = os.path.abspath(target_dir)
    if os.path.exists(spec_arg):
        return os.path.abspath(spec_arg)

    wf_root = get_workflow_root(target_dir)
    specs_root = os.path.join(wf_root, "specs")

    # 1. Active candidate: .workflow/specs/active/<spec_arg>
    active_cand = os.path.join(specs_root, "active", spec_arg)
    if os.path.exists(active_cand):
        return active_cand

    # 2. Direct candidate: .workflow/specs/<spec_arg> (flat fallback)
    direct_cand = os.path.join(specs_root, spec_arg)
    if os.path.exists(direct_cand):
        return direct_cand

    # 3. Fallback for legacy specs in subfolders (features, bugs, refactor, docs)
    for folder in ["features", "bugs", "refactor", "docs"]:
        candidate = os.path.join(specs_root, folder, spec_arg)
        if os.path.exists(candidate):
            return candidate

    return os.path.abspath(active_cand)


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

    gh_ok = False
    gh_ver = "Not installed"
    gh_auth = "Run 'gh auth login'"
    try:
        res = subprocess.run(["gh", "--version"], capture_output=True, text=True, check=False)
        if res.returncode == 0:
            gh_ok = True
            first_line = res.stdout.strip().split("\n")[0]
            gh_ver = first_line.replace("gh version ", "")
            auth_res = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, check=False)
            if auth_res.returncode == 0:
                gh_auth = "Authenticated"
            else:
                gh_auth = "Run 'gh auth login'"
    except Exception:
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
        "github_cli": {
            "version": gh_ver,
            "installed": gh_ok,
            "auth_status": gh_auth,
        },
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
    print(f"{'GitHub CLI (gh)':<20} │ {'[PASS]' if gh_ok else '[INFO]':<10} │ {gh_ver:<30} │ {gh_auth} (PRs & issues)")
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
    print(f"{'Test Runner':<24} │ {res['test_runner']}")
    print(f"{'Specs Directory':<24} │ {res['specs_dir']} (active/ & archive/)")
    print(f"{'Memory Catalog':<24} │ {res['memory_dir']} (workflow_methodology.md, coding_preferences.md, project_context.md, docs/)")
    print(f"{'PRs Catalog':<24} │ {res['prs_dir']} (active, archive)")
    if res.get("gitignore_created"):
        print(f"{'Gitignore Status':<24} │ Created .gitignore (.workflow/worktrees/ ignored)")
    elif res.get("gitignore_updated"):
        print(f"{'Gitignore Status':<24} │ Updated .gitignore (.workflow/worktrees/ ignored)")
    else:
        print(f"{'Gitignore Status':<24} │ Verified (.workflow/worktrees/ ignored)")
    print("=" * 110)

    print("\nℹ️  AI Agent Interactive Question Directive:")
    print("   No explicit test script in manifest. Ask developer with ask_question to choose test runner:")
    print("   Candidates: pytest, cargo test, go test ./..., pnpm test")

    print_next_steps([
        {"cmd": "/workflow explore", "desc": "Survey polyglot stack & update context"},
        {"cmd": "/workflow new <spec-name>", "desc": "Scaffold your first feature specification"},
        {"cmd": "/workflow run <spec-name>", "desc": "Run 7-stage sequential subagent pipeline"},
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
        {"cmd": "/workflow memory list", "desc": "Inspect generated coding preferences & project context"},
        {"cmd": "/workflow new <spec-name>", "desc": "Scaffold a new feature specification"},
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
        {"cmd": "/workflow drift --sync", "desc": "Reconcile drift and update project context"},
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
            {"cmd": "/workflow memory add <title> --content \"...\"", "desc": "Add indexed note to memory/docs/"},
            {"cmd": "/workflow explore", "desc": "Re-survey stack and update project context"},
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
            {"cmd": f"/workflow memory show {res['index']:02d}", "desc": "View recorded memory note"},
            {"cmd": "/workflow memory list", "desc": "View full memory catalog"},
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
    """Creates a new spec directory under .workflow/specs/<spec_name>/."""
    archetype = getattr(args, "archetype", None)
    res = scaffold_new_spec(args.spec_name, archetype=archetype, target_dir=args.target_dir)
    if args.json:
        print(json.dumps(res, indent=2))
        return 0

    spec_clean = res.get("spec_name", args.spec_name)

    print("=" * 110)
    print(f" ✨ SPECIFICATION SCAFFOLDED: '{args.spec_name}'")
    print("=" * 110)
    print(f"{'PROPERTY':<24} │ VALUE")
    print("-" * 110)
    print(f"{'Directory':<24} │ {res['spec_dir']}")
    print(f"{'Spec Document':<24} │ {res['spec_file']}")
    print(f"{'Issues Directory':<24} │ {os.path.join(res['spec_dir'], 'issues')} (Clean, ready for /workflow plan)")
    print(f"{'ADRs Directory':<24} │ {os.path.join(res['spec_dir'], 'adrs')} (Decision audit trail)")
    print(f"{'Default Branch':<24} │ feat/{spec_clean}")
    print(f"{'Hierarchical Worktree':<24} │ .workflow/worktrees/{spec_clean}/worker")
    print("=" * 110)

    print("\nℹ️  AI Agent Interactive Grilling & Branch Selection Directive:")
    print(f"   Ask developer with ask_question to confirm or customize the target git branch:")
    print(f"   Candidates: (Recommended) feat/{spec_clean} | {spec_clean} | fix/{spec_clean} | refactor/{spec_clean}")

    print_next_steps([
        {"cmd": f"/workflow specify {args.spec_name}", "desc": "Draft functional specification (spec.md) focusing on what and why"},
        {"cmd": f"/workflow clarify {args.spec_name}", "desc": "Ambiguity Checkpoint & Socratic Q&A to close gaps"},
        {"cmd": f"/workflow plan {args.spec_name}", "desc": "Convert approved spec into technical design (plan.md)"},
    ])
    return 0


def cmd_specify(args: argparse.Namespace) -> int:
    """Drafts or updates functional specification (spec.md) focusing on what and why."""
    resolved_path = resolve_spec_path(args.spec_name, target_dir=args.target_dir)
    audit = audit_spec(resolved_path)

    spec_file = audit.get("spec_file", resolved_path)
    spec_name = os.path.basename(resolved_path.rstrip("/\\"))

    data = {
        "status": "SPEC_DRAFTED",
        "spec_name": spec_name,
        "spec_path": resolved_path,
        "spec_file": spec_file,
        "current_score": audit["score"],
        "checks": audit["checks"],
        "recommendations": audit.get("recommendations", []),
    }

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    print("=" * 110)
    print(f" 📝 FUNCTIONAL SPECIFICATION: '{spec_name}' (Quality Score: {audit['score']}/100)")
    print("=" * 110)
    print(f"{'Target Spec File':<24} │ {spec_file}")
    print(f"{'Focus':<24} │ User Stories, Functional Scenarios, Edge Cases & Acceptance Criteria")
    print(f"{'Implementation Details':<24} │ Excluded (pure functional requirements; defer to /workflow plan)")
    print("=" * 110)

    if audit.get("recommendations"):
        print("\n💡 Recommendations to complete spec.md:")
        for r in audit["recommendations"]:
            print(f"   - {r}")

    print_next_steps([
        {"cmd": f"/workflow clarify {spec_name}", "desc": "Ambiguity Checkpoint & Socratic Q&A to resolve gaps"},
        {"cmd": f"/workflow plan {spec_name}", "desc": "Convert approved spec into technical design (plan.md)"},
    ])
    return 0


def cmd_clarify(args: argparse.Namespace) -> int:
    """Ambiguity Checkpoint: detects gaps, asks Socratic questions, and records ADR."""
    resolved_path = resolve_spec_path(args.spec_name, target_dir=args.target_dir)
    audit = audit_spec(resolved_path)

    spec_file = audit.get("spec_file", resolved_path)
    spec_name = os.path.basename(resolved_path.rstrip("/\\"))

    adr_res = None
    if getattr(args, "generate_adr", False) or getattr(args, "decisions", None) or audit.get("passed", False):
        adr_res = generate_specify_adr(
            spec_name=spec_name,
            target_dir=args.target_dir,
            decisions_summary=getattr(args, "decisions", None),
            context=getattr(args, "context", None),
        )

    questions = []
    if not audit["checks"].get("edge_cases"):
        questions.append("What boundary conditions, network timeouts, or error states must be handled?")
    if not audit["checks"].get("acceptance_criteria"):
        questions.append("What are the 3 to 5 measurable, testable acceptance criteria to verify completion?")
    if not audit["checks"].get("requirements"):
        questions.append("What are the primary user interaction scenarios and alternative paths?")
    if not questions:
        questions.append("Are there any third-party dependencies, rate limits, or security constraints to clarify?")

    data = {
        "status": "CLARIFICATION_READY",
        "spec_name": spec_name,
        "spec_path": resolved_path,
        "spec_file": spec_file,
        "current_score": audit["score"],
        "clarification_questions": questions,
        "adr": adr_res,
    }

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    print("=" * 110)
    print(f" 🔍 AMBIGUITY CHECKPOINT & CLARIFICATION: '{spec_name}'")
    print("=" * 110)
    print(f"{'Target Spec':<24} │ {spec_file}")
    if adr_res and adr_res.get("adr_file"):
        print(f"{'ADR Record':<24} │ {adr_res['adr_file']} (Status: Accepted)")
    print("=" * 110)

    print("\nℹ️  AI Agent Interactive Clarification Directive:")
    print("   Inspect spec.md and prompt developer using ask_question one question at a time to close gaps:")
    for idx, q in enumerate(questions, 1):
        print(f"   {idx}. {q}")

    print_next_steps([
        {"cmd": f"/workflow plan {spec_name}", "desc": "Generate technical architecture and contracts (plan.md)"},
        {"cmd": f"/workflow analyze {spec_name}", "desc": "Audit consistency across spec, plan and tasks"},
    ])
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    """Converts approved spec into technical design (plan.md)."""
    resolved_path = resolve_spec_path(args.spec_name, target_dir=args.target_dir)
    spec_name = os.path.basename(resolved_path.rstrip("/\\"))

    res = scaffold_spec_plan(spec_name, target_dir=args.target_dir)
    plan_audit = audit_plan(resolved_path)

    data = {
        "status": "SUCCESS",
        "spec_name": spec_name,
        "spec_path": resolved_path,
        "plan_file": res["plan_file"],
        "plan_created": res.get("created", False),
        "plan_score": plan_audit.get("score", 0),
        "checks": plan_audit.get("checks", {}),
    }

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    print("=" * 110)
    print(f" 📐 TECHNICAL DESIGN PLAN: '{spec_name}' (Score: {plan_audit.get('score', 0)}/100)")
    print("=" * 110)
    print(f"{'Plan Document':<24} │ {res['plan_file']}")
    checks = plan_audit.get("checks", {})
    print(f"{'Data Models':<24} │ {'PASS' if checks.get('data_models') else 'NEEDS_SPECIFICATION':<20} (Schemas & validation)")
    print(f"{'Interfaces':<24} │ {'PASS' if checks.get('interfaces') else 'NEEDS_SPECIFICATION':<20} (Signatures & contracts)")
    print(f"{'Dependencies':<24} │ {'PASS' if checks.get('dependencies') else 'NEEDS_SPECIFICATION':<20} (Library selection)")
    print(f"{'Security & Perf':<24} │ {'PASS' if checks.get('security_perf') else 'NEEDS_SPECIFICATION':<20} (OWASP compliance)")
    print("=" * 110)

    print_next_steps([
        {"cmd": f"/workflow tasks {spec_name}", "desc": "Decompose technical plan into atomic tasks (tasks.md & issues/)"},
        {"cmd": f"/workflow analyze {spec_name}", "desc": "Audit static consistency across spec, plan, and tasks"},
    ])
    return 0


def cmd_tasks(args: argparse.Namespace) -> int:
    """Decomposes technical design into atomic tasks (tasks.md and issues/*.md)."""
    resolved_path = resolve_spec_path(args.spec_name, target_dir=args.target_dir)
    spec_name = os.path.basename(resolved_path.rstrip("/\\"))

    res = scaffold_spec_tasks(spec_name, target_dir=args.target_dir)

    data = {
        "status": "SUCCESS",
        "spec_name": spec_name,
        "spec_path": resolved_path,
        "tasks_file": res["tasks_file"],
        "issues_dir": res["issues_dir"],
        "issues_count": res["issues_count"],
        "issue_files": res["issue_files"],
    }

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    print("=" * 110)
    print(f" 📋 ATOMIC TASKS BREAKDOWN: '{spec_name}' ({res['issues_count']} tasks)")
    print("=" * 110)
    print(f"{'Tasks Document':<24} │ {res['tasks_file']}")
    print(f"{'Issues Directory':<24} │ {res['issues_dir']}")
    print("-" * 110)
    print(f"{'ISSUE FILE':<36} │ DIRECTORY")
    print("-" * 110)
    for iss in res["issue_files"]:
        print(f"{iss:<36} │ {res['issues_dir']}")
    print("=" * 110)

    print_next_steps([
        {"cmd": f"/workflow analyze {spec_name}", "desc": "Audit static consistency across spec, plan, and tasks"},
        {"cmd": f"/workflow run {spec_name}", "desc": "Execute 7-stage sequential pipeline"},
    ])
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    """Statically verifies consistency between Constitution, spec.md, plan.md, and tasks."""
    spec_target = getattr(args, "spec_name", None) or getattr(args, "spec_dir", None)
    target_dir = getattr(args, "target_dir", ".") or "."
    resolved_path = resolve_spec_path(spec_target, target_dir=target_dir)
    spec_name = os.path.basename(resolved_path.rstrip("/\\"))

    res = analyze_spec_consistency(resolved_path, target_dir=target_dir)

    if getattr(args, "json", False):
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1

    status_label = "PASS (100% CONSISTENT)" if res["passed"] else "NEEDS_REFINEMENT"
    print("=" * 110)
    print(f" 🔬 STATIC CONSISTENCY AUDIT: '{spec_name}' (Score: {res['score']}/100 — {status_label})")
    print("=" * 110)
    print(f"{'LAYER / ARTIFACT':<28} │ {'STATUS':<10} │ DETAILS")
    print("-" * 110)
    spec_a = res.get("spec_audit", {})
    plan_a = res.get("plan_audit", {})
    tasks_a = res.get("tasks_audit", {})

    print(f"{'Functional Spec (spec.md)':<28} │ {'PASS' if spec_a.get('passed') else 'FAIL':<10} │ Score: {spec_a.get('score', 0)}/100 (User stories & acceptance criteria)")
    print(f"{'Technical Design (plan.md)':<28} │ {'PASS' if plan_a.get('passed') else 'FAIL':<10} │ Score: {plan_a.get('score', 0)}/100 (Architecture, schemas & interfaces)")
    print(f"{'Tasks Breakdown (tasks.md)':<28} │ {'PASS' if tasks_a.get('passed') else 'FAIL':<10} │ {tasks_a.get('issues_count', 0)} atomic task issues")
    print("=" * 110)

    if res.get("contradictions"):
        print("\n⚠️  Gaps & Contradictions Found:")
        for c in res["contradictions"]:
            print(f"   ❌ {c}")

    if res["passed"]:
        print_next_steps([
            {"cmd": f"/workflow run {spec_name}", "desc": "Execute deterministic 7-stage subagent pipeline"},
        ])
    else:
        print_next_steps([
            {"cmd": f"/workflow clarify {spec_name}", "desc": "Resolve specification gaps via Socratic Q&A"},
            {"cmd": f"/workflow plan {spec_name}", "desc": "Refine technical design plan"},
        ])
    return 0 if res["passed"] else 1


def cmd_check(args: argparse.Namespace) -> int:
    """Alias for cmd_analyze (Pre-Execution Quality Gate)."""
    return cmd_analyze(args)


def cmd_run(args: argparse.Namespace) -> int:
    """Executes the deterministic 7-stage sequential subagent pipeline for a spec."""
    target_dir = os.path.abspath(getattr(args, "target_dir", ".") or ".")
    spec_name = getattr(args, "spec_name", None) or getattr(args, "spec", None) or getattr(args, "spec_dir", None)

    if not spec_name:
        print("Error: Specification name is required. Example: workflow run user-login", file=sys.stderr)
        return 1

    schedule_minutes = getattr(args, "schedule", None) or getattr(args, "interval", None)
    auto_merge = getattr(args, "auto_merge", False)
    create_pr = getattr(args, "create_pr", False)
    push = getattr(args, "push", False)

    runner = PipelineRunner(target_dir=target_dir)
    res = runner.run_pipeline(
        spec_name=spec_name,
        schedule_minutes=schedule_minutes,
        auto_merge=auto_merge,
        create_pr=create_pr,
        push=push,
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
    if res.get("push_flag_active"):
        print(f"{'Push Status':<24} │ 🚀 Pushed to origin ({res.get('push_status')})")
    else:
        print(f"{'Push Status':<24} │ 🔒 Local Commit Only (Default Security: pass --push to push to origin)")
    if res.get("adr") and res["adr"].get("adr_file"):
        print(f"{'ADR Record':<24} │ {res['adr']['adr_file']}")
    if res.get("pr_summary") and res["pr_summary"].get("pr_file"):
        print(f"{'PR Summary':<24} │ {res['pr_summary']['pr_file']}")
    print("=" * 110)

    print("\nℹ️  AI Agent Native Subagent Dispatch Directives:")
    print("   🚫 STRICT ZERO-COMMENTS RULE: Write 100% clean, self-documenting code with ZERO comments (no //, #, or \"\"\" \"\"\") unless explicitly requested.")
    for d in res["subagent_directives"]:
        print(f"   - {d['stage']} ({d['role']}): {d['action']}")

    print("\n💡 Suggested PR & Integration Commands:")
    if not res.get("push_flag_active"):
        print(f"   👉 Git Push: {res.get('suggested_push_command')}")
    print(f"   👉 GitHub PR: {res.get('suggested_gh_command')}")
    print(f"   👉 Git Merge: {res.get('suggested_git_merge')}")

    if res.get("on_protected_branch"):
        curr_b = res.get("current_branch", "main")
        print("\n" + "=" * 110)
        print(f" ⚠️  PROTECTED BRANCH GATE ACTIVE: '{curr_b}'")
        print("=" * 110)
        print(f" 🔒 Direct commits and pushes to '{curr_b}' are deterministically blocked.")
        print(f" 🌿 Worktree base automatically routed to feature branch '{res['target_base']}'.")
        print("=" * 110)
        print("\nℹ️  AI Agent Interactive Grilling Directive:")
        print(f"   Current active branch is protected ('{curr_b}'). You MUST prompt developer using ask_question")
        print(f"   to confirm target feature branch before pushing or opening PRs to protect {curr_b}:")
        raw_base = res['target_base']
        for pfx in ["feat/", "fix/", "refactor/"]:
            if raw_base.startswith(pfx):
                raw_base = raw_base[len(pfx):]
        print(f"   Candidates: (Recommended) feat/{raw_base} | {raw_base} | fix/{raw_base}")

    if res.get("scheduled_interval"):
        print(f"\n⏰ Opt-In Recurring Daemon Registered: Runs every {res['scheduled_interval']}m (Fixed-Delay)")
        print(f"   To stop: /workflow stop {res['spec_name']}")

    print_next_steps([
        {"cmd": f"/workflow quality {res['spec_name']} --create-pr", "desc": "Evaluate quality gates and open pull request directly via gh CLI"},
        {"cmd": f"/workflow security {res['spec_name']}", "desc": "Run OWASP Top 10 SAST and vulnerability audit"},
        {"cmd": "/workflow status", "desc": "Check active pipeline status & worktrees"},
        {"cmd": f"/workflow archive {res['spec_name']}", "desc": "Archive completed specification when merged"},
    ])
    return 0


def resolve_spec_and_target_dir(args: argparse.Namespace) -> Tuple[Optional[str], str]:
    """Smart resolver that disambiguates whether a single positional argument is a spec_name or a target directory path."""
    pos1 = getattr(args, "spec_name", None) or getattr(args, "name", None) or getattr(args, "spec_dir", None)
    pos2 = getattr(args, "target_dir", None)
    
    target_dir = "."
    spec_name = None

    if pos2 and pos2 != ".":
        target_dir = pos2
        spec_name = pos1
    elif pos1:
        if os.path.isdir(pos1) or pos1.startswith("/") or pos1.startswith("./") or pos1.startswith("../") or "\\" in pos1 or pos1 == ".":
            target_dir = pos1
            spec_name = None
        else:
            spec_name = pos1
            target_dir = getattr(args, "target_dir", ".") or "."
    else:
        target_dir = getattr(args, "target_dir", ".") or "."

    return spec_name, os.path.abspath(target_dir)


def cmd_status(args: argparse.Namespace) -> int:
    """Displays active specifications and physical worktrees under .workflow/."""
    filter_spec, target_dir = resolve_spec_and_target_dir(args)
    wf_root = get_workflow_root(target_dir)

    # 1. Scan active specifications
    active_specs_dir = os.path.join(wf_root, "specs", "active")
    specs_data = []
    if os.path.exists(active_specs_dir):
        for name in sorted(os.listdir(active_specs_dir)):
            if filter_spec and filter_spec.lower() not in name.lower():
                continue
            spec_path = os.path.join(active_specs_dir, name)
            if os.path.isdir(spec_path):
                issues_dir = os.path.join(spec_path, "issues")
                adrs_dir = os.path.join(spec_path, "adrs")
                
                issues_count = len([f for f in os.listdir(issues_dir) if f.endswith(".md") and f != ".gitkeep"]) if os.path.exists(issues_dir) else 0
                adrs_count = len([f for f in os.listdir(adrs_dir) if f.endswith(".md") and f != ".gitkeep"]) if os.path.exists(adrs_dir) else 0
                
                prs_active_dir = os.path.join(wf_root, "prs", "active")
                has_pr = any(f.startswith(f"PR_spec_{name}_") for f in os.listdir(prs_active_dir)) if os.path.exists(prs_active_dir) else False

                if has_pr:
                    dag_step = "PR_SYNTHESIZED"
                elif adrs_count > 0:
                    dag_step = "ADR_ACCEPTED"
                elif issues_count > 0:
                    dag_step = f"{issues_count} TASKS"
                else:
                    dag_step = "SPEC_DRAFT"

                audit = audit_spec(spec_path)
                specs_data.append({
                    "spec_name": name,
                    "score": audit.get("score", 0),
                    "dag_step": dag_step,
                    "issues_count": issues_count,
                    "adrs_count": adrs_count,
                    "spec_path": spec_path,
                })

    # 2. Scan active worktrees
    worktrees = list_worktrees(target_dir)

    data = {
        "status": "SUCCESS",
        "target_dir": target_dir,
        "active_specs": specs_data,
        "worktrees": worktrees,
    }

    if getattr(args, "json", False):
        print(json.dumps(data, indent=2))
        return 0

    print("=" * 110)
    print(f" 📊 WORKFLOW STATUS: {len(specs_data)} active specs, {len(worktrees)} worktrees")
    print("=" * 110)
    print(" 📦 ACTIVE SPECIFICATIONS (.workflow/specs/active/)")
    print(f"{'SPEC NAME':<24} │ {'SCORE':<8} │ {'DAG STEP':<20} │ {'TASKS':<8} │ ADRS")
    print("-" * 110)
    if not specs_data:
        print(f"{'No active specs':<24} │ {'-':<8} │ {'-':<20} │ {'-':<8} │ -")
    else:
        for s in specs_data:
            print(f"{s['spec_name']:<24} │ {s['score']}/100   │ {s['dag_step']:<20} │ {s['issues_count']:<8} │ {s['adrs_count']}")

    print("\n 🌿 PHYSICAL WORKTREES (.workflow/worktrees/)")
    print(f"{'WORKTREE NAME':<24} │ {'BRANCH':<24} │ STATUS")
    print("-" * 110)
    if not worktrees:
        print(f"{'No active worktrees':<24} │ {'-':<24} │ Clean")
    else:
        for wt in worktrees:
            print(f"{wt.get('name', '-'):<24} │ {wt.get('branch', '-'):<24} │ {wt.get('path', '-')}")
    print("=" * 110)

    print_next_steps([
        {"cmd": "/workflow new <spec-name>", "desc": "Scaffold a new feature specification"},
        {"cmd": "/workflow run <spec-name>", "desc": "Execute 7-stage Quality pipeline"},
    ])
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    """Stops/resets active worktrees for a specification."""
    spec_name, target_dir = resolve_spec_and_target_dir(args)

    success = prune_worktrees(target_dir)
    data = {
        "status": "STOPPED" if success else "ERROR",
        "spec_name": spec_name,
        "target_dir": target_dir,
    }
    if getattr(args, "json", False):
        print(json.dumps(data, indent=2))
        return 0 if success else 1

    print("=" * 110)
    print(f" 🛑 WORKFLOW WORKTREES RESET {'FOR ' + spec_name if spec_name else ''}")
    print("=" * 110)
    print_next_steps([
        {"cmd": "/workflow status", "desc": "Inspect active specs and worktrees"},
    ])
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    """Performs deep cleanup of orphaned worktrees, dangling locks, and temporary files."""
    _, target_dir = resolve_spec_and_target_dir(args)
    wf_root = get_workflow_root(target_dir)

    success = prune_worktrees(target_dir)

    # Clean orphaned worktrees inside .workflow/worktrees/
    wt_dir = os.path.join(wf_root, "worktrees")
    pruned_count = 0
    if os.path.exists(wt_dir):
        for item in os.listdir(wt_dir):
            item_path = os.path.join(wt_dir, item)
            if os.path.isdir(item_path):
                try:
                    run_git(["worktree", "remove", "--force", item_path], cwd=target_dir)
                except Exception:
                    pass
                if os.path.exists(item_path):
                    shutil.rmtree(item_path, ignore_errors=True)
                pruned_count += 1

    reconcile_all_gitkeeps(target_dir)

    data = {
        "status": "CLEANED",
        "worktrees_pruned": pruned_count,
        "target_dir": target_dir,
    }

    if getattr(args, "json", False):
        print(json.dumps(data, indent=2))
        return 0

    print("=" * 110)
    print(" 🧹 WORKFLOW CLEAN COMPLETE")
    print("=" * 110)
    print(f"Worktrees Pruned: {pruned_count}")
    print(f"Directory Tree:   {wf_root}")
    print("=" * 110)

    print_next_steps([
        {"cmd": "/workflow status", "desc": "View clean status"},
    ])
    return 0


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
            {"cmd": "/workflow quality", "desc": "Compile memory decisions into release PR"},
            {"cmd": "/workflow new <next-spec>", "desc": "Scaffold your next specification"},
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
        {"cmd": "/workflow new <name> --archetype feat", "desc": "Turn brainstormed idea into a feature spec"},
        {"cmd": "/workflow specify <name>", "desc": "Refine architectural decisions into spec.md"},
    ])
    return 0


def cmd_security(args: argparse.Namespace) -> int:
    """Runs OWASP Top 10 SAST, secret detection, and dependency vulnerability audit."""
    target_dir = os.path.abspath(getattr(args, "target_dir", ".") or ".")
    spec_name = getattr(args, "spec_name", None) or getattr(args, "spec", None)
    res = audit_codebase(target_dir=target_dir, spec_name=spec_name)

    if getattr(args, "json", False):
        print(json.dumps(res, indent=2))
        return 0 if res["security_gate_passed"] else 1

    print("=" * 110)
    print(f" 🛡️  SECURITY AUDIT REPORT: '{spec_name or 'GLOBAL'}'")
    print("=" * 110)
    print(f"{'CATEGORY':<24} │ VALUE")
    print("-" * 110)
    print(f"{'Security Gate':<24} │ {'✅ PASSED (0 Crit / 0 High)' if res['security_gate_passed'] else '🚨 FAILED (Critical/High Vulns Found)'}")
    print(f"{'Critical Issues':<24} │ {res['summary']['critical']}")
    print(f"{'High Issues':<24} │ {res['summary']['high']}")
    print(f"{'Medium Issues':<24} │ {res['summary']['medium']}")
    print(f"{'Low / Info Issues':<24} │ {res['summary']['low']}")
    print(f"{'Report File':<24} │ {res.get('report_file')}")
    print("=" * 110)

    if res["sast_findings"]:
        print("\n🔍 OWASP Top 10 Findings:")
        for f in res["sast_findings"][:5]:
            print(f"   - [{f['severity']}] {f['owasp']} ({f['file']}:{f['line_number']}): {f['title']}")
        if len(res["sast_findings"]) > 5:
            print(f"   ... and {len(res['sast_findings']) - 5} more issues in {res.get('report_file')}")

    if res["dependency_vulnerabilities"]:
        print("\n📦 Dependency Vulnerabilities:")
        for d in res["dependency_vulnerabilities"][:5]:
            print(f"   - [{d.get('severity')}] {d.get('package')}: {d.get('title')}")

    return 0 if res["security_gate_passed"] else 1


def cmd_audit_deps(args: argparse.Namespace) -> int:
    """Audits project package manifests for known CVEs."""
    target_dir = os.path.abspath(getattr(args, "target_dir", ".") or ".")
    res = audit_dependencies(target_dir=target_dir)

    if getattr(args, "json", False):
        print(json.dumps(res, indent=2))
        return 0 if res["passed"] else 1

    print("=" * 90)
    print(" 📦 DEPENDENCY CVE AUDIT REPORT")
    print("=" * 90)
    print(f"Ecosystems Scanned: {', '.join(res['scanned_ecosystems']) or 'None detected'}")
    print(f"Vulnerabilities Found: {len(res['vulnerabilities'])}")
    print(f"Security Gate: {'PASSED' if res['passed'] else 'FAILED'}")
    print("=" * 90)
    return 0 if res["passed"] else 1


def cmd_quality(args: argparse.Namespace) -> int:
    """Executes the Quality Gatekeeper: evaluates quality score, generates ADR, and compiles release PR."""
    target_dir = os.path.abspath(getattr(args, "target_dir", ".") or ".")
    spec_name = getattr(args, "spec_name", None) or getattr(args, "spec", None) or getattr(args, "flag_spec", None)
    target_branch = getattr(args, "target_branch", None)
    if not target_branch:
        target_branch = f"feat/{spec_name}" if spec_name else "main"
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
        return 0

    res = create_quality_pr(
        target_dir=target_dir,
        archetype=archetype,
        spec_name=spec_name,
        target_branch=target_branch,
        create_pr=create_pr,
    )

    if args.json:
        print(json.dumps(res, indent=2))
        return 0

    file_slug = res.get("file_slug") or "PR_summary.md"
    head_branch = res.get("head_branch", f"{spec_name}-worker" if spec_name else "worker")
    base_branch = res.get("base_branch", target_branch)
    print("=" * 110)
    print(f" 🚀 WORKFLOW QUALITY SUMMARY ({res.get('pr_file')})")
    print("=" * 110)
    print(f"{'PROPERTY':<24} │ VALUE")
    print("-" * 110)
    print(f"{'Integration Branch':<24} │ {head_branch}")
    print(f"{'Target Base Branch':<24} │ {base_branch}")
    print(f"{'PR Document':<24} │ {res.get('pr_file')}")
    print(f"{'Total Integrated':<24} │ {res.get('total_changes', 0)} changes verified")
    if res.get("adr") and res["adr"].get("adr_path"):
        print(f"{'ADR Generated':<24} │ {res['adr']['adr_path']}")
    if res.get("pr_url"):
        print(f"{'GitHub PR URL':<24} │ {res['pr_url']}")
    print("=" * 110)

    if res.get("status") == "PR_CREATED":
        print(f"\n✅ Pull Request Opened: {res.get('pr_url')}")
    else:
        print("\n💡 Suggested PR & Integration Commands:")
        print(f"   👉 GitHub PR: {res.get('suggested_gh_command')}")
        print(f"   👉 Git Merge: {res.get('suggested_git_merge')}")

    print_next_steps([
        {"cmd": f"/workflow quality {spec_name or '<spec>'} --create-pr", "desc": "Open pull request directly on GitHub via gh CLI"},
        {"cmd": f"/workflow quality --archive {file_slug}", "desc": "Archive merged PR summary to history"},
    ])
    return 0


def cmd_commit(args: argparse.Namespace) -> int:
    """Deterministic atomic commit for Git-Worker with pre-commit security gates."""
    target_dir = os.path.abspath(getattr(args, "target_dir", ".") or ".")
    commit_type = getattr(args, "type", "feat") or "feat"
    scope = getattr(args, "scope", None) or getattr(args, "spec", None)
    message = getattr(args, "message", None)
    if not message:
        print("Error: -m/--message is required for commit.", file=sys.stderr)
        return 1
    
    body_bullets = getattr(args, "bullets", None)
    if body_bullets and isinstance(body_bullets, str):
        body_bullets = [b.strip() for b in body_bullets.split("\n") if b.strip()]

    res = execute_atomic_commit(
        commit_type=commit_type,
        scope=scope,
        message=message,
        body_bullets=body_bullets,
        target_dir=target_dir,
    )

    if getattr(args, "json", False):
        print(json.dumps(res, indent=2))
        return 0 if res.get("status") == "SUCCESS" else 1

    if res.get("status") == "SUCCESS":
        print("=" * 110)
        print(" ✅ ATOMIC COMMIT CREATED BY GIT-WORKER")
        print("=" * 110)
        print(f"Commit SHA:    {res.get('commit_sha')}")
        print(f"Commit Header: {res.get('commit_header')}")
        print(f"Working Dir:   {res.get('target_dir')}")
        print("=" * 110)
        return 0
    else:
        print("=" * 110)
        print(f" ❌ COMMIT FAILED: {res.get('status')}")
        print("=" * 110)
        print(f"Message: {res.get('message')}")
        if res.get("violations"):
            for v in res.get("violations"):
                print(f"  - [{v.get('type')}] {v.get('detail')}")
        if res.get("errors"):
            for e in res.get("errors"):
                print(f"  - {e}")
        print("=" * 110)
        return 1


def cmd_pr(args: argparse.Namespace) -> int:
    """Deterministic GitHub Pull Request creation for Git-Worker."""
    target_dir = os.path.abspath(getattr(args, "target_dir", ".") or ".")
    spec_name = getattr(args, "spec", None) or getattr(args, "spec_name", None)
    head_branch = getattr(args, "head", None) or (f"{spec_name}-worker" if spec_name else None)
    base_branch = getattr(args, "base", None) or spec_name or "main"
    title = getattr(args, "title", None) or (f"feat({spec_name}): integrate automated pipeline improvements" if spec_name else "chore: automated pipeline release")
    body_file = getattr(args, "body_file", None)

    if not head_branch:
        print("Error: --head or --spec is required to create a Pull Request.", file=sys.stderr)
        return 1

    res = create_github_pull_request(
        head_branch=head_branch,
        base_branch=base_branch,
        title=title,
        body_file=body_file,
        target_dir=target_dir,
        push_before_pr=getattr(args, "push", False),
    )

    if getattr(args, "json", False):
        print(json.dumps(res, indent=2))
        return 0 if res.get("status") == "SUCCESS" else 1

    if res.get("status") == "SUCCESS":
        print("=" * 110)
        print(" 🚀 PULL REQUEST OPENED BY GIT-WORKER")
        print("=" * 110)
        print(f"PR URL:      {res.get('pr_url')}")
        print(f"Head Branch: {res.get('head_branch')}")
        print(f"Base Branch: {res.get('base_branch')}")
        print(f"Title:       {res.get('title')}")
        print("=" * 110)
        return 0
    else:
        print("=" * 110)
        print(f" ❌ PR CREATION FAILED: {res.get('status')}")
        print("=" * 110)
        print(f"Message: {res.get('message')}")
        print("=" * 110)
        return 1


def cmd_list(args: argparse.Namespace) -> int:
    """Displays the concise, fixed command reference table."""
    commands = [
        {"slash": "/workflow init", "syntax": "workflow init [dir]", "desc": "Initialize encapsulated .workflow/ structure & memory"},
        {"slash": "/workflow explore", "syntax": "workflow explore [dir]", "desc": "Survey polyglot stack & extract coding preferences"},
        {"slash": "/workflow new", "syntax": "workflow new <name>", "desc": "Scaffold a new spec under .workflow/specs/active/<name>/"},
        {"slash": "/workflow specify", "syntax": "workflow specify <name>", "desc": "Draft functional spec.md focusing strictly on what and why"},
        {"slash": "/workflow clarify", "syntax": "workflow clarify <name> [--generate-adr]", "desc": "Ambiguity Checkpoint: Socratic Q&A to close specification gaps"},
        {"slash": "/workflow plan", "syntax": "workflow plan <name>", "desc": "Convert approved spec.md into technical design (plan.md)"},
        {"slash": "/workflow tasks", "syntax": "workflow tasks <name>", "desc": "Decompose technical plan into atomic tasks (tasks.md & issues/)"},
        {"slash": "/workflow analyze", "syntax": "workflow analyze <name>", "desc": "Auditoría previa: static consistency audit across spec, plan & tasks"},
        {"slash": "/workflow check", "syntax": "workflow check <name>", "desc": "Alias for /workflow analyze (Quality Gate 100/100)"},
        {"slash": "/workflow security", "syntax": "workflow security [spec] [--json]", "desc": "Run OWASP Top 10 SAST, secret leak & dependency CVE audit"},
        {"slash": "/workflow audit-deps", "syntax": "workflow audit-deps [dir]", "desc": "Audit project package manifests for known CVEs"},
        {"slash": "/workflow quality", "syntax": "workflow quality [spec] [--create-pr]", "desc": "Quality Gatekeeper: audit quality score & OWASP report, generate ADR"},
        {"slash": "/workflow run", "syntax": "workflow run <spec> [--push] [--schedule <m>]", "desc": "Primary Engine: Run 7-stage subagent pipeline (Implement -> Fix -> Refactor -> Security -> Quality -> Doc -> Git)"},
        {"slash": "/workflow commit", "syntax": "workflow commit -t <t> -s <s> -m <m>", "desc": "Git-Worker deterministic Conventional Commit with pre-commit security gates"},
        {"slash": "/workflow pr", "syntax": "workflow pr --spec <spec> [--push]", "desc": "Git-Worker deterministic GitHub PR creation via gh CLI (Default: no push; add --push)"},
        {"slash": "/workflow status", "syntax": "workflow status [spec]", "desc": "View active pipeline status, worktrees & security audits"},
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
        description="Deterministic State Machine Runner, SDD/TDD Engine, Cybersecurity Auditor & Quality Gatekeeper",
    )
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # check-env
    subparsers.add_parser("check-env", help="Verify runtime environment, Python >=3.10, Git, and dependencies")

    # init
    p_init = subparsers.add_parser("init", help="Initialize encapsulated .workflow/ structure in target repo")
    p_init.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")
    p_init.add_argument("--test-runner", help="Explicit test runner command to record in project_context.md")

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
    p_new = subparsers.add_parser("new", help="Scaffold a new feature specification directory under .workflow/specs/active/<spec-name>/")
    p_new.add_argument("spec_name", help="Name of the new specification")
    p_new.add_argument("--archetype", nargs="?", help="Optional legacy archetype alias (defaults to standard feature spec)")
    p_new.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # specify
    p_spec = subparsers.add_parser("specify", help="Draft or update functional specification (spec.md) focusing on what and why")
    p_spec.add_argument("spec_name", help="Name or path of the spec to refine")
    p_spec.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # clarify
    p_clarify = subparsers.add_parser("clarify", help="Ambiguity Checkpoint: Socratic Q&A to close specification gaps and record ADR")
    p_clarify.add_argument("spec_name", help="Name or path of the spec to clarify")
    p_clarify.add_argument("--generate-adr", action="store_true", help="Explicitly generate or refresh ADR in .workflow/specs/active/<spec>/adrs/")
    p_clarify.add_argument("--decisions", help="Summary of architectural decisions agreed upon during grilling")
    p_clarify.add_argument("--context", help="Context or problem statement for the ADR")
    p_clarify.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # plan
    p_plan = subparsers.add_parser("plan", help="Convert approved spec.md into technical design (plan.md)")
    p_plan.add_argument("spec_name", help="Name or path of the spec to plan")
    p_plan.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # tasks
    p_tasks = subparsers.add_parser("tasks", help="Decompose technical plan.md into atomic tasks (tasks.md and issues/*.md)")
    p_tasks.add_argument("spec_name", help="Name or path of the spec")
    p_tasks.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # analyze
    p_ana = subparsers.add_parser("analyze", help="Auditoría previa: static consistency audit across Constitution, spec.md, plan.md, and tasks.md")
    p_ana.add_argument("spec_name", help="Path or shorthand name of the spec")
    p_ana.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # check (alias to analyze)
    p_chk = subparsers.add_parser("check", help="Alias for /workflow analyze (Pre-Execution Quality Gate)")
    p_chk.add_argument("spec_dir", help="Path or shorthand name of the spec")
    p_chk.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # security
    p_sec = subparsers.add_parser("security", help="Run OWASP Top 10 SAST, secret leak, and dependency vulnerability audit")
    p_sec.add_argument("spec_name", nargs="?", default=None, help="Target specification name")
    p_sec.add_argument("--target-dir", default=".", help="Target workspace directory")

    # audit-deps
    p_deps = subparsers.add_parser("audit-deps", help="Audit project package manifests for known CVEs")
    p_deps.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # quality
    p_qual = subparsers.add_parser("quality", help="Quality Gatekeeper: audit quality score, generate ADR, and compile release PR")
    p_qual.add_argument("spec_name", nargs="?", help="Target specification name (e.g. user-login)")
    p_qual.add_argument("--spec", dest="flag_spec", help="Target specification name (alternative flag)")
    p_qual.add_argument("--archetype", choices=["fix", "refactor", "security", "implement", "doc_sync", "all"], help="Scope PR to specific archetype decisions")
    p_qual.add_argument("--archive", help="Archive a merged PR filename into .workflow/prs/archive/<year>/")
    p_qual.add_argument("--create-pr", action="store_true", help="Open GitHub PR directly via gh CLI")
    p_qual.add_argument("--target-branch", default=None, help="Target merge branch (defaults to spec branch or main)")
    p_qual.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # run
    p_run = subparsers.add_parser("run", help="Run deterministic 7-stage subagent pipeline (Implement -> Fix -> Refactor -> Security -> Quality -> Doc -> Git-Worker)")
    p_run.add_argument("spec_name", help="Target specification name (e.g. user-login)")
    p_run.add_argument("--schedule", "--interval", dest="schedule", type=int, default=None, help="Opt-in recurring interval in minutes (e.g. 30 or 45)")
    p_run.add_argument("--auto-merge", action="store_true", help="Auto-merge pipeline branch into feature branch if tests pass")
    p_run.add_argument("--create-pr", action="store_true", help="Open GitHub PR directly via gh CLI")
    p_run.add_argument("--push", action="store_true", default=False, help="Push staging branch to remote origin upon commit (Default: False for security)")
    p_run.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # commit (for git-worker)
    p_cmt = subparsers.add_parser("commit", help="Git-Worker deterministic Conventional Commit with pre-commit security gates")
    p_cmt.add_argument("-t", "--type", default="feat", help="Commit type (feat, fix, docs, refactor, chore, etc.)")
    p_cmt.add_argument("-s", "--scope", "--spec", dest="scope", help="Commit scope / spec name")
    p_cmt.add_argument("-m", "--message", required=True, help="Imperative commit description")
    p_cmt.add_argument("-b", "--bullets", help="Newline-separated bullet summary of changes")
    p_cmt.add_argument("--target-dir", default=".", help="Target working directory or worktree")

    # pr (for git-worker)
    p_pr = subparsers.add_parser("pr", help="Git-Worker deterministic GitHub PR creation via gh CLI")
    p_pr.add_argument("--spec", "--spec-name", dest="spec", help="Target specification name")
    p_pr.add_argument("--head", help="Head branch name (defaults to <spec>-worker)")
    p_pr.add_argument("--base", help="Base branch name (defaults to spec branch or main)")
    p_pr.add_argument("--title", help="PR title")
    p_pr.add_argument("--body-file", help="Path to markdown PR body file")
    p_pr.add_argument("--target-dir", default=".", help="Target repository directory")
    p_pr.add_argument("--push", action="store_true", default=False, help="Push branch to remote origin before creating PR (Default: False for security)")

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
        "clarify": cmd_clarify,
        "plan": cmd_plan,
        "tasks": cmd_tasks,
        "analyze": cmd_analyze,
        "check": cmd_check,
        "security": cmd_security,
        "audit-deps": cmd_audit_deps,
        "quality": cmd_quality,
        "run": cmd_run,
        "commit": cmd_commit,
        "pr": cmd_pr,
        "status": cmd_status,
        "stop": cmd_stop,
        "clean": cmd_clean,
        "archive": cmd_archive,
        "chat": cmd_chat,
        "list": cmd_list,
    }

    handler = commands.get(args.subcommand)
    if handler:
        return handler(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
