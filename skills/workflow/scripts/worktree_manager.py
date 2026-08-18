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


def generate_branch_name(
    archetype: Optional[str] = "implement",
    spec_name: Optional[str] = None,
    worker_name: Optional[str] = None,
) -> str:
    """Generates standardized semantic branch name based on archetype and spec/worker name (e.g. feat/login, fix/auth-bug)."""
    arch = (archetype or "implement").lower().strip()
    if arch in ["feat", "feature", "features", "implement"]:
        prefix = "feat"
    elif arch in ["fix", "bug", "bugs", "hotfix", "auto-fixer", "fixer"]:
        prefix = "fix"
    elif arch in ["refactor", "refactoring", "refactor-worker"]:
        prefix = "refactor"
    elif arch in ["doc", "docs", "doc_sync", "documentation", "doc-sync"]:
        prefix = "docs"
    else:
        prefix = re.sub(r"[^a-zA-Z0-9_-]+", "-", arch).strip("-._") or "feat"

    if spec_name:
        clean_spec = re.sub(r"[^a-zA-Z0-9_-]+", "-", os.path.basename(spec_name.replace("\\", "/"))).strip("-._").lower()
        return f"{prefix}/{clean_spec}"
    elif worker_name:
        clean_worker = re.sub(r"[^a-zA-Z0-9_-]+", "-", os.path.basename(worker_name.replace("\\", "/"))).strip("-._").lower()
        return f"{prefix}/{clean_worker}"
    else:
        return f"{prefix}/worker-{int(time.time())}"


def create_worktree(
    name: str,
    base_branch: Optional[str] = None,
    repo_dir: str = ".",
    branch_name: Optional[str] = None,
    archetype: Optional[str] = None,
    spec_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Creates a physical git worktree under .workflow/worktrees/<name> with an isolated semantic branch."""
    repo_dir = os.path.abspath(repo_dir)
    ensure_git_repository(repo_dir)
    
    clean_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", os.path.basename(name.replace("\\", "/"))).strip("-._").lower() or "unnamed"
    target_base = base_branch or get_default_branch(repo_dir)

    wf_root = os.path.join(repo_dir, ".workflow") if os.path.basename(repo_dir) != ".workflow" else repo_dir
    worktree_dir = os.path.join(wf_root, "worktrees", clean_name)

    # Resolve semantic branch name (e.g. feat/<spec-name>, fix/<spec-name>, docs/<daemon>)
    target_branch = branch_name or generate_branch_name(archetype=archetype, spec_name=spec_name, worker_name=clean_name)

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
            target_branch = f"{target_branch}-{int(time.time())}"
            res = run_git(["worktree", "add", "-b", target_branch, worktree_dir, target_base], cwd=repo_dir)
    else:
        res = run_git(["worktree", "add", "-b", target_branch, worktree_dir, target_base], cwd=repo_dir)
        if res.returncode != 0:
            target_branch = f"{target_branch}-{int(time.time())}"
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


def remove_worktree(name: str, repo_dir: str = ".", force: bool = False) -> Dict[str, Any]:
    """Removes a physical worktree and cleans up git references."""
    repo_dir = os.path.abspath(repo_dir)
    clean_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", os.path.basename(name.replace("\\", "/"))).strip("-._").lower()
    wf_root = os.path.join(repo_dir, ".workflow") if os.path.basename(repo_dir) != ".workflow" else repo_dir
    worktree_dir = os.path.join(wf_root, "worktrees", clean_name)
    if not os.path.exists(worktree_dir):
        legacy_dir = os.path.join(repo_dir, ".worktrees", clean_name)
        if os.path.exists(legacy_dir):
            worktree_dir = legacy_dir

    args = ["worktree", "remove", worktree_dir]
    if force:
        args.append("--force")

    res = run_git(args, cwd=repo_dir)
    prune_worktrees(repo_dir)

    if res.returncode != 0 and os.path.exists(worktree_dir):
        return {"status": "ERROR", "error": res.stderr.strip()}

    return {"status": "REMOVED", "worktree_path": worktree_dir}


def force_purge_worktree(name: str, repo_dir: str = ".") -> Dict[str, Any]:
    """Anti-Zombie Deep Purge: forces removal of worktree, lockfiles, and git references."""
    repo_dir = os.path.abspath(repo_dir)
    clean_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", os.path.basename(name.replace("\\", "/"))).strip("-._").lower()
    wf_root = os.path.join(repo_dir, ".workflow") if os.path.basename(repo_dir) != ".workflow" else repo_dir
    worktree_dir = os.path.join(wf_root, "worktrees", clean_name)

    # 1. Attempt standard git worktree remove with --force
    run_git(["worktree", "remove", "--force", worktree_dir], cwd=repo_dir)
    prune_worktrees(repo_dir)

    # 2. Check for leftover disk directory and forcefully wipe if necessary
    if os.path.exists(worktree_dir):
        safe_rmtree(worktree_dir)

    # 3. Clean any stale lockfiles (.git/index.lock or .git/worktrees/<name>/locked)
    git_dir = os.path.join(repo_dir, ".git")
    if os.path.exists(git_dir):
        main_index_lock = os.path.join(git_dir, "index.lock")
        if os.path.exists(main_index_lock):
            try:
                os.remove(main_index_lock)
            except Exception:
                pass
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

    # 1. Fetch from remotes if configured
    run_git(["fetch", "--all"], cwd=repo_dir)

    # 2. Dynamically resolve base branch
    target_ref = base_branch or get_default_branch(repo_dir)

    # 3. Execute safe rebase inside worktree
    rebase_res = run_git(["rebase", target_ref], cwd=worktree_path)
    if rebase_res.returncode != 0:
        # Abort rebase to maintain pristine working tree state
        run_git(["rebase", "--abort"], cwd=worktree_path)
        return {
            "status": "CONFLICT",
            "message": f"Conflict detected while rebasing worktree onto '{target_ref}'. Rebase aborted safely.",
            "error": rebase_res.stderr.strip() or rebase_res.stdout.strip(),
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
