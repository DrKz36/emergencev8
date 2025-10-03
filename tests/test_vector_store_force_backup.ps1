#requires -Version 5.1
<#
    EMERGENCE - Test force-backup (PowerShell 5.1 compatible, ASCII-only)
    - Corrompt le header SQLite du vector store Chroma
    - Attend le red�marrage backend (manuel)
    - V�rifie /api/health
    - D�tecte le dernier dossier de backup "vector_store_backup_*"
    - Fait un upload de contr�le via HttpClient avec authentification email/mot de passe
    Sorties:
      Exit 0 -> Succes (health OK, upload OK; backup trouv� si cr��)
      Exit 2 -> Upload FAIL (health OK)
      Exit 1 -> Health KO / autre erreur bloquante
#>

[CmdletBinding()]
param(
    [string]$ApiBase = 'http://127.0.0.1:8000',
    [string]$SmokeEmail,
    [string]$SmokePassword
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host ''
Write-Host '=== Force-Backup Test (PS 5.1 - Windows-proof) ===' -ForegroundColor Cyan

# ---------- R�solution des chemins & helper d'auth ----------
$ScriptDir = Split-Path -Parent $PSCommandPath
if (-not $ScriptDir) { $ScriptDir = (Get-Location).Path }
$ProjectRoot = (Get-Item (Join-Path $ScriptDir '..')).FullName

$AuthHelperPath = Join-Path $ScriptDir 'helpers/auth.ps1'
if (-not (Test-Path -LiteralPath $AuthHelperPath)) {
    throw 'Auth helper introuvable: ' + $AuthHelperPath
}
. $AuthHelperPath

$ApiBase = Resolve-SmokeBaseUrl -BaseUrl $ApiBase
$HealthUrl = "$ApiBase/api/health"
$UploadUrl = "$ApiBase/api/documents/upload"

$VectorRoot  = Join-Path $ProjectRoot 'src\backend\data\vector_store'
$DbFile      = Join-Path $VectorRoot  'chroma.sqlite3'
$TmpDir      = Join-Path $ProjectRoot 'tmp_tests'
$BackupGlob  = 'vector_store_backup_*'
$BackendHint = 'uvicorn --app-dir src backend.main:app --host 0.0.0.0 --port 8000'

$script:ForceAuthSession = $null
function Get-ForceAuthSession {
    if (-not $script:ForceAuthSession) {
        $script:ForceAuthSession = New-SmokeAuthSession -BaseUrl $ApiBase -Email $SmokeEmail -Password $SmokePassword -Source 'tests/test_vector_store_force_backup.ps1' -UserAgent 'emergence-vector-force'
        Write-Host ("[AUTH] Session {0} pr�te pour {1}" -f $script:ForceAuthSession.SessionId, $script:ForceAuthSession.Email) -ForegroundColor DarkGray
    }
    return $script:ForceAuthSession
}

# ---------- Utils ----------
function Wait-HealthOk {
    param([int]$TimeoutSec = 180, [int]$IntervalMs = 800)
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $TimeoutSec) {
        try {
            $res = Invoke-RestMethod -Uri $HealthUrl -Method GET -TimeoutSec 5
            if ($res.status -eq 'ok') {
                Write-Host '[OK]  /api/health OK.' -ForegroundColor Green
                return $true
            }
        } catch { }
        Start-Sleep -Milliseconds $IntervalMs
    }
    Write-Host ("[ERR] /api/health timeout apres {0} s." -f $TimeoutSec) -ForegroundColor Red
    return $false
}

function Get-LatestBackupFolder {
    param([datetime]$Since)
    $parent = Split-Path $VectorRoot -Parent
    $candidates = Get-ChildItem -LiteralPath $parent -Directory -ErrorAction SilentlyContinue |
                  Where-Object { $_.Name -like $BackupGlob }
    if (-not $candidates) { return $null }
    $latest = $candidates | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($Since -and ($latest.LastWriteTime -lt $Since)) { return $null }
    return $latest
}

