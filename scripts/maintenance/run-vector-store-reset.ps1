#requires -Version 5.1
<#
.SYNOPSIS
    Automates the weekly execution of tests/test_vector_store_reset.ps1 without manual prompts.
.DESCRIPTION
    Starts a backend instance (unless instructed otherwise), runs the vector store reset scenario end-to-end,
    and archives the console output in logs/vector-store. Designed to be scheduled (Task Scheduler / cron).
#>
[CmdletBinding()]
param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string[]]$BackendCommand = @("uvicorn","--app-dir","src","backend.main:app","--host","127.0.0.1","--port","8000"),
    [string]$BackendWorkingDirectory,
    [string]$LogDirectory = "logs\\vector-store",
    [string]$UploadFile = "test_upload.txt",
    [int]$StartupTimeoutSeconds = 90,
    [int]$HealthCheckIntervalSeconds = 3,
    [switch]$KeepBackendRunning,
    [switch]$ReuseRunningBackend
)

$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'

$repoRoot = (Resolve-Path '.').Path
$testsScript = Join-Path $repoRoot 'tests/test_vector_store_reset.ps1'
if (-not (Test-Path $testsScript)) {
    throw "Execution attendue depuis la racine du depot (tests/test_vector_store_reset.ps1 introuvable)."
}
if (-not $BackendWorkingDirectory) {
    $BackendWorkingDirectory = Join-Path $repoRoot 'src/backend'
}
$vectorDir = Join-Path $repoRoot 'src/backend/data/vector_store'
if (-not (Test-Path $vectorDir)) {
    throw "Repertoire vector_store introuvable : $vectorDir"
}

$logLines = New-Object System.Collections.Generic.List[string]
function Write-Log {
    param(
        [string]$Message,
        [object]$Color = ([ConsoleColor]::Gray)
    )
    $timestamp = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    $formatted = "[{0}] {1}" -f $timestamp, $Message
    $logLines.Add($formatted)
    $targetColor = [ConsoleColor]::Gray
    if ($Color -is [ConsoleColor]) {
        $targetColor = $Color
    } elseif ($Color) {
        try {
            $targetColor = [System.Enum]::Parse([ConsoleColor], [string]$Color, $true)
        } catch {
            $targetColor = [ConsoleColor]::Gray
        }
    }
    Write-Host $formatted -ForegroundColor $targetColor
}

function Start-Backend {
    param(
        [string[]]$Command,
        [string]$WorkingDirectory
    )
    if (-not $Command -or $Command.Count -eq 0) {
        throw "BackendCommand vide."
    }
    $exe = $Command[0]
    $args = $Command[1..($Command.Count-1)]
    Write-Log ("Demarrage backend : {0} {1}" -f $exe, ($args -join ' ')) [ConsoleColor]::Cyan

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $exe
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.RedirectStandardError = $true
    $psi.RedirectStandardOutput = $true
    $psi.CreateNoWindow = $true
    if ($args.Count -gt 0) {
        $psi.Arguments = [string]::Join(' ', $args)
    }

    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi
    $null = $proc.Start()
    $proc.BeginOutputReadLine()
    $proc.BeginErrorReadLine()
    return $proc
}

function Stop-Backend {
    param([System.Diagnostics.Process]$Process, [string]$Context = "backend")
    if (-not $Process) { return }
    try {
        if (-not $Process.HasExited) {
            Write-Log ("Arret {0} (PID={1})" -f $Context, $Process.Id) [ConsoleColor]::DarkCyan
            $Process.Kill()
            $Process.WaitForExit(15000) | Out-Null
        }
    } catch {
        Write-Log ("Arret {0} en erreur : {1}" -f $Context, $_.Exception.Message) [ConsoleColor]::Yellow
    }
}

function Wait-ForHealth {
    param(
        [string]$Url,
        [int]$TimeoutSeconds,
        [int]$IntervalSeconds
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $health = Invoke-RestMethod -Method Get -Uri ("{0}/api/health" -f $Url.TrimEnd('/')) -TimeoutSec 5
            Write-Log "Health-check OK" [ConsoleColor]::Green
            return
        } catch {
            Start-Sleep -Seconds $IntervalSeconds
        }
    } while (Get-Date) -lt $deadline
    throw "Expire : health-check KO apres ${TimeoutSeconds}s."
}

function Invoke-Upload {
    param(
        [string]$Url,
        [string]$FilePath,
        [string]$Label
    )
    Add-Type -AssemblyName System.Net.Http
    Write-Log ("Upload {0} via HttpClient..." -f $Label) [ConsoleColor]::DarkCyan
    $client = $null
    $content = $null
    $fileStream = $null
    $streamContent = $null
    try {
        $client = New-Object System.Net.Http.HttpClient
        $content = New-Object System.Net.Http.MultipartFormDataContent
        $fileStream = [System.IO.File]::OpenRead($FilePath)
        $streamContent = New-Object System.Net.Http.StreamContent($fileStream)
        $streamContent.Headers.ContentType = 'text/plain'
        $content.Add($streamContent, 'file', [System.IO.Path]::GetFileName($FilePath))
        $response = $client.PostAsync(("{0}/api/documents/upload" -f $Url.TrimEnd('/')), $content).Result
        $body = $response.Content.ReadAsStringAsync().Result
        Write-Log ("Reponse {0} : {1}" -f $Label, ($body -replace "\s+$", ''))
        if (-not $response.IsSuccessStatusCode) {
            throw "Upload ${Label} a echoue (HTTP $([int]$response.StatusCode))."
        }
    } finally {
        if ($streamContent) { $streamContent.Dispose() }
        if ($fileStream) { $fileStream.Dispose() }
        if ($content) { $content.Dispose() }
        if ($client) { $client.Dispose() }
    }
}

