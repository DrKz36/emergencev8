# Google Cloud CLI Helper Functions
# Provides timeout and retry logic for gcloud commands
# Usage: . .\scripts\gcloud-helpers.ps1

function Invoke-GCloudWithTimeout {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Command,

        [Parameter(Mandatory=$true)]
        [string[]]$Arguments,

        [int]$TimeoutSeconds = 60,
        [int]$MaxRetries = 3,
        [int]$RetryDelaySeconds = 5,
        [switch]$Silent
    )

    $attempt = 0
    $delaySeconds = $RetryDelaySeconds

    while ($attempt -lt $MaxRetries) {
        $attempt++

        if (-not $Silent) {
            if ($attempt -gt 1) {
                Write-Host "Retry attempt $attempt/$MaxRetries..." -ForegroundColor Yellow
            }
        }

        try {
            # Build the full gcloud command
            $gcloudArgs = @($Command) + $Arguments

            # Execute with timeout using Start-Job
            $job = Start-Job -ScriptBlock {
                param($gcmd, $gargs)
                # Build full argument array: command + args
                $fullArgs = @($gcmd) + $gargs
                $output = & gcloud $fullArgs 2>&1
                return @{
                    Output = $output
                    ExitCode = $LASTEXITCODE
                }
            } -ArgumentList $Command, $Arguments

            # Wait for job with timeout
            $completed = Wait-Job -Job $job -Timeout $TimeoutSeconds

            if ($null -eq $completed) {
                # Job timed out
                Stop-Job -Job $job
                Remove-Job -Job $job -Force

                if ($attempt -ge $MaxRetries) {
                    throw "gcloud command timed out after ${TimeoutSeconds}s (attempt $attempt/$MaxRetries)"
                }

                if (-not $Silent) {
                    Write-Host "Command timed out after ${TimeoutSeconds}s, retrying in ${delaySeconds}s..." -ForegroundColor Yellow
                }
                Start-Sleep -Seconds $delaySeconds
                $delaySeconds *= 2
                continue
            }

            # Get job result
            $result = Receive-Job -Job $job
            Remove-Job -Job $job -Force

            # Check exit code
            if ($result.ExitCode -ne 0) {
                if ($attempt -ge $MaxRetries) {
                    throw "gcloud command failed with exit code $($result.ExitCode): $($result.Output)"
                }

                if (-not $Silent) {
                    Write-Host "Command failed, retrying in ${delaySeconds}s..." -ForegroundColor Yellow
                }
                Start-Sleep -Seconds $delaySeconds
                $delaySeconds *= 2
                continue
            }

            # Success
            return $result.Output

        } catch {
            if ($attempt -ge $MaxRetries) {
                throw "gcloud command failed after $MaxRetries attempts: $_"
            }

            if (-not $Silent) {
                Write-Host "Error: $_, retrying in ${delaySeconds}s..." -ForegroundColor Yellow
            }
            Start-Sleep -Seconds $delaySeconds
            $delaySeconds *= 2
        }
    }

    throw "gcloud command failed after $MaxRetries attempts"
}

function Get-GCloudLogs {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Filter,
        [int]$Limit = 50,
        [string]$Freshness = "1h",
        [string]$Format = "json",
        [string]$Project = "",
        [int]$TimeoutSeconds = 60
    )

    $args = @("read", $Filter, "--limit=$Limit", "--format=$Format", "--freshness=$Freshness")
    if ($Project) {
        $args += "--project=$Project"
    }
    return Invoke-GCloudWithTimeout -Command "logging" -Arguments $args -TimeoutSeconds $TimeoutSeconds
}

function Get-GCloudRunService {
    param(
        [Parameter(Mandatory=$true)]
        [string]$ServiceName,
        [Parameter(Mandatory=$true)]
        [string]$Region,
        [string]$Project = "",
        [string]$Format = "json",
        [int]$TimeoutSeconds = 30
    )

    $args = @("services", "describe", $ServiceName, "--region=$Region", "--format=$Format")
    if ($Project) {
        $args += "--project=$Project"
    }
    return Invoke-GCloudWithTimeout -Command "run" -Arguments $args -TimeoutSeconds $TimeoutSeconds
}

function Get-GCloudRunRevisions {
    param(
        [Parameter(Mandatory=$true)]
        [string]$ServiceName,
        [Parameter(Mandatory=$true)]
        [string]$Region,
        [string]$Project = "",
        [int]$Limit = 10,
        [string]$Format = "json",
        [int]$TimeoutSeconds = 30
    )

    $args = @("revisions", "list", "--service=$ServiceName", "--region=$Region", "--limit=$Limit", "--format=$Format")
    if ($Project) {
        $args += "--project=$Project"
    }
    return Invoke-GCloudWithTimeout -Command "run" -Arguments $args -TimeoutSeconds $TimeoutSeconds
}

function Test-GCloudConnection {
    param(
        [int]$TimeoutSeconds = 15
    )

    Write-Host "Testing gcloud connectivity..." -ForegroundColor Cyan

    try {
        # Test 1: Check authentication - use auth list
        Write-Host "  Checking authentication..." -NoNewline
        $authList = Invoke-GCloudWithTimeout -Command "auth" -Arguments @("list", "--format", "value(account)") -TimeoutSeconds $TimeoutSeconds -Silent
        if ($authList) {
            $account = ($authList -split "`n")[0].Trim()
            if ($account) {
                Write-Host " OK ($account)" -ForegroundColor Green
            } else {
                Write-Host " FAILED" -ForegroundColor Red
                return $false
            }
        } else {
            Write-Host " FAILED" -ForegroundColor Red
            return $false
        }

        # Test 2: Check project - use config list
        Write-Host "  Checking active project..." -NoNewline
        $configList = Invoke-GCloudWithTimeout -Command "config" -Arguments @("list", "--format", "value(core.project)") -TimeoutSeconds $TimeoutSeconds -Silent
        if ($configList) {
            $project = $configList.Trim()
            if ($project) {
                Write-Host " OK ($project)" -ForegroundColor Green
            } else {
                Write-Host " WARNING: No active project" -ForegroundColor Yellow
            }
        } else {
            Write-Host " WARNING: Could not check project" -ForegroundColor Yellow
        }

        # Test 3: Test API connectivity
        Write-Host "  Testing API connectivity..." -NoNewline
        $projects = Invoke-GCloudWithTimeout -Command "projects" -Arguments @("list", "--limit", "1", "--format", "value(projectId)") -TimeoutSeconds $TimeoutSeconds -Silent
        if ($projects) {
            Write-Host " OK" -ForegroundColor Green
        } else {
            Write-Host " FAILED" -ForegroundColor Red
            return $false
        }

        Write-Host "gcloud connection test passed" -ForegroundColor Green
        return $true

    } catch {
        Write-Host " FAILED" -ForegroundColor Red
        Write-Host "gcloud connection test failed: $_" -ForegroundColor Red
        Write-Host "Try running: gcloud auth login" -ForegroundColor Yellow
        return $false
    }
}

# Export functions if used as module
if ($MyInvocation.InvocationName -ne '.') {
    Export-ModuleMember -Function @(
        'Invoke-GCloudWithTimeout',
        'Get-GCloudLogs',
        'Get-GCloudRunService',
        'Get-GCloudRunRevisions',
        'Test-GCloudConnection'
    )
}

Write-Host "gcloud-helpers.ps1 loaded - Timeout and retry protection active" -ForegroundColor Green
