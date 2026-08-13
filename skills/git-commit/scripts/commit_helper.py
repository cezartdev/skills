#!/usr/bin/env python3
"""
commit_helper.py - Automated validation gate and safe commit runner for Conventional Commits.

Strictly enforces:
- Type whitelist: feat, fix, docs, refactor, chore, test
- Scope: lowercase kebab-case
- Length limits: description >= 10 chars, header <= 120 chars
- English imperative action verbs (no past tense, no gerund, no non-English)
- No trailing period
- Lowercase start, clean single-space formatting
- Optional body with concise bullet points (- ...)
"""

import argparse
import re
import subprocess
import sys
from typing import List, Tuple, Dict, Any, Optional

ALLOWED_TYPES = {"feat", "fix", "docs", "refactor", "chore", "test"}

COMMON_IMPERATIVE_VERBS = {
    "add", "adjust", "align", "allow", "author", "bump", "clarify", "clean",
    "configure", "consolidate", "correct", "create", "decouple", "define",
    "deprecate", "disable", "document", "downgrade", "enable", "enforce",
    "ensure", "expand", "expose", "extract", "fix", "format", "handle",
    "implement", "improve", "include", "init", "initialize", "integrate",
    "introduce", "migrate", "optimize", "organize", "patch", "prevent",
    "publish", "refactor", "release", "remove", "rename", "reorganize",
    "resolve", "revert", "revise", "rewrite", "set", "setup", "simplify",
    "split", "standardize", "streamline", "structure", "support", "sync",
    "synchronize", "test", "update", "upgrade", "validate", "verify",
}

FORBIDDEN_VERB_SUFFIXES = ("ed", "ing", "es", "s")


# ==============================================================================
# Modular Step-by-Step Validation Functions
# ==============================================================================

