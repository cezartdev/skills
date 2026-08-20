"""Self-contained Git & GitHub Operations Engine for the Workflow Suite.
Provides pre-commit security gates, Conventional Commits validation, atomic commits, and GitHub PR automation.
"""

import os
import re
import subprocess
import shutil
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


def execute_atomic_commit(
    commit_type: str,
    scope: Optional[str],
    message: str,
    body_bullets: Optional[List[str]] = None,
    target_dir: str = ".",
    add_all: bool = True,
) -> Dict[str, Any]:
    """Executes a security scan, stages changes, and creates a Conventional Commit."""
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

    # 3. Stage changes
    if add_all:
        code, _, err = run_git_cmd(["add", "-A"], cwd=target_dir)
        if code != 0:
            return {"status": "GIT_ERROR", "message": f"Failed to stage changes: {err}"}

    # 4. Check if there are changes to commit
    code, status_out, _ = run_git_cmd(["status", "--porcelain"], cwd=target_dir)
    if not status_out.strip():
        return {"status": "NO_CHANGES", "message": "No staged changes to commit."}

    # 5. Commit
    code, commit_out, commit_err = run_git_cmd(["commit", "-m", full_msg], cwd=target_dir)
    if code != 0:
        return {"status": "GIT_ERROR", "message": f"Commit failed: {commit_err}"}

    # 6. Retrieve commit SHA
    code, sha, _ = run_git_cmd(["rev-parse", "HEAD"], cwd=target_dir)

    return {
        "status": "SUCCESS",
        "commit_sha": sha,
        "commit_header": full_msg.split("\n")[0],
        "full_message": full_msg,
        "target_dir": target_dir,
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
    """Creates a Pull Request on GitHub using the gh CLI with structured body."""
    target_dir = os.path.abspath(target_dir)

    # 1. Verify gh CLI is available
    if not shutil.which("gh"):
        return {
            "status": "GH_CLI_MISSING",
            "message": "GitHub CLI ('gh') is not installed. Please install 'gh' or open PR manually.",
        }

    # 2. Push branch if requested
    if push_before_pr:
        code, _, push_err = run_git_cmd(["push", "-u", "origin", head_branch], cwd=target_dir)
        if code != 0:
            return {
                "status": "PUSH_FAILED",
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
        return {
            "status": "PR_ERROR",
            "message": f"Failed to create PR: {pr_err}",
        }

    pr_url = pr_out.strip()
    return {
        "status": "SUCCESS",
        "pr_url": pr_url,
        "head_branch": head_branch,
        "base_branch": base_branch,
        "title": title,
    }
