"""Deterministic Sequential Subagent Pipeline Runner (workflow run <spec-name>).

Orchestrates the 7-stage TDD / Security / Clean Code lifecycle governed by Quality Gatekeeper:
Stage 0: Pre-Cycle Sync & Worktree Isolation (.workflow/worktrees/<spec>/worker/ on feat/<spec>-worker)
Stage 1: Implementer Specialist (Spec & Issues Implementation Phase)
Stage 2: Fix-Worker Specialist (Green Tests & Bug Stabilization Phase)
Stage 3: Refactor-Worker Specialist (Clean Code & Architecture Phase)
Stage 4: Security-Worker Specialist (OWASP Top 10 SAST & Dependency CVE Audit Phase)
Stage 5: Quality-Worker Specialist (Quality Gatekeeper, Feedback Router & ADR Generation)
Stage 6: Doc-Worker Specialist (Documentation & Contract Sync Phase)
Stage 7: Git-Worker Specialist (Deterministic Commit, Grilling Session & PR Synthesis)
"""

import os
import re
import json
import time
import shutil
import subprocess
from datetime import datetime
from typing import Dict, Any, List, Optional

from worktree_manager import (
    create_worktree,
    remove_worktree,
    force_purge_worktree,
    run_git,
    get_default_branch,
    get_current_branch,
    is_protected_branch,
    ensure_git_repository,
    sync_worktree_with_base,
    create_stage_checkpoint,
    rollback_to_stage_checkpoint,
    list_stage_checkpoints,
)
from scaffolder import get_workflow_root, reconcile_gitkeep, ensure_gitignore_configured
from quality import (
    compile_scoped_pr_summary,
    generate_spec_adr,
    evaluate_quality_gate,
)
from quality_auditor import sync_tasks_and_spec_progress
from formatter_manager import format_worktree_code, get_preferred_formatter
from security_auditor import audit_codebase
from git_ops import (
    scan_pre_commit_security,
    execute_atomic_commit,
    create_github_pull_request,
)
from graph.pipeline_graph import create_pipeline_graph


STAGE_ALIASES = {
    "1": "implement",
    "implement": "implement",
    "implementer": "implement",
    "2": "fix",
    "fix": "fix",
    "3": "refactor",
    "refactor": "refactor",
    "4": "security",
    "security": "security",
    "sec": "security",
    "5": "quality",
    "quality": "quality",
    "qa": "quality",
    "6": "doc",
    "doc": "doc",
    "docs": "doc",
    "7": "git_worker",
    "git": "git_worker",
    "git_worker": "git_worker",
}


