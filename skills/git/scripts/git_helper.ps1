# Git Suite Windows PowerShell launcher
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TargetScript = Join-Path $ScriptDir "git_helper.py"

if (Get-Command uv -ErrorAction SilentlyContinue) {
    & uv run $TargetScript @Arguments
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python $TargetScript @Arguments
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py $TargetScript @Arguments
} else {
    Write-Error "Error: Python runtime not found. Please install uv (e.g. 'pip install uv') or Python >= 3.8."
    exit 1
}
