"""Physical Git Worktree lifecycle manager with branch lock safety and self-healing prune."""

import os
import subprocess
import time
from typing import Dict, Any, List, Optional


def run_git(args: List[str], cwd: str = ".") -> subprocess.CompletedProcess:
    """Executes a git command and returns CompletedProcess."""
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def list_worktrees(repo_dir: str = ".") -> List[Dict[str, str]]:
    """Lists all active git worktrees."""
    res = run_git(["worktree", "list", "--porcelain"], cwd=repo_dir)
    if res.returncode != 0:
        return []

    worktrees: List[Dict[str, str]] = []
    current: Dict[str, str] = {}

    for line in res.stdout.splitlines():
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": line.replace("worktree ", "").strip()}
        elif line.startswith("HEAD "):
            current["head"] = line.replace("HEAD ", "").strip()
        elif line.startswith("branch "):
            current["branch"] = line.replace("branch ", "").strip()
        elif line == "bare":
            current["bare"] = "true"

    if current:
        worktrees.append(current)

    return worktrees


def create_worktree(
    name: str,
    base_branch: str = "HEAD",
    repo_dir: str = "."
) -> Dict[str, Any]:
    """Creates a physical git worktree under .worktrees/<name> with an isolated branch."""
    repo_dir = os.path.abspath(repo_dir)
    worktree_dir = os.path.join(repo_dir, ".worktrees", name)
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
    worktree_dir = os.path.join(repo_dir, ".worktrees", name)

    args = ["worktree", "remove", worktree_dir]
    if force:
        args.append("--force")

    res = run_git(args, cwd=repo_dir)
    prune_worktrees(repo_dir)

    if res.returncode != 0 and os.path.exists(worktree_dir):
        return {"status": "ERROR", "error": res.stderr.strip()}

    return {"status": "REMOVED", "worktree_path": worktree_dir}


def prune_worktrees(repo_dir: str = ".") -> bool:
    """Self-healing prune of stale worktree entries."""
    res = run_git(["worktree", "prune"], cwd=repo_dir)
    return res.returncode == 0
