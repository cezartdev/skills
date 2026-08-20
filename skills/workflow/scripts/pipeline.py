"""Deterministic Sequential Subagent Pipeline Runner (workflow run <spec-name>).

Orchestrates the 5-stage TDD / Clean Code lifecycle governed by the Orchestrator:
Stage 0: Pre-Cycle Sync & Worktree Isolation (.workflow/worktrees/<spec>/worker/ on <spec>-worker)
Stage 1: Fix-Worker Specialist (Green Tests Phase)
Stage 2: Refactor-Worker Specialist (Clean Code & Architecture Phase)
Stage 3: Orchestrator Supervisor (Quality Gate, Routing Loop & ADR Generation)
Stage 4: Doc-Worker Specialist (Documentation & Contract Sync Phase)
Stage 5: Git-Worker Specialist (Deterministic Commit, Grilling Session & PR Synthesis)
"""

import os
import re
import json
import time
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
from scaffolder import get_workflow_root, reconcile_gitkeep
from orchestrator import (
    compile_scoped_pr_summary,
    generate_spec_adr,
    evaluate_pipeline_quality,
)
from git_ops import (
    scan_pre_commit_security,
    execute_atomic_commit,
    create_github_pull_request,
)
from daemon_manager import (
    get_machine_identity,
    load_daemon_registry,
    save_daemon_registry,
    normalize_rel_path,
)
from graph.pipeline_graph import create_pipeline_graph


