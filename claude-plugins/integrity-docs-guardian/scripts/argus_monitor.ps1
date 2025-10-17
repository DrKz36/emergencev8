# ARGUS Log Monitor Script
# Monitors backend (FastAPI) and frontend (Vite) logs for errors
# Calls Python analyzer to generate fix proposals

param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [int]$DurationMinutes = 0,  # 0 = continuous
    [switch]$AutoFix = $false,
    [switch]$ReportOnly = $false
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$ProjectRoot = Split-Path -Parent $RootDir
$ReportsDir = Join-Path $RootDir "reports"

# Ensure reports directory exists
if (-not (Test-Path $ReportsDir)) {
    New-Item -ItemType Directory -Path $ReportsDir -Force | Out-Null
}

# Output files
$SessionID = Get-Date -Format "yyyyMMdd-HHmmss"
$LogFile = Join-Path $ReportsDir "argus_session_$SessionID.log"
$ReportFile = Join-Path $ReportsDir "dev_logs_report.json"
$BackendLogBuffer = Join-Path $ReportsDir "backend_buffer_$SessionID.log"
$FrontendLogBuffer = Join-Path $ReportsDir "frontend_buffer_$SessionID.log"

# Banner
Write-Host ""
Write-Host "🔍 ═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "   ARGUS - Development Log Monitor" -ForegroundColor Cyan
Write-Host "   The All-Seeing Guardian" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Session ID: $SessionID" -ForegroundColor Gray
Write-Host "Backend Port: $BackendPort" -ForegroundColor Gray
Write-Host "Frontend Port: $FrontendPort" -ForegroundColor Gray
Write-Host "Log File: $LogFile" -ForegroundColor Gray
Write-Host ""

# Function to check if process is listening on port
function Test-PortListening {
    param([int]$Port)

    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        return $connections.Count -gt 0
    } catch {
        return $false
    }
}

# Function to log with timestamp
function Write-ArgusLog {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [ConsoleColor]$Color = "White"
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"

    Write-Host $logEntry -ForegroundColor $Color
    Add-Content -Path $LogFile -Value $logEntry
}

# Check if backend is running
Write-Host "🔎 Checking for running services..." -ForegroundColor Yellow

$backendRunning = Test-PortListening -Port $BackendPort
$frontendRunning = Test-PortListening -Port $FrontendPort

if (-not $backendRunning -and -not $frontendRunning) {
    Write-Host ""
    Write-Host "❌ ERROR: Neither backend nor frontend is running!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please start the services first:" -ForegroundColor Yellow
    Write-Host "  Backend:  cd src/backend && python -m uvicorn main:app --reload --port $BackendPort" -ForegroundColor Gray
    Write-Host "  Frontend: cd src/frontend && npm run dev" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

if ($backendRunning) {
    Write-Host "✅ Backend detected on port $BackendPort" -ForegroundColor Green
} else {
    Write-Host "⚠️  Backend not detected on port $BackendPort" -ForegroundColor Yellow
}

if ($frontendRunning) {
    Write-Host "✅ Frontend detected on port $FrontendPort" -ForegroundColor Green
} else {
    Write-Host "⚠️  Frontend not detected on port $FrontendPort" -ForegroundColor Yellow
}

Write-Host ""

# Initialize log buffers
"" | Out-File -FilePath $BackendLogBuffer -Encoding UTF8
"" | Out-File -FilePath $FrontendLogBuffer -Encoding UTF8

Write-ArgusLog "Starting log monitoring..." "INFO" "Green"
Write-Host ""

# Function to monitor backend logs
function Start-BackendMonitor {
    Write-ArgusLog "Attaching to backend logs..." "INFO" "Cyan"

    # Try to find the backend process
    $backendProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowTitle -like "*uvicorn*" -or $_.CommandLine -like "*uvicorn*" } |
        Select-Object -First 1

    if ($null -eq $backendProcess) {
        Write-ArgusLog "Could not attach to backend process directly. Monitoring will be passive." "WARN" "Yellow"
        return $null
    }

    Write-ArgusLog "Backend process found (PID: $($backendProcess.Id))" "INFO" "Green"
    return $backendProcess
}

# Function to monitor frontend logs
function Start-FrontendMonitor {
    Write-ArgusLog "Attaching to frontend logs..." "INFO" "Cyan"

    # Try to find the frontend process
    $frontendProcess = Get-Process -Name "node" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*vite*" } |
        Select-Object -First 1

    if ($null -eq $frontendProcess) {
        Write-ArgusLog "Could not attach to frontend process directly. Monitoring will be passive." "WARN" "Yellow"
        return $null
    }

    Write-ArgusLog "Frontend process found (PID: $($frontendProcess.Id))" "INFO" "Green"
    return $frontendProcess
}

# Start monitoring
$backendProc = Start-BackendMonitor
$frontendProc = Start-FrontendMonitor

Write-Host ""
Write-Host "📡 Monitoring active..." -ForegroundColor Cyan
Write-Host "   Press Ctrl+C to stop and generate report" -ForegroundColor Gray
Write-Host ""

# Monitoring loop
$startTime = Get-Date
$errorCount = 0
$lastAnalysisTime = Get-Date

