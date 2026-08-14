#!/usr/bin/env python3
"""
git_helper.py - Deterministic Git Suite runner for AI agents and human developers.

Subcommands:
- commit     : Pre-flight security scan + 10-step message validation + safe atomic commit
- sync       : Commit + safe push to remote upstream branch
- status     : Smart working tree summary, unpushed commits, and inferred scopes
- branch     : Standardized branch creation with conventional prefixes
- undo       : Safe soft reset of last commit (preserves working directory)
- audit      : Audit past N commits for Conventional Commits compliance & suggested rewrites
- validate   : Pre-flight commit message validator
- draft      : Inspects staged changes, security status, and suggests commit scopes
- check-env  : Cross-platform diagnostic (Python, Git, Author config, uv runner)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from typing import List, Tuple, Dict, Any, Optional

# ==============================================================================
# Constants & Rules
# ==============================================================================

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
}

FORBIDDEN_VERB_SUFFIXES = ("ed", "ing", "es", "s")

# Files that should never be accidentally committed
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

# Patterns in diff content additions
SECRET_CONTENT_PATTERNS = [
    (r"-----BEGIN (RSA|EC|OPENSSH|PGP|DSA)? PRIVATE KEY-----", "Private cryptographic key block"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
    (r"(?:api_key|access_token|secret_key|private_token|auth_token)\s*=\s*['\"][a-zA-Z0-9_\-]{20,}['\"]", "Generic API secret/token assignment"),
]

CONFLICT_MARKER_PATTERNS = [
    r"^<<<<<<< ",
    r"^=======$",
    r"^>>>>>>> ",
]

LARGE_FILE_THRESHOLD_BYTES = 10 * 1024 * 1024  # 10 MB
LARGE_BINARY_EXTENSIONS = {".zip", ".tar.gz", ".tgz", ".rar", ".7z", ".iso", ".bin", ".exe", ".dmg"}


# ==============================================================================
# Cross-Platform UTF-8 & Git Execution Utilities
# ==============================================================================

def setup_terminal_encoding() -> None:
    """Configures UTF-8 encoding for standard streams across Linux, macOS, and Windows."""
    if sys.platform == "win32":
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        if hasattr(sys.stderr, "reconfigure"):
            try:
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def run_git_command(cmd_args: List[str]) -> Tuple[int, str, str]:
    """
    Executes a git command cross-platform with UTF-8 encoding.
    Returns (exit_code, stdout, stderr).
    """
    try:
        proc = subprocess.run(
            ["git"] + cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        err_msg = (
            "Git executable ('git') was not found in your system PATH.\n"
            "Installation instructions:\n"
            "  - Windows: Run 'winget install -e --id Git.Git' or download from https://git-scm.com/\n"
            "  - Linux (Fedora): Run 'sudo dnf install git'\n"
            "  - Linux (Ubuntu/Debian): Run 'sudo apt update && sudo apt install git'\n"
            "  - macOS: Run 'brew install git'"
        )
        return 127, "", err_msg
    except Exception as e:
        return 1, "", f"Unexpected error executing git: {e}"


# ==============================================================================
# Tier 1: Security & Hygiene Gates
# ==============================================================================

def scan_sensitive_files(file_list: List[str]) -> List[Dict[str, str]]:
    """Checks if any staged file matches sensitive file patterns."""
    violations = []
    for filepath in file_list:
        filename = os.path.basename(filepath)
        for pattern in SENSITIVE_FILE_PATTERNS:
            if re.match(pattern, filename, re.IGNORECASE) or re.match(pattern, filepath, re.IGNORECASE):
                violations.append({
                    "file": filepath,
                    "reason": f"Matches sensitive file pattern '{pattern}'"
                })
                break
    return violations


def scan_staged_content_secrets() -> List[Dict[str, str]]:
    """Scans added lines in staged diff for secret keys, tokens, and credentials."""
    code, diff_out, _ = run_git_command(["diff", "--cached", "-U0"])
    if code != 0 or not diff_out:
        return []

    violations = []
    current_file = "unknown"

    for line in diff_out.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
            continue

        if line.startswith("+") and not line.startswith("+++"):
            added_content = line[1:]
            for pattern, description in SECRET_CONTENT_PATTERNS:
                if re.search(pattern, added_content):
                    violations.append({
                        "file": current_file,
                        "reason": f"Detected potential secret: {description}"
                    })
                    break
    return violations


def scan_conflict_markers() -> List[Dict[str, str]]:
    """Scans added lines in staged diff for unresolved merge conflict markers."""
    code, diff_out, _ = run_git_command(["diff", "--cached", "-U0"])
    if code != 0 or not diff_out:
        return []

    violations = []
    current_file = "unknown"

    for line in diff_out.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
            continue

        if line.startswith("+") and not line.startswith("+++"):
            added_content = line[1:].strip()
            for marker in CONFLICT_MARKER_PATTERNS:
                if re.match(marker, added_content):
                    violations.append({
                        "file": current_file,
                        "reason": f"Unresolved merge conflict marker detected: '{added_content}'"
                    })
                    break
    return violations


def scan_large_files(file_list: List[str]) -> List[Dict[str, str]]:
    """Checks for files exceeding size threshold or binary archives."""
    warnings = []
    for filepath in file_list:
        if not os.path.exists(filepath):
            continue
        size = os.path.getsize(filepath)
        ext = os.path.splitext(filepath)[1].lower()
        if size > LARGE_FILE_THRESHOLD_BYTES:
            mb = size / (1024 * 1024)
            warnings.append({
                "file": filepath,
                "reason": f"Large file ({mb:.1f} MB exceeds {LARGE_FILE_THRESHOLD_BYTES // (1024*1024)} MB limit)"
            })
        elif ext in LARGE_BINARY_EXTENSIONS:
            warnings.append({
                "file": filepath,
                "reason": f"Binary archive format ('{ext}')"
            })
    return warnings


def run_security_scan(staged_files: List[str]) -> Tuple[bool, Dict[str, Any]]:
    """Runs all Tier 1 security and hygiene checks on staged files."""
    sensitive_violations = scan_sensitive_files(staged_files)
    content_secrets = scan_staged_content_secrets()
    conflict_markers = scan_conflict_markers()
    large_files = scan_large_files(staged_files)

    has_errors = bool(sensitive_violations or content_secrets or conflict_markers)
    scan_report = {
        "passed": not has_errors,
        "sensitive_files": sensitive_violations,
        "content_secrets": content_secrets,
        "conflict_markers": conflict_markers,
        "large_files": large_files,
    }
    return not has_errors, scan_report


# ==============================================================================
# Tier 2: 10-Step Message Validation Gate
# ==============================================================================

def validate_structure(header: str) -> Tuple[bool, str, Dict[str, str]]:
    """Step 1: Check if header matches `<type>(<scope>): <description>` or `<type>(<scope>)!: <description>`."""
    match = re.match(r"^([a-zA-Z0-9_-]+)(?:\(([a-zA-Z0-9_-]+)\))?(!)?:\s*(.*)$", header.strip())
    if not match:
        return False, "Header does not match standard pattern: `<type>(<scope>): <description>`", {}
    
    commit_type = (match.group(1) or "").strip()
    scope = (match.group(2) or "").strip()
    is_breaking = bool(match.group(3))
    description = (match.group(4) or "").strip()
    
    if not scope:
        return False, "Scope is missing. Format must be `<type>(<scope>): <description>`", {}
    if not description:
        return False, "Description is missing after scope and colon", {}
        
    return True, f"Structure parsed successfully: type='{commit_type}', scope='{scope}'", {
        "type": commit_type,
        "scope": scope,
        "is_breaking": is_breaking,
        "description": description
    }


def validate_type(commit_type: str) -> Tuple[bool, str]:
    """Step 2: Check if commit type is strictly in the whitelist."""
    if commit_type not in ALLOWED_TYPES:
        allowed_str = ", ".join(sorted(ALLOWED_TYPES))
        return False, f"Type '{commit_type}' is invalid. Strictly allowed types: [{allowed_str}]"
    return True, f"Type '{commit_type}' is whitelisted"


def validate_scope(scope: str) -> Tuple[bool, str]:
    """Step 3: Check if scope is lowercase kebab-case / alphanumeric."""
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", scope):
        return False, f"Scope '{scope}' must be lowercase alphanumeric or kebab-case (e.g. 'git', 'workflow')"
    return True, f"Scope '{scope}' is valid kebab-case"


def validate_header_length(header: str, max_length: int = 120) -> Tuple[bool, str]:
    """Step 4: Check if total header length is <= max_length."""
    length = len(header.strip())
    if length > max_length:
        return False, f"Header length ({length} chars) exceeds maximum limit of {max_length} chars"
    return True, f"Header length ({length}/{max_length} chars) within limit"


def validate_description_length(description: str, min_length: int = 10) -> Tuple[bool, str]:
    """Step 5: Check if description is >= min_length."""
    length = len(description.strip())
    if length < min_length:
        return False, f"Description ({length} chars) is too short. Minimum required is {min_length} chars"
    return True, f"Description ({length} chars >= {min_length}) is sufficiently detailed"


def validate_no_trailing_period(header: str) -> Tuple[bool, str]:
    """Step 6: Check that the subject line does not end with a period."""
    if header.strip().endswith("."):
        return False, "Header line must not end with a period ('.')"
    return True, "No trailing period in header"


def validate_english_imperative_verb(description: str) -> Tuple[bool, str]:
    """Step 7: Check that description begins with an English imperative verb."""
    words = description.strip().split()
    if not words:
        return False, "Description is empty"
    
    first_word = words[0].lower()
    
    if first_word in COMMON_IMPERATIVE_VERBS:
        return True, f"Leading verb '{first_word}' is an approved English imperative verb"
    
    if first_word.endswith("ed") or first_word.endswith("ing"):
        return False, f"Leading word '{first_word}' appears to be past tense or gerund. Use imperative present tense (e.g., 'add', 'update', 'fix')"
    
    return False, (
        f"Leading word '{first_word}' is not a recognized English imperative verb. "
        f"Examples of valid verbs: {', '.join(sorted(list(COMMON_IMPERATIVE_VERBS)[:8]))}..."
    )


def validate_casing_and_spacing(description: str) -> Tuple[bool, str]:
    """Step 8: Check casing (lowercase start) and clean single spacing."""
    desc = description.strip()
    if not desc:
        return False, "Description is empty"
    
    first_char = desc[0]
    if first_char.isupper() and not desc.split()[0].isupper():
        return False, f"Description should start with lowercase letter: '{desc[0].lower() + desc[1:]}'"
    
    if re.search(r"\s{2,}", desc):
        return False, "Description contains multiple consecutive spaces; use single normal spaces"
    
    words = desc.split()
    if len(words) == 1 and "_" in words[0]:
        return False, f"Description '{desc}' looks like snake_case. Use standard space-separated words"
        
    return True, "Casing and spacing format are clean"


def validate_body_bullets(body_lines: List[str], max_line_length: int = 120) -> Tuple[bool, str]:
    """Step 9: Check that all non-empty body lines are bullet points (- ...) and within limits."""
    if not body_lines:
        return True, "No body lines provided (optional)"
    
    for i, line in enumerate(body_lines, 1):
        stripped = line.strip()
        if not stripped:
            continue
        if not (stripped.startswith("- ") or stripped.startswith("BREAKING CHANGE:")):
            return False, f"Body line {i} does not start with bullet '- ': '{stripped}'"
        if len(stripped) > max_line_length:
            return False, f"Body bullet {i} exceeds {max_line_length} chars ({len(stripped)} chars)"
            
    return True, f"Body bullets ({len(body_lines)} lines) formatted correctly"


def validate_breaking_change_footer(body_lines: List[str]) -> Tuple[bool, str]:
    """Step 10: Validates BREAKING CHANGE formatting if present."""
    for line in body_lines:
        if line.startswith("BREAKING CHANGE:") and len(line.replace("BREAKING CHANGE:", "").strip()) < 5:
            return False, "BREAKING CHANGE description is too short"
    return True, "Breaking change footer specification valid"


def run_full_validation(full_message: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Runs the 10-step modular validation pipeline on a commit message."""
    lines = full_message.strip().splitlines()
    if not lines:
        return False, [{
            "step": 1,
            "name": "validate_presence",
            "passed": False,
            "message": "Commit message is completely empty"
        }]
    
    header = lines[0].strip()
    body_lines = [line for line in lines[1:] if line.strip()]
    
    reports: List[Dict[str, Any]] = []
    
    # 1. Structure
    p_ok, p_msg, parsed = validate_structure(header)
    reports.append({"step": 1, "name": "validate_structure", "passed": p_ok, "message": p_msg})
    if not p_ok:
        return False, reports
    
    commit_type = parsed["type"]
    scope = parsed["scope"]
    description = parsed["description"]
    
    # 2. Type whitelist
    t_ok, t_msg = validate_type(commit_type)
    reports.append({"step": 2, "name": "validate_type", "passed": t_ok, "message": t_msg})
    
    # 3. Scope format
    s_ok, s_msg = validate_scope(scope)
    reports.append({"step": 3, "name": "validate_scope", "passed": s_ok, "message": s_msg})
    
    # 4. Header length
    hl_ok, hl_msg = validate_header_length(header, max_length=120)
    reports.append({"step": 4, "name": "validate_header_length", "passed": hl_ok, "message": hl_msg})
    
    # 5. Description length
    dl_ok, dl_msg = validate_description_length(description, min_length=10)
    reports.append({"step": 5, "name": "validate_description_length", "passed": dl_ok, "message": dl_msg})
    
    # 6. No trailing period
    np_ok, np_msg = validate_no_trailing_period(header)
    reports.append({"step": 6, "name": "validate_no_trailing_period", "passed": np_ok, "message": np_msg})
    
    # 7. English imperative verb
    ev_ok, ev_msg = validate_english_imperative_verb(description)
    reports.append({"step": 7, "name": "validate_english_imperative_verb", "passed": ev_ok, "message": ev_msg})
    
    # 8. Casing and spacing
    cs_ok, cs_msg = validate_casing_and_spacing(description)
    reports.append({"step": 8, "name": "validate_casing_and_spacing", "passed": cs_ok, "message": cs_msg})
    
    # 9. Body bullets
    bb_ok, bb_msg = validate_body_bullets(body_lines, max_line_length=120)
    reports.append({"step": 9, "name": "validate_body_bullets", "passed": bb_ok, "message": bb_msg})
    
    # 10. Breaking change
    bc_ok, bc_msg = validate_breaking_change_footer(body_lines)
    reports.append({"step": 10, "name": "validate_breaking_change", "passed": bc_ok, "message": bc_msg})
    
    all_passed = all(r["passed"] for r in reports)
    return all_passed, reports