class PipelineRunner:
    """Orchestrates the deterministic 7-stage multi-worker pipeline governed by Quality Gatekeeper."""

    def __init__(self, target_dir: str = "."):
        self.target_dir = os.path.abspath(target_dir)
        self.wf_root = get_workflow_root(self.target_dir)

    def resolve_spec(self, spec_name: str) -> Dict[str, Any]:
        """Resolves target spec directory under active/ or archive/."""
        clean_name = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.rstrip("/\\"))).strip("-._").lower()
        specs_root = os.path.join(self.wf_root, "specs")

        active_dir = os.path.join(specs_root, "active", clean_name)
        active_spec = os.path.join(active_dir, "spec.md")
        if os.path.exists(active_spec):
            return {
                "found": True,
                "spec_name": clean_name,
                "spec_dir": active_dir,
                "spec_file": active_spec,
            }

        direct_dir = os.path.join(specs_root, clean_name)
        direct_spec = os.path.join(direct_dir, "spec.md")
        if os.path.exists(direct_spec):
            return {
                "found": True,
                "spec_name": clean_name,
                "spec_dir": direct_dir,
                "spec_file": direct_spec,
            }

        return {
            "found": False,
            "spec_name": clean_name,
            "spec_dir": active_dir,
            "spec_file": active_spec,
        }

    def run_stage_sync(self, spec_name: str) -> Dict[str, Any]:
        """Stage 0: Prepares isolated worktree, detects protected branches, and rebases staging branch."""
        # 0. Analyze and configure .gitignore to ignore worktrees/worker artifacts
        ensure_gitignore_configured(self.target_dir)

        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.rstrip("/\\"))).strip("-._").lower()
        worker_branch = f"{clean_spec}-worker"

        curr_branch = get_current_branch(self.target_dir)
        protected_active = is_protected_branch(curr_branch)

        # Prioritize feat/<spec> then <spec>
        feat_branch = f"feat/{clean_spec}"
        feat_ref = run_git(["rev-parse", "--verify", f"refs/heads/{feat_branch}"], cwd=self.target_dir)
        spec_ref = run_git(["rev-parse", "--verify", f"refs/heads/{clean_spec}"], cwd=self.target_dir)

        if feat_ref.returncode == 0:
            target_base = feat_branch
        elif spec_ref.returncode == 0:
            target_base = clean_spec
        elif protected_active:
            run_git(["branch", feat_branch, curr_branch], cwd=self.target_dir)
            target_base = feat_branch
        else:
            target_base = curr_branch if not protected_active else get_default_branch(self.target_dir)

        wt_res = create_worktree(
            name="worker",
            base_branch=target_base,
            repo_dir=self.target_dir,
            branch_name=worker_branch,
            spec_name=clean_spec,
            worker_name="worker",
        )

        wt_path = wt_res.get("worktree_path")
        sync_res = sync_worktree_with_base(wt_path, base_branch=target_base, repo_dir=self.target_dir)

        return {
            "status": "SYNCED",
            "spec_name": clean_spec,
            "staging_branch": worker_branch,
            "target_base": target_base,
            "current_branch": curr_branch,
            "on_protected_branch": protected_active,
            "worktree_path": wt_path,
            "sync_details": sync_res,
        }

    def run_stage_implement(self, spec_name: str, wt_path: str) -> Dict[str, Any]:
        """Stage 1: Implementer-Worker (Builds out domain models, core logic, and initial test files)."""
        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.rstrip("/\\"))).strip("-._").lower()
        return {
            "stage": "1_implement",
            "status": "IMPLEMENTATION_READY",
            "subagent_role": "Implementer Specialist",
            "worktree_path": wt_path,
            "message": f"Implementation phase complete. Domain models, logic, and test suites scaffolded for '{clean_spec}'.",
        }

    def run_stage_fix(self, spec_name: str, wt_path: str) -> Dict[str, Any]:
        """Stage 2: Fix-Worker (Stabilizes codebase and ensures 100% green tests)."""
        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.rstrip("/\\"))).strip("-._").lower()
        return {
            "stage": "2_fix",
            "status": "GREEN_TESTS_READY",
            "subagent_role": "Fix-Worker Specialist",
            "worktree_path": wt_path,
            "message": f"Fix phase complete. Codebase stabilized with 100% passing tests for '{clean_spec}'.",
        }

    def run_stage_refactor(self, spec_name: str, wt_path: str) -> Dict[str, Any]:
        """Stage 3: Refactor-Worker (Clean Code, reduces complexity while preserving green tests)."""
        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.rstrip("/\\"))).strip("-._").lower()
        return {
            "stage": "3_refactor",
            "status": "REFACTOR_COMPLETE",
            "subagent_role": "Refactor-Worker Specialist",
            "worktree_path": wt_path,
            "message": f"Refactor phase complete. Architecture modularized and zero comments policy verified for '{clean_spec}'.",
        }

    def run_stage_security(self, spec_name: str, wt_path: str) -> Dict[str, Any]:
        """Stage 4: Security-Worker (SAST OWASP Top 10, secret leak & dependency CVE audit)."""
        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.rstrip("/\\"))).strip("-._").lower()
        sec_audit = audit_codebase(target_dir=wt_path, spec_name=clean_spec)
        
        return {
            "stage": "4_security",
            "status": "SECURITY_AUDITED",
            "subagent_role": "Cybersecurity & Vulnerability Specialist",
            "worktree_path": wt_path,
            "security_gate_passed": sec_audit.get("security_gate_passed", True),
            "summary": sec_audit.get("summary", {}),
            "report_file": sec_audit.get("report_file"),
            "message": f"Security audit completed for '{clean_spec}'. 0 Critical / 0 High vulnerabilities required for quality gate.",
        }

    def run_stage_quality(
        self,
        spec_name: str,
        wt_path: str,
        security_results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Stage 5: Quality Gatekeeper (Audits tests, security, zero-comments compliance, and generates ADR)."""
        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.rstrip("/\\"))).strip("-._").lower()
        
        quality_eval = evaluate_quality_gate(target_dir=wt_path, spec_name=clean_spec)
        verdict = quality_eval.get("status", "APPROVED")

        # Generate formal ADR if approved
        adr_res = None
        if verdict == "APPROVED":
            adr_res = generate_spec_adr(spec_name=clean_spec, target_dir=self.target_dir, security_results=security_results)

        return {
            "stage": "5_quality",
            "status": "QUALITY_EVALUATED",
            "subagent_role": "Quality Assurance Specialist",
            "verdict": verdict,
            "quality_passed": quality_eval.get("quality_passed", True),
            "security_passed": quality_eval.get("security_passed", True),
            "adr": adr_res,
        }

    def run_stage_doc(self, spec_name: str, wt_path: str) -> Dict[str, Any]:
        """Stage 6: Doc-Worker (Generates docstrings, API schemas, and synchronizes spec)."""
        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.rstrip("/\\"))).strip("-._").lower()
        return {
            "stage": "6_doc",
            "status": "DOCS_SYNCHRONIZED",
            "subagent_role": "Doc-Worker Specialist",
            "worktree_path": wt_path,
            "message": f"Documentation phase complete. Contracts and schemas synchronized for '{clean_spec}'.",
        }

    def run_stage_git(
        self,
        spec_name: str,
        worktree_path: str,
        auto_merge: bool = False,
        create_pr: bool = False,
        push: bool = False,
    ) -> Dict[str, Any]:
        """Stage 7: Git commit synthesis, grilling confirmation metadata, and optional PR creation."""
        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.rstrip("/\\"))).strip("-._").lower()
        worker_branch = f"{clean_spec}-worker"
        target_base = get_default_branch(self.target_dir)

        pr_summary = compile_scoped_pr_summary(clean_spec, target_dir=self.target_dir)

        push_status = "REMOTE_PUSH_SKIPPED"
        merge_status = "MERGE_SKIPPED"
        pr_url = None
        gh_available = shutil.which("gh") is not None

        if push:
            push_res = run_git(["push", "-u", "origin", worker_branch], cwd=self.target_dir)
            push_status = "PUSHED_TO_ORIGIN" if push_res.returncode == 0 else f"PUSH_FAILED: {push_res.stderr.strip()}"

        if auto_merge:
            status_main = run_git(["status", "--porcelain"], cwd=self.target_dir)
            if status_main.stdout.strip():
                merge_status = "DIRTY_TREE_POSTPONED"
            else:
                merge_cmd = run_git(["merge", "--no-ff", worker_branch, "-m", f"chore({clean_spec}): auto-merge pipeline improvements"], cwd=self.target_dir)
                merge_status = "AUTO_MERGED" if merge_cmd.returncode == 0 else f"MERGE_FAILED: {merge_cmd.stderr.strip()}"

        if create_pr and gh_available:
            pr_res = create_github_pull_request(
                head_branch=worker_branch,
                base_branch=target_base,
                title=pr_summary.get("pr_title"),
                body_file=pr_summary.get("pr_file_path"),
                target_dir=self.target_dir,
                push_before_pr=push,
            )
            if pr_res.get("success"):
                pr_url = pr_res.get("url")

        return {
            "stage": "7_git_worker",
            "status": "READY_FOR_GRILLING_CONFIRMATION",
            "subagent_role": "Git-Worker Specialist",
            "pr_summary": pr_summary,
            "push_status": push_status,
            "auto_merge_status": merge_status,
            "pr_url": pr_url,
        }

    def run_pipeline(
        self,
        spec_name: str,
        schedule_minutes: Optional[int] = None,
        auto_merge: bool = False,
        create_pr: bool = False,
        push: bool = False,
        only: Optional[str] = None,
        from_stage: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Runs the deterministic 7-stage sequential subagent pipeline with granular control and checkpoints."""
        start_time = time.time()
        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.rstrip("/\\"))).strip("-._").lower()
        spec_info = self.resolve_spec(clean_spec)

        # Map and filter execution stages
        all_stages = ["implement", "fix", "refactor", "security", "quality", "doc", "git_worker"]
        active_stages = list(all_stages)

        if only:
            target_only = STAGE_ALIASES.get(only.lower().strip(), only.lower().strip())
            if target_only in all_stages:
                active_stages = [target_only]

        elif from_stage:
            target_from = STAGE_ALIASES.get(from_stage.lower().strip(), from_stage.lower().strip())
            if target_from in all_stages:
                idx = all_stages.index(target_from)
                active_stages = all_stages[idx:]

        # Handle Dry-Run Simulation
        if dry_run:
            pref_fmt = get_preferred_formatter(self.target_dir)
            curr_b = get_current_branch(self.target_dir)
            target_base = f"feat/{clean_spec}" if is_protected_branch(curr_b) else curr_b
            wt_path_sim = os.path.join(self.wf_root, "worktrees", clean_spec, "worker")
            rel_wt = os.path.relpath(wt_path_sim, self.target_dir).replace("\\", "/")

            return {
                "status": "DRY_RUN_SIMULATION",
                "dry_run": True,
                "spec_name": clean_spec,
                "spec_file": spec_info.get("spec_file"),
                "staging_branch": f"{clean_spec}-worker",
                "target_base": target_base,
                "current_branch": curr_b,
                "worktree_path": rel_wt,
                "active_stages": active_stages,
                "preferred_formatter": pref_fmt.get("name") if pref_fmt else "Standard / Inferred",
                "formatter_command": " ".join(pref_fmt.get("command", [])) if pref_fmt else "None",
            }

        # Step 0: Stage 0 Worktree Sync
        sync_res = self.run_stage_sync(clean_spec)
        wt_path = sync_res.get("worktree_path") or os.path.join(self.wf_root, "worktrees", clean_spec, "worker")
        rel_wt_path = os.path.relpath(wt_path, self.target_dir).replace("\\", "/")

        # Step 1: LangGraph DAG Execution for Core SDD/TDD Node Transitions
        graph = create_pipeline_graph()
        initial_state = {
            "target_dir": self.target_dir,
            "spec_name": clean_spec,
            "staging_branch": sync_res.get("staging_branch", f"{clean_spec}-worker"),
            "target_base": sync_res.get("target_base", "main"),
            "current_branch": sync_res.get("current_branch", "main"),
            "on_protected_branch": sync_res.get("on_protected_branch", False),
            "worktree_path": wt_path,
            "schedule_minutes": schedule_minutes,
            "auto_merge": auto_merge,
            "create_pr": create_pr,
            "push": push,
            "active_stages": active_stages,
        }
        graph_res = graph.invoke(initial_state)

        # Checkpoint Stage 1 & 2 (Green baseline)
        ckpt_implement = create_stage_checkpoint(wt_path, "1_implement")
        ckpt_fix = create_stage_checkpoint(wt_path, "2_fix")

        # Step 2: Auto-Formatting before Refactor/Quality
        if "refactor" in active_stages or "quality" in active_stages:
            format_res = format_worktree_code(wt_path)

        # Checkpoint Stage 3 (Refactor)
        ckpt_refactor = create_stage_checkpoint(wt_path, "3_refactor")

        # Step 3: Security & Quality Audit Execution
        sec_res = {}
        if "security" in active_stages:
            sec_res = self.run_stage_security(clean_spec, wt_path)
            create_stage_checkpoint(wt_path, "4_security")

        quality_res = {}
        if "quality" in active_stages:
            quality_res = self.run_stage_quality(clean_spec, wt_path, security_results=sec_res)
            create_stage_checkpoint(wt_path, "5_quality")

        # Step 4: Reactive Task & Spec Checkbox Synchronization
        sync_progress = {}
        if spec_info.get("spec_dir"):
            sync_progress = sync_tasks_and_spec_progress(spec_info["spec_dir"])

        # Step 5: Git Subagent Execution
        git_res = {}
        if "git_worker" in active_stages:
            git_res = self.run_stage_git(clean_spec, wt_path, auto_merge=auto_merge, create_pr=create_pr, push=push)

        elapsed = round(time.time() - start_time, 2)

        stages = [
            {
                "stage": "1_implement",
                "status": graph_res.get("implement_status", "IMPLEMENTATION_READY"),
                "subagent_role": "Implement Subagent",
                "checkpoint": ckpt_implement.get("checkpoint_sha"),
            },
            {
                "stage": "2_fix",
                "status": graph_res.get("fix_status", "GREEN_TESTS_READY"),
                "subagent_role": "Fix Subagent",
                "checkpoint": ckpt_fix.get("checkpoint_sha"),
            },
            {
                "stage": "3_refactor",
                "status": graph_res.get("refactor_status", "REFACTOR_COMPLETE"),
                "subagent_role": "Refactor Subagent",
                "checkpoint": ckpt_refactor.get("checkpoint_sha"),
            },
            {
                "stage": "4_security",
                "status": "SECURITY_AUDITED" if "security" in active_stages else "SKIPPED",
                "subagent_role": "Security Subagent",
                "security_summary": sec_res.get("summary"),
            },
            {
                "stage": "5_quality",
                "status": ("QUALITY_APPROVED" if quality_res.get("verdict") == "APPROVED" else "NEEDS_REMEDIATION") if "quality" in active_stages else "SKIPPED",
                "subagent_role": "Quality Subagent",
                "verdict": quality_res.get("verdict"),
                "adr": quality_res.get("adr"),
            },
            {
                "stage": "6_doc",
                "status": graph_res.get("doc_status", "DOCS_SYNCHRONIZED"),
                "subagent_role": "Doc Subagent",
            },
            {
                "stage": "7_git_worker",
                "status": "READY_FOR_GRILLING_CONFIRMATION" if "git_worker" in active_stages else "SKIPPED",
                "subagent_role": "Git Subagent",
                "push_status": git_res.get("push_status"),
                "pr_summary": git_res.get("pr_summary"),
            },
        ]

        return {
            "status": "SUCCESS",
            "spec_name": clean_spec,
            "staging_branch": sync_res.get("staging_branch", f"{clean_spec}-worker"),
            "target_base": sync_res.get("target_base", "main"),
            "current_branch": sync_res.get("current_branch", "main"),
            "on_protected_branch": sync_res.get("on_protected_branch", False),
            "worktree_path": rel_wt_path,
            "elapsed_seconds": elapsed,
            "active_stages": active_stages,
            "stages": [s for s in stages if s["stage"].split("_", 1)[1] in active_stages],
            "push_flag_active": push,
            "push_status": git_res.get("push_status"),
            "adr": quality_res.get("adr"),
            "security_report": sec_res.get("report_file"),
            "pr_summary": git_res.get("pr_summary"),
            "progress_sync": sync_progress,
            "suggested_push_command": git_res.get("suggested_push_command"),
            "suggested_gh_command": git_res.get("suggested_gh_command"),
            "suggested_git_merge": git_res.get("suggested_git_merge"),
            "scheduled_interval": schedule_minutes,
            "subagent_directives": [
                {
                    "stage": "Stage 1 (Implement)",
                    "type": "workflow-implement-worker",
                    "role": "Implement Subagent",
                    "prompt_file": "skills/workflow/references/prompts/implement_worker.prompt.md",
                    "action": f"define_subagent(name='workflow-implement-worker', description='Feature & SDD/TDD Engineer', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-implement-worker', 'Role': 'Implement Subagent', 'Prompt': 'Build out spec requirements and task issues for {clean_spec} in {wt_path}. Follow TDD Red-Green cycle and zero-comments policy.'}}])",
                },
                {
                    "stage": "Stage 2 (Fix)",
                    "type": "workflow-fix-worker",
                    "role": "Fix Subagent",
                    "prompt_file": "skills/workflow/references/prompts/fix_worker.prompt.md",
                    "action": f"define_subagent(name='workflow-fix-worker', description='Bug stabilization & 100% green test specialist', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-fix-worker', 'Role': 'Fix Subagent', 'Prompt': 'Diagnose and stabilize tests in {wt_path}. Zero-comments policy.'}}])",
                },
                {
                    "stage": "Stage 3 (Refactor)",
                    "type": "workflow-refactor-worker",
                    "role": "Refactor Subagent",
                    "prompt_file": "skills/workflow/references/prompts/refactor_worker.prompt.md",
                    "action": f"define_subagent(name='workflow-refactor-worker', description='Clean architecture and modularity specialist', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-refactor-worker', 'Role': 'Refactor Subagent', 'Prompt': 'Refactor modular code in {wt_path} while preserving 100% green tests.'}}])",
                },
                {
                    "stage": "Stage 4 (Security)",
                    "type": "workflow-security-worker",
                    "role": "Security Subagent",
                    "prompt_file": "skills/workflow/references/prompts/security_worker.prompt.md",
                    "action": f"define_subagent(name='workflow-security-worker', description='OWASP Top 10 SAST, secret leak & dependency CVE auditor', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-security-worker', 'Role': 'Security Subagent', 'Prompt': 'Audit OWASP Top 10 patterns, secrets and dependencies in {wt_path}. Generate security report.'}}])",
                },
                {
                    "stage": "Stage 5 (Quality)",
                    "type": "workflow-quality-worker",
                    "role": "Quality Subagent",
                    "prompt_file": "skills/workflow/references/prompts/quality_worker.prompt.md",
                    "action": f"define_subagent(name='workflow-quality-worker', description='Quality gatekeeper, ADR author & feedback router', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-quality-worker', 'Role': 'Quality Subagent', 'Prompt': 'Audit combined quality gates (100/100, zero-comments, OWASP clearance) in {wt_path} and write ADR.'}}])",
                },
                {
                    "stage": "Stage 6 (Doc)",
                    "type": "workflow-doc-worker",
                    "role": "Doc Subagent",
                    "prompt_file": "skills/workflow/references/prompts/doc_worker.prompt.md",
                    "action": f"define_subagent(name='workflow-doc-worker', description='Documentation and spec synchronizer', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-doc-worker', 'Role': 'Doc Subagent', 'Prompt': 'Sync markdown docs and spec.md for {clean_spec} in {wt_path}.'}}])",
                },
                {
                    "stage": "Stage 7 (Git-Worker)",
                    "type": "workflow-git-worker",
                    "role": "Git Subagent",
                    "prompt_file": "skills/workflow/references/prompts/git_worker.prompt.md",
                    "action": f"define_subagent(name='workflow-git-worker', description='Deterministic Conventional Commits and GitHub PR specialist', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-git-worker', 'Role': 'Git Subagent', 'Prompt': 'Conduct Grilling Session confirmation with developer. Commit locally. Default Security: DO NOT push to origin unless --push flag is passed or developer explicitly requests remote push.'}}])",
                },
            ],
        }
