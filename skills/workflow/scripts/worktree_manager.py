"""Physical Git Worktree manager and self-healing lifecycle engine."""

import os
import re
import shutil
import stat
import subprocess
import time
from typing import Dict, Any, List, Optional


def _handle_remove_readonly(func, path, exc_info):
    """Error handler for shutil.rmtree on Windows to clear readonly attributes."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def safe_rmtree(dir_path: str) -> None:
    """Robust directory removal clearing read-only locks across Linux, macOS, and Windows."""
    if os.path.exists(dir_path):
        try:
            shutil.rmtree(dir_path, onerror=_handle_remove_readonly)
        except Exception:
            try:
                shutil.rmtree(dir_path, ignore_errors=True)
            except Exception:
                pass


def run_git(args: List[str], cwd: str = ".") -> subprocess.CompletedProcess:
    """Executes a git command safely in the specified working directory."""
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, check=False)


def get_default_branch(repo_dir: str = ".") -> str:
    """Dynamically resolves the default base branch (main vs master vs remote HEAD)."""
    repo_dir = os.path.abspath(repo_dir)
    
    # 1. Check remote HEAD symbolic-ref (e.g. origin/main)
    sym_res = run_git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd=repo_dir)
    if sym_res.returncode == 0 and sym_res.stdout.strip():
        branch = sym_res.stdout.strip().replace("origin/", "")
        if branch:
            return branch

    # 2. Check local main branch
    main_res = run_git(["rev-parse", "--verify", "main"], cwd=repo_dir)
    if main_res.returncode == 0:
        return "main"

    # 3. Check local master branch
    master_res = run_git(["rev-parse", "--verify", "master"], cwd=repo_dir)
    if master_res.returncode == 0:
        return "master"

    # 4. Fallback to current active branch
    current_res = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_dir)
    if current_res.returncode == 0 and current_res.stdout.strip() != "HEAD":
        return current_res.stdout.strip()

    return "main"


PROTECTED_BRANCHES = {"main", "master", "trunk", "production", "release"}


def get_current_branch(repo_dir: str = ".") -> str:
    """Returns the name of the currently checked-out git branch."""
    repo_dir = os.path.abspath(repo_dir)
    res = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_dir)
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout.strip()
    return "main"


def is_protected_branch(branch_name: str) -> bool:
    """Returns True if the branch is a protected production/default branch."""
    return branch_name.lower().strip() in PROTECTED_BRANCHES


def ensure_git_repository(repo_dir: str = ".") -> Dict[str, Any]:
    """Ensures target directory is a valid Git repository with at least one commit on HEAD."""
    repo_dir = os.path.abspath(repo_dir)
    res = run_git(["rev-parse", "--is-inside-work-tree"], cwd=repo_dir)
    initialized = False
    initial_commit_created = False

    if res.returncode != 0:
        run_git(["init", "-b", "main"], cwd=repo_dir)
        initialized = True

    head_check = run_git(["rev-parse", "--verify", "HEAD"], cwd=repo_dir)
    if head_check.returncode != 0:
        run_git(["commit", "--allow-empty", "-m", "chore: initialize repository"], cwd=repo_dir)
        initial_commit_created = True

    return {
        "status": "READY",
        "initialized": initialized,
        "initial_commit_created": initial_commit_created,
        "default_branch": get_default_branch(repo_dir),
    }


def list_worktrees(repo_dir: str = ".") -> List[Dict[str, str]]:
    """Lists active git worktrees and parses output into structured dictionary."""
    repo_dir = os.path.abspath(repo_dir)
    ensure_git_repository(repo_dir)
    res = run_git(["worktree", "list", "--porcelain"], cwd=repo_dir)
    if res.returncode != 0:
        return []

    worktrees = []
    current: Dict[str, str] = {}
    for line in res.stdout.splitlines():
        line = line.strip()
        if not line:
            if current:
                worktrees.append(current)
                current = {}
            continue
        if line.startswith("worktree "):
            current["path"] = line.replace("worktree ", "").strip()
        elif line.startswith("HEAD "):
            current["head"] = line.replace("HEAD ", "").strip()
        elif line.startswith("branch "):
            current["branch"] = line.replace("branch ", "").strip()
        elif line == "bare":
            current["bare"] = "true"
        elif line == "detached":
            current["detached"] = "true"

    if current:
        worktrees.append(current)
    return worktrees


def resolve_worktree_path(
    name: str,
    spec_name: Optional[str] = None,
    worker_name: Optional[str] = None,
    repo_dir: str = ".",
) -> str:
    """Resolves hierarchical worktree directory path within strict .workflow/worktrees sandbox."""
    repo_dir = os.path.abspath(repo_dir)
    wf_root = os.path.join(repo_dir, ".workflow") if os.path.basename(repo_dir) != ".workflow" else repo_dir
    sandbox_base = os.path.realpath(os.path.join(wf_root, "worktrees"))

    # Sanitize inputs to prevent path traversal
    if spec_name:
        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(str(spec_name).rstrip("/\\"))).strip("-._").lower() or "spec"
        clean_worker = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(str(worker_name or name).rstrip("/\\"))).strip("-._").lower() or "worker"
        candidate = os.path.join(sandbox_base, clean_spec, clean_worker)
    else:
        name_str = str(name).replace("\\", "/")
        if ".workflow/worktrees/" in name_str:
            name_str = name_str.split(".workflow/worktrees/")[-1]
        
        parts = [re.sub(r"[^a-zA-Z0-9_.-]+", "-", p).strip("-._").lower() for p in name_str.split("/") if p and p not in (".", "..")]
        if not parts:
            parts = ["unnamed", "worker"]
        elif len(parts) == 1:
            parts = [parts[0], "worker"]
        
        candidate = os.path.join(sandbox_base, *parts)

    # Strict Sandbox Security Validation: Must be a sub-path strictly inside sandbox_base
    resolved = os.path.realpath(candidate)
    try:
        common = os.path.commonpath([resolved, sandbox_base])
    except ValueError:
        raise ValueError(f"Security sandbox violation: Path '{resolved}' is on a different drive than '{sandbox_base}'.")

    if common != sandbox_base or resolved == sandbox_base or not resolved.startswith(sandbox_base + os.sep):
        raise ValueError(f"Security sandbox violation: Path '{resolved}' is outside allowed worktrees directory '{sandbox_base}'.")

    return resolved


def generate_branch_name(
    archetype: Optional[str] = "implement",
    spec_name: Optional[str] = None,
    worker_name: Optional[str] = None,
) -> str:
    """Generates branch name matching the spec functionality (e.g. user-login) or worker branch (e.g. user-login-fix-worker)."""
    clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(spec_name.replace("\\", "/"))).strip("-._").lower() if spec_name else None
    clean_worker = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(worker_name.replace("\\", "/"))).strip("-._").lower() if worker_name else None

    if clean_spec and clean_worker and clean_worker != clean_spec:
        return f"{clean_spec}-{clean_worker}"
    elif clean_spec:
        return clean_spec
    elif clean_worker:
        return clean_worker
    else:
        return f"task-{int(time.time())}"


def create_worktree(
    name: str,
    base_branch: Optional[str] = None,
    repo_dir: str = ".",
    branch_name: Optional[str] = None,
    archetype: Optional[str] = None,
    spec_name: Optional[str] = None,
    worker_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Creates a physical git worktree under .workflow/worktrees/<branch_name>/<worker_name> with its isolated branch."""
    repo_dir = os.path.abspath(repo_dir)
    ensure_git_repository(repo_dir)
    wf_root = os.path.join(repo_dir, ".workflow") if os.path.basename(repo_dir) != ".workflow" else repo_dir

    # 1. Resolve spec/branch and worker name
    effective_spec = spec_name
    effective_worker = worker_name or name

    if "/" in name.replace("\\", "/"):
        parts = name.replace("\\", "/").split("/", 1)
        effective_spec = effective_spec or parts[0]
        effective_worker = parts[1]

    if effective_spec:
        clean_spec = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(effective_spec.rstrip("/\\"))).strip("-._").lower()
        clean_branch_dir = clean_spec
    else:
        clean_spec = None
        clean_branch_dir = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(effective_worker.rstrip("/\\"))).strip("-._").lower()

    clean_worker = re.sub(r"[^a-zA-Z0-9_.-]+", "-", os.path.basename(effective_worker.rstrip("/\\"))).strip("-._").lower() or "worker"

    # Strict hierarchical directory: .workflow/worktrees/<branch>/<worker>
    worktree_dir = os.path.join(wf_root, "worktrees", clean_branch_dir, clean_worker)

    # Branch name: branch_name or <spec>-<worker> or <spec>
    if branch_name:
        target_branch = branch_name
    elif clean_spec and clean_worker and clean_worker != clean_spec:
        target_branch = f"{clean_spec}-{clean_worker}"
    elif clean_spec:
        target_branch = clean_spec
    else:
        target_branch = clean_worker

    # Resolve target base branch: if working on a spec and base_branch not explicitly specified,
    # rebase/branch off the spec branch (e.g. user-login) if it exists, else default repo branch (main).
    if base_branch:
        target_base = base_branch
    elif clean_spec:
        spec_ref = run_git(["rev-parse", "--verify", f"refs/heads/{clean_spec}"], cwd=repo_dir)
        if spec_ref.returncode == 0:
            target_base = clean_spec
        else:
            target_base = get_default_branch(repo_dir)
    else:
        target_base = get_default_branch(repo_dir)

    # Self-healing prune first
    prune_worktrees(repo_dir)

    if os.path.exists(worktree_dir):
        wt_list = list_worktrees(repo_dir)
        actual_branch = target_branch
        for wt in wt_list:
            if os.path.abspath(wt.get("path", "")) == os.path.abspath(worktree_dir):
                actual_branch = wt.get("branch", target_branch).replace("refs/heads/", "")
                break
        return {
            "status": "ALREADY_EXISTS",
            "worktree_path": worktree_dir,
            "branch_name": actual_branch,
            "base_branch": target_base,
        }

    os.makedirs(os.path.dirname(worktree_dir), exist_ok=True)

    # Check if branch already exists in local git
    branch_check = run_git(["rev-parse", "--verify", f"refs/heads/{target_branch}"], cwd=repo_dir)
    if branch_check.returncode == 0:
        existing_wts = list_worktrees(repo_dir)
        is_checked_out = any(wt.get("branch", "").replace("refs/heads/", "") == target_branch for wt in existing_wts)
        if not is_checked_out:
            res = run_git(["worktree", "add", worktree_dir, target_branch], cwd=repo_dir)
        else:
            # Scope branch with hyphen by worker name if main feature branch is currently checked out by another worker
            if not target_branch.endswith(f"-{clean_worker}"):
                candidate_branch = f"{target_branch}-{clean_worker}"
            else:
                candidate_branch = f"{target_branch}-{int(time.time() * 1000)}"

            cand_check = run_git(["rev-parse", "--verify", f"refs/heads/{candidate_branch}"], cwd=repo_dir)
            if cand_check.returncode == 0:
                is_cand_checked_out = any(wt.get("branch", "").replace("refs/heads/", "") == candidate_branch for wt in existing_wts)
                if not is_cand_checked_out:
                    res = run_git(["worktree", "add", worktree_dir, candidate_branch], cwd=repo_dir)
                    target_branch = candidate_branch
                else:
                    target_branch = f"{candidate_branch}-{int(time.time() * 1000)}"
                    res = run_git(["worktree", "add", "-b", target_branch, worktree_dir, target_base], cwd=repo_dir)
            else:
                target_branch = candidate_branch
                res = run_git(["worktree", "add", "-b", target_branch, worktree_dir, target_base], cwd=repo_dir)
    else:
        res = run_git(["worktree", "add", "-b", target_branch, worktree_dir, target_base], cwd=repo_dir)
        if res.returncode != 0:
            target_branch = f"{target_branch}-{int(time.time() * 1000)}"
            res = run_git(["worktree", "add", "-b", target_branch, worktree_dir, target_base], cwd=repo_dir)

    if res.returncode != 0:
        return {
            "status": "ERROR",
            "error": res.stderr.strip(),
            "worktree_path": worktree_dir,
            "branch_name": target_branch,
        }

    return {
        "status": "CREATED",
        "worktree_path": worktree_dir,
        "branch_name": target_branch,
        "base_branch": target_base,
    }


