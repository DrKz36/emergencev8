#requires -Version 5.1
<#
    EMERGENCE - Test force-backup (PowerShell 5.1 compatible, ASCII-only)
    - Corrupts the SQLite header of the Chroma vector store
    - Waits for a backend restart
    - Validates /api/health
    - Detects the latest backup directory "vector_store_backup_*"
    - Performs a control upload via HttpClient with real authentication
    Exit codes:
      0 -> Success (health OK, upload OK; backup detected if created)
      2 -> Upload failed (health OK)
      1 -> Health check failed or blocking error
#>

[CmdletBinding()]
param(
    [string]$ApiBase = 'http://127.0.0.1:8000',
    [string]$SmokeEmail,
    [string]$SmokePassword,
    [switch]$AutoBackend,
    [string]$BackendHost = '0.0.0.0',
    [int]$BackendPort = 8000,
    [int]$BackendStartupTimeoutSec = 180
)

try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host ''
Write-Host '=== Force-Backup Test (PS 5.1 - Windows-proof) ===' -ForegroundColor Cyan

# ---------- Paths and helpers ----------
$scriptDir = Split-Path -Parent $PSCommandPath
if (-not $scriptDir) { $scriptDir = (Get-Location).Path }
$projectRoot = (Get-Item (Join-Path $scriptDir '..')).FullName

$authHelperPath = Join-Path $scriptDir 'helpers/auth.ps1'
if (-not (Test-Path -LiteralPath $authHelperPath)) {
    throw 'Auth helper not found: ' + $authHelperPath
}
. $authHelperPath

if ($AutoBackend) {
    $ApiBase = "http://127.0.0.1:$BackendPort"
}
$ApiBase = Resolve-SmokeBaseUrl -BaseUrl $ApiBase
$healthUrl = "$ApiBase/api/health"
$uploadUrl = "$ApiBase/api/documents/upload"

$vectorRoot  = [System.IO.Path]::Combine($projectRoot, 'src', 'backend', 'data', 'vector_store')
$backupRoot  = [System.IO.Path]::GetDirectoryName($vectorRoot)
$dbFile      = Join-Path $vectorRoot  'chroma.sqlite3'
$tmpDir      = Join-Path $projectRoot 'tmp_tests'
$backupGlob  = 'vector_store_backup_*'

$script:ForceAuthSession = $null
function Get-ForceAuthSession {
    if (-not $script:ForceAuthSession) {
        $script:ForceAuthSession = New-SmokeAuthSession -BaseUrl $ApiBase -Email $SmokeEmail -Password $SmokePassword -Source 'tests/test_vector_store_force_backup.ps1' -UserAgent 'emergence-vector-force'
        Write-Host ("[AUTH] Session {0} ready for {1}" -f $script:ForceAuthSession.SessionId, $script:ForceAuthSession.Email) -ForegroundColor DarkGray
    }
    return $script:ForceAuthSession
}

# ---------- Auto-backend helpers ----------
function Resolve-PythonExe {
    param([string]$RepoRoot)
    $venvPython = Join-Path $RepoRoot '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $venvPython) { return $venvPython }
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) { return $pythonCmd.Path }
    return 'python'
}

function Wait-HealthOk {
    param([int]$TimeoutSec = 180, [int]$IntervalMs = 800)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $res = Invoke-RestMethod -Uri $healthUrl -Method GET -TimeoutSec 5
            if ($res.status -eq 'ok' -or $res.status -eq 'healthy') {
                return $true
            }
        } catch {}
        Start-Sleep -Milliseconds $IntervalMs
    }
    return $false
}

