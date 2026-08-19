"""Deterministic self-contained Commit Validator & Safe Executor for Workflow Suite.

Provides pre-commit security gates, secret/sensitive file blockers, conflict marker scanners,
and Conventional Commits validation without external dependencies.
"""

import os
import re
import subprocess
from typing import Dict, Any, List, Optional, Tuple

ALLOWED_TYPES = {"feat", "fix", "docs", "refactor", "chore", "test"}

COMMON_IMPERATIVE_VERBS = {
    "add", "adjust", "align", "allow", "apply", "author", "bump", "clarify",
    "clean", "configure", "consolidate", "correct", "create", "decouple",
    "define", "deprecate", "disable", "document", "downgrade", "enable",
    "enforce", "ensure", "expand", "expose", "extract", "fix", "format",
    "handle", "implement", "improve", "include", "init", "initialize",
    "integrate", "introduce", "migrate", "optimize", "organize", "patch",
    "prevent", "publish", "refactor", "release", "remove", "rename",
    "reorganize", "resolve", "revert", "revise", "rewrite", "set", "setup",
    "simplify", "split", "standardize", "streamline", "structure", "support",
    "sync", "synchronize", "test", "update", "upgrade", "validate", "verify",
    "record", "scope", "curate", "scaffold"
}

SENSITIVE_FILE_PATTERNS = [
    r"^\.env(\..+)?$",
    r".*\.pem$",
    r".*\.key$",
    r".*\.pfx$",
    r".*\.p12$",
    r".*\.keystore$",
    r"^id_rsa(\.pub)?$",
    r"^id_ed25519(\.pub)?$",
    r".*credential.*\.json$",
    r".*service-account.*\.json$",
    r".*client_secret.*\.json$",
    r".*\.sqlite$",
    r".*\.db$",
]

SECRET_CONTENT_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
    (r"(?i)aws_secret_access_key\s*=\s*[A-Za-z0-9/+=]{40}", "AWS Secret Key"),
    (r"gh[pousr]_[A-Za-z0-9_]{36,}", "GitHub Token"),
    (r"xox[baprs]-[0-9]{12}-[0-9]{12}-[A-Za-z0-9]{24,}", "Slack Token"),
    (r"-----BEGIN\s+(RSA|EC|DSA|OPENSSH|PGP)?\s*PRIVATE KEY-----", "Private Key Block"),
]

CONFLICT_MARKER_REGEX = re.compile(r"^(<{7}|={7}|>{7})(\s|$)", re.MULTILINE)


def run_git_cmd(args: List[str], cwd: str) -> subprocess.CompletedProcess:
    """Executes a git command in the target directory."""
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False
    )


def scan_pre_commit_security(repo_dir: str) -> Tuple[bool, List[str]]:
    """Scans staged files for sensitive filenames, secret patterns, and conflict markers."""
    repo_dir = os.path.abspath(repo_dir)
    errors: List[str] = []

    res = run_git_cmd(["diff", "--cached", "--name-only"], cwd=repo_dir)
    if res.returncode != 0:
        return False, [f"Git error checking staged files: {res.stderr.strip()}"]

    staged_files = [f.strip() for f in res.stdout.splitlines() if f.strip()]
    if not staged_files:
        return True, []

    for fpath in staged_files:
        fname = os.path.basename(fpath)
        for pattern in SENSITIVE_FILE_PATTERNS:
            if re.match(pattern, fname, re.IGNORECASE):
                errors.append(f"Blocked sensitive file staged for commit: '{fpath}'")

        diff_res = run_git_cmd(["diff", "--cached", "--", fpath], cwd=repo_dir)
        if diff_res.returncode == 0:
            diff_text = diff_res.stdout
            if CONFLICT_MARKER_REGEX.search(diff_text):
                errors.append(f"Unresolved merge conflict markers detected in: '{fpath}'")

            for secret_re, label in SECRET_CONTENT_PATTERNS:
                if re.search(secret_re, diff_text):
                    errors.append(f"High-entropy secret pattern ({label}) detected in staged diff: '{fpath}'")

    return (len(errors) == 0), errors


