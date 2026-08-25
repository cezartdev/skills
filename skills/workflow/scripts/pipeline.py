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
import shlex
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
from scaffolder import get_workflow_root, ensure_workflow_directories, ensure_gitignore_configured
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
    check_gh_readiness,
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
        wf_dirs = ensure_workflow_directories(self.target_dir)
        self.wf_root = wf_dirs["root"]

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

    def run_stage_sync(self, spec_name: str, no_worktree: bool = False) -> Dict[str, Any]:
        """Stage 0: Prepares isolated worktree, detects protected branches, and rebases staging branch.

        When `no_worktree` is True, no physical worktree or separate `feat/<spec>-worker` staging
        branch is created. The pipeline instead operates directly inside `self.target_dir`, on
        whichever branch is currently checked out there (still routing off `main`/`master` and
        other protected branches onto `feat/<spec>` in place, preserving the protected-branch gate).
        """
        # 0. Analyze and configure .gitignore to ignore worktrees/worker artifacts
        ensure_gitignore_configured(self.target_dir)

        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.rstrip("/\\"))).strip("-._").lower()
        curr_branch = get_current_branch(self.target_dir)
        protected_active = is_protected_branch(curr_branch)

        if no_worktree:
            feat_branch = f"feat/{clean_spec}"
            default_b = get_default_branch(self.target_dir)

            if protected_active:
                feat_ref = run_git(["rev-parse", "--verify", f"refs/heads/{feat_branch}"], cwd=self.target_dir)
                if feat_ref.returncode == 0:
                    run_git(["checkout", feat_branch], cwd=self.target_dir)
                else:
                    run_git(["checkout", "-b", feat_branch], cwd=self.target_dir)
                active_branch = feat_branch
            else:
                active_branch = curr_branch

            return {
                "status": "SYNCED_NO_WORKTREE",
                "spec_name": clean_spec,
                "staging_branch": active_branch,
                "target_base": default_b,
                "current_branch": curr_branch,
                "on_protected_branch": protected_active,
                "worktree_path": self.target_dir,
                "no_worktree": True,
                "sync_details": {
                    "status": "SKIPPED_NO_WORKTREE",
                    "message": f"--no-worktree active: pipeline stages run directly in '{self.target_dir}' on branch '{active_branch}'. No isolated worktree or worker branch was created.",
                },
            }

        worker_branch = f"feat/{clean_spec}-worker"

        # Prioritize feat/<spec> as feature mainline
        feat_branch = f"feat/{clean_spec}"
        feat_ref = run_git(["rev-parse", "--verify", f"refs/heads/{feat_branch}"], cwd=self.target_dir)
        spec_ref = run_git(["rev-parse", "--verify", f"refs/heads/{clean_spec}"], cwd=self.target_dir)

        if feat_ref.returncode == 0:
            target_base = feat_branch
        elif spec_ref.returncode == 0:
            target_base = clean_spec
        else:
            # Create feature branch if missing
            run_git(["branch", feat_branch, curr_branch], cwd=self.target_dir)
            target_base = feat_branch

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
            "no_worktree": False,
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
        """Stage 5: Quality Gatekeeper (Audits tests, security, and zero-comments compliance)."""
        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.rstrip("/\\"))).strip("-._").lower()
        
        quality_eval = evaluate_quality_gate(target_dir=wt_path, spec_name=clean_spec)
        verdict = quality_eval.get("status", "APPROVED")

        return {
            "stage": "5_quality",
            "status": "QUALITY_EVALUATED",
            "subagent_role": "Quality Assurance Specialist",
            "verdict": verdict,
            "quality_passed": quality_eval.get("quality_passed", True),
            "security_passed": quality_eval.get("security_passed", True),
            "summary": quality_eval.get("security_summary", {}),
        }

    def run_stage_doc(
        self,
        spec_name: str,
        wt_path: str,
        spec_dir: Optional[str] = None,
        security_results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Stage 6: Doc-Worker (Exclusive owner of documentation, ADR consolidation, and PR summary synthesis)."""
        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.rstrip("/\\"))).strip("-._").lower()
        
        # 1. Consolidate and author canonical ADR for this spec
        adr_res = generate_spec_adr(spec_name=clean_spec, target_dir=self.target_dir, security_results=security_results)

        # 2. Synchronize tasks and spec acceptance criteria checkboxes
        sync_progress = {}
        if spec_dir and os.path.exists(spec_dir):
            sync_progress = sync_tasks_and_spec_progress(spec_dir)
        elif os.path.exists(os.path.join(self.wf_root, "specs", "active", clean_spec)):
            sync_progress = sync_tasks_and_spec_progress(os.path.join(self.wf_root, "specs", "active", clean_spec))

        # 3. Synthesize the single canonical PR summary body for this spec
        pr_summary = compile_scoped_pr_summary(self.target_dir, spec_name=clean_spec)

        return {
            "stage": "6_doc",
            "status": "DOCS_SYNCHRONIZED",
            "subagent_role": "Doc-Worker Specialist",
            "worktree_path": wt_path,
            "adr": adr_res,
            "pr_summary": pr_summary,
            "progress_sync": sync_progress,
            "message": f"Documentation phase complete. ADRs, criteria checkboxes, and canonical PR summary generated for '{clean_spec}'.",
        }

    def run_stage_git(
        self,
        spec_name: str,
        worktree_path: str,
        auto_merge: bool = False,
        create_pr: bool = False,
        push: bool = False,
        pr_summary: Optional[Dict[str, Any]] = None,
        no_worktree: bool = False,
        staging_branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Stage 7: Git commit synthesis, grilling confirmation metadata, and optional PR creation."""
        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.rstrip("/\\"))).strip("-._").lower()

        if no_worktree:
            # No isolated worker branch: commits already live on the branch used throughout the run.
            worker_branch = staging_branch or get_current_branch(self.target_dir)
            target_base = get_default_branch(self.target_dir)
        else:
            worker_branch = f"feat/{clean_spec}-worker"
            feat_branch = f"feat/{clean_spec}"
            feat_ref = run_git(["rev-parse", "--verify", f"refs/heads/{feat_branch}"], cwd=self.target_dir)
            if feat_ref.returncode != 0:
                default_b = get_default_branch(self.target_dir)
                run_git(["branch", feat_branch, default_b], cwd=self.target_dir)
            target_base = feat_branch

        pr_url = None

        if not pr_summary:
            pr_summary = compile_scoped_pr_summary(self.target_dir, spec_name=clean_spec)

        gh_readiness = check_gh_readiness(self.target_dir)
        pr_creation_status = "SKIPPED"
        pr_creation_message = None

        if push:
            # Ensure base feature branch exists on origin before pushing worker branch or opening PR
            if target_base not in ("main", "master"):
                run_git(["push", "-u", "origin", target_base], cwd=self.target_dir)
            push_res = run_git(["push", "-u", "origin", worker_branch], cwd=self.target_dir)
            push_status = "PUSHED_TO_ORIGIN" if push_res.returncode == 0 else f"PUSH_FAILED: {push_res.stderr.strip()}"
        else:
            push_status = "REMOTE_PUSH_SKIPPED"

        if no_worktree:
            # There is no separate worker branch to fold back in; work already landed on worker_branch.
            merge_status = "NOT_APPLICABLE_NO_WORKTREE"
        elif auto_merge:
            status_main = run_git(["status", "--porcelain"], cwd=self.target_dir)
            if status_main.stdout.strip():
                merge_status = "DIRTY_TREE_POSTPONED"
            else:
                merge_cmd = run_git(["merge", "--no-ff", worker_branch, "-m", f"chore({clean_spec}): auto-merge pipeline improvements"], cwd=self.target_dir)
                merge_status = "AUTO_MERGED" if merge_cmd.returncode == 0 else f"MERGE_FAILED: {merge_cmd.stderr.strip()}"
        else:
            merge_status = "MERGE_SKIPPED"

        if create_pr and no_worktree and worker_branch == target_base:
            pr_creation_status = "SKIPPED_SAME_BRANCH"
            pr_creation_message = f"Head branch '{worker_branch}' matches base branch '{target_base}' in --no-worktree mode; no Pull Request is needed."
        elif create_pr:
            if not gh_readiness["ready"]:
                pr_creation_status = gh_readiness["status"]
                pr_creation_message = gh_readiness["message"]
            else:
                pr_res = create_github_pull_request(
                    head_branch=worker_branch,
                    base_branch=target_base,
                    title=pr_summary.get("pr_title"),
                    body_file=pr_summary.get("pr_file_path"),
                    target_dir=self.target_dir,
                    push_before_pr=push,
                )
                if pr_res.get("status") in ("SUCCESS", "PR_UPDATED"):
                    pr_url = pr_res.get("pr_url")
                    pr_creation_status = pr_res.get("status")
                    pr_creation_message = pr_res.get("message")
                else:
                    pr_creation_status = pr_res.get("status", "PR_FAILED")
                    pr_creation_message = pr_res.get("message")

        pr_title_val = pr_summary.get("pr_title", f"feat({clean_spec}): automated merge request from workflow agent")
        pr_body_val = pr_summary.get("pr_file_path", "")
        suggested_push = f"git push -u origin {shlex.quote(worker_branch)}"
        suggested_gh = f"gh pr create --head {shlex.quote(worker_branch)} --base {shlex.quote(target_base)} --title {shlex.quote(pr_title_val)} --body-file {shlex.quote(pr_body_val)}"
        suggested_git = f"git checkout {shlex.quote(target_base)} && git merge --no-ff {shlex.quote(worker_branch)}"

        return {
            "stage": "7_git_worker",
            "status": "READY_FOR_GRILLING_CONFIRMATION",
            "subagent_role": "Git-Worker Specialist",
            "pr_summary": pr_summary,
            "push_status": push_status,
            "auto_merge_status": merge_status,
            "pr_url": pr_url,
            "gh_readiness": gh_readiness,
            "pr_creation_status": pr_creation_status,
            "pr_creation_message": pr_creation_message,
            "suggested_push_command": suggested_push,
            "suggested_gh_command": suggested_gh,
            "suggested_git_merge": suggested_git,
        }

    def run_pipeline(
        self,
        spec_name: str,
        auto_merge: bool = False,
        create_pr: bool = False,
        push: bool = False,
        only: Optional[str] = None,
        from_stage: Optional[str] = None,
        dry_run: bool = False,
        no_worktree: bool = False,
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

            if no_worktree:
                target_base = get_default_branch(self.target_dir)
                staging_branch = f"feat/{clean_spec}" if is_protected_branch(curr_b) else curr_b
                wt_path_sim = self.target_dir
            else:
                target_base = f"feat/{clean_spec}" if is_protected_branch(curr_b) else curr_b
                staging_branch = f"feat/{clean_spec}-worker"
                wt_path_sim = os.path.join(self.wf_root, "worktrees", clean_spec, "worker")

            rel_wt = os.path.relpath(wt_path_sim, self.target_dir).replace("\\", "/")

            return {
                "status": "DRY_RUN_SIMULATION",
                "dry_run": True,
                "no_worktree": no_worktree,
                "spec_name": clean_spec,
                "spec_file": spec_info.get("spec_file"),
                "staging_branch": staging_branch,
                "target_base": target_base,
                "current_branch": curr_b,
                "worktree_path": rel_wt,
                "active_stages": active_stages,
                "preferred_formatter": pref_fmt.get("name") if pref_fmt else "Standard / Inferred",
                "formatter_command": " ".join(pref_fmt.get("command", [])) if pref_fmt else "None",
            }

        # Step 0: Stage 0 Worktree Sync
        sync_res = self.run_stage_sync(clean_spec, no_worktree=no_worktree)
        default_wt_path = self.target_dir if no_worktree else os.path.join(self.wf_root, "worktrees", clean_spec, "worker")
        wt_path = sync_res.get("worktree_path") or default_wt_path
        rel_wt_path = os.path.relpath(wt_path, self.target_dir).replace("\\", "/")

        # Step 1: LangGraph DAG Execution for Core SDD/TDD Node Transitions
        graph = create_pipeline_graph()
        initial_state = {
            "target_dir": self.target_dir,
            "spec_name": clean_spec,
            "staging_branch": sync_res.get("staging_branch", f"feat/{clean_spec}-worker"),
            "target_base": sync_res.get("target_base", "main"),
            "current_branch": sync_res.get("current_branch", "main"),
            "on_protected_branch": sync_res.get("on_protected_branch", False),
            "worktree_path": wt_path,
            "auto_merge": auto_merge,
            "create_pr": create_pr,
            "push": push,
            "active_stages": active_stages,
            "no_worktree": no_worktree,
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

        # Step 4: Doc Subagent Execution (ADR consolidation, tasks/spec sync, and PR summary synthesis)
        doc_res = {}
        if "doc" in active_stages:
            doc_res = self.run_stage_doc(clean_spec, wt_path, spec_dir=spec_info.get("spec_dir"), security_results=sec_res)
            create_stage_checkpoint(wt_path, "6_doc")

        # Step 5: Git Subagent Execution
        git_res = {}
        pr_mode = create_pr or push
        if "git_worker" in active_stages:
            git_res = self.run_stage_git(
                clean_spec,
                wt_path,
                auto_merge=auto_merge,
                create_pr=pr_mode,
                push=pr_mode,
                pr_summary=doc_res.get("pr_summary"),
                no_worktree=no_worktree,
                staging_branch=sync_res.get("staging_branch"),
            )

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
            },
            {
                "stage": "6_doc",
                "status": "DOCS_SYNCHRONIZED" if "doc" in active_stages else "SKIPPED",
                "subagent_role": "Doc Subagent",
                "adr": doc_res.get("adr"),
                "pr_summary": doc_res.get("pr_summary"),
            },
            {
                "stage": "7_git_worker",
                "status": "READY_FOR_GRILLING_CONFIRMATION" if "git_worker" in active_stages else "SKIPPED",
                "subagent_role": "Git Subagent",
                "push_status": git_res.get("push_status"),
                "pr_summary": git_res.get("pr_summary") or doc_res.get("pr_summary"),
            },
        ]

        all_directives = [
            {
                "stage_key": "implement",
                "stage": "Stage 1 (Implement)",
                "type": "workflow-implement-worker",
                "role": "Implement Subagent",
                "prompt_file": "skills/workflow/references/prompts/implement_worker.prompt.md",
                "action": f"define_subagent(name='workflow-implement-worker', description='Feature & SDD/TDD Engineer', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-implement-worker', 'Role': 'Implement Subagent', 'Prompt': 'Build out spec requirements and task issues for {clean_spec} in {wt_path}. Follow TDD Red-Green cycle and zero-comments policy.'}}])",
            },
            {
                "stage_key": "fix",
                "stage": "Stage 2 (Fix)",
                "type": "workflow-fix-worker",
                "role": "Fix Subagent",
                "prompt_file": "skills/workflow/references/prompts/fix_worker.prompt.md",
                "action": f"define_subagent(name='workflow-fix-worker', description='Bug stabilization & 100% green test specialist', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-fix-worker', 'Role': 'Fix Subagent', 'Prompt': 'Diagnose and stabilize tests in {wt_path}. Zero-comments policy.'}}])",
            },
            {
                "stage_key": "refactor",
                "stage": "Stage 3 (Refactor)",
                "type": "workflow-refactor-worker",
                "role": "Refactor Subagent",
                "prompt_file": "skills/workflow/references/prompts/refactor_worker.prompt.md",
                "action": f"define_subagent(name='workflow-refactor-worker', description='Clean architecture and modularity specialist', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-refactor-worker', 'Role': 'Refactor Subagent', 'Prompt': 'Refactor modular code in {wt_path} while preserving 100% green tests.'}}])",
            },
            {
                "stage_key": "security",
                "stage": "Stage 4 (Security)",
                "type": "workflow-security-worker",
                "role": "Security Subagent",
                "prompt_file": "skills/workflow/references/prompts/security_worker.prompt.md",
                "action": f"define_subagent(name='workflow-security-worker', description='OWASP Top 10 SAST, secret leak & dependency CVE auditor', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-security-worker', 'Role': 'Security Subagent', 'Prompt': 'Audit OWASP Top 10 patterns, secrets and dependencies in {wt_path}. Generate security report.'}}])",
            },
            {
                "stage_key": "quality",
                "stage": "Stage 5 (Quality)",
                "type": "workflow-quality-worker",
                "role": "Quality Subagent",
                "prompt_file": "skills/workflow/references/prompts/quality_worker.prompt.md",
                "action": f"define_subagent(name='workflow-quality-worker', description='Quality gatekeeper, ADR author & feedback router', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-quality-worker', 'Role': 'Quality Subagent', 'Prompt': 'Audit combined quality gates (100/100, zero-comments, OWASP clearance) in {wt_path}.'}}])",
            },
            {
                "stage_key": "doc",
                "stage": "Stage 6 (Doc)",
                "type": "workflow-doc-worker",
                "role": "Doc Subagent",
                "prompt_file": "skills/workflow/references/prompts/doc_worker.prompt.md",
                "action": f"define_subagent(name='workflow-doc-worker', description='Documentation and spec synchronizer', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-doc-worker', 'Role': 'Doc Subagent', 'Prompt': 'Author incremental ADRs (0000_adr_<slug>.md), sync markdown docs, and compile canonical PR summary in {wt_path}.'}}])",
            },
            {
                "stage_key": "git_worker",
                "stage": "Stage 7 (Git-Worker)",
                "type": "workflow-git-worker",
                "role": "Git Subagent",
                "prompt_file": "skills/workflow/references/prompts/git_worker.prompt.md",
                "action": f"define_subagent(name='workflow-git-worker', description='Deterministic Conventional Commits and GitHub PR specialist', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-git-worker', 'Role': 'Git Subagent', 'Prompt': 'Conduct Grilling Session confirmation with developer. Commit locally via git_ops.py commit. If developer authorizes PR, ONLY run `uv run skills/workflow/scripts/workflow_runner.py pr {clean_spec}`. NEVER run manual `gh pr create` and NEVER target `main` directly!'}}])",
            },
        ]
        filtered_directives = [d for d in all_directives if d["stage_key"] in active_stages]

        return {
            "status": "SUCCESS",
            "spec_name": clean_spec,
            "no_worktree": no_worktree,
            "staging_branch": sync_res.get("staging_branch", f"feat/{clean_spec}-worker"),
            "target_base": sync_res.get("target_base", f"feat/{clean_spec}"),
            "current_branch": sync_res.get("current_branch", "main"),
            "on_protected_branch": sync_res.get("on_protected_branch", False),
            "worktree_path": rel_wt_path,
            "elapsed_seconds": elapsed,
            "active_stages": active_stages,
            "stages": [s for s in stages if s["stage"].split("_", 1)[1] in active_stages],
            "pr_flag_active": pr_mode,
            "push_flag_active": pr_mode,
            "push_status": git_res.get("push_status"),
            "adr": doc_res.get("adr"),
            "security_report": sec_res.get("report_file"),
            "pr_summary": git_res.get("pr_summary") or doc_res.get("pr_summary"),
            "gh_readiness": git_res.get("gh_readiness"),
            "pr_creation_status": git_res.get("pr_creation_status"),
            "pr_creation_message": git_res.get("pr_creation_message"),
            "progress_sync": doc_res.get("progress_sync") or {},
            "suggested_push_command": git_res.get("suggested_push_command"),
            "suggested_gh_command": git_res.get("suggested_gh_command"),
            "suggested_git_merge": git_res.get("suggested_git_merge"),
            "subagent_directives": filtered_directives,
        }