def remove_worktree(
    name: str,
    spec_name: Optional[str] = None,
    repo_dir: str = ".",
    force: bool = False
) -> Dict[str, Any]:
    """Removes a physical worktree and cleans up git references."""
    repo_dir = os.path.abspath(repo_dir)
    try:
        worktree_dir = resolve_worktree_path(name, spec_name=spec_name, repo_dir=repo_dir)
    except ValueError as e:
        return {"status": "SECURITY_ERROR", "error": str(e), "worktree_path": name}

    args = ["worktree", "remove", worktree_dir]
    if force:
        args.append("--force")

    res = run_git(args, cwd=repo_dir)
    prune_worktrees(repo_dir)

    if res.returncode != 0 and os.path.exists(worktree_dir):
        return {"status": "ERROR", "error": res.stderr.strip(), "worktree_path": worktree_dir}

    # Clean empty parent branch directory if left behind
    parent = os.path.dirname(worktree_dir)
    if os.path.exists(parent) and not os.listdir(parent):
        try:
            os.rmdir(parent)
        except Exception:
            pass

    return {"status": "REMOVED", "worktree_path": worktree_dir}


def force_purge_worktree(
    name: str,
    spec_name: Optional[str] = None,
    repo_dir: str = "."
) -> Dict[str, Any]:
    """Workspace Hygiene Cleanup: removes ephemeral worktree directory under .workflow/worktrees/ and clears git worktree locks."""
    repo_dir = os.path.abspath(repo_dir)
    try:
        worktree_dir = resolve_worktree_path(name, spec_name=spec_name, repo_dir=repo_dir)
    except ValueError as e:
        return {"status": "SECURITY_ERROR", "error": str(e), "worktree_path": name}

    # 1. Attempt standard git worktree remove with --force
    run_git(["worktree", "remove", "--force", worktree_dir], cwd=repo_dir)
    prune_worktrees(repo_dir)

    # 2. Check for leftover disk directory and forcefully wipe if necessary
    if os.path.exists(worktree_dir):
        safe_rmtree(worktree_dir)

    # Clean empty parent directory under worktrees/
    parent = os.path.dirname(worktree_dir)
    if os.path.exists(parent) and not os.listdir(parent):
        try:
            os.rmdir(parent)
        except Exception:
            pass

    # 3. Clean any stale lockfiles (.git/index.lock or .git/worktrees/<name>/locked)
    git_dir = os.path.join(repo_dir, ".git")
    if os.path.exists(git_dir):
        main_index_lock = os.path.join(git_dir, "index.lock")
        if os.path.exists(main_index_lock):
            try:
                os.remove(main_index_lock)
            except Exception:
                pass
        clean_name = os.path.basename(worktree_dir)
        wt_meta = os.path.join(git_dir, "worktrees", clean_name)
        if os.path.exists(wt_meta):
            safe_rmtree(wt_meta)

    prune_worktrees(repo_dir)
    return {"status": "PURGED", "worktree_path": worktree_dir}


