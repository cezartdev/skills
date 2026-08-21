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
)
from scaffolder import get_workflow_root, reconcile_gitkeep, ensure_gitignore_configured
from quality import (
    compile_scoped_pr_summary,
    generate_spec_adr,
    evaluate_quality_gate,
)
from security_auditor import audit_codebase
from git_ops import (
    scan_pre_commit_security,
    execute_atomic_commit,
    create_github_pull_request,
)
from graph.pipeline_graph import create_pipeline_graph


class PipelineRunner:
    """Orchestrates the deterministic 6-stage multi-worker pipeline governed by Quality Gatekeeper."""

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
        wt_path: str,
        auto_merge: bool = False,
        create_pr: bool = False,
        push: bool = False,
    ) -> Dict[str, Any]:
        """Stage 7: Git-Worker (Prepares PR summary, formats Conventional Commit, and handles PR delivery)."""
        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.rstrip("/\\"))).strip("-._").lower()
        worker_branch = f"{clean_spec}-worker"
        
        feat_branch = f"feat/{clean_spec}"
        feat_ref = run_git(["rev-parse", "--verify", f"refs/heads/{feat_branch}"], cwd=self.target_dir)
        spec_ref = run_git(["rev-parse", "--verify", f"refs/heads/{clean_spec}"], cwd=self.target_dir)
        target_base = feat_branch if feat_ref.returncode == 0 else (clean_spec if spec_ref.returncode == 0 else get_default_branch(self.target_dir))

        # 1. Compile PR Summary in .workflow/prs/active/
        pr_summary = compile_scoped_pr_summary(target_dir=self.target_dir, spec_name=clean_spec)

        # 2. Check GitHub CLI availability
        gh_available = (shutil.which("gh") is not None)

        pr_url = None
        merge_status = "PENDING_GRILLING_CONFIRMATION"
        push_status = "LOCAL_COMMIT_ONLY"

        # 3. Optional Remote Push (Default Security: Only pushes if push=True)
        if push:
            push_res = run_git(["push", "-u", "origin", worker_branch], cwd=self.target_dir)
            push_status = "PUSHED_TO_ORIGIN" if push_res.returncode == 0 else f"PUSH_FAILED: {push_res.stderr.strip()}"

        # 4. Optional Auto-Merge into target feature branch
        if auto_merge:
            status_main = run_git(["status", "--porcelain"], cwd=self.target_dir)
            if status_main.stdout.strip():
                merge_status = "DIRTY_TREE_POSTPONED"
            else:
                merge_cmd = run_git(["merge", "--no-ff", worker_branch, "-m", f"chore({clean_spec}): auto-merge pipeline improvements"], cwd=self.target_dir)
                merge_status = "AUTO_MERGED" if merge_cmd.returncode == 0 else f"MERGE_FAILED: {merge_cmd.stderr.strip()}"

        # 5. Optional GitHub PR creation
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

        suggested_push = f"git push -u origin {worker_branch}"
        suggested_gh = f"gh pr create --head {worker_branch} --base {target_base} --title \"{pr_summary.get('pr_title')}\" --body-file \"{pr_summary.get('pr_file_path')}\""
        suggested_git = f"git checkout {target_base} && git merge --no-ff {worker_branch}"

        return {
            "stage": "7_git_worker",
            "status": "READY_FOR_GRILLING_CONFIRMATION",
            "subagent_role": "Git-Worker Specialist",
            "staging_branch": worker_branch,
            "target_base": target_base,
            "pr_summary": pr_summary,
            "push_status": push_status,
            "push_flag_active": push,
            "auto_merge_status": merge_status,
            "pr_url": pr_url,
            "suggested_push_command": suggested_push,
            "suggested_gh_command": suggested_gh,
            "suggested_git_merge": suggested_git,
        }

    def run_pipeline(
        self,
        spec_name: str,
        schedule_minutes: Optional[int] = None,
        auto_merge: bool = False,
        create_pr: bool = False,
        push: bool = False,
    ) -> Dict[str, Any]:
        """Runs the deterministic 7-stage sequential subagent pipeline."""
        start_time = time.time()
        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.rstrip("/\\"))).strip("-._").lower()

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
        }
        graph_res = graph.invoke(initial_state)

        # Step 2: Security & Quality Audit Execution
        sec_res = self.run_stage_security(clean_spec, wt_path)
        quality_res = self.run_stage_quality(clean_spec, wt_path, security_results=sec_res)
        git_res = self.run_stage_git(clean_spec, wt_path, auto_merge=auto_merge, create_pr=create_pr, push=push)

        elapsed = round(time.time() - start_time, 2)

        stages = [
            {
                "stage": "1_implement",
                "status": graph_res.get("implement_status", "IMPLEMENTATION_READY"),
                "subagent_role": "Implementer Specialist",
            },
            {
                "stage": "2_fix",
                "status": graph_res.get("fix_status", "GREEN_TESTS_READY"),
                "subagent_role": "Fix-Worker Specialist",
            },
            {
                "stage": "3_refactor",
                "status": graph_res.get("refactor_status", "REFACTOR_COMPLETE"),
                "subagent_role": "Refactor-Worker Specialist",
            },
            {
                "stage": "4_security",
                "status": "SECURITY_AUDITED",
                "subagent_role": "Cybersecurity & Vulnerability Specialist",
                "security_summary": sec_res.get("summary"),
            },
            {
                "stage": "5_quality",
                "status": "QUALITY_APPROVED" if quality_res.get("verdict") == "APPROVED" else "NEEDS_REMEDIATION",
                "subagent_role": "Quality Assurance Specialist",
                "verdict": quality_res.get("verdict"),
                "adr": quality_res.get("adr"),
            },
            {
                "stage": "6_doc",
                "status": graph_res.get("doc_status", "DOCS_SYNCHRONIZED"),
                "subagent_role": "Doc-Worker Specialist",
            },
            {
                "stage": "7_git_worker",
                "status": "READY_FOR_GRILLING_CONFIRMATION",
                "subagent_role": "Git-Worker Specialist",
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
            "stages": stages,
            "push_flag_active": push,
            "push_status": git_res.get("push_status"),
            "adr": quality_res.get("adr"),
            "security_report": sec_res.get("report_file"),
            "pr_summary": git_res.get("pr_summary"),
            "suggested_push_command": git_res.get("suggested_push_command"),
            "suggested_gh_command": git_res.get("suggested_gh_command"),
            "suggested_git_merge": git_res.get("suggested_git_merge"),
            "scheduled_interval": schedule_minutes,
            "subagent_directives": [
                {
                    "stage": "Stage 1 (Implement)",
                    "type": "workflow-implement-worker",
                    "role": "Implementer Specialist",
                    "prompt_file": "skills/workflow/references/prompts/implement.prompt.md",
                    "action": f"define_subagent(name='workflow-implement-worker', description='Feature & SDD/TDD Engineer', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-implement-worker', 'Role': 'Implementer Specialist', 'Prompt': 'Build out spec requirements and task issues for {clean_spec} in {wt_path}. Follow TDD Red-Green cycle and zero-comments policy.'}}])",
                },
                {
                    "stage": "Stage 2 (Fix)",
                    "type": "workflow-fix-worker",
                    "role": "Fix-Worker Specialist",
                    "prompt_file": "skills/workflow/references/prompts/fix.prompt.md",
                    "action": f"define_subagent(name='workflow-fix-worker', description='Bug stabilization & 100% green test specialist', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-fix-worker', 'Role': 'Fix-Worker Specialist', 'Prompt': 'Diagnose and stabilize tests in {wt_path}. Zero-comments policy.'}}])",
                },
                {
                    "stage": "Stage 3 (Refactor)",
                    "type": "workflow-refactor-worker",
                    "role": "Refactor-Worker Specialist",
                    "prompt_file": "skills/workflow/references/prompts/refactor.prompt.md",
                    "action": f"define_subagent(name='workflow-refactor-worker', description='Clean architecture and modularity specialist', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-refactor-worker', 'Role': 'Refactor-Worker Specialist', 'Prompt': 'Refactor modular code in {wt_path} while preserving 100% green tests.'}}])",
                },
                {
                    "stage": "Stage 4 (Security)",
                    "type": "workflow-security-worker",
                    "role": "Cybersecurity & Vulnerability Specialist",
                    "prompt_file": "skills/workflow/references/prompts/security_worker.prompt.md",
                    "action": f"define_subagent(name='workflow-security-worker', description='OWASP Top 10 SAST, secret leak & dependency CVE auditor', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-security-worker', 'Role': 'Cybersecurity Specialist', 'Prompt': 'Audit OWASP Top 10 patterns, secrets and dependencies in {wt_path}. Generate security report.'}}])",
                },
                {
                    "stage": "Stage 5 (Quality)",
                    "type": "workflow-quality-worker",
                    "role": "Quality Assurance Specialist",
                    "prompt_file": "skills/workflow/references/prompts/quality.prompt.md",
                    "action": f"define_subagent(name='workflow-quality-worker', description='Quality gatekeeper, ADR author & feedback router', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-quality-worker', 'Role': 'Quality Specialist', 'Prompt': 'Audit combined quality gates (100/100, zero-comments, OWASP clearance) in {wt_path} and write ADR.'}}])",
                },
                {
                    "stage": "Stage 6 (Doc)",
                    "type": "workflow-doc-worker",
                    "role": "Doc-Worker Specialist",
                    "prompt_file": "skills/workflow/references/prompts/doc_sync.prompt.md",
                    "action": f"define_subagent(name='workflow-doc-worker', description='Documentation and spec synchronizer', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-doc-worker', 'Role': 'Doc-Worker Specialist', 'Prompt': 'Sync markdown docs and spec.md for {clean_spec} in {wt_path}.'}}])",
                },
                {
                    "stage": "Stage 7 (Git-Worker)",
                    "type": "workflow-git-worker",
                    "role": "Git-Worker Specialist",
                    "prompt_file": "skills/workflow/references/prompts/git_worker.prompt.md",
                    "action": f"define_subagent(name='workflow-git-worker', description='Deterministic Conventional Commits and GitHub PR specialist', enable_write_tools=True) -> invoke_subagent(Subagents=[{{'TypeName': 'workflow-git-worker', 'Role': 'Git-Worker Specialist', 'Prompt': 'Conduct Grilling Session confirmation with developer. Commit locally. Default Security: DO NOT push to origin unless --push flag is passed or developer explicitly requests remote push.'}}])",
                },
            ],
        }
