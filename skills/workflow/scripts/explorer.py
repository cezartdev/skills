"""Universal Polyglot Codebase Scanner & Stack Explorer for AI Agents."""

import os
import json
import hashlib
import glob
from typing import Dict, Any, List
from datetime import datetime


def compute_file_hash(file_path: str) -> str:
    """Computes SHA-256 fingerprint for a given manifest file."""
    if not os.path.exists(file_path):
        return ""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()[:16]


def scan_codebase(root_dir: str = ".") -> Dict[str, Any]:
    """Scans repository workspace and deterministically detects polyglot stacks and test runners."""
    root_dir = os.path.abspath(root_dir)
    languages: List[str] = []
    frameworks: List[str] = []
    package_managers: List[str] = []
    test_candidates: List[str] = []
    manifest_hashes: Dict[str, str] = {}
    has_explicit_test_script: bool = False

    # 1. Check Node / JS / TS ecosystem
    pkg_json_path = os.path.join(root_dir, "package.json")
    if os.path.exists(pkg_json_path):
        languages.append("TypeScript / JavaScript")
        manifest_hashes["package.json"] = compute_file_hash(pkg_json_path)
        has_pnpm = os.path.exists(os.path.join(root_dir, "pnpm-lock.yaml"))
        has_yarn = os.path.exists(os.path.join(root_dir, "yarn.lock"))
        has_bun = os.path.exists(os.path.join(root_dir, "bun.lockb")) or os.path.exists(os.path.join(root_dir, "bun.lock"))

        if has_pnpm:
            package_managers.append("pnpm")
            node_pkg = "pnpm"
        elif has_bun:
            package_managers.append("bun")
            node_pkg = "bun"
        elif has_yarn:
            package_managers.append("yarn")
            node_pkg = "yarn"
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
                test_candidates = [f"{node_pkg} test" if "test" in scripts else "vitest run", "vitest run"]
                has_explicit_test_script = True
            elif "jest" in deps:
                test_candidates = [f"{node_pkg} test" if "test" in scripts else "jest", "jest"]
                has_explicit_test_script = True
            elif "test" in scripts:
                test_candidates = [f"{node_pkg} test", "vitest run", "jest"]
                has_explicit_test_script = True
            else:
                # Default Node fallback without explicit test script
                test_candidates = [f"{node_pkg} test", "vitest run", "jest"]
                has_explicit_test_script = False
        except Exception:
            test_candidates = [f"{node_pkg} test", "vitest run", "jest"]

    # 2. Check Python ecosystem
    pyproject_path = os.path.join(root_dir, "pyproject.toml")
    reqs_path = os.path.join(root_dir, "requirements.txt")
    setup_py = os.path.join(root_dir, "setup.py")

    if os.path.exists(pyproject_path) or os.path.exists(reqs_path) or os.path.exists(setup_py):
        languages.append("Python")
        if os.path.exists(pyproject_path):
            manifest_hashes["pyproject.toml"] = compute_file_hash(pyproject_path)
            package_managers.append("uv")
        elif os.path.exists(reqs_path):
            manifest_hashes["requirements.txt"] = compute_file_hash(reqs_path)
            package_managers.append("pip")

        # Python test runners
        py_runner = "uv run pytest" if os.path.exists(pyproject_path) else "pytest"
        if not test_candidates:
            test_candidates = [py_runner, "pytest", "python -m unittest"]
            has_explicit_test_script = True
        else:
            test_candidates.append(py_runner)

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

    # 3. Check Rust ecosystem
    cargo_path = os.path.join(root_dir, "Cargo.toml")
    if os.path.exists(cargo_path):
        languages.append("Rust")
        package_managers.append("cargo")
        manifest_hashes["Cargo.toml"] = compute_file_hash(cargo_path)
        if not test_candidates:
            test_candidates = ["cargo test"]
            has_explicit_test_script = True
        else:
            test_candidates.append("cargo test")

    # 4. Check Go ecosystem
    gomod_path = os.path.join(root_dir, "go.mod")
    if os.path.exists(gomod_path):
        languages.append("Go")
        package_managers.append("go")
        manifest_hashes["go.mod"] = compute_file_hash(gomod_path)
        if not test_candidates:
            test_candidates = ["go test ./..."]
            has_explicit_test_script = True
        else:
            test_candidates.append("go test ./...")

    # 5. Check Java / Kotlin (Maven / Gradle)
    pom_path = os.path.join(root_dir, "pom.xml")
    gradle_path = os.path.join(root_dir, "build.gradle")
    gradle_kts = os.path.join(root_dir, "build.gradle.kts")
    if os.path.exists(pom_path):
        languages.append("Java")
        package_managers.append("maven")
        manifest_hashes["pom.xml"] = compute_file_hash(pom_path)
        if not test_candidates:
            test_candidates = ["mvn test"]
            has_explicit_test_script = True
        else:
            test_candidates.append("mvn test")
    elif os.path.exists(gradle_path) or os.path.exists(gradle_kts):
        languages.append("Java / Kotlin")
        package_managers.append("gradle")
        gradle_file = gradle_path if os.path.exists(gradle_path) else gradle_kts
        manifest_hashes[os.path.basename(gradle_file)] = compute_file_hash(gradle_file)
        gradle_cmd = "./gradlew test" if os.path.exists(os.path.join(root_dir, "gradlew")) else "gradle test"
        if not test_candidates:
            test_candidates = [gradle_cmd]
            has_explicit_test_script = True
        else:
            test_candidates.append(gradle_cmd)

    # 6. Check C# / .NET
    sln_files = glob.glob(os.path.join(root_dir, "*.sln"))
    csproj_files = glob.glob(os.path.join(root_dir, "*.csproj"))
    if sln_files or csproj_files:
        languages.append("C# / .NET")
        package_managers.append("dotnet")
        if not test_candidates:
            test_candidates = ["dotnet test"]
            has_explicit_test_script = True
        else:
            test_candidates.append("dotnet test")

    # Defaults if none detected
    if not languages:
        languages.append("Polyglot / Generic")
    if not package_managers:
        package_managers.append("standard")
    if not test_candidates:
        test_candidates = ["pytest", "cargo test", "go test ./...", "pnpm test"]
        has_explicit_test_script = False

    primary_test_runner = test_candidates[0]

    return {
        "project_name": os.path.basename(root_dir),
        "languages": ", ".join(list(dict.fromkeys(languages))),
        "frameworks": ", ".join(list(dict.fromkeys(frameworks))) if frameworks else "Custom / Standard",
        "package_manager": ", ".join(list(dict.fromkeys(package_managers))),
        "test_runner": primary_test_runner,
        "test_candidates": list(dict.fromkeys(test_candidates)),
        "has_explicit_test_script": has_explicit_test_script,
        "manifest_hashes": manifest_hashes,
        "scanned_at": datetime.now().isoformat(),
    }


def generate_master_context(root_dir: str = ".") -> str:
    """Scans repository and creates/updates .workflow/memory/00_project_context.md."""
    root_dir = os.path.abspath(root_dir)
    wf_root = os.path.join(root_dir, ".workflow") if os.path.basename(root_dir) != ".workflow" else root_dir
    scan = scan_codebase(root_dir)
    memory_dir = os.path.join(wf_root, "memory")
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
1. **Spec-Driven Architecture**: All functional features are declared in `.workflow/specs/features/` and executed via TDD issues.
2. **Worktree Isolation**: Background workers run strictly inside dedicated `.workflow/worktrees/` instances.
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