def print_validation_report(full_message: str, all_passed: bool, reports: List[Dict[str, Any]]) -> None:
    """Prints a clear terminal report of the validation gate."""
    print("=" * 70)
    print(" COMMIT MESSAGE PRE-FLIGHT VALIDATION REPORT")
    print("=" * 70)
    print(f"Candidate Header: {full_message.splitlines()[0] if full_message else '(empty)'}")
    print("-" * 70)
    
    for r in reports:
        status = "[PASS]" if r["passed"] else "[FAIL]"
        print(f"Step {r['step']:<2}/10 {r['name']:<35} {status} : {r['message']}")
        
    print("=" * 70)
    if all_passed:
        print(">>> RESULT: 100% VALIDATED. Message is safe for git commit.")
    else:
        print(">>> RESULT: VALIDATION FAILED. Please resolve errors before committing.")
    print("=" * 70)


# ==============================================================================
# Inference Engine
# ==============================================================================

def infer_scope_and_type(files: List[str]) -> Tuple[str, str]:
    """Infers the most appropriate Conventional Commit scope and type from file paths."""
    if not files:
        return "root", "chore"

    all_docs = all(f.endswith(".md") or "docs/" in f for f in files)
    all_tests = all("test" in f or f.endswith(".spec.ts") or f.endswith(".test.js") for f in files)
    all_configs = all(f in ("package.json", "pnpm-lock.yaml", "pyproject.toml", ".gitignore") or ".github/" in f for f in files)

    if all_docs:
        inferred_type = "docs"
    elif all_tests:
        inferred_type = "test"
    elif all_configs:
        inferred_type = "chore"
    else:
        inferred_type = "feat"

    target_file = files[0]
    if "->" in target_file:
        target_file = target_file.split("->")[-1].strip()
    target_file = target_file.replace("\\", "/")

    parts = [p for p in target_file.split("/") if p]
    if "skills" in parts:
        idx = parts.index("skills")
        inferred_scope = parts[idx + 1] if len(parts) > idx + 1 else "skills"
    elif "docs" in parts:
        idx = parts.index("docs")
        inferred_scope = parts[idx + 1] if len(parts) > idx + 1 else "docs"
    elif ".changeset" in parts:
        inferred_scope = "release"
    elif ".github" in parts:
        inferred_scope = "release" if "release" in target_file else "ci"
    elif target_file in ("package.json", "pnpm-lock.yaml", "pyproject.toml"):
        inferred_scope = "deps"
    elif len(parts) > 1:
        inferred_scope = re.sub(r"[^a-z0-9-]", "-", parts[0].lower()).strip("-")
    else:
        inferred_scope = "root"

    return inferred_scope, inferred_type


