"""Universal Polyglot Codebase Scanner & Stack Explorer for AI Agents."""

import os
import json
import hashlib
import re
import glob
from typing import Dict, Any, List, Optional
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


def detect_linters_and_formatters(root_dir: str = ".") -> Dict[str, Any]:
    """Detects active linters, formatters, and config files in the project."""
    root_dir = os.path.abspath(root_dir)
    tools = []
    configs = {}

    # ESLint
    eslint_files = [
        "eslint.config.js", "eslint.config.mjs", "eslint.config.cjs", "eslint.config.ts",
        ".eslintrc.js", ".eslintrc.cjs", ".eslintrc.json", ".eslintrc.yaml", ".eslintrc.yml", ".eslintrc"
    ]
    for f in eslint_files:
        if os.path.exists(os.path.join(root_dir, f)):
            tools.append("ESLint")
            configs["ESLint"] = f
            break

    # Biome
    for f in ["biome.json", "biome.jsonc"]:
        if os.path.exists(os.path.join(root_dir, f)):
            tools.append("Biome")
            configs["Biome"] = f
            break

    # Prettier
    prettier_files = [
        ".prettierrc", ".prettierrc.json", ".prettierrc.js", ".prettierrc.cjs",
        "prettier.config.js", "prettier.config.cjs", "prettier.config.mjs"
    ]
    for f in prettier_files:
        if os.path.exists(os.path.join(root_dir, f)):
            tools.append("Prettier")
            configs["Prettier"] = f
            break

    # Ruff (Python)
    if os.path.exists(os.path.join(root_dir, "ruff.toml")) or os.path.exists(os.path.join(root_dir, ".ruff.toml")):
        tools.append("Ruff")
        configs["Ruff"] = "ruff.toml"
    elif os.path.exists(os.path.join(root_dir, "pyproject.toml")):
        try:
            with open(os.path.join(root_dir, "pyproject.toml"), "r", encoding="utf-8") as f:
                if "[tool.ruff]" in f.read():
                    tools.append("Ruff")
                    configs["Ruff"] = "pyproject.toml [tool.ruff]"
        except Exception:
            pass

    # Black (Python)
    if os.path.exists(os.path.join(root_dir, "pyproject.toml")):
        try:
            with open(os.path.join(root_dir, "pyproject.toml"), "r", encoding="utf-8") as f:
                if "[tool.black]" in f.read():
                    tools.append("Black")
                    configs["Black"] = "pyproject.toml [tool.black]"
        except Exception:
            pass

    # Rustfmt / Clippy
    if os.path.exists(os.path.join(root_dir, "rustfmt.toml")) or os.path.exists(os.path.join(root_dir, ".rustfmt.toml")):
        tools.append("rustfmt")
        configs["rustfmt"] = "rustfmt.toml"

    # Golangci-lint
    for f in [".golangci.yml", ".golangci.yaml", ".golangci.json", ".golangci.toml"]:
        if os.path.exists(os.path.join(root_dir, f)):
            tools.append("golangci-lint")
            configs["golangci-lint"] = f
            break

    # EditorConfig
    if os.path.exists(os.path.join(root_dir, ".editorconfig")):
        tools.append("EditorConfig")
        configs["EditorConfig"] = ".editorconfig"

    return {
        "tools": ", ".join(tools) if tools else "Standard / Unconfigured",
        "configs": configs,
    }