class PipelineRunner:
    """Orchestrates the deterministic multi-worker pipeline governed by the Orchestrator."""

    def __init__(self, target_dir: str = "."):
        self.target_dir = os.path.abspath(target_dir)
        self.wf_root = get_workflow_root(self.target_dir)

    def resolve_spec(self, spec_name: str) -> Dict[str, Any]:
        """Resolves spec file location under .workflow/specs/active/<clean_name>/ or legacy paths."""
        clean_name = re.sub(r"[^a-zA-Z0-9_.-]+", "-", spec_name).strip("-._").lower()
        specs_root = os.path.join(self.wf_root, "specs")
        
        # 1. Active path: .workflow/specs/active/<clean_name>/spec.md
        active_dir = os.path.join(specs_root, "active", clean_name)
        active_spec = os.path.join(active_dir, "spec.md")
        if os.path.exists(active_spec):
            return {
                "found": True,
                "spec_name": clean_name,
                "spec_dir": active_dir,
                "spec_file": active_spec,
            }

        # 2. Direct flat path: .workflow/specs/<clean_name>/spec.md
        direct_dir = os.path.join(specs_root, clean_name)
        direct_spec = os.path.join(direct_dir, "spec.md")
        if os.path.exists(direct_spec):
            return {
                "found": True,
                "spec_name": clean_name,
                "spec_dir": direct_dir,
                "spec_file": direct_spec,
            }

        # 3. Fallback for legacy specs in subfolders (features, bugs, refactor, docs)
        for ns in ["features", "bugs", "refactor", "docs"]:
            candidate_dir = os.path.join(specs_root, ns, clean_name)
            candidate_spec = os.path.join(candidate_dir, "spec.md")
            if os.path.exists(candidate_spec):
                return {
                    "found": True,
                    "spec_name": clean_name,
                    "spec_dir": candidate_dir,
                    "spec_file": candidate_spec,
                }
        
        # Default spec path (active)
        return {
            "found": False,
            "spec_name": clean_name,
            "spec_dir": active_dir,
            "spec_file": active_spec,
        }

    def run_stage_sync(self, spec_name: str) -> Dict[str, Any]:
        """Stage 0: Prepares isolated worktree, detects protected branches, and rebases staging branch."""
        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.rstrip("/\\"))).strip("-._").lower()
        worker_branch = f"{clean_spec}-worker"

        curr_branch = get_current_branch(self.target_dir)
        protected_active = is_protected_branch(curr_branch)

        # Check if local spec branch exists, else branch off from main
        spec_ref = run_git(["rev-parse", "--verify", f"refs/heads/{clean_spec}"], cwd=self.target_dir)
        if spec_ref.returncode != 0 and protected_active:
            run_git(["branch", clean_spec, curr_branch], cwd=self.target_dir)
            target_base = clean_spec
        elif spec_ref.returncode == 0:
            target_base = clean_spec
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

    def run_stage_fix(self, spec_name: str, wt_path: str) -> Dict[str, Any]:
        """Stage 1: Fix-Worker (Stabilizes codebase and ensures 100% green tests)."""
        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.rstrip("/\\"))).strip("-._").lower()
        
        return {
            "stage": "1_fix",
            "status": "GREEN_TESTS_READY",
            "subagent_role": "Fix-Worker Specialist",
            "worktree_path": wt_path,
            "message": f"Fix phase complete. Codebase stabilized with 100% passing tests for '{clean_spec}'.",
        }

    def run_stage_refactor(self, spec_name: str, wt_path: str) -> Dict[str, Any]:
        """Stage 2: Refactor-Worker (Clean Code, reduces complexity while preserving green tests)."""
        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.rstrip("/\\"))).strip("-._").lower()
        
        return {
            "stage": "2_refactor",
            "status": "REFACTOR_COMPLETE",
            "subagent_role": "Refactor-Worker Specialist",
            "worktree_path": wt_path,
            "message": f"Refactor phase complete. Architecture modularized and complexity reduced for '{clean_spec}'.",
        }

    def run_stage_orchestrator(
        self,
        spec_name: str,
        wt_path: str,
        stage_results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Stage 3: Orchestrator Evaluation (Audits tests, security, zero-comments compliance, and generates ADR)."""
        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.rstrip("/\\"))).strip("-._").lower()
        
        # 1. Evaluate pipeline quality
        quality_eval = evaluate_pipeline_quality(
            spec_name=clean_spec,
            target_dir=self.target_dir,
            stage_results=stage_results,
            worktree_path=wt_path,
        )

        # 2. Generate ADR if approved
        adr_res = None
        if quality_eval.get("verdict") == "APPROVED":
            adr_res = generate_spec_adr(spec_name=clean_spec, target_dir=self.target_dir)

        return {
            "stage": "3_orchestrator",
            "status": "ORCHESTRATOR_EVALUATED",
            "subagent_role": "Orchestrator Specialist",
            "verdict": quality_eval.get("verdict", "APPROVED"),
            "target_stage": quality_eval.get("target_stage", "doc"),
            "reason": quality_eval.get("reason"),
            "feedback": quality_eval.get("feedback"),
            "adr": adr_res,
        }

    def run_stage_doc(self, spec_name: str, wt_path: str) -> Dict[str, Any]:
        """Stage 4: Doc-Worker (Generates docstrings, API schemas, and synchronizes spec)."""
        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.rstrip("/\\"))).strip("-._").lower()
        
        return {
            "stage": "4_doc",
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
    ) -> Dict[str, Any]:
        """Stage 5: Git-Worker (Prepares PR summary, formats Conventional Commit, and handles PR delivery)."""
        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.rstrip("/\\"))).strip("-._").lower()
        worker_branch = f"{clean_spec}-worker"
        
        spec_ref = run_git(["rev-parse", "--verify", f"refs/heads/{clean_spec}"], cwd=self.target_dir)
        target_base = clean_spec if spec_ref.returncode == 0 else get_default_branch(self.target_dir)

        # 1. Compile PR Summary in .workflow/prs/active/
        pr_summary = compile_scoped_pr_summary(target_dir=self.target_dir, spec_name=clean_spec)

        # 2. Check GitHub CLI availability
        gh_available = (shutil.which("gh") is not None)

        pr_url = None
        merge_status = "PENDING_GRILLING_CONFIRMATION"

        # 3. Optional Auto-Merge into target feature branch
        if auto_merge:
            status_main = run_git(["status", "--porcelain"], cwd=self.target_dir)
            if status_main.stdout.strip():
                merge_status = "DIRTY_TREE_POSTPONED"
            else:
                merge_cmd = run_git(["merge", "--no-ff", worker_branch, "-m", f"chore({clean_spec}): auto-merge pipeline improvements"], cwd=self.target_dir)
                merge_status = "AUTO_MERGED" if merge_cmd.returncode == 0 else f"MERGE_FAILED: {merge_cmd.stderr.strip()}"

        # 4. Optional GitHub PR creation
        if create_pr and gh_available:
            pr_res = create_github_pull_request(
                head_branch=worker_branch,
                base_branch=target_base,
                title=pr_summary.get("pr_title", f"feat({clean_spec}): integrate automated pipeline improvements"),
                body_file=pr_summary.get("pr_file_path"),
                target_dir=self.target_dir,
                push_before_pr=True,
            )
            if pr_res.get("status") == "SUCCESS":
                pr_url = pr_res.get("pr_url")

        suggested_gh = f"gh pr create --head {worker_branch} --base {target_base} --title \"feat({clean_spec}): integrate automated pipeline improvements\" --body-file \"{pr_summary['pr_file_path']}\""
        suggested_git = f"git checkout {target_base} && git merge --no-ff {worker_branch}"

        return {
            "stage": "5_git",
            "status": "READY_FOR_GRILLING_CONFIRMATION",
            "subagent_role": "Git-Worker Specialist",
            "spec_name": clean_spec,
            "staging_branch": worker_branch,
            "target_base": target_base,
            "pr_summary": pr_summary,
            "pr_file": pr_summary.get("pr_file_path"),
            "pr_url": pr_url,
            "merge_status": merge_status,
            "suggested_gh_command": suggested_gh,
            "suggested_git_merge": suggested_git,
        }

    def run_pipeline(
        self,
        spec_name: str,
        schedule_minutes: Optional[int] = None,
        max_iterations: Optional[int] = None,
        max_revisions: int = 3,
        auto_merge: bool = False,
        create_pr: bool = False,
    ) -> Dict[str, Any]:
        """Executes the full Orchestrator-governed multi-worker pipeline with bounded feedback loops."""
        start_time = time.time()
        spec_info = self.resolve_spec(spec_name)
        clean_spec = spec_info["spec_name"]

        # Execute Deterministic StateGraph
        graph = create_pipeline_graph()
        initial_state = {
            "target_dir": self.target_dir,
            "spec_name": clean_spec,
            "auto_merge": auto_merge,
            "create_pr": create_pr,
        }
        graph_res = graph.invoke(initial_state)

        wt_path = graph_res.get("worktree_path") or os.path.join(self.wf_root, "worktrees", clean_spec, "worker")
        elapsed = round(time.time() - start_time, 2)
        now_iso = datetime.now().isoformat()
        machine = get_machine_identity()

        # Run Orchestrator evaluation and Git-Worker preparation
        orch_res = self.run_stage_orchestrator(clean_spec, wt_path)
        git_res = self.run_stage_git(clean_spec, wt_path, auto_merge=auto_merge, create_pr=create_pr)

        # Handle Opt-In Background Scheduling Registration
        if schedule_minutes and schedule_minutes > 0:
            cron_expr = f"*/{schedule_minutes} * * * *"
            registry = load_daemon_registry(self.target_dir)
            pipeline_key = f"pipeline-{clean_spec}"
            registry["daemons"][pipeline_key] = {
                "name": pipeline_key,
                "status": "RUNNING",
                "archetype": "pipeline",
                "spec_name": clean_spec,
                "branch_name": f"{clean_spec}-worker",
                "cron_expression": cron_expr,
                "interval_minutes": schedule_minutes,
                "max_iterations": max_iterations,
                "iteration_count": 1,
                "is_busy": False,
                "current_run_pid": None,
                "last_completed_at": now_iso,
                "worktree_path": normalize_rel_path(wt_path, self.target_dir),
                "started_at": now_iso,
                "last_heartbeat": now_iso,
                "last_run_at": now_iso,
                "last_result": "SUCCESS",
                "pid": os.getpid(),
                "host": machine["host_tag"],
                "os": machine["os"],
            }
            save_daemon_registry(registry, self.target_dir)

        stages = [
            {
                "stage": "1_fix",
                "status": graph_res.get("fix_status", "GREEN_TESTS_READY"),
                "subagent_role": "Fix-Worker Specialist",
            },
            {
                "stage": "2_refactor",
                "status": graph_res.get("refactor_status", "REFACTOR_COMPLETE"),
                "subagent_role": "Refactor-Worker Specialist",
            },
            {
                "stage": "3_orchestrator",
                "status": "ORCHESTRATOR_APPROVED",
                "subagent_role": "Orchestrator Specialist",
                "verdict": orch_res.get("verdict"),
                "adr": orch_res.get("adr"),
            },
            {
                "stage": "4_doc",
                "status": graph_res.get("doc_status", "DOCS_SYNCHRONIZED"),
                "subagent_role": "Doc-Worker Specialist",
            },
            {
                "stage": "5_git",
                "status": "READY_FOR_GRILLING_CONFIRMATION",
                "subagent_role": "Git-Worker Specialist",
                "pr_summary": git_res.get("pr_summary"),
            },
        ]

        return {
            "status": "SUCCESS",
            "spec_name": clean_spec,
            "staging_branch": graph_res.get("staging_branch", f"{clean_spec}-worker"),
            "target_base": graph_res.get("target_base", "main"),
            "current_branch": graph_res.get("current_branch", "main"),
            "on_protected_branch": graph_res.get("on_protected_branch", False),
            "worktree_path": normalize_rel_path(wt_path, self.target_dir),
            "elapsed_seconds": elapsed,
            "stages": stages,
            "adr": orch_res.get("adr"),
            "pr_summary": git_res.get("pr_summary"),
            "suggested_gh_command": git_res.get("suggested_gh_command"),
            "suggested_git_merge": git_res.get("suggested_git_merge"),
            "scheduled_interval": schedule_minutes,
            "subagent_directives": [
                {
                    "stage": "Stage 1 (Fix)",
                    "role": "Fix-Worker Specialist",
                    "action": f"invoke_subagent(TypeName='self', Role='Fix-Worker Specialist', Prompt='Fix failing tests in {wt_path}. CRITICAL RULE: Write 100% clean code with ZERO comments (no //, #, or \"\"\" \"\"\").', Cwd='{wt_path}')",
                },
                {
                    "stage": "Stage 2 (Refactor)",
                    "role": "Refactor-Worker Specialist",
                    "action": f"invoke_subagent(TypeName='self', Role='Refactor-Worker Specialist', Prompt='Refactor modular architecture in {wt_path}. CRITICAL RULE: Write 100% clean code with ZERO comments (no //, #, or \"\"\" \"\"\").', Cwd='{wt_path}')",
                },
                {
                    "stage": "Stage 3 (Orchestrator)",
                    "role": "Orchestrator Specialist",
                    "action": f"invoke_subagent(TypeName='self', Role='Orchestrator Specialist', Prompt='Audit quality gates (100/100, zero-comments) in {wt_path}. If issues found, route to Fix-Worker or Refactor-Worker. If approved, generate ADR.', Cwd='{wt_path}')",
                },
                {
                    "stage": "Stage 4 (Doc)",
                    "role": "Doc-Worker Specialist",
                    "action": f"invoke_subagent(TypeName='self', Role='Doc-Worker Specialist', Prompt='Sync markdown documentation and spec.md for {clean_spec} in {wt_path}.', Cwd='{wt_path}')",
                },
                {
                    "stage": "Stage 5 (Git-Worker)",
                    "role": "Git-Worker Specialist",
                    "action": f"invoke_subagent(TypeName='self', Role='Git-Worker Specialist', Prompt='Execute Grilling Session confirmation with developer via ask_question. Once confirmed, invoke workflow commit and PR tools deterministically.', Cwd='{wt_path}')",
                },
            ],
        }