def sync_worktree_with_base(
    worktree_path: str,
    base_branch: Optional[str] = None,
    repo_dir: str = "."
) -> Dict[str, Any]:
    """Pre-Cycle Synchronization: Safely rebases the worktree branch onto the latest base branch."""
    worktree_path = os.path.abspath(worktree_path)
    repo_dir = os.path.abspath(repo_dir)

    if not os.path.exists(worktree_path):
        return {"status": "NOT_FOUND", "worktree_path": worktree_path}

    # 1. Fetch latest refs from remotes if remote origin exists
    remotes_check = run_git(["remote"], cwd=repo_dir)
    if remotes_check.returncode == 0 and remotes_check.stdout.strip():
        run_git(["fetch", "--all"], cwd=repo_dir)

    # 2. Dynamically resolve base branch
    target_ref = base_branch or get_default_branch(repo_dir)

    # 3. Execute safe non-destructive merge inside worktree (no history rewriting)
    merge_res = run_git(["merge", "--no-edit", target_ref], cwd=worktree_path)
    if merge_res.returncode != 0:
        # Abort merge to maintain pristine working tree state on conflict
        run_git(["merge", "--abort"], cwd=worktree_path)
        return {
            "status": "CONFLICT",
            "message": f"Conflict detected while merging base branch '{target_ref}' into worktree. Merge aborted safely.",
            "error": merge_res.stderr.strip() or merge_res.stdout.strip(),
            "worktree_path": worktree_path,
            "base_branch": target_ref,
        }

    return {
        "status": "SYNCHRONIZED",
        "worktree_path": worktree_path,
        "base_branch": target_ref,
    }