def detect_codebase_conventions(root_dir: str = ".") -> Dict[str, Any]:
    """Samples source files to analyze coding style, naming conventions, indentation, and imports."""
    root_dir = os.path.abspath(root_dir)
    
    ignored_dirs = {
        "node_modules", ".git", ".workflow", "dist", "build", "target", ".venv", "venv",
        "__pycache__", ".pytest_cache", ".next", ".turbo", "coverage", ".gemini", "out"
    }

    target_extensions = {".ts", ".tsx", ".js", ".jsx", ".py", ".rs", ".go", ".java", ".cs"}
    sampled_files: List[str] = []

    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in target_extensions:
                rel_path = os.path.relpath(os.path.join(root, file), root_dir)
                sampled_files.append(rel_path)
                if len(sampled_files) >= 40:
                    break
        if len(sampled_files) >= 40:
            break

    if not sampled_files:
        return {
            "file_naming": "kebab-case / snake_case",
            "indentation": "2 spaces",
            "quotes": "double quotes",
            "semicolons": "always",
            "variable_naming": "camelCase / snake_case",
            "import_style": "ES Module / standard",
            "type_annotations": "Standard / Typed",
            "samples_analyzed": 0,
        }

    # 1. Analyze File Naming Conventions
    file_styles = {"kebab-case": 0, "snake_case": 0, "camelCase": 0, "PascalCase": 0}
    for path in sampled_files:
        basename = os.path.splitext(os.path.basename(path))[0]
        if "_" in basename:
            file_styles["snake_case"] += 1
        elif "-" in basename:
            file_styles["kebab-case"] += 1
        elif basename[0].isupper() and not basename.isupper():
            file_styles["PascalCase"] += 1
        elif basename[0].islower() and any(c.isupper() for c in basename):
            file_styles["camelCase"] += 1
        else:
            file_styles["kebab-case"] += 1

    predominant_file_naming = max(file_styles, key=file_styles.get)

    # 2. Analyze Indentation, Quotes, Semicolons & Imports
    two_spaces = 0
    four_spaces = 0
    tabs = 0
    single_quotes = 0
    double_quotes = 0
    semicolons = 0
    no_semicolons = 0
    path_aliases = 0
    relative_imports = 0
    snake_vars = 0
    camel_vars = 0
    has_type_hints = False

    for rel_path in sampled_files[:25]:
        full_path = os.path.join(root_dir, rel_path)
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            continue

        ext = os.path.splitext(rel_path)[1].lower()

        for line in lines:
            # Indentation
            if line.startswith("  ") and not line.startswith("    "):
                two_spaces += 1
            elif line.startswith("    "):
                four_spaces += 1
            elif line.startswith("\t"):
                tabs += 1

            # Quotes
            single_quotes += line.count("'")
            double_quotes += line.count('"')

            # Semicolons (JS/TS)
            stripped = line.strip()
            if ext in {".ts", ".tsx", ".js", ".jsx"}:
                if stripped.endswith(";"):
                    semicolons += 1
                elif stripped and not stripped.startswith("//") and not stripped.startswith("/*") and not stripped.endswith("{") and not stripped.endswith("}") and not stripped.endswith(","):
                    no_semicolons += 1

            # Imports
            if "import " in line or "from " in line:
                if "@/" in line or "~/" in line or "@apps/" in line or "@packages/" in line:
                    path_aliases += 1
                elif "../" in line or "./" in line:
                    relative_imports += 1

            # Variable naming patterns
            if ext == ".py":
                if "def " in line or "=" in line:
                    if re.search(r"\b[a-z]+_[a-z0-9_]+\b", line):
                        snake_vars += 1
                if "-> " in line or ": str" in line or ": int" in line or ": Dict" in line or ": List" in line:
                    has_type_hints = True
            elif ext in {".ts", ".tsx", ".js", ".jsx"}:
                if re.search(r"\bconst\s+[a-z][a-zA-Z0-9]+\b", line) or re.search(r"\blet\s+[a-z][a-zA-Z0-9]+\b", line):
                    camel_vars += 1
                if ": " in line or "interface " in line or "type " in line:
                    has_type_hints = True

    # Compute predominant style
    if tabs > two_spaces and tabs > four_spaces:
        indent_style = "Tabs"
    elif four_spaces > two_spaces:
        indent_style = "4 spaces"
    else:
        indent_style = "2 spaces"

    quote_style = "Single quotes (')" if single_quotes > double_quotes else 'Double quotes (")'
    semi_style = "Always (Semicolons required)" if semicolons >= no_semicolons else "Never / Standard (No semicolons)"
    import_style = "Path aliases (@/*, ~/*)" if path_aliases > relative_imports else "Relative paths (./, ../)"
    var_style = "snake_case" if snake_vars > camel_vars else "camelCase (variables/functions), PascalCase (types/components)"
    type_style = "Strict TypeScript / Explicit Type Hints" if has_type_hints else "Standard / Inferred"

    return {
        "file_naming": predominant_file_naming,
        "indentation": indent_style,
        "quotes": quote_style,
        "semicolons": semi_style,
        "variable_naming": var_style,
        "import_style": import_style,
        "type_annotations": type_style,
        "samples_analyzed": len(sampled_files),
    }