function Corrupt-SqliteHeader {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "DB introuvable: $Path"
    }
    $fs = [System.IO.File]::Open($Path,[System.IO.FileMode]::Open,[System.IO.FileAccess]::ReadWrite,[System.IO.FileShare]::None)
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
    New-Item -ItemType Directory -Force -Path $TmpDir | Out-Null

    $filePath = Join-Path $TmpDir ("upload_vector_check_{0}.txt" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
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
        $req = New-Object System.Net.Http.HttpRequestMessage([System.Net.Http.HttpMethod]::Post, $UploadUrl)
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
                Write-Host ("[OK]  Upload post-reset reussi. HTTP {0} | ID={1} | file={2}" -f $status, $json.document_id, $json.filename) -ForegroundColor Green
                return $true
            } else {
                Write-Host ("[WARN] Upload: HTTP {0}, corps inattendu: {1}" -f $status, $body) -ForegroundColor Yellow
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

# ---------- D�but ----------
Write-Host ''
Write-Host '=== Preflight & vector_store targeting ===' -ForegroundColor Cyan
if (-not (Test-Path -LiteralPath $VectorRoot)) { throw "Vector root introuvable: $VectorRoot" }
if (-not (Test-Path -LiteralPath $DbFile))   { throw "DB introuvable: $DbFile" }
Write-Host ("[OK]  Project root: {0}" -f $ProjectRoot) -ForegroundColor Green
Write-Host ("[OK]  Vector root : {0}" -f $VectorRoot)  -ForegroundColor Green
Write-Host ("[OK]  DB file     : {0}" -f $DbFile)      -ForegroundColor Green

Write-Host ''
Write-Host '=== Lock check & stop backend if needed ===' -ForegroundColor Cyan
Write-Host '[OK]  Pas d''arret force par le script (gere cote Terminal B si besoin).' -ForegroundColor Green

Write-Host ''
Write-Host '=== Corrupt SQLite header (schema error trigger) ===' -ForegroundColor Cyan
$corruptStart = Get-Date
Corrupt-SqliteHeader -Path $DbFile
Write-Host '[OK]  Header corrupted.' -ForegroundColor Green

Write-Host ''
Write-Host '=== Redemarre le backend puis reviens ici et appuie Entree ===' -ForegroundColor Cyan
Write-Host ('Hint: {0}' -f $BackendHint)
Read-Host | Out-Null

Write-Host ''
Write-Host 'Waiting for /api/health...' -ForegroundColor Cyan
if (-not (Wait-HealthOk -TimeoutSec 180)) {
    Write-Host '[ERR] Health check KO.' -ForegroundColor Red
    exit 1
}

Write-Host ''
Write-Host '=== Check for recent backup ===' -ForegroundColor Cyan
$latest = Get-LatestBackupFolder -Since $corruptStart
if ($latest) {
    Write-Host ('[OK]  Backup trouve: {0} (LastWriteTime: {1})' -f $latest.FullName, $latest.LastWriteTime) -ForegroundColor Green
} else {
    Write-Host ('[WARN] Aucun dossier ''{0}'' recent detecte depuis {1}. Verifie les logs backend; le nommage peut differer.' -f $BackupGlob, $corruptStart) -ForegroundColor Yellow
}

Write-Host ''
Write-Host '=== Post-reset upload check ===' -ForegroundColor Cyan
$uploadOk = Upload-Smoke

Write-Host ''
Write-Host '=== Summary ===' -ForegroundColor Cyan
Write-Host ('Project root  : {0}' -f $ProjectRoot)
Write-Host ('Vector root   : {0}' -f $VectorRoot)
Write-Host ('DB file       : {0}' -f $DbFile)
Write-Host ('Health        : {0}' -f ($(if ($uploadOk) { 'OK' } else { 'OK (API)' })))
Write-Host ('Upload check  : {0}' -f ($(if ($uploadOk) { 'OK' } else { 'FAIL' })))
Write-Host ('Backup latest : {0}' -f ($(if ($latest) { $latest.FullName } else { 'NO' })))

if ($uploadOk) { exit 0 } else { exit 2 }
