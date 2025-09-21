param(
    [string]$BaseBranch = "main",
    [object[]]$TestCommands = @(
        @("pwsh","-NoProfile","-ExecutionPolicy","Bypass","-File","tests/run_all.ps1")
    ),
    [switch]$SkipTests,
    [switch]$NoPush,
    [switch]$AllowDirty
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." )).Path
Set-Location $repoRoot

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

    if ($Command -is [System.Array]) {
        $flat = @()
        foreach ($item in $Command) { $flat += $item }
        if ($flat.Count -eq 0) { return }
        $exe = [string]$flat[0]
        if ($flat.Count -gt 1) {
            $args = $flat[1..($flat.Count - 1)]
        }
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

try {
    Write-Step "Repository root: $repoRoot"
    Assert-CleanWorkingTree -AllowDirty:$AllowDirty

    Write-Step "Fetching remotes"
    Invoke-Git fetch --all --prune | Out-Null

    $currentBranchOutput = Invoke-Git rev-parse --abbrev-ref HEAD
    $currentBranch = ($currentBranchOutput | Select-Object -Last 1).Trim()
    Write-Host ("Current branch: {0}" -f $currentBranch)

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
