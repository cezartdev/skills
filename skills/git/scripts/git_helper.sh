#!/usr/bin/env bash
# Git Suite POSIX launcher (Linux / macOS)
# Tier 1: Uses Astral uv if available; Tier 2: Falls back to python3 / python

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_SCRIPT="$SCRIPT_DIR/git_helper.py"

if command -v uv >/dev/null 2>&1; then
    exec uv run "$TARGET_SCRIPT" "$@"
elif command -v python3 >/dev/null 2>&1; then
    exec python3 "$TARGET_SCRIPT" "$@"
elif command -v python >/dev/null 2>&1; then
    exec python "$TARGET_SCRIPT" "$@"
else
    echo "Error: Python runtime not found. Please install Astral uv (https://astral.sh/uv) or Python >= 3.8." >&2
    exit 1
fi
