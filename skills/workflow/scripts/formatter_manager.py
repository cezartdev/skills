#!/usr/bin/env python3
"""Deterministic Polyglot Code Formatter & Linter Manager for the Workflow Suite.
Detects, configures, and deterministically executes code formatters (Ruff, Biome, Prettier, rustfmt, gofmt, dotnet format).
"""

import os
import sys
import json
import shutil
import subprocess
import argparse
from typing import Dict, Any, List, Optional, Tuple


FORMATTER_ECOSYSTEM_DEFAULTS = {
    "typescript": {
        "primary": "Biome",
        "command": ["pnpm", "dlx", "@biomejs/biome", "format", "--write"],
        "fallback_command": ["npx", "@biomejs/biome", "format", "--write"],
        "extensions": [".ts", ".tsx", ".js", ".jsx", ".json", ".jsonc"],
    },
    "javascript": {
        "primary": "Biome",
        "command": ["pnpm", "dlx", "@biomejs/biome", "format", "--write"],
        "fallback_command": ["npx", "@biomejs/biome", "format", "--write"],
        "extensions": [".js", ".jsx", ".mjs", ".cjs", ".json"],
    },
    "python": {
        "primary": "Ruff",
        "command": ["uv", "run", "ruff", "format"],
        "fallback_command": ["ruff", "format"],
        "extensions": [".py", ".pyi"],
    },
    "rust": {
        "primary": "rustfmt",
        "command": ["cargo", "fmt", "--"],
        "fallback_command": ["rustfmt"],
        "extensions": [".rs"],
    },
    "go": {
        "primary": "gofmt",
        "command": ["gofmt", "-w"],
        "fallback_command": ["gofmt", "-w"],
        "extensions": [".go"],
    },
    "csharp": {
        "primary": "dotnet format",
        "command": ["dotnet", "format", "--include"],
        "fallback_command": ["dotnet", "format"],
        "extensions": [".cs"],
    },
    "java": {
        "primary": "Spotless",
        "command": ["mvn", "spotless:apply"],
        "fallback_command": ["mvn", "spotless:apply"],
        "extensions": [".java"],
    },
}


