"""Language- and framework-agnostic codebase exploration scanner."""

import os
import json
import hashlib
from typing import Dict, Any, List
from datetime import datetime


def compute_file_hash(filepath: str) -> str:
    """Computes SHA-256 hash of a file."""
    if not os.path.exists(filepath):
        return ""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()[:16]


def scan_codebase(root_dir: str = ".") -> Dict[str, Any]:
    """Scans workspace to detect language, framework, test runner candidates, and package managers."""
    root_dir = os.path.abspath(root_dir)
    
    languages: List[str] = []
    frameworks: List[str] = []
    package_managers: List[str] = []
    test_candidates: List[str] = []
    manifest_hashes: Dict[str, str] = {}

    # 1. Check Python ecosystem first
    pyproject_path = os.path.join(root_dir, "pyproject.toml")
    has_python = os.path.exists(pyproject_path) or os.path.exists(os.path.join(root_dir, "requirements.txt")) or os.path.exists(os.path.join(root_dir, "uv.lock"))
    if has_python:
        languages.append("Python")
        if os.path.exists(pyproject_path):
            manifest_hashes["pyproject.toml"] = compute_file_hash(pyproject_path)
        if os.path.exists(os.path.join(root_dir, "uv.lock")) or os.path.exists(pyproject_path):
            package_managers.append("uv")
            test_candidates.extend(["uv run pytest", "pytest", "python -m unittest"])
        else:
            test_candidates.extend(["pytest", "python -m unittest"])

        if os.path.exists(pyproject_path):
            try:
                with open(pyproject_path, "r", encoding="utf-8") as f:
                    py_content = f.read().lower()
                if "fastapi" in py_content:
                    frameworks.append("FastAPI")
                elif "django" in py_content:
                    frameworks.append("Django")
                elif "flask" in py_content:
                    frameworks.append("Flask")
                elif "langgraph" in py_content:
                    frameworks.append("LangGraph")
            except Exception:
                pass

    # 2. Check Node / JS / TS ecosystem
    pkg_json_path = os.path.join(root_dir, "package.json")
    if os.path.exists(pkg_json_path):
        languages.append("TypeScript / JavaScript")
        manifest_hashes["package.json"] = compute_file_hash(pkg_json_path)
        has_pnpm = os.path.exists(os.path.join(root_dir, "pnpm-lock.yaml"))
        has_yarn = os.path.exists(os.path.join(root_dir, "yarn.lock"))
        has_bun = os.path.exists(os.path.join(root_dir, "bun.lockb"))

        if has_pnpm:
            package_managers.append("pnpm")
            node_pkg = "pnpm"
        elif has_yarn:
            package_managers.append("yarn")
            node_pkg = "yarn"
        elif has_bun:
            package_managers.append("bun")
            node_pkg = "bun"
        else:
            package_managers.append("npm")
            node_pkg = "npm"

        try:
            with open(pkg_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            scripts = data.get("scripts", {})

            if "next" in deps:
                frameworks.append("Next.js")
            elif "nest" in deps or "@nestjs/core" in deps:
                frameworks.append("NestJS")
            elif "express" in deps:
                frameworks.append("Express")
            elif "react" in deps:
                frameworks.append("React")
            elif "vue" in deps:
                frameworks.append("Vue")

            if "vitest" in deps:
                test_candidates.insert(0, f"{node_pkg} test" if "test" in scripts else "vitest run")
            elif "jest" in deps:
                test_candidates.insert(0, f"{node_pkg} test" if "test" in scripts else "jest")
            elif "test" in scripts:
                test_candidates.insert(0, f"{node_pkg} test")
        except Exception:
            pass

    # 3. Check Rust ecosystem
    cargo_path = os.path.join(root_dir, "Cargo.toml")
    if os.path.exists(cargo_path):
        languages.append("Rust")
        package_managers.append("cargo")
        manifest_hashes["Cargo.toml"] = compute_file_hash(cargo_path)
        test_candidates.insert(0, "cargo test")

    # 4. Check Go ecosystem
    gomod_path = os.path.join(root_dir, "go.mod")
    if os.path.exists(gomod_path):
        languages.append("Go")
        package_managers.append("go")
        manifest_hashes["go.mod"] = compute_file_hash(gomod_path)
        test_candidates.insert(0, "go test ./...")

    # Defaults if none detected
    if not languages:
        languages.append("Polyglot / Generic")
    if not package_managers:
        package_managers.append("standard")
    if not test_candidates:
        test_candidates = ["pnpm test", "pytest", "cargo test", "go test ./..."]

    primary_test_runner = test_candidates[0]

    return {
        "project_name": os.path.basename(root_dir),
        "languages": ", ".join(set(languages)),
        "frameworks": ", ".join(set(frameworks)) if frameworks else "Custom / Standard",
        "package_manager": ", ".join(set(package_managers)),
        "test_runner": primary_test_runner,
        "test_candidates": list(dict.fromkeys(test_candidates)),
        "manifest_hashes": manifest_hashes,
        "scanned_at": datetime.now().isoformat(),
    }


def generate_master_context(root_dir: str = ".") -> str:
    """Scans repository and creates/updates memory/00_project_context.md."""
    scan = scan_codebase(root_dir)
    memory_dir = os.path.join(root_dir, "memory")
    os.makedirs(memory_dir, exist_ok=True)
    master_file = os.path.join(memory_dir, "00_project_context.md")

    manifest_lines = [f"{k}: `{v}`" for k, v in scan["manifest_hashes"].items()]
    manifest_str = " | ".join(manifest_lines) if manifest_lines else "None"

    content = f"""# Project Master Context & Architectural Invariants

**Project Name**: `{scan['project_name']}`  
**Last Updated**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`  
**Manifest Fingerprints**: {manifest_str}

---

## 1. Technology Stack & Runtimes
- **Primary Language(s)**: `{scan['languages']}`
- **Framework(s)**: `{scan['frameworks']}`
- **Package Manager**: `{scan['package_manager']}`
- **Test Runner & Suite**: `{scan['test_runner']}`

---

## 2. Core Architectural Invariants & Rules
1. **Spec-Driven Architecture**: All functional features are declared in `specs/features/` and executed via TDD issues.
2. **Worktree Isolation**: Background workers run strictly inside dedicated `.worktrees/` instances.
3. **Quality Gate Compliance**: Tests must pass 100% with no security gate violations prior to merging.

---

## 3. Cumulative Decisions & Historical Rollup Log

| Date | Archetype | Decision / Milestone | Summary & Impact |
|---|---|---|---|
| {datetime.now().strftime('%Y-%m-%d')} | `explorer` | Initial Stack Survey | Initialized context for {scan['languages']} ({scan['frameworks']}). |
"""
    with open(master_file, "w", encoding="utf-8") as f:
        f.write(content)

    return master_file