# ==============================================================================
# Subcommands: draft, validate, commit, sync, status, branch, undo, audit, check-env
# ==============================================================================

def cmd_validate(message: str, as_json: bool = False) -> int:
    all_passed, reports = run_full_validation(message)
    if as_json:
        print(json.dumps({"passed": all_passed, "reports": reports}, indent=2))
    else:
        print_validation_report(message, all_passed, reports)
    return 0 if all_passed else 1


def cmd_draft(as_json: bool = False) -> int:
    """Inspects git status, security hygiene, and suggests candidate commit scopes and drafts."""
    code, stdout, stderr = run_git_command(["status", "--porcelain"])
    if code != 0:
        if as_json:
            print(json.dumps({"error": stderr, "exit_code": code}))
        else:
            print(f"Error checking git status:\n{stderr}", file=sys.stderr)
        return code

    if not stdout:
        if as_json:
            print(json.dumps({"status": "clean", "staged_files": [], "unstaged_files": []}))
        else:
            print("Working tree is completely clean. Nothing to commit.")
        return 0

    staged_files = []
    unstaged_files = []

    for line in stdout.splitlines():
        if len(line) < 3:
            continue
        index_status = line[0]
        work_status = line[1]
        filepath = line[3:].strip()
        
        if index_status in ("M", "A", "D", "R"):
            staged_files.append(filepath)
        elif work_status in ("M", "D") or index_status == "?":
            unstaged_files.append(filepath)

    sec_passed, sec_report = run_security_scan(staged_files)
    inferred_scope, inferred_type = infer_scope_and_type(staged_files or unstaged_files)

    if as_json:
        print(json.dumps({
            "staged_files": staged_files,
            "unstaged_files": unstaged_files,
            "security_scan": sec_report,
            "suggestions": {
                "inferred_scope": inferred_scope,
                "inferred_type": inferred_type,
                "template": f"{inferred_type}({inferred_scope}): <imperative_verb> <description>"
            }
        }, indent=2))
        return 0

    print("=" * 70)
    print(" GIT STATUS SUMMARY & DRAFT SUGGESTIONS")
    print("=" * 70)
    print(f"Staged files ({len(staged_files)}):")
    for f in staged_files:
        print(f"  + {f}")
    if not staged_files:
        print("  (No files currently staged. Use 'git add <files>' first)")

    print(f"\nUnstaged/Untracked files ({len(unstaged_files)}):")
    for f in unstaged_files:
        print(f"  - {f}")

    print("\n--- Security & Hygiene Pre-Scan ---")
    if sec_passed:
        print("[PASS] No sensitive files, tokens, or merge conflict markers detected.")
    else:
        print("[FAIL] Security violations found:")
        for viol in sec_report["sensitive_files"] + sec_report["content_secrets"] + sec_report["conflict_markers"]:
            print(f"  ! {viol['file']}: {viol['reason']}")

    print("\n--- Smart Suggestions ---")
    print(f"Inferred Scope: '{inferred_scope}' | Inferred Type: '{inferred_type}'")
    print(f"Template: {inferred_type}({inferred_scope}): <imperative_verb> <description (10-120 chars)>")
    print("=" * 70)
    return 0