try {
    while ($true) {
        # Check duration limit
        if ($DurationMinutes -gt 0) {
            $elapsed = (Get-Date) - $startTime
            if ($elapsed.TotalMinutes -ge $DurationMinutes) {
                Write-ArgusLog "Monitoring duration reached ($DurationMinutes minutes)" "INFO" "Yellow"
                break
            }
        }

        # Check if processes are still alive
        if ($backendRunning -and $backendProc -and $backendProc.HasExited) {
            Write-ArgusLog "Backend process terminated!" "ERROR" "Red"
            $errorCount++
        }

        if ($frontendRunning -and $frontendProc -and $frontendProc.HasExited) {
            Write-ArgusLog "Frontend process terminated!" "ERROR" "Red"
            $errorCount++
        }

        # Passive monitoring: Try to fetch logs from localhost endpoints
        # (This requires backend/frontend to expose log endpoints - optional feature)

        # Every 30 seconds, run analysis on collected logs
        $timeSinceLastAnalysis = (Get-Date) - $lastAnalysisTime
        if ($timeSinceLastAnalysis.TotalSeconds -ge 30) {
            Write-Host ""
            Write-Host "⚙️  Running log analysis..." -ForegroundColor Cyan

            # Call Python analyzer
            $analyzerScript = Join-Path $ScriptDir "argus_analyzer.py"
            if (Test-Path $analyzerScript) {
                $analysisResult = & python $analyzerScript --session-id $SessionID --output $ReportFile

                if ($LASTEXITCODE -eq 0) {
                    Write-ArgusLog "Analysis complete. Report saved to: $ReportFile" "INFO" "Green"

                    # Check if errors were found
                    if (Test-Path $ReportFile) {
                        $report = Get-Content $ReportFile -Raw | ConvertFrom-Json
                        $newErrors = $report.statistics.total_errors

                        if ($newErrors -gt 0) {
                            Write-Host ""
                            Write-Host "⚠️  $newErrors error(s) detected!" -ForegroundColor Red
                            Write-Host "   Run analysis for details and fix proposals." -ForegroundColor Yellow
                            $errorCount += $newErrors
                        }
                    }
                } else {
                    Write-ArgusLog "Analysis failed (exit code: $LASTEXITCODE)" "ERROR" "Red"
                }
            } else {
                Write-ArgusLog "Analyzer script not found: $analyzerScript" "WARN" "Yellow"
            }

            $lastAnalysisTime = Get-Date
            Write-Host ""
        }

        # Sleep for 5 seconds
        Start-Sleep -Seconds 5

        # Show heartbeat every minute
        $elapsed = (Get-Date) - $startTime
        if ($elapsed.TotalSeconds % 60 -lt 5) {
            $minutes = [math]::Floor($elapsed.TotalMinutes)
            Write-Host "💓 Monitoring... ($minutes min elapsed, $errorCount errors detected)" -ForegroundColor DarkGray
        }
    }
} catch {
    Write-ArgusLog "Monitoring interrupted: $($_.Exception.Message)" "ERROR" "Red"
} finally {
    Write-Host ""
    Write-Host "🛑 Stopping monitor..." -ForegroundColor Yellow
}

# Final analysis
Write-Host ""
Write-Host "📊 Generating final report..." -ForegroundColor Cyan

$analyzerScript = Join-Path $ScriptDir "argus_analyzer.py"
if (Test-Path $analyzerScript) {
    $analysisArgs = @(
        $analyzerScript,
        "--session-id", $SessionID,
        "--output", $ReportFile,
        "--final"
    )

    if ($AutoFix) {
        $analysisArgs += "--auto-fix"
    }

    if ($ReportOnly) {
        $analysisArgs += "--report-only"
    }

    & python @analysisArgs

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Report generated successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "📄 Report location: $ReportFile" -ForegroundColor Cyan
        Write-Host "📄 Session log: $LogFile" -ForegroundColor Cyan
        Write-Host ""

        # Show summary
        if (Test-Path $ReportFile) {
            $report = Get-Content $ReportFile -Raw | ConvertFrom-Json

            Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
            Write-Host "   ARGUS Session Summary" -ForegroundColor Cyan
            Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "  Duration: $([math]::Round($report.monitoring_duration_minutes, 1)) minutes" -ForegroundColor Gray
            Write-Host "  Status: $($report.status.ToUpper())" -ForegroundColor $(if ($report.status -eq "ok") { "Green" } elseif ($report.status -eq "warnings") { "Yellow" } else { "Red" })
            Write-Host ""
            Write-Host "  Total Errors: $($report.statistics.total_errors)" -ForegroundColor Gray
            Write-Host "    Critical: $($report.statistics.critical)" -ForegroundColor $(if ($report.statistics.critical -gt 0) { "Red" } else { "Green" })
            Write-Host "    Warnings: $($report.statistics.warnings)" -ForegroundColor $(if ($report.statistics.warnings -gt 0) { "Yellow" } else { "Green" })
            Write-Host "    Info: $($report.statistics.info)" -ForegroundColor Gray
            Write-Host ""
            Write-Host "  Backend Errors: $($report.statistics.backend_errors)" -ForegroundColor Gray
            Write-Host "  Frontend Errors: $($report.statistics.frontend_errors)" -ForegroundColor Gray
            Write-Host ""

            if ($report.statistics.total_errors -gt 0) {
                Write-Host "💡 Run with fix proposals enabled to see suggested fixes." -ForegroundColor Yellow
            } else {
                Write-Host "🎉 No errors detected! Your code is clean." -ForegroundColor Green
            }

            Write-Host ""
            Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
        }
    } else {
        Write-Host ""
        Write-Host "❌ Report generation failed!" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host ""
    Write-Host "❌ Analyzer script not found: $analyzerScript" -ForegroundColor Red
    Write-Host "   Please create the Python analyzer script." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-ArgusLog "ARGUS monitoring session ended." "INFO" "Green"
Write-Host ""

# Cleanup buffers
if (Test-Path $BackendLogBuffer) {
    Remove-Item $BackendLogBuffer -Force
}
if (Test-Path $FrontendLogBuffer) {
    Remove-Item $FrontendLogBuffer -Force
}

exit 0
