# ==============================================================================
# git_helper.ps1 - Deterministic Git Suite runner for AI agents & developers.
# Native Windows PowerShell Implementation (PowerShell 5.1+ / PowerShell 7+)
#
# High-frequency usage:
#   pwsh git_helper.ps1 "<message>"          (commit + push to origin /git default)
#   pwsh git_helper.ps1 commit "<message>"   (local commit only /git commit)
#
# Subcommands:
#   commit    : Security scan + 10-step message validation + local git commit
#   sync      : Security scan + validation + commit + safe push to remote
#   status    : Working tree summary, unpushed commits, and security scan
#   draft     : Working tree status, security scan, and smart commit suggestion
#   validate  : Pre-flight commit message validator (10-step gate)
#   branch    : Standardized branch creation enforcing conventional prefixes
#   undo      : Safe soft reset of last commit (preserves staged changes)
#   audit     : Audit past N commits for Conventional Commits compliance
#   check-env : Environment diagnostics (Git, author, PowerShell/Windows)
# ==============================================================================

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$CommandOrMessage,

    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs,

    [Alias("m")]
    [string]$Message,

    [Alias("t")]
    [string]$Type,

    [Alias("s")]
    [string]$Scope,

    [Alias("b")]
    [string[]]$Bullet,

    [string]$Raw,

    [Alias("n")]
    [int]$Limit = 10,

    [switch]$Json,

    [switch]$Help
)

$ErrorActionPreference = "Stop"

# ------------------------------------------------------------------------------
# Constants & Whitelists
# ------------------------------------------------------------------------------

$script:AllowedTypes = @("feat", "fix", "docs", "refactor", "chore", "test")

$script:CommonImperativeVerbs = @(
    "add", "adjust", "align", "allow", "apply", "author", "bump", "clarify",
    "clean", "configure", "consolidate", "correct", "create", "decouple",
    "define", "deprecate", "disable", "document", "downgrade", "enable",
    "enforce", "ensure", "expand", "expose", "extract", "fix", "format",
    "handle", "implement", "improve", "include", "init", "initialize",
    "integrate", "introduce", "migrate", "optimize", "organize", "patch",
    "prevent", "publish", "refactor", "release", "remove", "rename",
    "reorganize", "resolve", "revert", "revise", "rewrite", "set", "setup",
    "simplify", "split", "standardize", "streamline", "structure", "support",
    "sync", "synchronize", "test", "update", "upgrade", "validate", "verify"
)

# Allowed env templates (explicit exception for .env.example, etc.)
$script:AllowedEnvTemplates = @(".env.example", ".env.sample", ".env.template", ".env.dist", ".env.ci")

$script:LargeFileThresholdBytes = 10 * 1024 * 1024  # 10 MB

# ------------------------------------------------------------------------------
# Git Helper
# ------------------------------------------------------------------------------

function Invoke-GitCommand {
    param([string[]]$GitArgs)
    $pinfo = New-Object System.Diagnostics.ProcessStartInfo
    $pinfo.FileName = "git"
    $pinfo.Arguments = ($GitArgs -join " ")
    $pinfo.RedirectStandardOutput = $true
    $pinfo.RedirectStandardError = $true
    $pinfo.UseShellExecute = $false
    $pinfo.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $pinfo.StandardErrorEncoding = [System.Text.Encoding]::UTF8

    try {
        $proc = [System.Diagnostics.Process]::Start($pinfo)
        $stdout = $proc.StandardOutput.ReadToEnd()
        $stderr = $proc.StandardError.ReadToEnd()
        $proc.WaitForExit()
        return [PSCustomObject]@{
            ExitCode = $proc.ExitCode
            StdOut   = $stdout.Trim()
            StdErr   = $stderr.Trim()
        }
    } catch {
        return [PSCustomObject]@{
            ExitCode = 127
            StdOut   = ""
            StdErr   = "Git command failed to execute: $_"
        }
    }
}

# ------------------------------------------------------------------------------
# Tier 1: Security & Hygiene Gates
# ------------------------------------------------------------------------------