def cmd_commit(
    commit_type: str,
    scope: str,
    description: str,
    bullets: Optional[List[str]] = None,
    raw_message: Optional[str] = None,
    as_json: bool = False
) -> int:
    """Runs security check, validation gate, and executes git commit."""
    code, status_out, stderr = run_git_command(["status", "--porcelain"])
    if code != 0:
        print(f"Error checking git status:\n{stderr}", file=sys.stderr)
        return code
        
    if not status_out:
        print("[NO CHANGES] Working tree is completely clean. No changes detected to commit. No action taken.")
        return 0
        
    code, diff_cached, stderr = run_git_command(["diff", "--cached", "--name-only"])
    if code != 0:
        print(f"Error checking staged diff:\n{stderr}", file=sys.stderr)
        return code
        
    staged_files = [f for f in diff_cached.splitlines() if f.strip()]
    if not staged_files:
        print("[NO STAGED CHANGES] Changes exist in working tree, but none are staged. Please stage files using 'git add <files>' first.")
        return 1

    sec_passed, sec_report = run_security_scan(staged_files)
    if not sec_passed:
        print("\n" + "=" * 70, file=sys.stderr)
        print(" [SECURITY ALERT] Commit Aborted Due to Security Violations", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        for v in sec_report["sensitive_files"] + sec_report["content_secrets"] + sec_report["conflict_markers"]:
            print(f"  ! {v['file']}: {v['reason']}", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        return 1

    if raw_message:
        full_message = raw_message
    else:
        header = f"{commit_type}({scope}): {description}"
        if bullets:
            bullet_str = "\n".join(f"- {b.lstrip('- ').strip()}" for b in bullets if b.strip())
            full_message = f"{header}\n\n{bullet_str}"
        else:
            full_message = header

    all_passed, reports = run_full_validation(full_message)
    if not as_json:
        print_validation_report(full_message, all_passed, reports)

    if not all_passed:
        print("ERROR: Commit aborted due to pre-flight validation failure.", file=sys.stderr)
        return 1

    if not as_json:
        print("\nExecuting git commit...")
    code, commit_out, commit_err = run_git_command(["commit", "-m", full_message])
    if code != 0:
        print(f"Git commit failed:\n{commit_err or commit_out}", file=sys.stderr)
        return code

    _, log_out, _ = run_git_command(["log", "-1", "--stat"])
    if as_json:
        print(json.dumps({"status": "committed", "message": full_message, "log": log_out}, indent=2))
    else:
        print(commit_out)
        print("\nCommit successful! Verifying latest commit:")
        print(log_out)
    return 0


def cmd_sync(
    commit_type: str,
    scope: str,
    description: str,
    bullets: Optional[List[str]] = None,
    raw_message: Optional[str] = None,
    as_json: bool = False
) -> int:
    """Executes validated commit and pushes to the current branch upstream."""
    commit_code = cmd_commit(commit_type, scope, description, bullets=bullets, raw_message=raw_message, as_json=as_json)
    if commit_code != 0:
        return commit_code

    if not as_json:
        print("\n--- Syncing to Remote Repository ---")
    code, branch_out, _ = run_git_command(["branch", "--show-current"])
    current_branch = branch_out.strip() or "HEAD"

    push_code, push_out, push_err = run_git_command(["push", "origin", current_branch])
    if push_code != 0:
        if "no upstream branch" in push_err or "set-upstream" in push_err:
            if not as_json:
                print(f"Setting upstream tracking for branch '{current_branch}'...")
            push_code, push_out, push_err = run_git_command(["push", "--set-upstream", "origin", current_branch])

    if push_code != 0:
        print(f"Git push failed:\n{push_err or push_out}", file=sys.stderr)
        return push_code

    if as_json:
        print(json.dumps({"status": "synced", "branch": current_branch, "push_output": push_out or push_err}, indent=2))
    else:
        print(f"Successfully committed and pushed to origin/{current_branch}!")
    return 0


def cmd_status(as_json: bool = False) -> int:
    """Provides an overview of working tree status, unpushed commits, and branch health."""
    _, branch_name, _ = run_git_command(["branch", "--show-current"])
    _, status_raw, _ = run_git_command(["status", "-s"])
    _, unpushed_raw, _ = run_git_command(["log", "@{u}..HEAD", "--oneline"])
    
    staged = []
    unstaged = []
    for line in (status_raw or "").splitlines():
        if len(line) < 3:
            continue
        if line[0] in ("M", "A", "D", "R"):
            staged.append(line[3:].strip())
        elif line[1] in ("M", "D") or line[0] == "?":
            unstaged.append(line[3:].strip())

    unpushed_commits = [c for c in (unpushed_raw or "").splitlines() if c.strip()]
    sec_passed, sec_report = run_security_scan(staged)

    if as_json:
        print(json.dumps({
            "branch": branch_name.strip(),
            "staged_count": len(staged),
            "staged_files": staged,
            "unstaged_count": len(unstaged),
            "unstaged_files": unstaged,
            "unpushed_count": len(unpushed_commits),
            "unpushed_commits": unpushed_commits,
            "security_passed": sec_passed
        }, indent=2))
        return 0

    print("=" * 70)
    print(f" REPOSITORY STATUS OVERVIEW (Branch: {branch_name.strip() or 'detached'})")
    print("=" * 70)
    print(f"Staged changes   : {len(staged)} files")
    for f in staged:
        print(f"  + {f}")
    print(f"Unstaged changes : {len(unstaged)} files")
    for f in unstaged:
        print(f"  - {f}")
    print(f"Unpushed commits : {len(unpushed_commits)} commits")
    for c in unpushed_commits:
        print(f"  * {c}")
    print("=" * 70)
    return 0


def cmd_branch(branch_name: str, as_json: bool = False) -> int:
    """Creates and checks out a new branch enforcing conventional prefixing (feat/, fix/, chore/, etc.)."""
    clean_name = branch_name.strip()
    valid_prefixes = ("feat/", "fix/", "chore/", "docs/", "refactor/", "test/")
    
    if not any(clean_name.startswith(p) for p in valid_prefixes):
        err_msg = f"Branch '{clean_name}' must start with one of: {', '.join(valid_prefixes)}"
        if as_json:
            print(json.dumps({"error": err_msg}))
        else:
            print(f"ERROR: {err_msg}", file=sys.stderr)
        return 1

    code, out, err = run_git_command(["checkout", "-b", clean_name])
    if code != 0:
        print(f"Branch creation failed:\n{err or out}", file=sys.stderr)
        return code

    if as_json:
        print(json.dumps({"status": "created", "branch": clean_name}))
    else:
        print(f"Created and switched to branch '{clean_name}' successfully.")
    return 0


def cmd_undo(as_json: bool = False) -> int:
    """Performs a safe soft reset of the last commit (keeps changes staged)."""
    code, log_out, err = run_git_command(["log", "-1", "--oneline"])
    if code != 0 or not log_out:
        print("No commits found to undo.", file=sys.stderr)
        return 1

    code, _, err = run_git_command(["reset", "--soft", "HEAD~1"])
    if code != 0:
        print(f"Undo failed:\n{err}", file=sys.stderr)
        return code

    if as_json:
        print(json.dumps({"status": "undone", "reverted_commit": log_out.strip()}))
    else:
        print(f"Undid commit: '{log_out.strip()}' (changes preserved in staging area).")
    return 0


def cmd_audit(limit: int = 10, as_json: bool = False) -> int:
    """Audits past N commits for Conventional Commits compliance and generates suggested rewrites."""
    code, log_raw, err = run_git_command(["log", f"-n{limit}", "--pretty=format:%h|||%s|||%b<<<END_COMMIT>>>"])
    if code != 0 or not log_raw:
        print("No commit history found to audit.", file=sys.stderr)
        return 1

    commits = []
    for raw in log_raw.split("<<<END_COMMIT>>>"):
        stripped = raw.strip()
        if not stripped:
            continue
        parts = stripped.split("|||")
        commit_hash = parts[0].strip()
        subject = parts[1].strip() if len(parts) > 1 else ""
        body = parts[2].strip() if len(parts) > 2 else ""
        commits.append({"hash": commit_hash, "subject": subject, "body": body})

    total = len(commits)
    compliant_count = 0
    audit_results = []

    for c in commits:
        full_msg = f"{c['subject']}\n\n{c['body']}".strip()
        passed, reports = run_full_validation(full_msg)
        if passed:
            compliant_count += 1
            audit_results.append({
                "hash": c["hash"],
                "subject": c["subject"],
                "passed": True,
                "issues": []
            })
        else:
            failing_issues = [r["message"] for r in reports if not r["passed"]]
            subj = c["subject"].strip()
            match = re.match(r"^([a-zA-Z0-9_-]+)(?:\(([a-zA-Z0-9_-]+)\))?(!)?:\s*(.*)$", subj)
            if match:
                raw_type = (match.group(1) or "chore").lower()
                raw_scope = (match.group(2) or "general").lower()
                raw_desc = (match.group(4) or "").strip().rstrip(".")
                t = raw_type if raw_type in ALLOWED_TYPES else "chore"
                s = raw_scope if re.match(r"^[a-z0-9-]+$", raw_scope) else "general"
                words = raw_desc.split()
                v = words[0].lower() if words else "update"
                if v not in COMMON_IMPERATIVE_VERBS:
                    v = "update"
                rest = " ".join(words[1:]) if len(words) > 1 else "components"
                suggested = f"{t}({s}): {v} {rest}"
            else:
                words = subj.split()
                v = words[0].lower() if words else "update"
                if v not in COMMON_IMPERATIVE_VERBS:
                    v = "update"
                rest = " ".join(words[1:]) if len(words) > 1 else "components"
                suggested = f"chore(general): {v} {rest.rstrip('.')}"
            
            audit_results.append({
                "hash": c["hash"],
                "subject": c["subject"],
                "passed": False,
                "issues": failing_issues,
                "suggested_rewrite": suggested
            })

    score = round((compliant_count / total) * 100, 1) if total > 0 else 100.0

    if as_json:
        print(json.dumps({
            "total_commits": total,
            "compliant_commits": compliant_count,
            "compliance_score": score,
            "audit": audit_results
        }, indent=2))
        return 0

    print("=" * 70)
    print(f" GIT COMMIT HISTORY AUDIT & COMPLIANCE REPORT (Last {total} Commits)")
    print("=" * 70)
    print(f"Analyzed: {total} commits | Compliant: {compliant_count} ({score}%) | Non-compliant: {total - compliant_count}")
    print("-" * 70)

    for item in audit_results:
        if item["passed"]:
            print(f"[PASS] {item['hash']} {item['subject']}")
        else:
            print(f"[FAIL] {item['hash']} \"{item['subject']}\"")
            for issue in item["issues"]:
                print(f"       ! {issue}")
            if "suggested_rewrite" in item:
                print(f"       >>> Suggested Rewrite: {item['suggested_rewrite']}")

    print("=" * 70)
    print(f"Overall Compliance Score: {score}/100")
    print("=" * 70)
    return 0


def cmd_check_env(as_json: bool = False) -> int:
    """Runs a complete cross-platform environment diagnostic for Linux, Windows, and macOS."""
    py_ver = sys.version_info
    py_ok = py_ver >= (3, 8)
    git_code, git_ver, git_err = run_git_command(["--version"])
    _, user_name, _ = run_git_command(["config", "user.name"])
    _, user_email, _ = run_git_command(["config", "user.email"])

    uv_detected = False
    uv_version = ""
    try:
        uv_proc = subprocess.run(["uv", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
        if uv_proc.returncode == 0:
            uv_detected = True
            uv_version = uv_proc.stdout.strip()
    except FileNotFoundError:
        pass

    all_ok = py_ok and (git_code == 0)

    if as_json:
        print(json.dumps({
            "all_ok": all_ok,
            "python": {
                "version": f"{py_ver.major}.{py_ver.minor}.{py_ver.micro}",
                "platform": sys.platform,
                "passed": py_ok
            },
            "git": {
                "installed": git_code == 0,
                "version": git_ver if git_code == 0 else "",
                "user_name": user_name,
                "user_email": user_email
            },
            "uv": {
                "installed": uv_detected,
                "version": uv_version
            }
        }, indent=2))
        return 0 if all_ok else 1

    print("=" * 70)
    print(" ENVIRONMENT DIAGNOSTIC (CROSS-PLATFORM CHECK)")
    print("=" * 70)
    print(f"Python Version : {py_ver.major}.{py_ver.minor}.{py_ver.micro} on {sys.platform} {'[PASS]' if py_ok else '[FAIL]'}")
    if not py_ok:
        print("  ! Python 3.8 or higher is required.")

    if git_code == 0:
        print(f"Git Executable : {git_ver} [PASS]")
    else:
        print("Git Executable : NOT FOUND [FAIL]")
        print(f"  ! {git_err}")

    if user_name and user_email:
        print(f"Git Author     : {user_name} <{user_email}> [PASS]")
    else:
        print("Git Author     : Incomplete configuration [WARN]")
        if not user_name:
            print("  ! Missing user.name (run: git config --global user.name 'Your Name')")
        if not user_email:
            print("  ! Missing user.email (run: git config --global user.email 'you@example.com')")

    if uv_detected:
        print(f"uv Runner      : {uv_version} [DETECTED]")
    else:
        print("uv Runner      : Not installed (optional, install with: curl -LsSf https://astral.sh/uv/install.sh | sh or 'winget install --id=astral-sh.uv -e')")

    print("=" * 70)
    print("All core runtime requirements checked.")
    print("=" * 70)
    return 0 if all_ok else 1


# ==============================================================================
# Main CLI Entrypoint
# ==============================================================================

def main() -> None:
    setup_terminal_encoding()
    
    # Common parent parser for flags like --json
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--json", action="store_true", help="Output results in machine-readable JSON format")

    parser = argparse.ArgumentParser(
        description="Deterministic Git Suite (commit, sync, status, branch, undo, audit, check-env)",
        parents=[common_parser]
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: validate
    val_parser = subparsers.add_parser("validate", help="Validate a commit message string", parents=[common_parser])
    val_parser.add_argument("message", help="The full commit message to validate")

    # Subcommand: draft
    subparsers.add_parser("draft", help="Inspect git status, security scan, and suggest scopes/drafts", parents=[common_parser])

    # Subcommand: commit
    com_parser = subparsers.add_parser("commit", help="Validate and execute safe git commit", parents=[common_parser])
    com_parser.add_argument("-t", "--type", choices=sorted(ALLOWED_TYPES), help="Whitelisted commit type")
    com_parser.add_argument("-s", "--scope", help="Lowercase kebab-case scope")
    com_parser.add_argument("-m", "--message", help="Imperative description (10-120 chars)")
    com_parser.add_argument("-b", "--bullet", action="append", help="Optional body bullet point")
    com_parser.add_argument("--raw", help="Raw full commit message")

    # Subcommand: sync
    sync_parser = subparsers.add_parser("sync", help="Validate, commit, and push to upstream branch", parents=[common_parser])
    sync_parser.add_argument("-t", "--type", choices=sorted(ALLOWED_TYPES), help="Whitelisted commit type")
    sync_parser.add_argument("-s", "--scope", help="Lowercase kebab-case scope")
    sync_parser.add_argument("-m", "--message", help="Imperative description (10-120 chars)")
    sync_parser.add_argument("-b", "--bullet", action="append", help="Optional body bullet point")
    sync_parser.add_argument("--raw", help="Raw full commit message")

    # Subcommand: status
    subparsers.add_parser("status", help="Overview of working tree, branch, unpushed commits, and security", parents=[common_parser])

    # Subcommand: branch
    branch_parser = subparsers.add_parser("branch", help="Create conventional branch (feat/, fix/, chore/, etc.)", parents=[common_parser])
    branch_parser.add_argument("name", help="Branch name (e.g. feat/login-screen)")

    # Subcommand: undo
    subparsers.add_parser("undo", help="Safe soft reset of last commit", parents=[common_parser])

    # Subcommand: audit
    audit_parser = subparsers.add_parser("audit", help="Audit commit history compliance and suggest rewrites", parents=[common_parser])
    audit_parser.add_argument("-n", "--limit", type=int, default=10, help="Number of past commits to audit (default: 10)")

    # Subcommand: check-env
    subparsers.add_parser("check-env", help="Check Python, Git, and environment compatibility", parents=[common_parser])

    args = parser.parse_args()

    if args.command == "validate":
        sys.exit(cmd_validate(args.message, as_json=args.json))
    elif args.command == "draft":
        sys.exit(cmd_draft(as_json=args.json))
    elif args.command == "commit":
        if args.raw:
            sys.exit(cmd_commit("", "", "", raw_message=args.raw, as_json=args.json))
        else:
            if not args.type or not args.scope or not args.message:
                print("Error: -t/--type, -s/--scope, and -m/--message are required when not using --raw", file=sys.stderr)
                sys.exit(1)
            sys.exit(cmd_commit(args.type, args.scope, args.message, bullets=args.bullet, as_json=args.json))
    elif args.command == "sync":
        if args.raw:
            sys.exit(cmd_sync("", "", "", raw_message=args.raw, as_json=args.json))
        else:
            if not args.type or not args.scope or not args.message:
                print("Error: -t/--type, -s/--scope, and -m/--message are required when not using --raw", file=sys.stderr)
                sys.exit(1)
            sys.exit(cmd_sync(args.type, args.scope, args.message, bullets=args.bullet, as_json=args.json))
    elif args.command == "status":
        sys.exit(cmd_status(as_json=args.json))
    elif args.command == "branch":
        sys.exit(cmd_branch(args.name, as_json=args.json))
    elif args.command == "undo":
        sys.exit(cmd_undo(as_json=args.json))
    elif args.command == "audit":
        sys.exit(cmd_audit(limit=args.limit, as_json=args.json))
    elif args.command == "check-env":
        sys.exit(cmd_check_env(as_json=args.json))


if __name__ == "__main__":
    main()
