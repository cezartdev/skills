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
from memory_manager import (
    add_memory_doc,
    list_memory_catalog,
    read_memory_doc,
    update_project_business_context,
    read_project_business_context,
)
from worktree_manager import prune_worktrees, run_git
from quality_auditor import audit_spec, audit_plan, audit_tasks, analyze_spec_consistency
from quality import generate_specify_adr
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

    docs_info = scan.get("agent_docs", {}).get("docs", [])
    if docs_info:
        print("\n 📜 DISCOVERED AGENT DIRECTIVES & PROJECT DOCS")
        print("=" * 110)
        print(f"{'DOCUMENT':<24} │ {'CATEGORY':<20} │ {'PATH':<28} │ SUMMARY")
        print("-" * 110)
        for d in docs_info:
            print(f"{d['name']:<24} │ {d['category']:<20} │ {d['path']:<28} │ {d['summary']}")
        print("=" * 110)

    print("\nℹ️  AI Agent Native Subagent Dispatch Directive:")
    print("   - Explorer Specialist: define_subagent(name='workflow-explorer-specialist', description='Codebase, agent rules & polyglot stack discovery specialist', enable_write_tools=True) -> invoke_subagent(Subagents=[{'TypeName': 'workflow-explorer-specialist', 'Role': 'Explorer Specialist', 'Prompt': 'Survey codebase polyglot stack, agent rules (AGENTS.md, CLAUDE.md, CONTEXT.md), test runner, linters and update .workflow/memory/project_context.md and coding_preferences.md.'}])")

    print_next_steps([
        {"cmd": "/workflow memory list", "desc": "Inspect generated coding preferences & project context"},
        {"cmd": "/workflow context", "desc": "Add business domain and application context"},
        {"cmd": "/workflow new <spec-name>", "desc": "Scaffold a new feature specification"},
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

    print("\nℹ️  AI Agent Native Subagent Dispatch Directive:")
    print(f"   - Specify Specialist: define_subagent(name='workflow-specify-specialist', description='Functional requirements and user stories scribe', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-specify-specialist', 'Role': 'Specify Specialist', 'Prompt': 'Author pure functional requirements (what and why) in {spec_file} with user stories and acceptance criteria.'}}])")

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

    print("\nℹ️  AI Agent Native Subagent Dispatch Directive:")
    print(f"   - Clarify Specialist: define_subagent(name='workflow-clarify-specialist', description='Ambiguity checkpoint and Socratic griller', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-clarify-specialist', 'Role': 'Clarify Specialist', 'Prompt': 'Detect ambiguities in {spec_file}, conduct Socratic Q&A using ask_question, and write ADR.'}}])")

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

    plan_file = res["plan_file"]
    print("\nℹ️  AI Agent Native Subagent Dispatch Directive:")
    print(f"   - Plan Specialist: define_subagent(name='workflow-plan-specialist', description='Technical architecture and contract design engineer', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-plan-specialist', 'Role': 'Plan Specialist', 'Prompt': 'Translate spec.md into technical design in {plan_file} with data models, schemas, and interfaces.'}}])")

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

    tasks_file = res["tasks_file"]
    issues_dir = res["issues_dir"]
    print("\nℹ️  AI Agent Native Subagent Dispatch Directive:")
    print(f"   - Tasks Specialist: define_subagent(name='workflow-tasks-specialist', description='Atomic task decomposition and TDD issue specialist', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-tasks-specialist', 'Role': 'Tasks Specialist', 'Prompt': 'Decompose plan.md into ordered atomic tasks in {tasks_file} and populate {issues_dir}.'}}])")

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

    print("\nℹ️  AI Agent Native Subagent Dispatch Directive:")
    print(f"   - Analyze Specialist: define_subagent(name='workflow-analyze-specialist', description='Pre-execution static consistency auditor', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-analyze-specialist', 'Role': 'Analyze Specialist', 'Prompt': 'Statically audit consistency between Memory, spec.md, plan.md, and tasks.md for {spec_name}.'}}])")

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
    only = getattr(args, "only", None)
    from_stage = getattr(args, "from_stage", None) or getattr(args, "from", None)
    dry_run = getattr(args, "dry_run", False)

    runner = PipelineRunner(target_dir=target_dir)
    res = runner.run_pipeline(
        spec_name=spec_name,
        schedule_minutes=schedule_minutes,
        auto_merge=auto_merge,
        create_pr=create_pr,
        push=push,
        only=only,
        from_stage=from_stage,
        dry_run=dry_run,
    )

    if getattr(args, "json", False):
        print(json.dumps(res, indent=2))
        return 0

    if res.get("dry_run"):
        print("=" * 110)
        print(f" 🔍 WORKFLOW RUN DRY-RUN SIMULATION: '{res['spec_name']}'")
        print("=" * 110)
        print(f"{'PROPERTY':<24} │ VALUE")
        print("-" * 110)
        print(f"{'Target Spec':<24} │ {res['spec_file']}")
        print(f"{'Staging Branch':<24} │ {res['staging_branch']}")
        print(f"{'Target Base':<24} │ {res['target_base']}")
        print(f"{'Target Worktree':<24} │ {res['worktree_path']}")
        print(f"{'Formatter':<24} │ {res['preferred_formatter']} ({res['formatter_command']})")
        print(f"{'Stages Selected':<24} │ {', '.join(res['active_stages'])}")
        print("=" * 110)
        print("\nℹ️  Dry-run simulation completed. No files were modified, no worktrees created.")
        print_next_steps([
            {"cmd": f"/workflow run {spec_name}", "desc": "Execute the full pipeline across all stages"},
            {"cmd": f"/workflow run {spec_name} --only security", "desc": "Execute only the Security Audit stage"},
            {"cmd": f"/workflow run {spec_name} --from quality", "desc": "Resume execution from Quality Gatekeeper"},
        ])
        return 0

    print("=" * 110)
    print(f" 🚀 PIPELINE COMPLETED: '{res['spec_name']}' ({res['elapsed_seconds']}s)")
    print("=" * 110)
    print(f"{'STAGE':<24} │ {'STATUS':<24} │ SUBAGENT WORKER")
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
    if res.get("progress_sync") and res["progress_sync"].get("tasks_updated", 0) > 0:
        print(f"{'Progress Sync':<24} │ ⚡ {res['progress_sync']['tasks_updated']} tasks and {res['progress_sync']['criteria_updated']} criteria checkboxes marked [x]")
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
        {"cmd": f"/workflow archive {res['spec_name']}", "desc": "Archive completed specification when merged"},
        {"cmd": "/workflow clean", "desc": "Clean up ephemeral worktrees and reset staging"},
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
        {"cmd": "/workflow clean", "desc": "Perform deep cleanup of worktrees and locks"},
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
        {"cmd": "/workflow new <spec-name>", "desc": "Scaffold a new feature specification"},
        {"cmd": "/workflow list", "desc": "View workflow command reference"},
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
            {"cmd": "/workflow clean", "desc": "Clean ephemeral worktree directories"},
            {"cmd": "/workflow new <next-spec>", "desc": "Scaffold your next specification"},
        ])
    else:
        print(f"❌ Archive Error: {res.get('message')}")
        print("=" * 110)
    return 0 if res.get("status") == "ARCHIVED" else 1