function Test-Security {
    $violations = @()
    $warnings = @()

    $res = Invoke-GitCommand @("diff", "--cached", "--name-only")
    if ($res.ExitCode -ne 0 -or [string]::IsNullOrWhiteSpace($res.StdOut)) {
        return [PSCustomObject]@{
            Passed     = $true
            Violations = @()
            Warnings   = @()
        }
    }

    $stagedFiles = $res.StdOut -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

    foreach ($filepath in $stagedFiles) {
        $filename = [System.IO.Path]::GetFileName($filepath)

        # 1. Environment files check with .env.example exception
        if ($filename -match '^\.env(\..+)?$') {
            if ($script:AllowedEnvTemplates -contains $filename) {
                # Allowed template
            } else {
                $violations += "$filepath`: Matches sensitive file pattern '^\.env(\..+)?$' (untracked environment file)"
            }
        # 2. Cryptographic keys and certificates
        } elseif ($filename -match '\.(pem|key|pfx|p12|keystore)$') {
            $violations += "$filepath`: Sensitive cryptographic key/certificate file"
        # 3. SSH keys
        } elseif ($filename -match '^id_(rsa|ed25519)(\.pub)?$') {
            $violations += "$filepath`: Sensitive SSH key file"
        # 4. Credential files
        } elseif ($filename -match '(credential|service-account|client_secret).*\.json$') {
            $violations += "$filepath`: Sensitive credentials or service account JSON"
        # 5. Local database files
        } elseif ($filename -match '\.(sqlite|db)$') {
            $violations += "$filepath`: Local SQLite or database binary file"
        }

        # 6. File size and binary warnings
        if (Test-Path $filepath -PathType Leaf) {
            $fileInfo = Get-Item $filepath
            if ($fileInfo.Length -gt $script:LargeFileThresholdBytes) {
                $mb = [math]::Round($fileInfo.Length / (1024 * 1024), 1)
                $warnings += "$filepath`: Large file ($($mb)MB) exceeds 10MB threshold"
            }
            $ext = $fileInfo.Extension.TrimStart(".").ToLower()
            if (@("zip", "tar", "gz", "tgz", "rar", "7z", "iso", "bin", "exe", "dmg") -contains $ext) {
                $warnings += "$filepath`: Binary archive or executable format ('.$ext')"
            }
        }
    }

    # 7. Scan staged diff additions for secret tokens & merge conflict markers
    $diffRes = Invoke-GitCommand @("diff", "--cached", "-U0")
    if ($diffRes.ExitCode -eq 0 -and -not [string]::IsNullOrWhiteSpace($diffRes.StdOut)) {
        $currentFile = "unknown"
        $diffLines = $diffRes.StdOut -split "`r?`n"
        foreach ($line in $diffLines) {
            if ($line -match '^\+\+\+ b/(.*)') {
                $currentFile = $Matches[1]
                continue
            }
            if ($line -match '^\+[^\+]') {
                $addedContent = $line.Substring(1)
                $trimmed = $addedContent.Trim()

                # Conflict markers
                if ($trimmed -match '^<{7}\s' -or $trimmed -match '^={7}$' -or $trimmed -match '^>{7}\s') {
                    $violations += "$currentFile`: Unresolved merge conflict marker detected: '$trimmed'"
                    continue
                }
                # Cryptographic private keys
                if ($addedContent -match '-----BEGIN ([A-Z]+ )?PRIVATE KEY-----') {
                    $violations += "$currentFile`: Detected potential secret: Private cryptographic key block"
                    continue
                }
                # AWS Access Key ID
                if ($addedContent -match '(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}') {
                    $violations += "$currentFile`: Detected potential secret: AWS Access Key ID"
                    continue
                }
                # Generic secret / token assignment
                if ($addedContent -match '(?i)(api[_-]?key|access[_-]?token|secret[_-]?key|private[_-]?token|auth[_-]?token)\s*=\s*[''"][a-zA-Z0-9_\-]{20,}[''"]') {
                    $violations += "$currentFile`: Detected potential secret: Generic API secret/token assignment"
                    continue
                }
            }
        }
    }

    return [PSCustomObject]@{
        Passed     = ($violations.Count -eq 0)
        Violations = $violations
        Warnings   = $warnings
    }
}

# ------------------------------------------------------------------------------
# Tier 2: 10-Step Conventional Commits Validation Gate
# ------------------------------------------------------------------------------