def generate_coding_preferences(root_dir: str = ".") -> str:
    """Generates and updates .workflow/memory/coding_preferences.md."""
    root_dir = os.path.abspath(root_dir)
    wf_root = os.path.join(root_dir, ".workflow") if os.path.basename(root_dir) != ".workflow" else root_dir
    memory_dir = os.path.join(wf_root, "memory")
    os.makedirs(memory_dir, exist_ok=True)

    linters = detect_linters_and_formatters(root_dir)
    conventions = detect_codebase_conventions(root_dir)
    pref_file = os.path.join(memory_dir, "coding_preferences.md")
    legacy_pref = os.path.join(memory_dir, "00_coding_preferences.md")
    if os.path.exists(legacy_pref):
        try:
            os.remove(legacy_pref)
        except Exception:
            pass

    config_lines = "\n".join([f"- **{k}**: `{v}`" for k, v in linters["configs"].items()]) if linters["configs"] else "- *No explicit linter configs found; inferred from codebase.*"

    content = f"""# Codebase Style & Writing Preferences (Extracted by /workflow explore)

**Project Root**: `{os.path.basename(root_dir)}`  
**Last Extracted**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`  
**Source Files Analyzed**: `{conventions['samples_analyzed']} files sampled`

---

## 1. Linters, Formatters & Tooling
{config_lines}
- **Active Formatting Engines**: `{linters['tools']}`

---

## 2. File & Directory Naming Conventions
- **Primary File Naming Idiom**: `{conventions['file_naming']}` (e.g. `user-service.ts`, `data_loader.py`)
- **Type/Component Files**: `PascalCase` for React/Vue components (e.g. `UserProfile.tsx`), `kebab-case` or `snake_case` for modules.

---

## 3. Code Syntax & Formatting Preferences
- **Indentation**: `{conventions['indentation']}`
- **Quote Style**: `{conventions['quotes']}`
- **Semicolons**: `{conventions['semicolons']}`

---

## 4. Identifier & Variable Naming Idioms
- **Variables & Functions**: `{conventions['variable_naming']}`
- **Constants & Enums**: `SCREAMING_SNAKE_CASE` (e.g. `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT`)
- **Types, Interfaces & Classes**: `PascalCase` (e.g. `WorkflowState`, `UserEntity`)

---

## 5. Module Imports & Resolution Rules
- **Import Resolution**: `{conventions['import_style']}`
- **Type Imports**: Use explicit type imports (`import type {{ ... }}`) where applicable in TypeScript.

---

## 6. Type Safety & Testing Invariants
- **Type Annotations**: `{conventions['type_annotations']}`
- **TDD Workflow**: Always write failing unit/integration tests first before implementing green logic.
"""
    with open(pref_file, "w", encoding="utf-8") as f:
        f.write(content)

    return pref_file


def scan_codebase(root_dir: str = ".") -> Dict[str, Any]:
    """Scans repository workspace and deterministically detects polyglot stacks, test runners, and coding styles."""
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

        try:
            if os.path.exists(pyproject_path):
                with open(pyproject_path, "r", encoding="utf-8") as f:
                    content = f.read().lower()
                if "fastapi" in content:
                    frameworks.append("FastAPI")
                elif "django" in content:
                    frameworks.append("Django")
                elif "flask" in content:
                    frameworks.append("Flask")
                elif "langgraph" in content:
                    frameworks.append("LangGraph")
        except Exception:
            pass

        test_candidates.extend(["pytest", "python -m unittest", "uv run pytest"])
        has_explicit_test_script = True

    # 3. Check Rust ecosystem
    cargo_path = os.path.join(root_dir, "Cargo.toml")
    if os.path.exists(cargo_path):
        languages.append("Rust")
        package_managers.append("cargo")
        manifest_hashes["Cargo.toml"] = compute_file_hash(cargo_path)
        if not test_candidates or "cargo test" not in test_candidates:
            test_candidates = ["cargo test"]
            has_explicit_test_script = True
        else:
            test_candidates.append("cargo test")

    # 4. Check Go ecosystem
    go_mod_path = os.path.join(root_dir, "go.mod")
    if os.path.exists(go_mod_path):
        languages.append("Go")
        package_managers.append("go modules")
        manifest_hashes["go.mod"] = compute_file_hash(go_mod_path)
        if not test_candidates or "go test ./..." not in test_candidates:
            test_candidates = ["go test ./..."]
            has_explicit_test_script = True
        else:
            test_candidates.append("go test ./...")

    # 5. Check Java / Kotlin (Maven / Gradle)
    pom_path = os.path.join(root_dir, "pom.xml")
    gradle_path = os.path.join(root_dir, "build.gradle") or os.path.join(root_dir, "build.gradle.kts")
    if os.path.exists(pom_path):
        languages.append("Java")
        package_managers.append("maven")
        manifest_hashes["pom.xml"] = compute_file_hash(pom_path)
        if not test_candidates or "mvn test" not in test_candidates:
            test_candidates = ["mvn test"]
            has_explicit_test_script = True
        else:
            test_candidates.append("mvn test")
    elif os.path.exists(gradle_path):
        languages.append("Java / Kotlin")
        package_managers.append("gradle")
        manifest_hashes["build.gradle"] = compute_file_hash(gradle_path)
        if not test_candidates or "gradle test" not in test_candidates:
            test_candidates = ["gradle test"]
            has_explicit_test_script = True
        else:
            test_candidates.append("gradle test")

    # 6. Check .NET / C#
    csproj_files = glob.glob(os.path.join(root_dir, "*.csproj")) + glob.glob(os.path.join(root_dir, "**", "*.csproj"), recursive=True)
    if csproj_files:
        languages.append("C# / .NET")
        package_managers.append("dotnet")
        manifest_hashes[os.path.basename(csproj_files[0])] = compute_file_hash(csproj_files[0])
        if not test_candidates or "dotnet test" not in test_candidates:
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

    linters = detect_linters_and_formatters(root_dir)
    conventions = detect_codebase_conventions(root_dir)

    return {
        "project_name": os.path.basename(root_dir),
        "languages": ", ".join(list(dict.fromkeys(languages))),
        "frameworks": ", ".join(list(dict.fromkeys(frameworks))) if frameworks else "Custom / Standard",
        "package_manager": ", ".join(list(dict.fromkeys(package_managers))),
        "test_runner": primary_test_runner,
        "test_candidates": list(dict.fromkeys(test_candidates)),
        "has_explicit_test_script": has_explicit_test_script,
        "manifest_hashes": manifest_hashes,
        "linters": linters,
        "conventions": conventions,
        "scanned_at": datetime.now().isoformat(),
    }


