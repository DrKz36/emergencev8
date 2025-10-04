param(
    [string]$BaseBranch = "main",
    [object[]]$TestCommands,
    [switch]$SkipTests,
    [switch]$NoPush,
    [switch]$AllowDirty
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." )).Path
Set-Location $repoRoot

$generatedArtifacts = @(
    (Join-Path $repoRoot "test_upload.txt")
)

if (-not $PSBoundParameters.ContainsKey('TestCommands')) {
    $TestCommands = ,@(
        "pwsh","-NoProfile","-ExecutionPolicy","Bypass","-File","tests/run_all.ps1"
    )
}

if ($null -ne $TestCommands) {
    $containsNested = $false
    foreach ($entry in $TestCommands) {
        if ($entry -is [System.Collections.IEnumerable] -and $entry -isnot [string]) {
            $containsNested = $true
            break
        }
    }
    if (-not $containsNested -and $TestCommands.Count -gt 0) {
        $TestCommands = ,$TestCommands
    }
}

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-Git {
    param(
        [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )
    Write-Host ("git {0}" -f ($Arguments -join ' ')) -ForegroundColor DarkGray
    $output = git @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "git command failed: git $($Arguments -join ' ')"
    }
    return $output
}

function Test-BranchMerged {
    param(
        [string]$BranchName,
        [string]$BaseBranch = "main"
    )

    if ([string]::IsNullOrWhiteSpace($BranchName)) { return $false }

    $remoteRef = "origin/$BranchName"
    $baseRef = "origin/$BaseBranch"

    $remoteBranches = git branch -r --list $remoteRef
    if ($LASTEXITCODE -ne 0) {
        Write-Warning ("Unable to list remote branches for {0}" -f $BranchName)
        return $false
    }

    if (-not $remoteBranches) {
        Write-Host ("Branch {0} not found on remote (already deleted)." -f $BranchName) -ForegroundColor Green
        return $true
    }

    $revList = git rev-list "$baseRef..$remoteRef" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning ("Unable to compare {0} with {1}" -f $baseRef, $remoteRef)
        return $false
    }

    if (-not $revList) {
        Write-Warning ("Branch {0} appears merged into {1} but still exists on remote." -f $BranchName, $BaseBranch)
        Write-Host ("Cleanup suggestion: git push origin --delete {0}" -f $BranchName) -ForegroundColor Yellow
        return $true
    }

    return $false
}


function Assert-CleanWorkingTree {
    param([switch]$AllowDirty)
    $status = git status --porcelain
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to read git status."
    }
    if (-not $AllowDirty -and $status) {
        Write-Host $status
        throw "Working tree is not clean. Commit or stash changes or rerun with -AllowDirty."
    }
}

function Invoke-TestCommand {
    param([object]$Command)
    if ($null -eq $Command) { return }
    if ($Command -is [string] -and [string]::IsNullOrWhiteSpace($Command)) { return }

    $exe = $null
    $args = @()

    if ($Command -is [System.Collections.IEnumerable] -and $Command -isnot [string]) {
        $flat = @()
        foreach ($item in $Command) {
            if ($null -eq $item) { continue }
            if ($item -is [string]) {
                if (-not [string]::IsNullOrWhiteSpace($item)) {
                    $flat += $item
                }
            } else {
                $flat += $item
            }
        }
        if ($flat.Count -eq 0) { return }
        $exe = [string]$flat[0]
        if ($flat.Count -gt 1) {
            $args = @()
            for ($i = 1; $i -lt $flat.Count; $i++) {
                $args += [string]$flat[$i]
            }
        }
    } elseif ($Command -is [scriptblock]) {
        $exe = "pwsh"
        $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $Command.ToString())
    } else {
        $exe = "pwsh"
        $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", [string]$Command)
    }

    Write-Host ("Running: {0} {1}" -f $exe, ($args -join ' ')) -ForegroundColor Yellow
    & $exe @args
    if ($LASTEXITCODE -ne 0) {
        throw "Test command failed: $exe $($args -join ' ')"
    }
}


function Remove-GeneratedArtifacts {
    param([string[]]$Paths)
    if ($null -eq $Paths) { return }
    foreach ($path in $Paths) {
        if ([string]::IsNullOrWhiteSpace($path)) { continue }
        if (Test-Path -LiteralPath $path) {
            try {
                Remove-Item -LiteralPath $path -Force
                Write-Host ("Removed generated artifact: {0}" -f $path) -ForegroundColor DarkGray
            } catch {
                Write-Warning ("Unable to remove generated artifact {0}: {1}" -f $path, $_.Exception.Message)
            }
        }
    }
}

try {
    Write-Step "Repository root: $repoRoot"
    Assert-CleanWorkingTree -AllowDirty:$AllowDirty

    Write-Step "Fetching remotes"
    Invoke-Git fetch --all --prune | Out-Null

    $currentBranchOutput = Invoke-Git rev-parse --abbrev-ref HEAD
    $currentBranch = ($currentBranchOutput | Select-Object -Last 1).Trim()
    Write-Host ("Current branch: {0}" -f $currentBranch)

    Write-Step "Checking merged branch status"
    if ($currentBranch -ne $BaseBranch) {
        if (Test-BranchMerged -BranchName $currentBranch -BaseBranch $BaseBranch) {
            throw "Branch ''{0}'' appears already merged into origin/{1}. Checkout main, clean up the branch, then rerun sync." -f $currentBranch, $BaseBranch
        }
    }

    Write-Step "Rebasing onto origin/$BaseBranch"
    Invoke-Git fetch origin $BaseBranch | Out-Null
    Invoke-Git rebase ("origin/{0}" -f $BaseBranch)

    if (-not $SkipTests) {
        Write-Step "Running test suite"
        foreach ($cmd in $TestCommands) {
            Invoke-TestCommand -Command $cmd
        }
    } else {
        Write-Host "Tests skipped (SkipTests flag)." -ForegroundColor Yellow
    }

    Remove-GeneratedArtifacts -Paths $generatedArtifacts

    Assert-CleanWorkingTree -AllowDirty:$AllowDirty

    if (-not $NoPush) {
        Write-Step "Pushing branch to origin"
        Invoke-Git push origin $currentBranch
    } else {
        Write-Host "Push skipped (NoPush flag)." -ForegroundColor Yellow
    }

    Write-Step "Sync complete"
    Write-Host "Everything up to date with origin/$currentBranch." -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "Sync failed: $($_.Exception.Message)" -ForegroundColor Red
    throw
}
finally {
    Remove-GeneratedArtifacts -Paths $generatedArtifacts
}