def cmd_context(args: argparse.Namespace) -> int:
    """Adds or displays business domain and application context in .workflow/memory/project_context.md."""
    target_dir = os.path.abspath(getattr(args, "target_dir", ".") or ".")
    context_args = getattr(args, "context_text", None) or getattr(args, "text", None) or getattr(args, "context", None)

    if isinstance(context_args, list):
        context_text = " ".join(context_args).strip()
    elif context_args:
        context_text = str(context_args).strip()
    else:
        context_text = ""

    if context_text:
        append_mode = not getattr(args, "overwrite", False)
        res = update_project_business_context(context_text, target_dir=target_dir, append=append_mode)

        if getattr(args, "json", False):
            print(json.dumps(res, indent=2))
            return 0

        print("=" * 110)
        print(" 🏢 PROJECT BUSINESS & DOMAIN CONTEXT UPDATED")
        print("=" * 110)
        print(f"{'Target Document':<24} │ {res['context_file']}")
        print(f"{'Timestamp':<24} │ {res['timestamp']}")
        print(f"{'Added Context':<24} │ {res['added_context']}")
        print("=" * 110)

        print("\nℹ️  AI Agent Native Subagent Dispatch Directive:")
        print("   - Context Specialist: define_subagent(name='workflow-context-specialist', description='Business domain and application context curator', enable_write_tools=True) -> invoke_subagent(Subagents=[{'TypeName': 'workflow-context-specialist', 'Role': 'Context Specialist', 'Prompt': 'Synthesize business domain knowledge and update .workflow/memory/project_context.md under Business & Application Domain Context.'}])")

        print_next_steps([
            {"cmd": "/workflow explore", "desc": "Survey codebase stack & refresh project context"},
            {"cmd": "/workflow new <spec-name>", "desc": "Scaffold a new feature specification"},
        ])
        return 0
    else:
        res = read_project_business_context(target_dir=target_dir)
        if getattr(args, "json", False):
            print(json.dumps(res, indent=2))
            return 0

        print("=" * 110)
        print(" 🏢 PROJECT BUSINESS & DOMAIN CONTEXT")
        print("=" * 110)
        print(f"{'Target Document':<24} │ {res['context_file']}")
        print(f"{'Status':<24} │ {res['status']}")
        print("-" * 110)
        print(res["business_context"])
        print("=" * 110)

        print("\nℹ️  AI Agent Native Subagent Dispatch Directive:")
        print("   - Context Specialist: define_subagent(name='workflow-context-specialist', description='Business domain and application context curator', enable_write_tools=True) -> invoke_subagent(Subagents=[{'TypeName': 'workflow-context-specialist', 'Role': 'Context Specialist', 'Prompt': 'Synthesize business domain knowledge and update .workflow/memory/project_context.md under Business & Application Domain Context.'}])")

        print_next_steps([
            {"cmd": "/workflow context \"<business context or app description>\"", "desc": "Add domain context to project_context.md"},
            {"cmd": "/workflow explore", "desc": "Survey codebase stack & refresh project context"},
        ])
        return 0


