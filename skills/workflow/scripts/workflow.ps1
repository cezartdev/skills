<#
.SYNOPSIS
  Cross-platform PowerShell launcher for Workflow Suite with automatic environment bootstrapping.
.DESCRIPTION
  Detects uv, py, or python on Windows and executes workflow_runner.py.
#>

param (
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArgs
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RunnerPy = Join-Path $ScriptDir "workflow_runner.py"

# 1. Try Astral uv first (Recommended)
if (Get-Command uv -ErrorAction SilentlyContinue) {
    & uv run $RunnerPy @ScriptArgs
    exit $LASTEXITCODE
}

# 2. Try Python 3 launcher (py)
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 $RunnerPy @ScriptArgs
    exit $LASTEXITCODE
}

# 3. Try standard python
if (Get-Command python -ErrorAction SilentlyContinue) {
    & python $RunnerPy @ScriptArgs
    exit $LASTEXITCODE
}

Write-Host "⚠️ Python or Astral uv not found on system." -ForegroundColor Yellow
Write-Host "Install uv (Recommended, standalone user-space runner):" -ForegroundColor Cyan
Write-Host "  powershell -ExecutionPolicy ByPass -c `"irm https://astral.sh/uv/install.ps1 | iex`"" -ForegroundColor Gray
Write-Host "Or install Python via WinGet:" -ForegroundColor Cyan
Write-Host "  winget install -e --id Python.Python.3.12" -ForegroundColor Gray
exit 1