function Test-CommitMessage {
    param([string]$FullMessage)

    $reports = [System.Collections.Generic.List[PSCustomObject]]::new()
    $passed = $true

    if ([string]::IsNullOrWhiteSpace($FullMessage)) {
        $reports.Add([PSCustomObject]@{
            Step    = 1
            Name    = "validate_presence"
            Passed  = $false
            Message = "Commit message is completely empty"
        })
        return [PSCustomObject]@{ Passed = $false; Reports = $reports }
    }

    $lines = $FullMessage -split "`r?`n"
    $header = $lines[0].Trim()
    $bodyLines = @()
    if ($lines.Count -gt 1) {
        for ($i = 1; $i -lt $lines.Count; $i++) {
            $b = $lines[$i].Trim()
            if (-not [string]::IsNullOrWhiteSpace($b)) {
                $bodyLines += $b
            }
        }
    }

    # Step 1: Structure: <type>(<scope>): <description> or <type>(<scope>)!: <description>
    $commitType = ""
    $scope = ""
    $isBreaking = $false
    $description = ""

    if ($header -match '^([a-zA-Z0-9_-]+)(\(([^)]+)\))?(!)?:\s*(.*)$') {
        $commitType = $Matches[1]
        $hasParens = $Matches[2]
        $scope = $Matches[3]
        $isBreaking = [bool]$Matches[4]
        $description = $Matches[5]

        if ([string]::IsNullOrWhiteSpace($hasParens) -or [string]::IsNullOrWhiteSpace($scope)) {
            $reports.Add([PSCustomObject]@{
                Step    = 1
                Name    = "validate_structure"
                Passed  = $false
                Message = "Scope is missing. Format must be `<type>(<scope>): <description>`"
            })
            return [PSCustomObject]@{ Passed = $false; Reports = $reports }
        }

        if ([string]::IsNullOrWhiteSpace($description)) {
            $reports.Add([PSCustomObject]@{
                Step    = 1
                Name    = "validate_structure"
                Passed  = $false
                Message = "Description is missing after scope and colon"
            })
            return [PSCustomObject]@{ Passed = $false; Reports = $reports }
        }

        $reports.Add([PSCustomObject]@{
            Step    = 1
            Name    = "validate_structure"
            Passed  = $true
            Message = "Structure parsed successfully: type='$commitType', scope='$scope'"
        })
    } else {
        $reports.Add([PSCustomObject]@{
            Step    = 1
            Name    = "validate_structure"
            Passed  = $false
            Message = "Header does not match standard pattern: `<type>(<scope>): <description>`"
        })
        return [PSCustomObject]@{ Passed = $false; Reports = $reports }
    }

    # Step 2: Type whitelist
    if ($script:AllowedTypes -contains $commitType) {
        $reports.Add([PSCustomObject]@{
            Step    = 2
            Name    = "validate_type"
            Passed  = $true
            Message = "Type '$commitType' is whitelisted"
        })
    } else {
        $passed = $false
        $allowedStr = ($script:AllowedTypes -join " ")
        $reports.Add([PSCustomObject]@{
            Step    = 2
            Name    = "validate_type"
            Passed  = $false
            Message = "Type '$commitType' is invalid. Strictly allowed types: [$allowedStr]"
        })
    }

    # Step 3: Scope format
    if ($scope -match '^[a-z0-9]+(-[a-z0-9]+)*$') {
        $reports.Add([PSCustomObject]@{
            Step    = 3
            Name    = "validate_scope"
            Passed  = $true
            Message = "Scope '$scope' is valid kebab-case"
        })
    } else {
        $passed = $false
        $reports.Add([PSCustomObject]@{
            Step    = 3
            Name    = "validate_scope"
            Passed  = $false
            Message = "Scope '$scope' must be lowercase alphanumeric or kebab-case (e.g. 'git', 'workflow')"
        })
    }

    # Step 4: Header length
    if ($header.Length -le 120) {
        $reports.Add([PSCustomObject]@{
            Step    = 4
            Name    = "validate_header_length"
            Passed  = $true
            Message = "Header length ($($header.Length)/120 chars) within limit"
        })
    } else {
        $passed = $false
        $reports.Add([PSCustomObject]@{
            Step    = 4
            Name    = "validate_header_length"
            Passed  = $false
            Message = "Header length ($($header.Length) chars) exceeds maximum limit of 120 chars"
        })
    }

    # Step 5: Description length
    if ($description.Length -ge 10) {
        $reports.Add([PSCustomObject]@{
            Step    = 5
            Name    = "validate_description_length"
            Passed  = $true
            Message = "Description ($($description.Length) chars >= 10) is sufficiently detailed"
        })
    } else {
        $passed = $false
        $reports.Add([PSCustomObject]@{
            Step    = 5
            Name    = "validate_description_length"
            Passed  = $false
            Message = "Description ($($description.Length) chars) is too short. Minimum required is 10 chars"
        })
    }

    # Step 6: No trailing period
    if ($header.EndsWith(".")) {
        $passed = $false
        $reports.Add([PSCustomObject]@{
            Step    = 6
            Name    = "validate_no_trailing_period"
            Passed  = $false
            Message = "Header line must not end with a period ('.')"
        })
    } else {
        $reports.Add([PSCustomObject]@{
            Step    = 6
            Name    = "validate_no_trailing_period"
            Passed  = $true
            Message = "No trailing period in header"
        })
    }

    # Step 7: English imperative verb
    $descWords = $description.Trim() -split '\s+'
    $firstWord = $descWords[0]
    $firstWordLower = $firstWord.ToLower()

    if ($script:CommonImperativeVerbs -contains $firstWordLower) {
        $reports.Add([PSCustomObject]@{
            Step    = 7
            Name    = "validate_english_imperative_verb"
            Passed  = $true
            Message = "Leading verb '$firstWordLower' is an approved English imperative verb"
        })
    } elseif ($firstWordLower -match '(ed|ing)$') {
        $passed = $false
        $reports.Add([PSCustomObject]@{
            Step    = 7
            Name    = "validate_english_imperative_verb"
            Passed  = $false
            Message = "Leading word '$firstWord' appears to be past tense or gerund. Use imperative present tense (e.g. 'add', 'update', 'fix')"
        })
    } elseif ($firstWordLower -match '(es|s)$' -and $firstWordLower -notmatch '(pass|process)$') {
        $passed = $false
        $reports.Add([PSCustomObject]@{
            Step    = 7
            Name    = "validate_english_imperative_verb"
            Passed  = $false
            Message = "Leading word '$firstWord' appears to be 3rd-person singular or plural. Use imperative present tense (e.g. 'add', 'update', 'fix')"
        })
    } else {
        $passed = $false
        $reports.Add([PSCustomObject]@{
            Step    = 7
            Name    = "validate_english_imperative_verb"
            Passed  = $false
            Message = "Leading word '$firstWord' is not a recognized English imperative verb. Examples: add, fix, update, implement, refactor..."
        })
    }

    # Step 8: Casing and spacing
    $casingOk = $true
    $firstChar = $description.Substring(0, 1)
    if ($firstChar -cmatch '^[A-Z]') {
        if ($firstWord -notmatch '^[A-Z0-9]+$' -or $firstWord.Length -lt 2) {
            $casingOk = $false
            $suggested = $firstChar.ToLower() + $description.Substring(1)
            $passed = $false
            $reports.Add([PSCustomObject]@{
                Step    = 8
                Name    = "validate_casing_and_spacing"
                Passed  = $false
                Message = "Description should start with lowercase letter: '$suggested'"
            })
        }
    }

    if ($casingOk) {
        if ($description -match '\s{2,}') {
            $passed = $false
            $reports.Add([PSCustomObject]@{
                Step    = 8
                Name    = "validate_casing_and_spacing"
                Passed  = $false
                Message = "Description contains multiple consecutive spaces; use single normal spaces"
            })
        } elseif ($description -notmatch '\s' -and $description -match '_') {
            $passed = $false
            $reports.Add([PSCustomObject]@{
                Step    = 8
                Name    = "validate_casing_and_spacing"
                Passed  = $false
                Message = "Description '$description' looks like snake_case. Use standard space-separated words"
            })
        } else {
            $reports.Add([PSCustomObject]@{
                Step    = 8
                Name    = "validate_casing_and_spacing"
                Passed  = $true
                Message = "Casing and spacing format are clean"
            })
        }
    }

    # Step 9: Body bullets
    $bulletsOk = $true
    if ($bodyLines.Count -gt 0) {
        $bIdx = 0
        foreach ($bLine in $bodyLines) {
            $bIdx++
            if ($bLine -notmatch '^-\s' -and $bLine -notmatch '^BREAKING CHANGE:') {
                $bulletsOk = $false
                $passed = $false
                $reports.Add([PSCustomObject]@{
                    Step    = 9
                    Name    = "validate_body_bullets"
                    Passed  = $false
                    Message = "Body line $bIdx does not start with bullet '- ': '$bLine'"
                })
                break
            }
            if ($bLine.Length -gt 120) {
                $bulletsOk = $false
                $passed = $false
                $reports.Add([PSCustomObject]@{
                    Step    = 9
                    Name    = "validate_body_bullets"
                    Passed  = $false
                    Message = "Body bullet $bIdx exceeds 120 chars ($($bLine.Length) chars)"
                })
                break
            }
        }
        if ($bulletsOk) {
            $reports.Add([PSCustomObject]@{
                Step    = 9
                Name    = "validate_body_bullets"
                Passed  = $true
                Message = "Body bullets ($($bodyLines.Count) lines) formatted correctly"
            })
        }
    } else {
        $reports.Add([PSCustomObject]@{
            Step    = 9
            Name    = "validate_body_bullets"
            Passed  = $true
            Message = "No body lines provided (optional)"
        })
    }

    # Step 10: Breaking change footer
    $bcOk = $true
    foreach ($bLine in $bodyLines) {
        if ($bLine -match '^BREAKING CHANGE:\s*(.*)') {
            $bcDesc = $Matches[1].Trim()
            if ($bcDesc.Length -lt 5) {
                $bcOk = $false
                $passed = $false
                $reports.Add([PSCustomObject]@{
                    Step    = 10
                    Name    = "validate_breaking_change"
                    Passed  = $false
                    Message = "BREAKING CHANGE description is too short"
                })
                break
            }
        }
    }
    if ($bcOk) {
        $reports.Add([PSCustomObject]@{
            Step    = 10
            Name    = "validate_breaking_change"
            Passed  = $true
            Message = "Breaking change footer specification valid"
        })
    }

    return [PSCustomObject]@{
        Passed  = $passed
        Reports = $reports
    }
}

