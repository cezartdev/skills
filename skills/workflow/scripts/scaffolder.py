"""Scaffolder module: initializes target project structure and creates new specs inside .workflow/."""

import os
import json
import shutil
import re
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from .explorer import scan_codebase, generate_master_context, generate_coding_preferences
except ImportError:
    from explorer import scan_codebase, generate_master_context, generate_coding_preferences


import stat


def _handle_remove_readonly(func, path, exc_info):
    """Error handler for shutil.rmtree on Windows/POSIX to clear readonly attributes."""
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


def sanitize_identifier(name: str) -> str:
    """Sanitizes an identifier (spec, daemon, worktree) against path traversal and invalid chars."""
    if not name:
        return "unnamed"
    cleaned = os.path.basename(name.replace("\\", "/"))
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", cleaned).strip("-._")
    return cleaned.lower() or "unnamed"


def atomic_write_json(file_path: str, data: Dict[str, Any]) -> None:
    """Safely writes a JSON dictionary atomically to disk using a temporary file and os.replace."""
    file_path = os.path.abspath(file_path)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    temp_path = f"{file_path}.tmp.{os.getpid()}_{int(time.time()*1000)}"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        # Cross-platform atomic replace with retry for Windows file handle locks
        for attempt in range(3):
            try:
                os.replace(temp_path, file_path)
                break
            except PermissionError:
                if attempt == 2:
                    raise
                time.sleep(0.05)
    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        raise e


def ensure_dir_with_gitkeep(dir_path: str) -> str:
    """Ensures directory exists and places an empty .gitkeep file so git preserves the directory structure."""
    os.makedirs(dir_path, exist_ok=True)
    reconcile_gitkeep(dir_path)
    return dir_path


def reconcile_gitkeep(dir_path: str) -> None:
    """Ensures .gitkeep is deleted if directory contains real files/dirs, or restored if completely empty."""
    if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
        return
    gitkeep_file = os.path.join(dir_path, ".gitkeep")
    entries = [e for e in os.listdir(dir_path) if e != ".gitkeep"]
    if len(entries) > 0:
        if os.path.exists(gitkeep_file):
            try:
                os.remove(gitkeep_file)
            except OSError:
                pass
    else:
        if not os.path.exists(gitkeep_file):
            try:
                with open(gitkeep_file, "w", encoding="utf-8") as f:
                    f.write("")
            except OSError:
                pass


def get_skill_assets_dir() -> str:
    """Returns the absolute path to skills/workflow/assets."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(script_dir, "..", "assets"))


def get_workflow_root(target_dir: str = ".") -> str:
    """Returns the absolute path to the encapsulated .workflow directory in target project."""
    target_dir = os.path.abspath(target_dir)
    if os.path.basename(target_dir) == ".workflow":
        return target_dir
    return os.path.join(target_dir, ".workflow")


def inject_agent_rules(target_dir: str = ".") -> Dict[str, Any]:
    """Detects agent rule files (AGENTS.md, CLAUDE.md, GEMINI.md, .cursorrules, etc.)
    and ensures AGENTS.md exists with directives to inspect .workflow/memory/ and .workflow/specs/active/."""
    target_dir = os.path.abspath(target_dir)
    
    agent_rules_files = [
        "AGENTS.md",
        "CLAUDE.md",
        ".claude.md",
        "GEMINI.md",
        ".gemini.md",
        ".cursorrules",
        "COPILOT.md",
        ".windsurfrules",
        ".clinerules",
        "CURSOR.md",
    ]

    detected = []
    for fname in agent_rules_files:
        p = os.path.join(target_dir, fname)
        if os.path.exists(p):
            detected.append(fname)

    agents_md_path = os.path.join(target_dir, "AGENTS.md")
    agents_md_created = False
    agents_md_updated = False
    secondary_updated = []

    workflow_directives_block = """<!-- WORKFLOW_AGENT_GUIDELINES_START -->
## 🤖 Workflow Agent Directives & Memory Integration
All AI coding agents working in this repository MUST adhere to the following mandatory workflow directives:

1. **Skill Execution & References**: Always invoke workflow CLI commands using `uv run` (e.g. `uv run skills/workflow/scripts/workflow_runner.py <subcommand>` or `uv run .agents/skills/workflow/scripts/workflow_runner.py <subcommand>`). Refer to `skills/workflow/SKILL.md` (or `.agents/skills/workflow/SKILL.md`) and `skills/workflow/references/ARCHITECTURE.md`.
2. **Methodology Invariants**: Thoroughly read `.workflow/memory/workflow_methodology.md` to understand the Spec-Driven Development (SDD), Test-Driven Development (TDD), and 4-stage sequential subagent pipeline.
3. **Project Context & Coding Preferences**: Inspect `.workflow/memory/project_context.md` for tech stack runtimes and `.workflow/memory/coding_preferences.md` for linters, naming conventions, and style rules before modifying any code.
4. **Active Specifications**: In-flight feature specifications and atomic TDD tasks reside under `.workflow/specs/active/<spec-name>/`.
5. **Architectural Decisions (ADRs)**: Consult and record all architectural decisions in `.workflow/specs/active/<spec-name>/adrs/`.
6. **Strict Zero-Comments Code Policy**: Write 100% clean, self-documenting code with **ZERO comments** (no `//`, `#`, or `\"\"\" \"\"\"`) in all source code generation/edits unless explicitly requested by the user.
<!-- WORKFLOW_AGENT_GUIDELINES_END -->"""

    if not os.path.exists(agents_md_path):
        project_name = os.path.basename(target_dir) or "Project"
        initial_content = f"""# Agent Operating Guidelines & Standards

This document establishes the mandatory operating standards, execution workflow, and rules of engagement for all AI agents working on `{project_name}`.

---

{workflow_directives_block.strip()}
"""
        with open(agents_md_path, "w", encoding="utf-8") as f:
            f.write(initial_content)
        agents_md_created = True
        if "AGENTS.md" not in detected:
            detected.append("AGENTS.md")
    else:
        with open(agents_md_path, "r", encoding="utf-8") as f:
            current_content = f.read()
        if "<!-- WORKFLOW_AGENT_GUIDELINES_START -->" not in current_content and "workflow_methodology.md" not in current_content:
            with open(agents_md_path, "a", encoding="utf-8") as f:
                f.write("\n\n" + workflow_directives_block.strip() + "\n")
            agents_md_updated = True

    # Pointers in other detected rule files
    secondary_pointer = """<!-- WORKFLOW_POINTER_START -->
