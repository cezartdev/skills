"""Physical Git Worktree manager and self-healing lifecycle engine."""

import os
import shutil
import subprocess
import time
from typing import Dict, Any, List, Optional


def run_git(args: List[str], cwd: str = ".") -> subprocess.CompletedProcess:
    """Executes a git command safely in the specified working directory."""
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, check=False)


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


def create_worktree(
    name: str,
    base_branch: str = "HEAD",
    repo_dir: str = "."
) -> Dict[str, Any]:
    """Creates a physical git worktree under .workflow/worktrees/<name> with an isolated branch."""
    repo_dir = os.path.abspath(repo_dir)
    ensure_git_repository(repo_dir)
    wf_root = os.path.join(repo_dir, ".workflow") if os.path.basename(repo_dir) != ".workflow" else repo_dir
    worktree_dir = os.path.join(wf_root, "worktrees", name)
    branch_name = f"workflow/worktree-{name}-{int(time.time())}"

    # Self-healing prune first
    prune_worktrees(repo_dir)

    if os.path.exists(worktree_dir):
        return {
            "status": "ALREADY_EXISTS",
            "worktree_path": worktree_dir,
            "branch_name": branch_name,
        }

    os.makedirs(os.path.dirname(worktree_dir), exist_ok=True)
    res = run_git(["worktree", "add", "-b", branch_name, worktree_dir, base_branch], cwd=repo_dir)

    if res.returncode != 0:
        return {
            "status": "ERROR",
            "error": res.stderr.strip(),
            "worktree_path": worktree_dir,
        }

    return {
        "status": "CREATED",
        "worktree_path": worktree_dir,
        "branch_name": branch_name,
    }


def remove_worktree(name: str, repo_dir: str = ".", force: bool = False) -> Dict[str, Any]:
    """Removes a physical worktree and cleans up git references."""
    repo_dir = os.path.abspath(repo_dir)
    wf_root = os.path.join(repo_dir, ".workflow") if os.path.basename(repo_dir) != ".workflow" else repo_dir
    worktree_dir = os.path.join(wf_root, "worktrees", name)
    if not os.path.exists(worktree_dir):
        legacy_dir = os.path.join(repo_dir, ".worktrees", name)
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
    wf_root = os.path.join(repo_dir, ".workflow") if os.path.basename(repo_dir) != ".workflow" else repo_dir
    worktree_dir = os.path.join(wf_root, "worktrees", name)

    # 1. Attempt standard git worktree remove with --force
    run_git(["worktree", "remove", "--force", worktree_dir], cwd=repo_dir)
    prune_worktrees(repo_dir)

    # 2. Check for leftover disk directory and forcefully wipe if necessary
    if os.path.exists(worktree_dir):
        try:
            shutil.rmtree(worktree_dir, ignore_errors=True)
        except Exception as e:
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
        wt_meta = os.path.join(git_dir, "worktrees", name)
        if os.path.exists(wt_meta):
            try:
                shutil.rmtree(wt_meta, ignore_errors=True)
            except Exception:
                pass

    prune_worktrees(repo_dir)
    return {"status": "PURGED", "worktree_path": worktree_dir}


def sync_worktree_with_base(
    worktree_path: str,
    base_branch: str = "main",
    repo_dir: str = "."
) -> Dict[str, Any]:
    """Pre-Cycle Synchronization: Safely rebases the worktree branch onto the latest base branch."""
    worktree_path = os.path.abspath(worktree_path)
    repo_dir = os.path.abspath(repo_dir)

    if not os.path.exists(worktree_path):
        return {"status": "NOT_FOUND", "worktree_path": worktree_path}

    # 1. Fetch from remotes if configured
    run_git(["fetch", "--all"], cwd=repo_dir)

    # 2. Check if base_branch exists, fallback to HEAD
    has_branch = run_git(["rev-parse", "--verify", base_branch], cwd=repo_dir)
    target_ref = base_branch if has_branch.returncode == 0 else "HEAD"

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