$script:BackendProcess = $null
function Start-AutoBackend {
    param(
        [string]$RepoRoot,
        [string]$ListenHost,
        [int]$Port,
        [int]$TimeoutSec
    )
    if ($script:BackendProcess -and -not $script:BackendProcess.HasExited) {
        throw "A backend process is already active (PID $($script:BackendProcess.Id))."
    }
    $pythonExe = Resolve-PythonExe -RepoRoot $RepoRoot
    $args = @('-m','uvicorn','--app-dir','src','backend.main:app','--host',$ListenHost,'--port',$Port.ToString())
    Write-Host ("[AUTO] Starting backend ($pythonExe $($args -join ' ')).") -ForegroundColor DarkGray
    $proc = Start-Process -FilePath $pythonExe -ArgumentList $args -WorkingDirectory $RepoRoot -PassThru -NoNewWindow
    Start-Sleep -Milliseconds 300
    if (-not (Wait-HealthOk -TimeoutSec $TimeoutSec)) {
        try { if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } } catch {}
        throw "Backend did not respond on $healthUrl after $TimeoutSec second(s)."
    }
    $script:BackendProcess = $proc
    Write-Host '[AUTO] Backend ready.' -ForegroundColor Green
}

function Stop-AutoBackend {
    param([string]$Reason = 'Stopping backend')
    $proc = $script:BackendProcess
    if (-not $proc) { return }
    Write-Host ("[AUTO] $Reason (PID $($proc.Id)).") -ForegroundColor DarkGray
    try {
        if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -ErrorAction SilentlyContinue }
        Start-Sleep -Milliseconds 300
        if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
        $proc.WaitForExit()
    } catch {
        Write-Warning ("Unable to stop backend: $($_.Exception.Message)")
    } finally {
        $proc.Dispose()
        $script:BackendProcess = $null
    }
}

# ---------- Backup helpers ----------
function Get-BackupTimestamp {
    param([System.IO.DirectoryInfo]$Directory)
    if (-not $Directory) { return [datetime]::MinValue }

    $lastWrite = $Directory.LastWriteTime
    $regex = [regex]'^vector_store_backup_(\d{8})_(\d{6})$'

    $timestamp = $null
    if ($regex.IsMatch($Directory.Name)) {
        $match = $regex.Match($Directory.Name)
        $combined = $match.Groups[1].Value + $match.Groups[2].Value
        try {
            $timestamp = [datetime]::ParseExact(
                $combined,
                'yyyyMMddHHmmss',
                [System.Globalization.CultureInfo]::InvariantCulture,
                [System.Globalization.DateTimeStyles]::AssumeLocal
            )
        } catch {
            $timestamp = $null
        }
    }

    if (-not $timestamp) {
        $metadataPath = Join-Path $Directory.FullName 'metadata.json'
        if (Test-Path -LiteralPath $metadataPath) {
            try {
                $raw = Get-Content -LiteralPath $metadataPath -Raw
                if ($raw) {
                    $metadata = $raw | ConvertFrom-Json
                    foreach ($key in @('timestamp', 'created_at', 'createdAt')) {
                        $value = $metadata.$key
                        if ([string]::IsNullOrWhiteSpace($value)) { continue }
                        try {
                            $timestamp = [datetime]::Parse(
                                $value,
                                [System.Globalization.CultureInfo]::InvariantCulture,
                                [System.Globalization.DateTimeStyles]::AssumeUniversal
                            )
                            break
                        } catch {
                            try {
                                $timestamp = [datetime]::ParseExact(
                                    [string]$value,
                                    'yyyy-MM-ddTHH:mm:ss.fffZ',
                                    [System.Globalization.CultureInfo]::InvariantCulture,
                                    [System.Globalization.DateTimeStyles]::AssumeUniversal
                                )
                                break
                            } catch {
                                $timestamp = $null
                            }
                        }
                    }
                }
            } catch {
                $timestamp = $null
            }
        }
    }

    if ($timestamp) {
        if ($lastWrite -gt $timestamp) { return $lastWrite }
        return $timestamp
    }
    return $lastWrite
}

function Get-LatestBackupFolder {
    if (-not (Test-Path -LiteralPath $backupRoot)) { return $null }
    $directories = Get-ChildItem -Path $backupRoot -Directory -Filter $backupGlob -ErrorAction SilentlyContinue
    if (-not $directories) { return $null }
    $best = $null
    $bestStamp = [datetime]::MinValue
    foreach ($dir in $directories) {
        $stamp = Get-BackupTimestamp -Directory $dir
        if ($stamp -gt $bestStamp) {
            $bestStamp = $stamp
            $best = [pscustomobject]@{
                Directory = $dir
                Timestamp = $stamp
            }
        }
    }
    return $best
}