function Wait-ForFileUnlock {
    param(
        [string]$Path,
        [int]$TimeoutSeconds = 60,
        [int]$IntervalMilliseconds = 500
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $stream = [System.IO.File]::Open($Path,
                                             [System.IO.FileMode]::Open,
                                             [System.IO.FileAccess]::ReadWrite,
                                             [System.IO.FileShare]::None)
            $stream.Close()
            return $true
        } catch {
            Start-Sleep -Milliseconds $IntervalMilliseconds
        }
    }
    return $false
}

if (-not (Test-Path $LogDirectory)) {
    New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
}

$uploadFilePath = if ([System.IO.Path]::IsPathRooted($UploadFile)) {
    $UploadFile
} else {
    Join-Path $repoRoot $UploadFile
}
if (-not (Test-Path $uploadFilePath)) {
    "Fichier de test pour Emergence." | Out-File -FilePath $uploadFilePath -Encoding UTF8
    Write-Log ("Fichier cree : {0}" -f $uploadFilePath)
}

$backendProc = $null
$startedBackend = $false
$scriptSuccess = $false

try {
    Write-Log "=== Vector store reset (hebdo) ===" [ConsoleColor]::Green
    Write-Log ("Repo : {0}" -f $repoRoot)
    Write-Log ("BaseUrl : {0}" -f $BaseUrl)
    if (-not $ReuseRunningBackend) {
        $backendProc = Start-Backend -Command $BackendCommand -WorkingDirectory $BackendWorkingDirectory
        $startedBackend = $true
        Start-Sleep -Seconds 2
    }

    Wait-ForHealth -Url $BaseUrl -TimeoutSeconds $StartupTimeoutSeconds -IntervalSeconds $HealthCheckIntervalSeconds

    Invoke-Upload -Url $BaseUrl -FilePath $uploadFilePath -Label 'initial'

    if (-not $ReuseRunningBackend) {
        Stop-Backend -Process $backendProc
        $backendProc = $null
        Start-Sleep -Seconds 2
    } else {
        throw "Mode ReuseRunningBackend non supporte pour l'automatisation (impossible de liberer le fichier SQLite)."
    }

    $sqliteCandidate = Get-ChildItem -Path $vectorDir -Recurse -File -Include *.sqlite* | Sort-Object Length -Descending | Select-Object -First 1
    if (-not $sqliteCandidate) {
        throw "Aucun fichier *.sqlite* trouve dans $vectorDir"
    }
    Write-Log ("Fichier SQLite cible : {0}" -f $sqliteCandidate.FullName)
    Write-Log ("Taille avant corruption : {0} octets" -f $sqliteCandidate.Length)
    Write-Log "Attente liberation du fichier SQLite (verrou exclusif)..." [ConsoleColor]::DarkGray
    if (-not (Wait-ForFileUnlock -Path $sqliteCandidate.FullName -TimeoutSeconds 60)) {
        throw "Impossible d'obtenir un acces exclusif sur $($sqliteCandidate.FullName) (verrou persistant)."
    }

    $fs = [System.IO.File]::Open($sqliteCandidate.FullName,
                                 [System.IO.FileMode]::Truncate,
                                 [System.IO.FileAccess]::ReadWrite,
                                 [System.IO.FileShare]::None)
    $fs.Close()
    Write-Log "Tronquage realise (taille = 0)."

    $backendProc = Start-Backend -Command $BackendCommand -WorkingDirectory $BackendWorkingDirectory
    Start-Sleep -Seconds 2
    Wait-ForHealth -Url $BaseUrl -TimeoutSeconds $StartupTimeoutSeconds -IntervalSeconds $HealthCheckIntervalSeconds

    $backupRoots = Get-ChildItem -Path (Split-Path $vectorDir -Parent) -Directory -Filter 'vector_store_backup_*' | Sort-Object Name -Descending
    if ($backupRoots.Count -eq 0) {
        Write-Log "Aucun backup detecte apres relance." [ConsoleColor]::Yellow
    } else {
        Write-Log ("Dernier backup : {0}" -f $backupRoots[0].FullName) [ConsoleColor]::Green
    }

    Invoke-Upload -Url $BaseUrl -FilePath $uploadFilePath -Label 'post-reset'

    Write-Log "Succes : auto-reset valide." [ConsoleColor]::Green
    $scriptSuccess = $true
}
catch {
    Write-Log ("Erreur : {0}" -f $_.Exception.Message) [ConsoleColor]::Red
    $scriptSuccess = $false
    throw
}
finally {
    if ($backendProc -and -not $KeepBackendRunning) {
        Stop-Backend -Process $backendProc
    }
    $ts = Get-Date -Format 'yyyyMMdd-HHmmss'
    $logPath = Join-Path $LogDirectory ("vector_store_reset_{0}.log" -f $ts)
    $logLines | Out-File -FilePath $logPath -Encoding UTF8
    Write-Host "Log archive dans $logPath" -ForegroundColor Cyan
}

if (-not $scriptSuccess) {
    exit 1
}
exit 0