> [!IMPORTANT]
> **Workflow Directives**: Always consult `AGENTS.md` and `.workflow/memory/workflow_methodology.md` before executing tasks or proposing architectural changes.
<!-- WORKFLOW_POINTER_END -->"""

    for fname in detected:
        if fname == "AGENTS.md":
            continue
        fpath = os.path.join(target_dir, fname)
        if os.path.isfile(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                sec_content = f.read()
            if "<!-- WORKFLOW_POINTER_START -->" not in sec_content and "AGENTS.md" not in sec_content:
                with open(fpath, "a", encoding="utf-8") as f:
                    f.write("\n\n" + secondary_pointer.strip() + "\n")
                secondary_updated.append(fname)

    return {
        "detected_rule_files": detected,
        "agents_md_created": agents_md_created,
        "agents_md_updated": agents_md_updated,
        "secondary_updated": secondary_updated,
    }


def scaffold_init(target_dir: str = ".", test_runner_cmd: Optional[str] = None) -> Dict[str, Any]:
    """Initializes encapsulated .workflow structure in target directory with .gitkeep placeholders."""
    target_dir = os.path.abspath(target_dir)
    wf_root = get_workflow_root(target_dir)
    assets_dir = get_skill_assets_dir()

    # 1. Create .workflow/specs/ directory with active/ and archive/ placeholders
    specs_dir = os.path.join(wf_root, "specs")
    os.makedirs(specs_dir, exist_ok=True)
    active_specs_dir = os.path.join(specs_dir, "active")
    archive_specs_dir = os.path.join(specs_dir, "archive")
    ensure_dir_with_gitkeep(active_specs_dir)
    ensure_dir_with_gitkeep(archive_specs_dir)

    # 2. Create clean .workflow/memory/ directory with docs/ subfolder and workflow_methodology.md
    memory_dir = os.path.join(wf_root, "memory")
    os.makedirs(memory_dir, exist_ok=True)
    ensure_dir_with_gitkeep(os.path.join(memory_dir, "docs"))

    methodology_file = os.path.join(memory_dir, "workflow_methodology.md")
    methodology_created = False
    if not os.path.exists(methodology_file):
        template_meth = os.path.join(assets_dir, "workflow_methodology.template.md")
        project_name = os.path.basename(target_dir) or "Project"
        if os.path.exists(template_meth):
            with open(template_meth, "r", encoding="utf-8") as f:
                meth_content = f.read().replace("{{PROJECT_NAME}}", project_name)
        else:
            meth_content = f"# Workflow Methodology\n\n**Project**: `{project_name}`\n"
        with open(methodology_file, "w", encoding="utf-8") as f:
            f.write(meth_content)
        methodology_created = True

    # 3. Deterministically generate project_context.md and coding_preferences.md
    context_file = generate_master_context(target_dir)
    pref_file = os.path.join(memory_dir, "coding_preferences.md")

    # 4. Create .workflow/prs/ catalog with .gitkeep (active, archive)
    prs_dir = os.path.join(wf_root, "prs")
    ensure_dir_with_gitkeep(os.path.join(prs_dir, "active"))
    ensure_dir_with_gitkeep(os.path.join(prs_dir, "archive"))

    # 5. Create .workflow/worktrees/ placeholder
    worktrees_dir = os.path.join(wf_root, "worktrees")
    os.makedirs(worktrees_dir, exist_ok=True)

    # 6. Determine test runner dynamically via polyglot scan
    if not test_runner_cmd:
        scan = scan_codebase(target_dir)
        test_cmd = scan.get("test_runner", "pytest")
    else:
        test_cmd = test_runner_cmd

    # 7. Scaffold .workflow/workflow.json if not present
    config_file = os.path.join(wf_root, "workflow.json")
    config_created = False
    if not os.path.exists(config_file):
        template_config = os.path.join(assets_dir, "workflow.config.json")
        if os.path.exists(template_config):
            with open(template_config, "r", encoding="utf-8") as f:
                cfg_data = json.load(f)
            cfg_data.setdefault("test_runner", {})["command"] = test_cmd
            atomic_write_json(config_file, cfg_data)
        else:
            atomic_write_json(config_file, {
                "version": "2.0",
                "pipeline": {
                    "default_interval_minutes": 30,
                    "max_iterations": None,
                    "stages": [
                        {"id": "fix", "role": "Fix-Worker Specialist", "description": "Bug stabilization and 100% green test pass"},
                        {"id": "refactor", "role": "Refactor-Worker Specialist", "description": "Clean code, modularity, and complexity reduction"},
                        {"id": "doc", "role": "Doc-Worker Specialist", "description": "Docstrings, OpenAPI schemas, and spec sync"},
                        {"id": "curator", "role": "Curator Specialist", "description": "Quality gate, ADR generation, and PR synthesis"}
                    ],
                    "auto_merge": {
                        "enabled": False,
                        "strategy": "no-ff",
                        "require_all_tests_pass": True,
                        "require_security_scan": True
                    },
                    "adrs": {
                        "enabled": True,
                        "format": "MADR",
                        "directory": ".workflow/specs/active/{spec}/adrs"
                    }
                },
                "test_runner": {"command": test_cmd, "args": ["--run"], "coverage_threshold": 80},
                "drift_detection": {"enabled": True, "auto_reexplore": True},
                "memory": {"directory": ".workflow/memory", "max_episodic_files_per_archetype": 10},
                "prs": {"directory": ".workflow/prs"},
                "worktrees": {"directory": ".workflow/worktrees", "auto_clean_on_merge": True}
            })
        config_created = True

    # 8. Add .workflow/worktrees to .gitignore if not present
    gitignore_path = os.path.join(target_dir, ".gitignore")
    gitignore_updated = False
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as f:
            content = f.read()
        needed_entries = [".workflow/worktrees/", ".workflow/logs/"]
        to_add = [e for e in needed_entries if e not in content]
        if to_add:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                f.write("\n# Workflow Ephemeral Artifacts\n" + "\n".join(to_add) + "\n")
            gitignore_updated = True
    else:
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write("# Workflow Ephemeral Artifacts\n.workflow/worktrees/\n.workflow/logs/\n")
        gitignore_updated = True

    # 9. Inject agent rules & pointers into AGENTS.md, CLAUDE.md, etc.
    rules_injection = inject_agent_rules(target_dir)

    return {
        "status": "INITIALIZED",
        "target_dir": target_dir,
        "workflow_dir": wf_root,
        "specs_dir": specs_dir,
        "active_specs_dir": active_specs_dir,
        "archive_specs_dir": archive_specs_dir,
        "memory_dir": memory_dir,
        "methodology_file": methodology_file,
        "methodology_created": methodology_created,
        "project_context_file": context_file,
        "coding_preferences_file": pref_file,
        "prs_dir": prs_dir,
        "config_file": config_file,
        "test_runner": test_cmd,
        "config_created": config_created,
        "gitignore_updated": gitignore_updated,
        "rules_injection": rules_injection,
    }


def scaffold_new_spec(
    spec_name: str,
    archetype: Optional[str] = None,
    target_dir: str = "."
) -> Dict[str, Any]:
    """Creates a new spec directory under .workflow/specs/active/<spec_name>/."""
    target_dir = os.path.abspath(target_dir)
    wf_root = get_workflow_root(target_dir)
    assets_dir = get_skill_assets_dir()

    clean_name = sanitize_identifier(spec_name)
    active_specs_dir = os.path.join(wf_root, "specs", "active")
    spec_dir = os.path.join(active_specs_dir, clean_name)
    issues_dir = os.path.join(spec_dir, "issues")
    adrs_dir = os.path.join(spec_dir, "adrs")
    ensure_dir_with_gitkeep(issues_dir)
    ensure_dir_with_gitkeep(adrs_dir)

    # 1. Create spec.md from assets/spec.template.md
    spec_file = os.path.join(spec_dir, "spec.md")
    template_spec = os.path.join(assets_dir, "spec.template.md")
    if os.path.exists(template_spec):
        with open(template_spec, "r", encoding="utf-8") as f:
            spec_content = f.read().replace("{{SPEC_NAME}}", clean_name)
    else:
        spec_content = f"# Spec: {clean_name}\n\n## 1. Overview\n\n## 5. Acceptance Criteria\n"
    
    with open(spec_file, "w", encoding="utf-8") as f:
        f.write(spec_content)

    # 2. Create initial state.json
    state_file = os.path.join(spec_dir, "state.json")
    rel_spec_dir = os.path.join(".workflow", "specs", "active", clean_name).replace("\\", "/")
    
    initial_state = {
        "spec_name": clean_name,
        "spec_path": rel_spec_dir,
        "worktree_path": None,
        "branch_name": clean_name,
        "current_issue_index": 0,
        "issues": [],
        "dag_step": "NEW_SPEC_INITIALIZED",
        "checkpoint_history": [],
        "quality_gate_passed": False,
        "user_confirmed": False,
        "all_tests_passing": False,
        "spec_verified": False,
        "can_auto_merge": False,
    }
    atomic_write_json(state_file, initial_state)

    reconcile_gitkeep(active_specs_dir)

    return {
        "status": "SUCCESS",
        "spec_name": clean_name,
        "spec_dir": spec_dir,
        "spec_file": spec_file,
        "state_file": state_file,
    }


def archive_spec(spec_name: str, target_dir: str = ".") -> Dict[str, Any]:
    """Moves a completed spec folder into .workflow/specs/archive/<year>/<spec_name>/."""
    wf_root = get_workflow_root(target_dir)
    specs_root = os.path.join(wf_root, "specs")
    clean_name = sanitize_identifier(spec_name)

    # 1. Search in active/ specs
    found_src = None
    active_cand = os.path.join(specs_root, "active", clean_name)
    if os.path.exists(active_cand) and os.path.isdir(active_cand):
        found_src = active_cand
    else:
        # 2. Search directly under specs/ (flat fallback)
        candidate = os.path.join(specs_root, clean_name)
        if os.path.exists(candidate) and os.path.isdir(candidate):
            found_src = candidate
        else:
            # 3. Fallback for legacy specs in subfolders (features, bugs, refactor, docs)
            for folder in ["features", "bugs", "refactor", "docs"]:
                legacy_cand = os.path.join(specs_root, folder, clean_name)
                if os.path.exists(legacy_cand) and os.path.isdir(legacy_cand):
                    found_src = legacy_cand
                    break

    if not found_src:
        if os.path.exists(spec_name) and os.path.isdir(spec_name):
            found_src = os.path.abspath(spec_name)
            clean_name = sanitize_identifier(os.path.basename(found_src))
        else:
            return {"status": "ERROR", "message": f"Spec '{spec_name}' not found under .workflow/specs/."}

    year = str(datetime.now().year)
    archive_dest = os.path.join(specs_root, "archive", year, clean_name)
    os.makedirs(os.path.dirname(archive_dest), exist_ok=True)

    if os.path.exists(archive_dest):
        safe_rmtree(archive_dest)

    shutil.move(found_src, archive_dest)

    reconcile_gitkeep(os.path.join(specs_root, "active"))
    reconcile_gitkeep(os.path.join(specs_root, "archive"))
    reconcile_gitkeep(os.path.dirname(archive_dest))

    return {
        "status": "ARCHIVED",
        "spec_name": clean_name,
        "source_path": found_src,
        "archive_path": archive_dest,
    }