def prune_worktrees(repo_dir: str = ".") -> bool:
    """Self-healing prune of stale worktree entries."""
    res = run_git(["worktree", "prune"], cwd=repo_dir)
    return res.returncode == 0


def create_stage_checkpoint(worktree_dir: str, stage_name: str) -> Dict[str, Any]:
    """Creates a local Git checkpoint commit and metadata reference in the worktree after a verified green stage."""
    worktree_dir = os.path.abspath(worktree_dir)
    if not os.path.exists(worktree_dir):
        return {"status": "ERROR", "message": f"Worktree not found: {worktree_dir}", "checkpoint_sha": ""}

    run_git(["add", "-A"], cwd=worktree_dir)
    msg = f"chore(workflow-checkpoint): [{stage_name}] green baseline"
    commit_res = run_git(["commit", "-m", msg, "--allow-empty"], cwd=worktree_dir)
    sha_res = run_git(["rev-parse", "HEAD"], cwd=worktree_dir)
    sha = sha_res.stdout.strip() if sha_res.returncode == 0 else ""

    return {
        "status": "SUCCESS",
        "stage": stage_name,
        "checkpoint_sha": sha,
        "worktree_dir": worktree_dir,
        "message": f"Created checkpoint for stage '{stage_name}' at {sha[:8]}",
    }