# ------------------------------------------------------------------------------
# Report Printing
# ------------------------------------------------------------------------------

function Show-ValidationReport {
    param([string]$Header, [PSCustomObject]$ValidationResult)

    Write-Host "======================================================================"
    Write-Host " COMMIT MESSAGE PRE-FLIGHT VALIDATION REPORT"
    Write-Host "======================================================================"
    Write-Host "Candidate Header: $Header"
    Write-Host "----------------------------------------------------------------------"
    foreach ($r in $ValidationResult.Reports) {
        $stat = if ($r.Passed) { "[PASS]" } else { "[FAIL]" }
        $stepStr = "{0,-2}" -f $r.Step
        $nameStr = "{0,-35}" -f $r.Name
        Write-Host "Step $stepStr/10 $nameStr $stat : $($r.Message)"
    }
    Write-Host "======================================================================"
    if ($ValidationResult.Passed) {
        Write-Host ">>> RESULT: 100% VALIDATED. Message is safe for git commit."
    } else {
        Write-Host ">>> RESULT: VALIDATION FAILED. Please resolve errors before committing."
    }
    Write-Host "======================================================================"
}

# ------------------------------------------------------------------------------
# Inference Engine
# ------------------------------------------------------------------------------

function Get-InferredScopeAndType {
    $res = Invoke-GitCommand @("status", "--porcelain")
    if ($res.ExitCode -ne 0 -or [string]::IsNullOrWhiteSpace($res.StdOut)) {
        return @{ Scope = "root"; Type = "chore" }
    }

    $lines = $res.StdOut -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    $files = @()
    foreach ($l in $lines) {
        if ($l.Length -gt 3) {
            $files += $l.Substring(3).Trim()
        }
    }

    if ($files.Count -eq 0) {
        return @{ Scope = "root"; Type = "chore" }
    }

    $allDocs = $true
    $allTests = $true
    $allConfigs = $true

    foreach ($f in $files) {
        if ($f -notmatch '\.md$' -and $f -notmatch '^docs/') { $allDocs = $false }
        if ($f -notmatch 'test' -and $f -notmatch '\.spec\.[a-z]+$' -and $f -notmatch '\.test\.[a-z]+$') { $allTests = $false }
        if ($f -notin @("package.json", "pnpm-lock.yaml", "pyproject.toml", ".gitignore") -and $f -notmatch '^\.github/') { $allConfigs = $false }
    }

    $inferredType = "feat"
    if ($allDocs) { $inferredType = "docs" }
    elseif ($allTests) { $inferredType = "test" }
    elseif ($allConfigs) { $inferredType = "chore" }

    $targetFile = $files[0].Replace("\", "/")
    $inferredScope = "root"

    if ($targetFile -match 'skills/([^/]+)') {
        $inferredScope = $Matches[1]
    } elseif ($targetFile -match 'docs/([^/]+)') {
        $inferredScope = $Matches[1]
    } elseif ($targetFile -match '^\.changeset/') {
        $inferredScope = "release"
    } elseif ($targetFile -match '^\.github/') {
        $inferredScope = if ($targetFile -match 'release') { "release" } else { "ci" }
    } elseif ($targetFile -in @("package.json", "pnpm-lock.yaml", "pyproject.toml")) {
        $inferredScope = "deps"
    } else {
        $parts = $targetFile.Split("/")
        if ($parts.Count -gt 1) {
            $inferredScope = ($parts[0].ToLower() -replace '[^a-z0-9-]', '-').Trim("-")
        }
    }

    return @{ Scope = $inferredScope; Type = $inferredType }
}

# ------------------------------------------------------------------------------
# Subcommands Implementation
# ------------------------------------------------------------------------------

function Invoke-ValidateCmd {
    param([string]$Message, [bool]$AsJson)

    $res = Test-CommitMessage $Message
    $header = ($Message -split "`r?`n")[0].Trim()

    if ($AsJson) {
        $outputObj = [PSCustomObject]@{
            passed  = $res.Passed
            header  = $header
            reports = $res.Reports
        }
        $outputObj | ConvertTo-Json -Depth 5
    } else {
        Show-ValidationReport $header $res
    }

    if (-not $res.Passed) { exit 1 }
}

function Invoke-DraftCmd {
    param([bool]$AsJson)

    $statusRes = Invoke-GitCommand @("status", "--porcelain")
    if ($statusRes.ExitCode -ne 0) {
        Write-Error "Error checking git status: $($statusRes.StdErr)"
        exit $statusRes.ExitCode
    }

    if ([string]::IsNullOrWhiteSpace($statusRes.StdOut)) {
        if ($AsJson) {
            @{ status = "clean"; staged_files = @(); unstaged_files = @() } | ConvertTo-Json
        } else {
            Write-Host "Working tree is completely clean. Nothing to commit."
        }
        return
    }

    $staged = @()
    $unstaged = @()
    $lines = $statusRes.StdOut -split "`r?`n"
    foreach ($l in $lines) {
        if ($l.Length -lt 3) { continue }
        $idx = $l.Substring(0, 1)
        $wrk = $l.Substring(1, 1)
        $f = $l.Substring(3).Trim()
        if ($idx -match '[MADR]') { $staged += $f }
        if ($wrk -match '[MD]' -or $idx -eq '?') { $unstaged += $f }
    }

    $sec = Test-Security
    $inference = Get-InferredScopeAndType

    if ($AsJson) {
        [PSCustomObject]@{
            staged_count       = $staged.Count
            unstaged_count     = $unstaged.Count
            security_passed    = $sec.Passed
            inferred_scope     = $inference.Scope
            inferred_type      = $inference.Type
            suggested_template = "$($inference.Type)($($inference.Scope)): <imperative_verb> <description>"
        } | ConvertTo-Json
        return
    }

    Write-Host "======================================================================"
    Write-Host " GIT STATUS SUMMARY & DRAFT SUGGESTIONS"
    Write-Host "======================================================================"
    Write-Host "Staged files ($($staged.Count)):"
    foreach ($s in $staged) { Write-Host "  + $s" }
    if ($staged.Count -eq 0) { Write-Host "  (No files currently staged. Use 'git add <files>' first)" }

    Write-Host "`nUnstaged/Untracked files ($($unstaged.Count)):"
    foreach ($u in $unstaged) { Write-Host "  - $u" }

    Write-Host "`n--- Security & Hygiene Pre-Scan ---"
    if ($sec.Passed) {
        Write-Host "[PASS] No sensitive files, tokens, or merge conflict markers detected."
        Write-Host "       (Note: .env.example / templates are explicitly allowed)"
    } else {
        Write-Host "[FAIL] Security violations found:"
        foreach ($v in $sec.Violations) { Write-Host "  ! $v" }
    }

    if ($sec.Warnings.Count -gt 0) {
        Write-Host "`n--- Warnings ---"
        foreach ($w in $sec.Warnings) { Write-Host "  ? $w" }
    }

    Write-Host "`n--- Smart Suggestions ---"
    Write-Host "Inferred Scope: '$($inference.Scope)' | Inferred Type: '$($inference.Type)'"
    Write-Host "Template: $($inference.Type)($($inference.Scope)): <imperative_verb> <description (10-120 chars)>"
    Write-Host "======================================================================"
}

function Invoke-StatusCmd {
    param([bool]$AsJson)

    $branchRes = Invoke-GitCommand @("branch", "--show-current")
    $branch = if ($branchRes.StdOut) { $branchRes.StdOut } else { "detached" }

    $statusRes = Invoke-GitCommand @("status", "-s")
    $unpushedRes = Invoke-GitCommand @("log", "@{u}..HEAD", "--oneline")

    $staged = @()
    $unstaged = @()
    if (-not [string]::IsNullOrWhiteSpace($statusRes.StdOut)) {
        foreach ($l in ($statusRes.StdOut -split "`r?`n")) {
            if ($l.Length -lt 3) { continue }
            $idx = $l.Substring(0, 1)
            $wrk = $l.Substring(1, 1)
            $f = $l.Substring(3).Trim()
            if ($idx -match '[MADR]') { $staged += $f }
            if ($wrk -match '[MD]' -or $idx -eq '?') { $unstaged += $f }
        }
    }

    $unpushed = @()
    if (-not [string]::IsNullOrWhiteSpace($unpushedRes.StdOut)) {
        $unpushed = ($unpushedRes.StdOut -split "`r?`n") | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    }

    $sec = Test-Security

    if ($AsJson) {
        [PSCustomObject]@{
            branch          = $branch
            staged_count    = $staged.Count
            unstaged_count  = $unstaged.Count
            unpushed_count  = $unpushed.Count
            security_passed = $sec.Passed
        } | ConvertTo-Json
        return
    }

    Write-Host "======================================================================"
    Write-Host " REPOSITORY STATUS OVERVIEW (Branch: $branch)"
    Write-Host "======================================================================"
    Write-Host "Staged changes   : $($staged.Count) files"
    foreach ($s in $staged) { Write-Host "  + $s" }
    Write-Host "Unstaged changes : $($unstaged.Count) files"
    foreach ($u in $unstaged) { Write-Host "  - $u" }
    Write-Host "Unpushed commits : $($unpushed.Count) commits"
    foreach ($c in $unpushed) { Write-Host "  * $c" }
    Write-Host "======================================================================"
}

function Invoke-CommitCmd {
    param([string]$FullMessage, [bool]$AsJson)

    $statusRes = Invoke-GitCommand @("status", "--porcelain")
    if ([string]::IsNullOrWhiteSpace($statusRes.StdOut)) {
        Write-Host "[NO CHANGES] Working tree is completely clean. No changes detected to commit."
        return
    }

    $diffRes = Invoke-GitCommand @("diff", "--cached", "--name-only")
    if ([string]::IsNullOrWhiteSpace($diffRes.StdOut)) {
        Write-Error "ERROR: [NO STAGED CHANGES] Changes exist in working tree, but none are staged.`nPlease stage files using 'git add <files>' first."
        exit 1
    }

    # 1. Tier 1: Security scan
    $sec = Test-Security
    if (-not $sec.Passed) {
        Write-Host "`n======================================================================"
        Write-Host " [SECURITY ALERT] Commit Aborted Due to Security Violations"
        Write-Host "======================================================================"
        foreach ($v in $sec.Violations) { Write-Host "  ! $v" }
        Write-Host "======================================================================"
        exit 1
    }

    # 2. Tier 2: Validation
    $val = Test-CommitMessage $FullMessage
    $header = ($FullMessage -split "`r?`n")[0].Trim()

    if (-not $AsJson) {
        Show-ValidationReport $header $val
    }

    if (-not $val.Passed) {
        Write-Error "ERROR: Commit aborted due to pre-flight validation failure."
        exit 1
    }

    if (-not $AsJson) {
        Write-Host "`nExecuting git commit..."
    }

    $commitRes = Invoke-GitCommand @("commit", "-m", $FullMessage)
    if ($commitRes.ExitCode -ne 0) {
        Write-Error "Git commit failed:`n$($commitRes.StdErr)`n$($commitRes.StdOut)"
        exit $commitRes.ExitCode
    }

    $logRes = Invoke-GitCommand @("log", "-1", "--stat")

    if ($AsJson) {
        [PSCustomObject]@{
            status  = "committed"
            message = $header
        } | ConvertTo-Json
    } else {
        Write-Host $commitRes.StdOut
        Write-Host "`nCommit successful! Latest commit verified:"
        Write-Host $logRes.StdOut
    }
}

function Invoke-SyncCmd {
    param([string]$FullMessage, [bool]$AsJson)

    Invoke-CommitCmd -FullMessage $FullMessage -AsJson $AsJson

    $branchRes = Invoke-GitCommand @("branch", "--show-current")
    $branch = if ($branchRes.StdOut) { $branchRes.StdOut } else { "HEAD" }

    if (-not $AsJson) {
        Write-Host "`n--- Syncing to Remote Repository ---"
        Write-Host "Pushing to origin/$branch..."
    }

    $pushRes = Invoke-GitCommand @("push", "origin", $branch)
    if ($pushRes.ExitCode -ne 0) {
        if ($pushRes.StdErr -match 'no upstream branch' -or $pushRes.StdErr -match 'set-upstream') {
            if (-not $AsJson) {
                Write-Host "Setting upstream tracking for branch '$branch'..."
            }
            $pushRes = Invoke-GitCommand @("push", "--set-upstream", "origin", $branch)
        }
    }

    if ($pushRes.ExitCode -ne 0) {
        Write-Error "Git push failed:`n$($pushRes.StdErr)`n$($pushRes.StdOut)"
        exit $pushRes.ExitCode
    }

    if ($AsJson) {
        [PSCustomObject]@{
            status = "synced"
            branch = $branch
        } | ConvertTo-Json
    } else {
        Write-Host "Successfully committed and pushed to origin/$branch!"
    }
}

function Invoke-BranchCmd {
    param([string]$BranchName, [bool]$AsJson)

    $validPrefixes = @("feat/", "fix/", "chore/", "docs/", "refactor/", "test/")
    $prefixOk = $false
    foreach ($p in $validPrefixes) {
        if ($BranchName.StartsWith($p)) {
            $prefixOk = $true
            break
        }
    }

    if (-not $prefixOk) {
        $err = "Branch '$BranchName' must start with one of: $($validPrefixes -join ' ')"
        if ($AsJson) {
            @{ error = $err } | ConvertTo-Json
        } else {
            Write-Error "ERROR: $err"
        }
        exit 1
    }

    $res = Invoke-GitCommand @("checkout", "-b", $BranchName)
    if ($res.ExitCode -ne 0) {
        Write-Error "Branch creation failed:`n$($res.StdErr)`n$($res.StdOut)"
        exit $res.ExitCode
    }

    if ($AsJson) {
        @{ status = "created"; branch = $BranchName } | ConvertTo-Json
    } else {
        Write-Host "Created and switched to branch '$BranchName' successfully."
    }
}

function Invoke-UndoCmd {
    param([bool]$AsJson)

    $logRes = Invoke-GitCommand @("log", "-1", "--oneline")
    if ([string]::IsNullOrWhiteSpace($logRes.StdOut)) {
        Write-Error "ERROR: No commits found to undo."
        exit 1
    }

    $resetRes = Invoke-GitCommand @("reset", "--soft", "HEAD~1")
    if ($resetRes.ExitCode -ne 0) {
        Write-Error "Undo failed:`n$($resetRes.StdErr)"
        exit $resetRes.ExitCode
    }

    if ($AsJson) {
        @{ status = "undone"; reverted_commit = $logRes.StdOut } | ConvertTo-Json
    } else {
        Write-Host "Undid commit: '$($logRes.StdOut)' (changes preserved in staging area)."
    }
}

function Invoke-AuditCmd {
    param([int]$AuditLimit, [bool]$AsJson)

    $logRes = Invoke-GitCommand @("log", "-n$AuditLimit", '--pretty=format:COMMIT:%h%nSUBJECT:%s%nBODY:%b%nEND_COMMIT')
    if ([string]::IsNullOrWhiteSpace($logRes.StdOut)) {
        Write-Error "No commit history found to audit."
        exit 1
    }

    $total = 0
    $compliantCount = 0
    $auditItems = [System.Collections.Generic.List[PSCustomObject]]::new()

    $curHash = ""
    $curSubject = ""
    $curBodyLines = @()
    $inBody = $false

    foreach ($line in ($logRes.StdOut -split "`r?`n")) {
        if ($line -match '^COMMIT:(.*)') {
            $curHash = $Matches[1]
            $curSubject = ""
            $curBodyLines = @()
            $inBody = $false
        } elseif ($line -match '^SUBJECT:(.*)') {
            $curSubject = $Matches[1]
            $inBody = $false
        } elseif ($line -eq 'BODY:') {
            $inBody = $true
        } elseif ($line -eq 'END_COMMIT') {
            if (-not [string]::IsNullOrWhiteSpace($curHash)) {
                $total++
                $fullMsg = $curSubject
                if ($curBodyLines.Count -gt 0) {
                    $bStr = ($curBodyLines -join "`n").Trim()
                    if (-not [string]::IsNullOrWhiteSpace($bStr)) {
                        $fullMsg += "`n`n$bStr"
                    }
                }

                $val = Test-CommitMessage $fullMsg
                if ($val.Passed) {
                    $compliantCount++
                    $auditItems.Add([PSCustomObject]@{
                        Hash     = $curHash
                        Passed   = $true
                        Subject  = $curSubject
                        Issues   = @()
                        Rewrite  = ""
                    })
                } else {
                    $failing = @()
                    foreach ($r in $val.Reports) {
                        if (-not $r.Passed) { $failing += $r.Message }
                    }

                    # Suggested rewrite
                    $suggested = ""
                    if ($curSubject -match '^([a-zA-Z0-9_-]+)(\(([^)]+)\))?(!)?:\s*(.*)$') {
                        $rawT = $Matches[1]
                        $rawS = $Matches[3]
                        $rawD = $Matches[5]
                        $cleanT = if ($script:AllowedTypes -contains $rawT) { $rawT } else { "chore" }
                        $cleanS = if ($rawS) { ($rawS.ToLower() -replace '[^a-z0-9-]', '-') } else { "general" }
                        $words = $rawD.Trim() -split '\s+'
                        $vFirst = if ($words.Count -gt 0) { $words[0].ToLower() } else { "update" }
                        if ($script:CommonImperativeVerbs -notcontains $vFirst) { $vFirst = "update" }
                        $vRest = if ($words.Count -gt 1) { ($words[1..($words.Count - 1)] -join " ").TrimEnd(".") } else { "changes" }
                        $suggested = "$cleanT($cleanS): $vFirst $vRest"
                    } else {
                        $words = $curSubject.TrimEnd(".")
                        $suggested = "chore(general): update $words"
                    }

                    $auditItems.Add([PSCustomObject]@{
                        Hash     = $curHash
                        Passed   = $false
                        Subject  = $curSubject
                        Issues   = $failing
                        Rewrite  = $suggested
                    })
                }
            }
            $curHash = ""
            $curSubject = ""
            $curBodyLines = @()
            $inBody = $false
        } elseif ($inBody) {
            $curBodyLines += $line
        }
    }

    $score = if ($total -gt 0) { [math]::Round(($compliantCount * 100.0) / $total, 1) } else { 100.0 }

    if ($AsJson) {
        [PSCustomObject]@{
            total_commits      = $total
            compliant_commits  = $compliantCount
            compliance_score   = $score
            audit              = $auditItems
        } | ConvertTo-Json -Depth 5
        return
    }

    Write-Host "======================================================================"
    Write-Host " GIT COMMIT HISTORY AUDIT & COMPLIANCE REPORT (Last $total Commits)"
    Write-Host "======================================================================"
    Write-Host "Analyzed: $total commits | Compliant: $compliantCount ($score%) | Non-compliant: $($total - $compliantCount)"
    Write-Host "----------------------------------------------------------------------"
    foreach ($item in $auditItems) {
        if ($item.Passed) {
            Write-Host "[PASS] $($item.Hash) $($item.Subject)"
        } else {
            Write-Host "[FAIL] $($item.Hash) `"$($item.Subject)`""
            foreach ($iss in $item.Issues) {
                Write-Host "       ! $iss"
            }
            if ($item.Rewrite) {
                Write-Host "       >>> Suggested Rewrite: $($item.Rewrite)"
            }
        }
    }
    Write-Host "======================================================================"
    Write-Host "Overall Compliance Score: $score/100"
    Write-Host "======================================================================"
}

function Invoke-CheckEnvCmd {
    param([bool]$AsJson)

    $gitRes = Invoke-GitCommand @("--version")
    $gitInstalled = ($gitRes.ExitCode -eq 0)

    $nameRes = Invoke-GitCommand @("config", "user.name")
    $emailRes = Invoke-GitCommand @("config", "user.email")
    $authorOk = (-not [string]::IsNullOrWhiteSpace($nameRes.StdOut) -and -not [string]::IsNullOrWhiteSpace($emailRes.StdOut))

    $allOk = ($gitInstalled -and $authorOk)

    if ($AsJson) {
        [PSCustomObject]@{
            all_ok      = $allOk
            git         = @{
                installed  = $gitInstalled
                version    = $gitRes.StdOut
                user_name  = $nameRes.StdOut
                user_email = $emailRes.StdOut
            }
            environment = @{
                powershell = $PSVersionTable.PSVersion.ToString()
                os         = [System.Environment]::OSVersion.ToString()
            }
        } | ConvertTo-Json
        if (-not $allOk) { exit 1 }
        return
    }

    Write-Host "======================================================================"
    Write-Host " ENVIRONMENT DIAGNOSTIC (NATIVE POWERSHELL GIT SUITE)"
    Write-Host "======================================================================"
    Write-Host "PowerShell     : $($PSVersionTable.PSVersion) [PASS]"
    if ($gitInstalled) {
        Write-Host "Git Executable : $($gitRes.StdOut) [PASS]"
    } else {
        Write-Host "Git Executable : NOT FOUND [FAIL]"
        Write-Host "  ! Install Git for Windows: winget install -e --id Git.Git"
    }

    if ($authorOk) {
        Write-Host "Git Author     : $($nameRes.StdOut) <$($emailRes.StdOut)> [PASS]"
    } else {
        Write-Host "Git Author     : Incomplete configuration [WARN]"
        if (-not $nameRes.StdOut) { Write-Host "  ! Missing user.name (run: git config --global user.name 'Your Name')" }
        if (-not $emailRes.StdOut) { Write-Host "  ! Missing user.email (run: git config --global user.email 'you@example.com')" }
    }
    Write-Host "======================================================================"
    Write-Host "All native runtime requirements checked (No Python required)."
    Write-Host "======================================================================"

    if (-not $allOk) { exit 1 }
}

# ------------------------------------------------------------------------------
# Help / Usage
# ------------------------------------------------------------------------------

function Show-Help {
    @"
git_helper.ps1 - Deterministic Git Suite runner for AI agents & developers.

High-Frequency Usage:
  pwsh git_helper.ps1 "<message>"          # Commit + push to remote (/git default)
  pwsh git_helper.ps1 commit "<message>"   # Commit local only (/git commit)
  pwsh git_helper.ps1 status               # Show staged, unstaged & security status
  pwsh git_helper.ps1 undo                 # Safely undo last commit (retains staging)

Subcommands:
  sync      Validate, commit and push to remote upstream branch
  commit    Validate and execute local git commit
  status    Overview of working tree, branch, unpushed commits, and security
  draft     Inspect git status, security scan, and suggest commit scopes/drafts
  validate  Validate a commit message string (10-step Conventional Commits)
  branch    Create and checkout branch enforcing conventional prefixes (feat/, fix/...)
  undo      Safe soft reset of last commit
  audit     Audit past N commits for Conventional Commits compliance
  check-env Diagnostic check of Git and environment

Message Options:
  "<message>"              Pass full commit message directly as argument
  -Message, -m <desc>      Imperative description (10-120 chars)
  -Type, -t <type>         Whitelisted commit type (feat, fix, docs, refactor, chore, test)
  -Scope, -s <scope>       Lowercase kebab-case scope
  -Bullet, -b <bullet>     Optional body bullet point (repeatable)
  -Raw <message>           Raw full commit message
  -Json                    Output machine-readable JSON format
"@
}

# ------------------------------------------------------------------------------
# Main Dispatcher
# ------------------------------------------------------------------------------

if ($Help) {
    Show-Help
    exit 0
}

$knownSubcommands = @("commit", "sync", "status", "draft", "validate", "branch", "undo", "audit", "check-env", "help")
$subcmd = ""
$targetMessage = ""

if ($knownSubcommands -contains $CommandOrMessage) {
    $subcmd = $CommandOrMessage
    if ($RemainingArgs -and $RemainingArgs.Count -gt 0) {
        $targetMessage = $RemainingArgs[0]
    }
} elseif (-not [string]::IsNullOrWhiteSpace($CommandOrMessage)) {
    # Direct message passed: defaults to sync (/git workflow)
    $subcmd = "sync"
    $targetMessage = $CommandOrMessage
} elseif ($Raw) {
    $subcmd = "sync"
    $targetMessage = $Raw
} elseif ($Message) {
    $subcmd = "sync"
} else {
    $subcmd = "draft"
}

switch ($subcmd) {
    "validate" {
        $msg = if ($Raw) { $Raw } elseif ($targetMessage) { $targetMessage } else { $Message }
        if (-not $msg) {
            Write-Error "ERROR: Message required for validate. Usage: pwsh git_helper.ps1 validate `"<message>`""
            exit 1
        }
        Invoke-ValidateCmd -Message $msg -AsJson $Json
    }
    "draft" {
        Invoke-DraftCmd -AsJson $Json
    }
    "status" {
        Invoke-StatusCmd -AsJson $Json
    }
    "branch" {
        $bName = if ($targetMessage) { $targetMessage } elseif ($RemainingArgs) { $RemainingArgs[0] } else { "" }
        if (-not $bName) {
            Write-Error "ERROR: Branch name required. Usage: pwsh git_helper.ps1 branch <name>"
            exit 1
        }
        Invoke-BranchCmd -BranchName $bName -AsJson $Json
    }
    "undo" {
        Invoke-UndoCmd -AsJson $Json
    }
    "audit" {
        Invoke-AuditCmd -AuditLimit $Limit -AsJson $Json
    }
    "check-env" {
        Invoke-CheckEnvCmd -AsJson $Json
    }
    "help" {
        Show-Help
    }
    Default {
        # commit or sync
        $fullMsg = ""
        if ($Raw) {
            $fullMsg = $Raw
        } elseif ($targetMessage) {
            $fullMsg = $targetMessage
            if ($Bullet -and $Bullet.Count -gt 0) {
                $bList = $Bullet | ForEach-Object { "- " + $_.TrimStart("- ") }
                $fullMsg += "`n`n" + ($bList -join "`n")
            }
        } elseif ($Message) {
            if ($Type -and $Scope) {
                $fullMsg = "$($Type)($($Scope)): $Message"
            } else {
                $fullMsg = $Message
            }
            if ($Bullet -and $Bullet.Count -gt 0) {
                $bList = $Bullet | ForEach-Object { "- " + $_.TrimStart("- ") }
                $fullMsg += "`n`n" + ($bList -join "`n")
            }
        } else {
            Write-Error "ERROR: Commit message is required.`nUsage examples:`n  pwsh git_helper.ps1 `"feat(auth): implement jwt refresh`"`n  pwsh git_helper.ps1 commit `"fix(api): handle timeout`""
            exit 1
        }

        if ($subcmd -eq "commit") {
            Invoke-CommitCmd -FullMessage $fullMsg -AsJson $Json
        } else {
            Invoke-SyncCmd -FullMessage $fullMsg -AsJson $Json
        }
    }
}