def validate_commit_message(
    ctype: str,
    scope: Optional[str],
    description: str,
    body_bullets: Optional[List[str]] = None
) -> Tuple[bool, List[str]]:
    """Validates Conventional Commits rules strictly in Python."""
    errors: List[str] = []

    if ctype not in ALLOWED_TYPES:
        errors.append(f"Invalid commit type '{ctype}'. Allowed: {sorted(ALLOWED_TYPES)}")

    if scope:
        if not re.match(r"^[a-z0-9_.-]+$", scope):
            errors.append(f"Invalid scope '{scope}'. Must be kebab-case/alphanumeric.")

    clean_desc = description.strip()
    if len(clean_desc) < 5:
        errors.append(f"Description too short: '{clean_desc}' (minimum 5 chars required).")
    if clean_desc.endswith("."):
        errors.append("Commit description MUST NOT end with a period '.'.")

    # Verify imperative verb in description
    first_word = clean_desc.split()[0].lower() if clean_desc else ""
    if first_word and first_word not in COMMON_IMPERATIVE_VERBS:
        # Check forbidden suffixes (ed, ing)
        if first_word.endswith(("ed", "ing")):
            errors.append(f"Use present imperative verb (e.g. 'fix', 'add', 'update') instead of '{first_word}'.")

    # Header length constraint
    scope_part = f"({scope})" if scope else ""
    header = f"{ctype}{scope_part}: {clean_desc}"
    if len(header) > 120:
        errors.append(f"Commit header too long ({len(header)}/120 chars).")

    return (len(errors) == 0), errors


def safe_atomic_commit(
    repo_dir: str,
    ctype: str,
    scope: Optional[str],
    description: str,
    body_bullets: Optional[List[str]] = None,
    allow_empty: bool = False,
) -> Dict[str, Any]:
    """Executes a fully validated, atomic Conventional Commit inside target repository/worktree."""
    repo_dir = os.path.abspath(repo_dir)

    # 1. Security Scan
    sec_pass, sec_errors = scan_pre_commit_security(repo_dir)
    if not sec_pass:
        return {
            "status": "SECURITY_VIOLATION",
            "errors": sec_errors,
            "committed": False,
        }

    # 2. Message Validation
    msg_pass, msg_errors = validate_commit_message(ctype, scope, description, body_bullets)
    if not msg_pass:
        return {
            "status": "VALIDATION_FAILED",
            "errors": msg_errors,
            "committed": False,
        }

    # 3. Assemble commit message
    scope_str = f"({scope})" if scope else ""
    header = f"{ctype}{scope_str}: {description.strip()}"
    full_message = header

    if body_bullets:
        bullet_text = "\n".join(b if b.startswith("- ") else f"- {b}" for b in body_bullets)
        full_message = f"{header}\n\n{bullet_text}"

    # 4. Check if there are staged changes
    status_res = run_git_cmd(["status", "--porcelain"], cwd=repo_dir)
    if not status_res.stdout.strip() and not allow_empty:
        return {
            "status": "NOTHING_TO_COMMIT",
            "committed": False,
            "message": "Working tree is clean; no changes staged for commit.",
        }

    # Stage all in worktree
    run_git_cmd(["add", "-A"], cwd=repo_dir)

    commit_args = ["commit", "-m", full_message]
    if allow_empty:
        commit_args.append("--allow-empty")

    commit_res = run_git_cmd(commit_args, cwd=repo_dir)
    if commit_res.returncode != 0:
        return {
            "status": "COMMIT_FAILED",
            "committed": False,
            "error": commit_res.stderr.strip() or commit_res.stdout.strip(),
        }

    rev_res = run_git_cmd(["rev-parse", "HEAD"], cwd=repo_dir)
    commit_sha = rev_res.stdout.strip()

    return {
        "status": "SUCCESS",
        "committed": True,
        "commit_sha": commit_sha,
        "header": header,
        "message": full_message,
    }