def rollback_to_stage_checkpoint(worktree_dir: str, checkpoint_sha: str) -> Dict[str, Any]:
    """Rolls back the worktree cleanly to a previous verified green stage checkpoint."""
    worktree_dir = os.path.abspath(worktree_dir)
    if not os.path.exists(worktree_dir):
        return {"status": "ERROR", "message": f"Worktree not found: {worktree_dir}"}

    if not checkpoint_sha:
        return {"status": "ERROR", "message": "No checkpoint SHA provided"}

    res_reset = run_git(["reset", "--hard", checkpoint_sha], cwd=worktree_dir)
    run_git(["clean", "-fd"], cwd=worktree_dir)

    success = (res_reset.returncode == 0)
    return {
        "status": "ROLLED_BACK" if success else "ROLLBACK_ERROR",
        "checkpoint_sha": checkpoint_sha,
        "worktree_dir": worktree_dir,
        "message": f"Successfully rolled back worktree to checkpoint {checkpoint_sha[:8]}" if success else res_reset.stderr.strip(),
    }


def list_stage_checkpoints(worktree_dir: str, limit: int = 10) -> List[Dict[str, str]]:
    """Lists recent workflow checkpoint commits in the worktree."""
    worktree_dir = os.path.abspath(worktree_dir)
    if not os.path.exists(worktree_dir):
        return []

    log_res = run_git(["log", f"-n{limit}", "--grep=chore(workflow-checkpoint):", "--pretty=format:%H|%s|%ai"], cwd=worktree_dir)
    if log_res.returncode != 0 or not log_res.stdout.strip():
        return []

    checkpoints = []
    for line in log_res.stdout.strip().split("\n"):
        if "|" in line:
            parts = line.split("|", 2)
            if len(parts) == 3:
                checkpoints.append({
                    "sha": parts[0].strip(),
                    "subject": parts[1].strip(),
                    "date": parts[2].strip(),
                })
    return checkpoints