def generate_master_context(root_dir: str = ".") -> str:
    """Scans repository and creates/updates .workflow/memory/project_context.md and coding_preferences.md."""
    root_dir = os.path.abspath(root_dir)
    wf_root = os.path.join(root_dir, ".workflow") if os.path.basename(root_dir) != ".workflow" else root_dir
    scan = scan_codebase(root_dir)
    memory_dir = os.path.join(wf_root, "memory")
    os.makedirs(memory_dir, exist_ok=True)
    master_file = os.path.join(memory_dir, "project_context.md")
    legacy_master = os.path.join(memory_dir, "00_project_context.md")
    if os.path.exists(legacy_master):
        try:
            os.remove(legacy_master)
        except Exception:
            pass

    # Generate or refresh coding_preferences.md
    pref_file = generate_coding_preferences(root_dir)

    manifest_lines = [f"{k}: `{v}`" for k, v in scan["manifest_hashes"].items()]
    manifest_str = " | ".join(manifest_lines) if manifest_lines else "None"

    content = f"""# Project Master Context & Architectural Invariants

**Project Name**: `{scan['project_name']}`  
**Last Updated**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`  
**Manifest Fingerprints**: {manifest_str}  
**Coding Preferences**: [coding_preferences.md](./coding_preferences.md)

---

## 1. Technology Stack & Runtimes
- **Primary Language(s)**: `{scan['languages']}`
- **Framework(s)**: `{scan['frameworks']}`
- **Package Manager**: `{scan['package_manager']}`
- **Test Runner & Suite**: `{scan['test_runner']}`
- **Linters & Formatters**: `{scan['linters']['tools']}`

---

## 2. Inferred Coding Conventions & Style
- **File Naming**: `{scan['conventions']['file_naming']}`
- **Indentation**: `{scan['conventions']['indentation']}`
- **Quotes**: `{scan['conventions']['quotes']}`
- **Semicolons**: `{scan['conventions']['semicolons']}`
- **Variables & Functions**: `{scan['conventions']['variable_naming']}`
- **Imports**: `{scan['conventions']['import_style']}`

---

## 3. Core Architectural Invariants & Rules
1. **Spec-Driven Architecture**: All functional features are declared in `.workflow/specs/<spec-name>/` and executed via TDD issues.
2. **Worktree Isolation**: Background workers run strictly inside dedicated `.workflow/worktrees/` instances.
3. **Quality Gate Compliance**: Tests must pass 100% with no security gate violations prior to merging.

---

## 4. Cumulative Decisions & Historical Rollup Log

| Date | Archetype | Decision / Milestone | Summary & Impact |
|---|---|---|---|
| {datetime.now().strftime('%Y-%m-%d')} | `explorer` | Stack & Style Survey | Initialized context for {scan['languages']} ({scan['frameworks']}). |
"""
    with open(master_file, "w", encoding="utf-8") as f:
        f.write(content)

    return master_file
