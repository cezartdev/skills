#!/usr/bin/env bash
# Cross-platform POSIX shell launcher for Workflow Suite with auto-detection.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNNER_PY="${SCRIPT_DIR}/workflow_runner.py"

# 1. Try Astral uv first (Recommended)
if command -v uv >/dev/null 2>&1; then
    exec uv run "${RUNNER_PY}" "$@"
fi

# 2. Try python3
if command -v python3 >/dev/null 2>&1; then
    exec python3 "${RUNNER_PY}" "$@"
fi

# 3. Try python
if command -v python >/dev/null 2>&1; then
    exec python "${RUNNER_PY}" "$@"
fi

echo "⚠️ Python or Astral uv not found on system." >&2
echo "Install uv (Recommended, standalone runner):" >&2
echo "  curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
exit 1