def validate_structure(header: str) -> Tuple[bool, str, Dict[str, str]]:
    """Step 1: Check if header matches `<type>(<scope>): <description>`."""
    match = re.match(r"^([a-zA-Z0-9_-]+)(?:\(([a-zA-Z0-9_-]+)\))?:\s*(.*)$", header.strip())
    if not match:
        return False, "Header does not match standard pattern: `<type>(<scope>): <description>`", {}
    
    commit_type = (match.group(1) or "").strip()
    scope = (match.group(2) or "").strip()
    description = (match.group(3) or "").strip()
    
    if not scope:
        return False, "Scope is missing. Format must be `<type>(<scope>): <description>`", {}
    if not description:
        return False, "Description is missing after scope and colon", {}
        
    return True, f"Structure parsed successfully: type='{commit_type}', scope='{scope}'", {
        "type": commit_type,
        "scope": scope,
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
        return False, f"Scope '{scope}' must be lowercase alphanumeric or kebab-case (e.g. 'git-commit', 'workflow')"
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
    
    # Check if first word is in known imperative verbs
    if first_word in COMMON_IMPERATIVE_VERBS:
        return True, f"Leading verb '{first_word}' is an approved English imperative verb"
    
    # If not recognized, check if it's past tense or non-imperative
    if first_word.endswith("ed") or first_word.endswith("ing"):
        return False, f"Leading word '{first_word}' appears to be past tense or gerund. Use imperative present tense (e.g., 'add', 'update', 'fix')"
    
    # Generic rejection if not in recognized English verb vocabulary
    return False, (
        f"Leading word '{first_word}' is not a recognized English imperative verb. "
        f"Examples of valid verbs: {', '.join(sorted(list(COMMON_IMPERATIVE_VERBS)[:8]))}..."
    )


def validate_casing_and_spacing(description: str) -> Tuple[bool, str]:
    """Step 8: Check casing (lowercase start) and clean single spacing."""
    desc = description.strip()
    if not desc:
        return False, "Description is empty"
    
    # Check if first char is uppercase (unless it's an acronym / filename)
    first_char = desc[0]
    if first_char.isupper() and not desc.split()[0].isupper():
        return False, f"Description should start with lowercase letter: '{desc[0].lower() + desc[1:]}'"
    
    # Check for multiple consecutive spaces
    if re.search(r"\s{2,}", desc):
        return False, "Description contains multiple consecutive spaces; use single normal spaces"
    
    # Check for accidental snake_case in regular prose (e.g., "add_helper_script")
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
        if not stripped.startswith("- "):
            return False, f"Body line {i} does not start with bullet '- ': '{stripped}'"
        if len(stripped) > max_line_length:
            return False, f"Body bullet {i} exceeds {max_line_length} chars ({len(stripped)} chars)"
            
    return True, f"Body bullets ({len(body_lines)} lines) formatted correctly"


# ==============================================================================
# Pipeline Runner & Reporter
# ==============================================================================

def run_full_validation(full_message: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Runs the entire modular validation pipeline on a commit message.
    Returns (all_passed: bool, step_reports: list).
    """
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
        print(f"Step {r['step']}/9 {r['name']:<35} {status} : {r['message']}")
        
    print("=" * 70)
    if all_passed:
        print(">>> RESULT: 100% VALIDATED. Message is safe for git commit.")
    else:
        print(">>> RESULT: VALIDATION FAILED. Please resolve errors before committing.")
    print("=" * 70)


# ==============================================================================
# CLI Actions (draft, validate, commit)
# ==============================================================================

def cmd_validate(message: str) -> int:
    all_passed, reports = run_full_validation(message)
    print_validation_report(message, all_passed, reports)
    return 0 if all_passed else 1


def cmd_draft() -> int:
    """Inspects git status and suggests candidate commit scopes and drafts."""
    try:
        status_out = subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running git status: {e}", file=sys.stderr)
        return 1

    if not status_out:
        print("Working tree is completely clean. Nothing to commit.")
        return 0

    staged_files = []
    unstaged_files = []

    for line in status_out.splitlines():
        if len(line) < 3:
            continue
        index_status = line[0]
        work_status = line[1]
        filepath = line[3:].strip()
        
        if index_status in ("M", "A", "D", "R"):
            staged_files.append(filepath)
        elif work_status in ("M", "D") or index_status == "?":
            unstaged_files.append(filepath)

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

    print("\nWhitelisted Types: " + ", ".join(sorted(ALLOWED_TYPES)))
    print("Template: <type>(<scope>): <imperative_verb> <description (10-120 chars)>")
    print("=" * 70)
    return 0


def cmd_commit(
    commit_type: str,
    scope: str,
    description: str,
    bullets: Optional[List[str]] = None,
    raw_message: Optional[str] = None
) -> int:
    """Constructs the message, runs full pre-flight validation, and executes git commit."""
    # Step 0: Check working tree status
    try:
        status_out = subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
        if not status_out:
            print("[NO CHANGES] Working tree is completely clean. No changes detected to commit. No action taken.")
            return 0
            
        diff_cached = subprocess.check_output(["git", "diff", "--cached", "--name-only"], text=True).strip()
        if not diff_cached:
            print("[NO STAGED CHANGES] Changes exist in working tree, but none are staged. Please stage files using 'git add <files>' first.")
            return 1
    except subprocess.CalledProcessError as e:
        print(f"Error checking git status: {e}", file=sys.stderr)
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

    # Step 1: Pre-flight validation gate
    all_passed, reports = run_full_validation(full_message)
    print_validation_report(full_message, all_passed, reports)

    if not all_passed:
        print("ERROR: Commit aborted due to pre-flight validation failure.", file=sys.stderr)
        return 1

    # Step 2: Safe commit execution
    try:
        print("\nExecuting git commit...")
        subprocess.check_call(["git", "commit", "-m", full_message])
        print("\nCommit successful! Verifying latest commit:")
        subprocess.check_call(["git", "log", "-1", "--stat"])
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Git commit failed: {e}", file=sys.stderr)
        return 1


# ==============================================================================
# Main CLI Entrypoint
# ==============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Conventional Commit Validator & Safe Commit Runner"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: validate
    val_parser = subparsers.add_parser("validate", help="Validate a commit message string")
    val_parser.add_argument("message", help="The full commit message to validate")

    # Subcommand: draft
    subparsers.add_parser("draft", help="Inspect git status and suggest scopes/drafts")

    # Subcommand: commit
    com_parser = subparsers.add_parser("commit", help="Validate and execute git commit")
    com_parser.add_argument("-t", "--type", choices=sorted(ALLOWED_TYPES), help="Whitelisted commit type")
    com_parser.add_argument("-s", "--scope", help="Lowercase kebab-case scope")
    com_parser.add_argument("-m", "--message", help="Imperative description (10-120 chars)")
    com_parser.add_argument("-b", "--bullet", action="append", help="Optional body bullet point")
    com_parser.add_argument("--raw", help="Raw full commit message (bypasses -t/-s/-m flags)")

    args = parser.parse_args()

    if args.command == "validate":
        sys.exit(cmd_validate(args.message))
    elif args.command == "draft":
        sys.exit(cmd_draft())
    elif args.command == "commit":
        if args.raw:
            sys.exit(cmd_commit("", "", "", raw_message=args.raw))
        else:
            if not args.type or not args.scope or not args.message:
                print("Error: -t/--type, -s/--scope, and -m/--message are all required when not using --raw", file=sys.stderr)
                sys.exit(1)
            sys.exit(cmd_commit(args.type, args.scope, args.message, bullets=args.bullet))


if __name__ == "__main__":
    main()