def cmd_list(args: argparse.Namespace) -> int:
    """Displays the concise, fixed command reference table."""
    commands = [
        {"slash": "/workflow init", "syntax": "workflow init [dir]", "desc": "Initialize encapsulated .workflow/ structure & memory"},
        {"slash": "/workflow explore", "syntax": "workflow explore [dir]", "desc": "Survey polyglot stack & extract coding preferences"},
        {"slash": "/workflow context", "syntax": "workflow context [text]", "desc": "Add or view business domain context in project_context.md"},
        {"slash": "/workflow memory", "syntax": "workflow memory [list|add|show]", "desc": "Manage coding preferences, project context & indexed docs"},
        {"slash": "/workflow new", "syntax": "workflow new <name>", "desc": "Scaffold a new spec under .workflow/specs/active/<name>/"},
        {"slash": "/workflow specify", "syntax": "workflow specify <name>", "desc": "Draft functional spec.md focusing strictly on what and why"},
        {"slash": "/workflow clarify", "syntax": "workflow clarify <name> [--generate-adr]", "desc": "Ambiguity Checkpoint: Socratic Q&A to close specification gaps"},
        {"slash": "/workflow plan", "syntax": "workflow plan <name>", "desc": "Convert approved spec.md into technical design (plan.md)"},
        {"slash": "/workflow tasks", "syntax": "workflow tasks <name>", "desc": "Decompose technical plan into atomic tasks (tasks.md & issues/)"},
        {"slash": "/workflow analyze", "syntax": "workflow analyze <name>", "desc": "Auditoría previa: static consistency audit across spec, plan & tasks"},
        {"slash": "/workflow run", "syntax": "workflow run <spec> [--push] [--schedule <m>]", "desc": "Primary Engine: Run 7-stage subagent pipeline (Implement -> Fix -> Refactor -> Security -> Quality -> Doc -> Git)"},
        {"slash": "/workflow stop", "syntax": "workflow stop [spec]", "desc": "Terminate background pipeline subagents and cancel timers"},
        {"slash": "/workflow clean", "syntax": "workflow clean", "desc": "Deep Anti-Zombie cleanup of orphaned worktrees, locks & dead PIDs"},
        {"slash": "/workflow archive", "syntax": "workflow archive <name>", "desc": "Move completed spec to .workflow/specs/archive/<year>/"},
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

    # init
    p_init = subparsers.add_parser("init", help="Initialize encapsulated .workflow/ structure in target repo")
    p_init.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")
    p_init.add_argument("--test-runner", help="Explicit test runner command to record in project_context.md")

    # explore
    p_exp = subparsers.add_parser("explore", help="Scan codebase polyglot stack and generate master context in .workflow/memory/")
    p_exp.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # context
    p_ctx = subparsers.add_parser("context", help="Add or inspect business domain and application context in .workflow/memory/project_context.md")
    p_ctx.add_argument("context_text", nargs="*", help="Business context or application domain description")
    p_ctx.add_argument("--overwrite", action="store_true", help="Overwrite existing business context instead of appending")
    p_ctx.add_argument("--target-dir", default=".", help="Target workspace directory")

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

    # run
    p_run = subparsers.add_parser("run", help="Run deterministic 7-stage subagent pipeline (Implement -> Fix -> Refactor -> Security -> Quality -> Doc -> Git-Worker)")
    p_run.add_argument("spec_name", help="Target specification name (e.g. user-login)")
    p_run.add_argument("--only", choices=["implement", "fix", "refactor", "security", "quality", "doc", "git_worker"], help="Execute only a single specified pipeline stage")
    p_run.add_argument("--from", "--from-stage", dest="from_stage", choices=["implement", "fix", "refactor", "security", "quality", "doc", "git_worker"], help="Resume pipeline execution starting from specified stage")
    p_run.add_argument("--dry-run", action="store_true", help="Simulate pipeline execution blueprint without modifying files or launching subagents")
    p_run.add_argument("--schedule", "--interval", dest="schedule", type=int, default=None, help="Opt-in recurring interval in minutes (e.g. 30 or 45)")
    p_run.add_argument("--auto-merge", action="store_true", help="Auto-merge pipeline branch into feature branch if tests pass")
    p_run.add_argument("--create-pr", action="store_true", help="Open GitHub PR directly via gh CLI")
    p_run.add_argument("--push", action="store_true", default=False, help="Push staging branch to remote origin upon commit (Default: False for security)")
    p_run.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

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
        "init": cmd_init,
        "explore": cmd_explore,
        "context": cmd_context,
        "memory": cmd_memory,
        "new": cmd_new,
        "specify": cmd_specify,
        "clarify": cmd_clarify,
        "plan": cmd_plan,
        "tasks": cmd_tasks,
        "analyze": cmd_analyze,
        "run": cmd_run,
        "stop": cmd_stop,
        "clean": cmd_clean,
        "archive": cmd_archive,
        "list": cmd_list,
    }

    handler = commands.get(args.subcommand)
    if handler:
        return handler(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