function Corrupt-SqliteHeader {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "DB file not found: $Path"
    }
    $fs = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
    try {
        $bytes = New-Object byte[] 16
        for ($i=0; $i -lt $bytes.Length; $i++) { $bytes[$i] = 0xFF }
        $fs.Position = 0
        $fs.Write($bytes,0,$bytes.Length)
        $fs.Flush()
    } finally {
        $fs.Dispose()
    }
}

function Upload-Smoke {
    Add-Type -AssemblyName System.Net.Http
    New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null

    $filePath = Join-Path $tmpDir ("upload_vector_check_{0}.txt" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
    "smoke upload $(Get-Date -Format s)" | Out-File -FilePath $filePath -Encoding UTF8 -Force

    $hc = $null
    $mp = $null
    $fs = $null
    $req = $null
    try {
        $hc = New-Object System.Net.Http.HttpClient
        $mp = New-Object System.Net.Http.MultipartFormDataContent

        $fs = [System.IO.File]::OpenRead($filePath)
        $sc = New-Object System.Net.Http.StreamContent($fs)
        $sc.Headers.ContentType = 'text/plain'
        $mp.Add($sc, 'file', [System.IO.Path]::GetFileName($filePath))

        $session = Get-ForceAuthSession
        $req = New-Object System.Net.Http.HttpRequestMessage([System.Net.Http.HttpMethod]::Post, $uploadUrl)
        $req.Headers.Authorization = [System.Net.Http.Headers.AuthenticationHeaderValue]::new('Bearer', $session.Token)
        $null = $req.Headers.TryAddWithoutValidation('X-Session-Id', $session.SessionId)
        if ($session.UserId) {
            $null = $req.Headers.TryAddWithoutValidation('X-User-Id', $session.UserId)
        }
        $req.Content = $mp

        $resp = $hc.SendAsync($req).Result
        $status = [int]$resp.StatusCode
        $body   = $resp.Content.ReadAsStringAsync().Result

        if ($status -ge 200 -and $status -lt 300) {
            try { $json = $body | ConvertFrom-Json } catch { $json = $null }
            if ($json -and $json.message -match 'succes') {
                Write-Host ("[OK]  Upload after reset succeeded. HTTP {0} | ID={1} | file={2}" -f $status, $json.document_id, $json.filename) -ForegroundColor Green
                return $true
            } else {
                Write-Host ("[WARN] Upload: HTTP {0}, unexpected body: {1}" -f $status, $body) -ForegroundColor Yellow
                return $false
            }
        } else {
            Write-Host ("[ERR] Upload HTTP {0}. Body: {1}" -f $status, $body) -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host ("[ERR] Upload exception: {0}" -f $_.Exception.Message) -ForegroundColor Red
        return $false
    } finally {
        if ($req) { $req.Dispose() }
        if ($mp) { $mp.Dispose() }
        if ($hc) { $hc.Dispose() }
        if ($fs) { $fs.Dispose() }
    }
}

# ---------- Main flow ----------
Write-Host ''
Write-Host '=== Preflight & vector_store targeting ===' -ForegroundColor Cyan
if (-not (Test-Path -LiteralPath $vectorRoot)) { throw "Vector root not found: $vectorRoot" }
if (-not (Test-Path -LiteralPath $dbFile))   { throw "DB file not found: $dbFile" }
Write-Host ("[OK]  Project root: {0}" -f $projectRoot) -ForegroundColor Green
Write-Host ("[OK]  Vector root : {0}" -f $vectorRoot)  -ForegroundColor Green
Write-Host ("[OK]  DB file     : {0}" -f $dbFile)      -ForegroundColor Green

$backendHint = 'uvicorn --app-dir src backend.main:app --host 0.0.0.0 --port 8000'
$corruptStart = Get-Date
$uploadOk = $false
$latestInfoBefore = $null
$latestInfo = $null

try {
    Write-Host ''
    Write-Host '=== Lock check & backend coordination ===' -ForegroundColor Cyan
    if ($AutoBackend) {
        Write-Host '[AUTO] Backend will be restarted automatically after corruption.' -ForegroundColor DarkGray
    } else {
        Write-Host '[OK]  Manual restart expected (use another terminal).' -ForegroundColor Green
    }

    Write-Host ''
    Write-Host '=== Corrupt SQLite header (schema error trigger) ===' -ForegroundColor Cyan
    Corrupt-SqliteHeader -Path $dbFile
    Write-Host '[OK]  Header corrupted.' -ForegroundColor Green

    Write-Host ''
    if ($AutoBackend) {
        Write-Host '=== Auto-start backend ===' -ForegroundColor Cyan
        Start-AutoBackend -RepoRoot $projectRoot -ListenHost $BackendHost -Port $BackendPort -TimeoutSec $BackendStartupTimeoutSec
    } else {
        Write-Host '=== Restart the backend then press Enter ===' -ForegroundColor Cyan
        Write-Host ('Hint: {0}' -f $backendHint)
        Read-Host | Out-Null
    }

    Write-Host ''
    Write-Host 'Waiting for /api/health...' -ForegroundColor Cyan
    if (-not (Wait-HealthOk -TimeoutSec $BackendStartupTimeoutSec)) {
        Write-Host '[ERR] Health check failed.' -ForegroundColor Red
        exit 1
    }

    Write-Host ''
    Write-Host '=== Check for recent backup ===' -ForegroundColor Cyan
    $latestInfoBefore = Get-LatestBackupFolder
    if ($latestInfoBefore -and $latestInfoBefore.Timestamp -ge $corruptStart) {
        Write-Host ('[OK]  Backup found: {0} (Timestamp: {1})' -f $latestInfoBefore.Directory.FullName, $latestInfoBefore.Timestamp) -ForegroundColor Green
    } elseif ($latestInfoBefore) {
        Write-Host ('[WARN] Latest backup {0} predates corruption ({1}). Inspect backend logs for reset timing.' -f $latestInfoBefore.Directory.FullName, $corruptStart) -ForegroundColor Yellow
    } else {
        Write-Host ('[WARN] No ''{0}'' directory detected. Check backend logs; naming may differ.' -f $backupGlob) -ForegroundColor Yellow
    }

    Write-Host ''
    Write-Host '=== Post-reset upload check ===' -ForegroundColor Cyan
    $uploadOk = Upload-Smoke
    $latestInfo = Get-LatestBackupFolder
    if ($latestInfo -and $latestInfo.Timestamp -ge $corruptStart) {
        Write-Host ('[OK]  Backup confirmed after upload: {0} (Timestamp: {1})' -f $latestInfo.Directory.FullName, $latestInfo.Timestamp) -ForegroundColor Green
    } elseif ($latestInfo) {
        Write-Host ('[WARN] Latest backup after upload {0} predates corruption ({1}). Inspect backend logs for reset timing.' -f $latestInfo.Directory.FullName, $corruptStart) -ForegroundColor Yellow
    } else {
        Write-Host ('[WARN] No ''{0}'' directory detected after upload. Check backend logs; naming may differ.' -f $backupGlob) -ForegroundColor Yellow
    }
} finally {
    if ($AutoBackend) {
        Stop-AutoBackend -Reason 'Force-backup scenario completed'
    }
}

Write-Host ''
Write-Host '=== Summary ===' -ForegroundColor Cyan
Write-Host ('Project root  : {0}' -f $projectRoot)
Write-Host ('Vector root   : {0}' -f $vectorRoot)
Write-Host ('DB file       : {0}' -f $dbFile)
Write-Host ('Health        : {0}' -f ($(if ($uploadOk) { 'OK' } else { 'OK (API)' })))
Write-Host ('Upload check  : {0}' -f ($(if ($uploadOk) { 'OK' } else { 'FAIL' })))
Write-Host ('Backup latest : {0}' -f ($(if ($latestInfo) { $latestInfo.Directory.FullName } else { 'NO' })))
Write-Host ('Backup stamp  : {0}' -f ($(if ($latestInfo) { $latestInfo.Timestamp } else { 'n/a' })))

if ($uploadOk) { exit 0 } else { exit 2 }
