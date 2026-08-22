"""Self-contained Git & GitHub Operations Engine for the Workflow Suite.
Provides pre-commit security gates, Conventional Commits validation, atomic commits, and GitHub PR automation.
"""

import os
import re
import subprocess
import shutil
import sys
import json
import argparse
from typing import Dict, Any, List, Optional, Tuple


# Security gate regexes
SECRET_PATTERNS = [
    (r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "Private key"),
    (r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}", "GitHub Token"),
    (r"eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*", "JWT Token"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
    (r"(?:sk_live|rk_live)_[0-9a-zA-Z]{24,}", "Stripe Secret Key"),
]

SENSITIVE_FILENAME_PATTERNS = [
    r"^\.env(?:\..+)?$",
    r"^.*\.pem$",
    r"^.*\.key$",
    r"^.*\.p12$",
    r"^.*\.pfx$",
    r"^id_rsa(?:\.pub)?$",
    r"^id_ed25519(?:\.pub)?$",
]

CONFLICT_MARKER_PATTERNS = [
    r"^<<<<<<< ",
    r"^=======$",
    r"^>>>>>>> ",
]

APPROVED_COMMIT_TYPES = ["feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore", "revert"]


def run_git_cmd(args: List[str], cwd: str = ".") -> Tuple[int, str, str]:
    """Runs a git command safely in the specified directory."""
    try:
        res = subprocess.run(
            ["git"] + args,
            cwd=os.path.abspath(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def run_gh_cmd(args: List[str], cwd: str = ".") -> Tuple[int, str, str]:
    """Runs a GitHub CLI (gh) command safely."""
    try:
        res = subprocess.run(
            ["gh"] + args,
            cwd=os.path.abspath(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def scan_pre_commit_security(target_dir: str = ".") -> Dict[str, Any]:
    """Scans staged files and diffs for secrets, sensitive files, and conflict markers."""
    target_dir = os.path.abspath(target_dir)
    violations = []

    # 1. Check staged files
    code, stdout, _ = run_git_cmd(["diff", "--cached", "--name-only"], cwd=target_dir)
    staged_files = stdout.splitlines() if stdout else []

    if not staged_files:
        # Fallback to checking unstaged/working tree diffs if nothing staged yet
        code, stdout, _ = run_git_cmd(["status", "--porcelain"], cwd=target_dir)
        staged_files = [line[3:].strip() for line in stdout.splitlines() if line.strip()]

    # 2. Check for sensitive files
    for filepath in staged_files:
        filename = os.path.basename(filepath)
        for pattern in SENSITIVE_FILENAME_PATTERNS:
            if re.match(pattern, filename, re.IGNORECASE):
                violations.append({
                    "type": "SENSITIVE_FILE",
                    "file": filepath,
                    "detail": f"Sensitive file matching pattern '{pattern}' must not be committed.",
                })

    # 3. Check diff content for secrets and conflict markers
    code, diff_out, _ = run_git_cmd(["diff", "HEAD"], cwd=target_dir)
    if not diff_out:
        code, diff_out, _ = run_git_cmd(["diff", "--cached"], cwd=target_dir)

    for line in diff_out.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            content = line[1:]
            for secret_re, secret_name in SECRET_PATTERNS:
                if re.search(secret_re, content):
                    violations.append({
                        "type": "SECRET_DETECTED",
                        "detail": f"Detected potential {secret_name} in diff.",
                    })
            for conflict_re in CONFLICT_MARKER_PATTERNS:
                if re.search(conflict_re, content):
                    violations.append({
                        "type": "CONFLICT_MARKER",
                        "detail": "Unresolved git merge conflict marker detected.",
                    })

    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "files_scanned": len(staged_files),
    }


def format_conventional_commit(
    commit_type: str,
    scope: Optional[str],
    message: str,
    body_bullets: Optional[List[str]] = None,
    breaking: bool = False,
) -> Tuple[bool, str, List[str]]:
    """Validates and formats a Conventional Commit message."""
    errors = []
    clean_type = commit_type.strip().lower()
    if clean_type not in APPROVED_COMMIT_TYPES:
        errors.append(f"Invalid commit type '{commit_type}'. Allowed: {', '.join(APPROVED_COMMIT_TYPES)}")

    clean_scope = scope.strip().lower() if scope else ""
    if clean_scope and not re.match(r"^[a-z0-9_-]+$", clean_scope):
        errors.append(f"Scope '{scope}' must be lowercase alphanumeric with hyphens/underscores.")

    clean_msg = message.strip()
    if clean_msg.endswith("."):
        clean_msg = clean_msg[:-1].strip()
    if len(clean_msg) < 5:
        errors.append("Commit description must be at least 5 characters.")

    breaking_marker = "!" if breaking else ""
    if clean_scope:
        header = f"{clean_type}({clean_scope}){breaking_marker}: {clean_msg}"
    else:
        header = f"{clean_type}{breaking_marker}: {clean_msg}"

    if len(header) > 120:
        errors.append(f"Commit header length ({len(header)}) exceeds 120 character limit.")

    full_message = header
    if body_bullets:
        clean_bullets = []
        for bullet in body_bullets:
            b = bullet.strip()
            if not b.startswith("- "):
                b = f"- {b}"
            clean_bullets.append(b)
        full_message += "\n\n" + "\n".join(clean_bullets)

    return len(errors) == 0, full_message, errors


def squash_stage_checkpoints(
    target_dir: str,
    base_branch: Optional[str] = None,
    scope: Optional[str] = None,
) -> Dict[str, Any]:
    """Squashes intermediate workflow checkpoint commits (chore(workflow-checkpoint): ...) into a clean staged index."""
    target_dir = os.path.abspath(target_dir)

    # 1. Inspect recent git log for checkpoint commits
    code, log_out, _ = run_git_cmd(["log", "-n", "50", "--format=%H %s"], cwd=target_dir)
    if code != 0 or not log_out.strip():
        return {"status": "NO_COMMITS", "squashed": False, "checkpoint_count": 0}

    checkpoint_shas = []
    for line in log_out.strip().split("\n"):
        parts = line.split(" ", 1)
        if len(parts) == 2:
            sha, msg = parts[0], parts[1]
            if "chore(workflow-checkpoint)" in msg or "workflow-checkpoint" in msg:
                checkpoint_shas.append(sha)

    if not checkpoint_shas:
        return {"status": "NO_CHECKPOINTS", "squashed": False, "checkpoint_count": 0}

    # 2. Determine base branch / merge base
    candidate_bases = []
    if base_branch:
        candidate_bases.append(base_branch)
    if scope:
        clean_s = re.sub(r"[^a-zA-Z0-9_.-]+", "-", scope.rstrip("/\\")).strip("-._").lower()
        candidate_bases.extend([f"feat/{clean_s}", clean_s])
    candidate_bases.extend(["main", "master"])

    target_merge_base = None
    for cand in candidate_bases:
        c_code, _, _ = run_git_cmd(["rev-parse", "--verify", f"refs/heads/{cand}"], cwd=target_dir)
        if c_code == 0:
            mb_code, mb_out, _ = run_git_cmd(["merge-base", cand, "HEAD"], cwd=target_dir)
            if mb_code == 0 and mb_out.strip():
                target_merge_base = mb_out.strip()
                break

    # Fallback: if no base branch found, reset to the parent of the oldest checkpoint
    if not target_merge_base:
        oldest_ckpt = checkpoint_shas[-1]
        p_code, p_out, _ = run_git_cmd(["rev-parse", f"{oldest_ckpt}^"], cwd=target_dir)
        if p_code == 0 and p_out.strip():
            target_merge_base = p_out.strip()

    if not target_merge_base:
        return {"status": "BASE_NOT_FOUND", "squashed": False, "checkpoint_count": 0}

    # Check current HEAD
    _, curr_head, _ = run_git_cmd(["rev-parse", "HEAD"], cwd=target_dir)
    if curr_head.strip() == target_merge_base:
        return {"status": "ALREADY_AT_BASE", "squashed": False, "checkpoint_count": 0}

    # Stage any current uncommitted files first
    run_git_cmd(["add", "-A"], cwd=target_dir)

    # Soft reset to merge base
    res_code, _, res_err = run_git_cmd(["reset", "--soft", target_merge_base], cwd=target_dir)
    if res_code != 0:
        return {"status": "RESET_ERROR", "message": res_err, "squashed": False, "checkpoint_count": 0}

    # Re-stage all changes
    run_git_cmd(["add", "-A"], cwd=target_dir)

    return {
        "status": "SQUASHED",
        "squashed": True,
        "checkpoint_count": len(checkpoint_shas),
        "target_merge_base": target_merge_base,
        "message": f"Successfully squashed {len(checkpoint_shas)} intermediate checkpoint commits to base {target_merge_base[:8]}.",
    }


def execute_atomic_commit(
    commit_type: str,
    scope: Optional[str],
    message: str,
    body_bullets: Optional[List[str]] = None,
    target_dir: str = ".",
    add_all: bool = True,
    squash_checkpoints: bool = True,
    base_branch: Optional[str] = None,
) -> Dict[str, Any]:
    """Executes a security scan, squashes intermediate checkpoint commits, stages changes, and creates a Conventional Commit."""
    target_dir = os.path.abspath(target_dir)

    # 1. Pre-commit security check
    sec_report = scan_pre_commit_security(target_dir)
    if not sec_report["passed"]:
        return {
            "status": "SECURITY_BLOCK",
            "message": "Pre-commit security gate failed. Refusing to commit.",
            "violations": sec_report["violations"],
        }

    # 2. Validate commit message format
    valid, full_msg, errors = format_conventional_commit(commit_type, scope, message, body_bullets)
    if not valid:
        return {
            "status": "VALIDATION_ERROR",
            "message": "Conventional Commit format validation failed.",
            "errors": errors,
        }

    # 3. Squash intermediate workflow checkpoint commits into clean staged index
    squash_res = {"squashed": False, "checkpoint_count": 0}
    if squash_checkpoints:
        squash_res = squash_stage_checkpoints(target_dir, base_branch=base_branch, scope=scope)

    # 4. Self-healing: Revert any accidental skill self-modifications in .agents/
    code, status_agents, _ = run_git_cmd(["status", "--porcelain", "--", ".agents"], cwd=target_dir)
    if status_agents.strip():
        run_git_cmd(["checkout", "HEAD", "--", ".agents"], cwd=target_dir)
        run_git_cmd(["clean", "-fd", "--", ".agents"], cwd=target_dir)

    # 5. Stage changes
    if add_all:
        code, _, err = run_git_cmd(["add", "-A"], cwd=target_dir)
        if code != 0:
            return {"status": "GIT_ERROR", "message": f"Failed to stage changes: {err}"}

    # 6. Check if there are changes to commit
    code, status_out, _ = run_git_cmd(["status", "--porcelain"], cwd=target_dir)
    if not status_out.strip():
        return {"status": "NO_CHANGES", "message": "No staged changes to commit."}

    # 6. Commit
    code, commit_out, commit_err = run_git_cmd(["commit", "-m", full_msg], cwd=target_dir)
    if code != 0:
        return {"status": "GIT_ERROR", "message": f"Commit failed: {commit_err}"}

    # 7. Retrieve commit SHA
    code, sha, _ = run_git_cmd(["rev-parse", "HEAD"], cwd=target_dir)

    return {
        "status": "SUCCESS",
        "commit_sha": sha,
        "commit_header": full_msg.split("\n")[0],
        "full_message": full_msg,
        "squashed_checkpoints": squash_res.get("checkpoint_count", 0),
        "target_dir": target_dir,
    }


def check_gh_readiness(target_dir: str = ".") -> Dict[str, Any]:
    """Validates if GitHub CLI ('gh') is installed, authenticated, and has a configured remote origin."""
    target_dir = os.path.abspath(target_dir)

    # 1. Check if gh CLI is installed
    gh_bin = shutil.which("gh")
    if not gh_bin:
        return {
            "installed": False,
            "authenticated": False,
            "has_remote_origin": False,
            "ready": False,
            "status": "GH_CLI_MISSING",
            "message": "GitHub CLI ('gh') is not installed in system PATH. Install 'gh' or create PR via web/git merge.",
        }

    # 2. Check if git remote origin is configured
    code, remotes_out, _ = run_git_cmd(["remote"], cwd=target_dir)
    has_origin = "origin" in remotes_out.split()
    if not has_origin:
        return {
            "installed": True,
            "authenticated": False,
            "has_remote_origin": False,
            "ready": False,
            "status": "REMOTE_ORIGIN_MISSING",
            "message": "Git remote 'origin' is not configured. Add a remote origin with 'git remote add origin <url>'.",
        }

    # 3. Check if gh is authenticated
    code, auth_out, auth_err = run_gh_cmd(["auth", "status"], cwd=target_dir)
    if code != 0:
        return {
            "installed": True,
            "authenticated": False,
            "has_remote_origin": True,
            "ready": False,
            "status": "GH_NOT_AUTHENTICATED",
            "message": "GitHub CLI ('gh') is not authenticated. Run 'gh auth login' before automated PR creation.",
        }

    return {
        "installed": True,
        "authenticated": True,
        "has_remote_origin": True,
        "ready": True,
        "status": "READY",
        "message": "GitHub CLI ('gh') is installed, authenticated, and ready for automated PR creation.",
    }


def create_github_pull_request(
    head_branch: str,
    base_branch: str,
    title: str,
    body_file: Optional[str] = None,
    body_text: Optional[str] = None,
    target_dir: str = ".",
    push_before_pr: bool = True,
) -> Dict[str, Any]:
    """Creates a Pull Request on GitHub using the gh CLI with structured body after full validation."""
    target_dir = os.path.abspath(target_dir)

    # 1. Full validation of gh CLI, auth status, and remote origin
    readiness = check_gh_readiness(target_dir)
    if not readiness["ready"]:
        return {
            "status": readiness["status"],
            "ready": False,
            "message": readiness["message"],
            "head_branch": head_branch,
            "base_branch": base_branch,
        }

    # 2. Push branch if requested
    if push_before_pr:
        if base_branch not in ("main", "master"):
            run_git_cmd(["push", "-u", "origin", base_branch], cwd=target_dir)

        code, _, push_err = run_git_cmd(["push", "-u", "origin", head_branch], cwd=target_dir)
        if code != 0:
            return {
                "status": "PUSH_FAILED",
                "ready": False,
                "message": f"Failed to push branch '{head_branch}' to origin: {push_err}",
            }

    # 3. Build gh pr create args
    args = ["pr", "create", "--head", head_branch, "--base", base_branch, "--title", title]
    if body_file and os.path.exists(body_file):
        args.extend(["--body-file", os.path.abspath(body_file)])
    elif body_text:
        args.extend(["--body", body_text])
    else:
        args.extend(["--body", f"Automated pull request from `{head_branch}` into `{base_branch}`."])

    code, pr_out, pr_err = run_gh_cmd(args, cwd=target_dir)
    if code != 0:
        # Check if PR already exists on GitHub for this branch pair
        if "already exists" in pr_err.lower():
            v_code, v_out, _ = run_gh_cmd(["pr", "view", head_branch, "--json", "url", "-q", ".url"], cwd=target_dir)
            existing_url = v_out.strip() if v_code == 0 and v_out.strip() else None

            if existing_url:
                edit_args = ["pr", "edit", head_branch, "--title", title]
                if body_file and os.path.exists(body_file):
                    edit_args.extend(["--body-file", os.path.abspath(body_file)])
                elif body_text:
                    edit_args.extend(["--body", body_text])
                run_gh_cmd(edit_args, cwd=target_dir)

                return {
                    "status": "PR_UPDATED",
                    "ready": True,
                    "pr_url": existing_url,
                    "head_branch": head_branch,
                    "base_branch": base_branch,
                    "title": title,
                    "message": f"Updated existing Pull Request with latest pipeline delivery: {existing_url}",
                }

        return {
            "status": "PR_ERROR",
            "ready": False,
            "message": f"Failed to create PR: {pr_err}",
        }

    pr_url = pr_out.strip()
    return {
        "status": "SUCCESS",
        "ready": True,
        "pr_url": pr_url,
        "head_branch": head_branch,
        "base_branch": base_branch,
        "title": title,
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="git_ops.py", description="Deterministic Git & GitHub Operations Engine")
    parser.add_argument("--json", action="store_true", help="JSON output")
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommands")

    # commit
    p_commit = subparsers.add_parser("commit", help="Execute deterministic atomic commit with security gates and checkpoint squashing")
    p_commit.add_argument("-t", "--type", default="feat", help="Commit type")
    p_commit.add_argument("-s", "--scope", help="Commit scope / spec name")
    p_commit.add_argument("-m", "--message", required=True, help="Imperative commit message")
    p_commit.add_argument("-b", "--bullets", help="Newline-separated bullet summary")
    p_commit.add_argument("--base-branch", help="Base branch name for calculating merge base during checkpoint squashing")
    p_commit.add_argument("--no-squash", action="store_true", default=False, help="Do not squash intermediate workflow checkpoints")
    p_commit.add_argument("--target-dir", default=".", help="Target working directory")

    # pr
    p_pr = subparsers.add_parser("pr", help="Create GitHub Pull Request via gh CLI")
    p_pr.add_argument("--head", required=True, help="Head branch name")
    p_pr.add_argument("--base", default="main", help="Base branch name")
    p_pr.add_argument("--title", required=True, help="Pull Request title")
    p_pr.add_argument("--body-file", help="Path to markdown body file")
    p_pr.add_argument("--body", help="Pull request body text")
    p_pr.add_argument("--push", action="store_true", default=False, help="Push head branch before opening PR")
    p_pr.add_argument("--target-dir", default=".", help="Target directory")

    args = parser.parse_args()
    if not args.subcommand:
        parser.print_help()
        return 0

    if args.subcommand == "commit":
        bullets = None
        if getattr(args, "bullets", None):
            bullets = [b.strip() for b in args.bullets.split("\n") if b.strip()]
        res = execute_atomic_commit(
            commit_type=args.type,
            scope=args.scope,
            message=args.message,
            body_bullets=bullets,
            target_dir=args.target_dir,
            squash_checkpoints=not getattr(args, "no_squash", False),
            base_branch=getattr(args, "base_branch", None),
        )
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            if res.get("status") == "SUCCESS":
                sq_info = f" (Squashed {res.get('squashed_checkpoints')} intermediate checkpoints)" if res.get('squashed_checkpoints') else ""
                print(f"✅ Commit Created: {res.get('commit_sha')} ({res.get('commit_header')}){sq_info}")
            else:
                print(f"❌ Commit Failed: {res.get('message')}")
        return 0 if res.get("status") == "SUCCESS" else 1

    elif args.subcommand == "pr":
        res = create_github_pull_request(
            head_branch=args.head,
            base_branch=args.base,
            title=args.title,
            body_file=args.body_file,
            body_text=getattr(args, "body", None),
            target_dir=args.target_dir,
            push_before_pr=args.push,
        )
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            if res.get("status") == "SUCCESS":
                print(f"🚀 Pull Request Created: {res.get('pr_url')}")
            else:
                print(f"❌ PR Creation Failed: {res.get('message')}")
        return 0 if res.get("status") == "SUCCESS" else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

