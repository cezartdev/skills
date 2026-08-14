# Git Suite Windows PowerShell launcher
# Tier 1: Uses Astral uv if available; Tier 2: Falls back to python / py

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TargetScript = Join-Path $ScriptDir "git_helper.py"

if (Get-Command uv -ErrorAction SilentlyContinue) {
    & uv run $TargetScript $args
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python $TargetScript $args
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py $TargetScript $args
} else {
    Write-Error "Error: Python runtime not found. Please install Astral uv (https://astral.sh/uv) or Python >= 3.8."
    exit 1
}