def run_cmd(args: List[str], cwd: str = ".") -> Tuple[int, str, str]:
    """Runs a shell command safely in the specified directory."""
    try:
        res = subprocess.run(
            args,
            cwd=os.path.abspath(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def detect_available_formatters(root_dir: str = ".") -> Dict[str, Any]:
    """Inspects workspace configurations and installed binaries to detect active code formatters."""
    root_dir = os.path.abspath(root_dir)
    detected: Dict[str, Any] = {}

    # 1. Biome
    for f in ["biome.json", "biome.jsonc"]:
        if os.path.exists(os.path.join(root_dir, f)):
            detected["Biome"] = {
                "config": f,
                "command": ["pnpm", "dlx", "@biomejs/biome", "format", "--write"] if os.path.exists(os.path.join(root_dir, "pnpm-lock.yaml")) else ["npx", "@biomejs/biome", "format", "--write"],
                "ecosystem": "typescript/javascript",
                "extensions": [".ts", ".tsx", ".js", ".jsx", ".json", ".jsonc"],
            }
            break

    # 2. Prettier
    prettier_files = [
        ".prettierrc", ".prettierrc.json", ".prettierrc.js", ".prettierrc.cjs",
        "prettier.config.js", "prettier.config.cjs", "prettier.config.mjs"
    ]
    for f in prettier_files:
        if os.path.exists(os.path.join(root_dir, f)):
            detected["Prettier"] = {
                "config": f,
                "command": ["pnpm", "exec", "prettier", "--write"] if os.path.exists(os.path.join(root_dir, "pnpm-lock.yaml")) else ["npx", "prettier", "--write"],
                "ecosystem": "typescript/javascript",
                "extensions": [".ts", ".tsx", ".js", ".jsx", ".json", ".css", ".md"],
            }
            break

    # 3. Ruff (Python)
    if os.path.exists(os.path.join(root_dir, "ruff.toml")) or os.path.exists(os.path.join(root_dir, ".ruff.toml")):
        detected["Ruff"] = {
            "config": "ruff.toml",
            "command": ["uv", "run", "ruff", "format"],
            "ecosystem": "python",
            "extensions": [".py", ".pyi"],
        }
    elif os.path.exists(os.path.join(root_dir, "pyproject.toml")):
        try:
            with open(os.path.join(root_dir, "pyproject.toml"), "r", encoding="utf-8") as f:
                if "[tool.ruff]" in f.read():
                    detected["Ruff"] = {
                        "config": "pyproject.toml [tool.ruff]",
                        "command": ["uv", "run", "ruff", "format"],
                        "ecosystem": "python",
                        "extensions": [".py", ".pyi"],
                    }
        except Exception:
            pass

    # 4. Black (Python)
    if "Ruff" not in detected and os.path.exists(os.path.join(root_dir, "pyproject.toml")):
        try:
            with open(os.path.join(root_dir, "pyproject.toml"), "r", encoding="utf-8") as f:
                if "[tool.black]" in f.read():
                    detected["Black"] = {
                        "config": "pyproject.toml [tool.black]",
                        "command": ["uv", "run", "black"],
                        "ecosystem": "python",
                        "extensions": [".py"],
                    }
        except Exception:
            pass

    # 5. Rustfmt
    if os.path.exists(os.path.join(root_dir, "Cargo.toml")):
        detected["rustfmt"] = {
            "config": "Cargo.toml",
            "command": ["cargo", "fmt", "--"],
            "ecosystem": "rust",
            "extensions": [".rs"],
        }

    # 6. Gofmt
    if os.path.exists(os.path.join(root_dir, "go.mod")):
        detected["gofmt"] = {
            "config": "go.mod",
            "command": ["gofmt", "-w"],
            "ecosystem": "go",
            "extensions": [".go"],
        }

    # 7. Dotnet Format
    if any(f.endswith(".csproj") or f.endswith(".sln") for f in os.listdir(root_dir)):
        detected["dotnet format"] = {
            "config": "*.csproj",
            "command": ["dotnet", "format", "--include"],
            "ecosystem": "csharp",
            "extensions": [".cs"],
        }

    return detected


def get_preferred_formatter(root_dir: str = ".") -> Optional[Dict[str, Any]]:
    """Returns the primary active or inferred formatter definition for the workspace."""
    detected = detect_available_formatters(root_dir)
    if detected:
        # Prioritize Biome / Ruff / cargo fmt / gofmt
        for priority in ["Biome", "Prettier", "Ruff", "rustfmt", "gofmt", "dotnet format"]:
            if priority in detected:
                res = detected[priority]
                res["name"] = priority
                return res
        first_key = list(detected.keys())[0]
        res = detected[first_key]
        res["name"] = first_key
        return res

    # Fallback to ecosystem default based on root files
    root_files = os.listdir(root_dir) if os.path.exists(root_dir) else []
    if "package.json" in root_files:
        val = dict(FORMATTER_ECOSYSTEM_DEFAULTS["typescript"])
        val["name"] = val["primary"]
        return val
    elif "pyproject.toml" in root_files or "requirements.txt" in root_files:
        val = dict(FORMATTER_ECOSYSTEM_DEFAULTS["python"])
        val["name"] = val["primary"]
        return val
    elif "Cargo.toml" in root_files:
        val = dict(FORMATTER_ECOSYSTEM_DEFAULTS["rust"])
        val["name"] = val["primary"]
        return val
    elif "go.mod" in root_files:
        val = dict(FORMATTER_ECOSYSTEM_DEFAULTS["go"])
        val["name"] = val["primary"]
        return val

    return None


def format_worktree_code(target_worktree: str, files: Optional[List[str]] = None) -> Dict[str, Any]:
    """Executes the active or preferred code formatter strictly on files within the specified worktree."""
    target_worktree = os.path.abspath(target_worktree)
    if not os.path.exists(target_worktree):
        return {
            "status": "DIR_NOT_FOUND",
            "formatted": False,
            "message": f"Target worktree directory not found: {target_worktree}",
        }

    fmt = get_preferred_formatter(target_worktree)
    if not fmt:
        return {
            "status": "NO_FORMATTER_CONFIGURED",
            "formatted": False,
            "message": "No standard code formatter detected or configured for this stack.",
        }

    # Filter files by extensions if provided
    target_extensions = fmt.get("extensions", [])
    valid_files: List[str] = []
    if files:
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if not target_extensions or ext in target_extensions:
                rel = os.path.relpath(os.path.join(target_worktree, f) if not os.path.isabs(f) else f, target_worktree)
                if os.path.exists(os.path.join(target_worktree, rel)):
                    valid_files.append(rel)

    # Build execution command
    cmd = list(fmt.get("command", []))
    if valid_files:
        cmd.extend(valid_files)
    else:
        # Format entire directory
        if fmt.get("name") in ["Ruff", "Black"]:
            cmd.append(".")
        elif fmt.get("name") in ["Biome", "Prettier"]:
            cmd.append(".")
        elif fmt.get("name") == "gofmt":
            cmd.append(".")

    code, out, err = run_cmd(cmd, cwd=target_worktree)
    if code != 0 and fmt.get("fallback_command"):
        # Attempt fallback command
        fallback_cmd = list(fmt["fallback_command"])
        if valid_files:
            fallback_cmd.extend(valid_files)
        else:
            fallback_cmd.append(".")
        code, out, err = run_cmd(fallback_cmd, cwd=target_worktree)

    success = (code == 0)
    return {
        "status": "SUCCESS" if success else "FORMATTER_ERROR",
        "formatted": success,
        "formatter": fmt.get("name", "Unknown"),
        "command_executed": " ".join(cmd),
        "target_worktree": target_worktree,
        "files_targeted": valid_files if valid_files else "all",
        "message": out if success else err,
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="formatter_manager.py", description="Deterministic Polyglot Code Formatter Manager")
    parser.add_argument("--json", action="store_true", help="JSON output")
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommands")

    # detect
    p_det = subparsers.add_parser("detect", help="Detect available code formatters in directory")
    p_det.add_argument("target_dir", nargs="?", default=".", help="Target workspace directory")

    # run
    p_run = subparsers.add_parser("run", help="Execute active code formatter on directory or files")
    p_run.add_argument("target_dir", nargs="?", default=".", help="Target workspace or worktree directory")
    p_run.add_argument("--files", nargs="*", help="Specific relative file paths to format")

    args = parser.parse_args()
    if not args.subcommand:
        parser.print_help()
        return 0

    if args.subcommand == "detect":
        detected = detect_available_formatters(args.target_dir)
        preferred = get_preferred_formatter(args.target_dir)
        res = {
            "target_dir": os.path.abspath(args.target_dir),
            "detected": detected,
            "preferred": preferred,
        }
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print("=" * 90)
            print(" 🎨 DETECTED CODE FORMATTERS")
            print("=" * 90)
            if detected:
                for k, v in detected.items():
                    print(f" - {k:<16} │ Config: {v.get('config')} │ Cmd: {' '.join(v.get('command', []))}")
            else:
                print(" - Standard / Unconfigured (No explicit formatter config detected)")
            if preferred:
                print("-" * 90)
                print(f" Preferred: {preferred.get('name')} ({' '.join(preferred.get('command', []))})")
            print("=" * 90)
        return 0

    elif args.subcommand == "run":
        res = format_worktree_code(args.target_dir, files=args.files)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            if res.get("formatted"):
                print(f"✅ Formatted with {res.get('formatter')}: {res.get('command_executed')}")
            else:
                print(f"⚠️  Format notice: {res.get('message')}")
        return 0 if res.get("formatted") else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
