[CmdletBinding()]
param(
    [string]$BaseUrl = 'http://127.0.0.1:8000',
    [string]$SmokeEmail,
    [string]$SmokePassword
)

Set-StrictMode -Version Latest
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'

$scriptRoot = Split-Path -Parent $PSCommandPath
$authHelperPath = Join-Path $scriptRoot 'helpers/auth.ps1'
if (-not (Test-Path -LiteralPath $authHelperPath)) {
    throw "Auth helper introuvable: $authHelperPath"
}
. $authHelperPath

$resolvedBase = Resolve-SmokeBaseUrl -BaseUrl $BaseUrl
$authSession = New-SmokeAuthSession -BaseUrl $resolvedBase -Email $SmokeEmail -Password $SmokePassword -Source 'tests/run_all.ps1' -UserAgent 'emergence-smoke-suite'

$authRole = if ($authSession.Role) { $authSession.Role } else { 'n/a' }
$commonHeaders = @{
    Authorization = "Bearer $($authSession.Token)"
    'X-Session-Id' = $authSession.SessionId
}

Write-Host '=== [AUTH] Session initialisee ==='
Write-Host ("Base URL : {0}" -f $authSession.BaseUrl)
Write-Host ("Email    : {0}" -f $authSession.Email)
Write-Host ("Role     : {0}" -f $authRole)
Write-Host ("Session  : {0}" -f $authSession.SessionId)

Write-Host "=== [1] Test /api/health ==="
try {
    $health = Invoke-RestMethod -Uri "$resolvedBase/api/health" -Method GET -TimeoutSec 10
    Write-Host "Health OK:" ($health | ConvertTo-Json -Depth 3)
} catch {
    Write-Host "Health check FAILED: $_"
}

Write-Host "`n=== [2] Test /api/dashboard/costs/summary ==="
try {
    $dashboard = Invoke-RestMethod -Uri "$resolvedBase/api/dashboard/costs/summary" -Method GET -Headers $commonHeaders -TimeoutSec 20
    Write-Host "Dashboard summary:" ($dashboard | ConvertTo-Json -Depth 3)
} catch {
    Write-Host "Dashboard check FAILED: $_"
}

Write-Host "`n=== [3] Test /api/documents (avec et sans slash) ==="
try {
    $docs1 = Invoke-RestMethod -Uri "$resolvedBase/api/documents" -Method GET -Headers $commonHeaders -TimeoutSec 20
    Write-Host "Documents (sans slash):" ($docs1 | ConvertTo-Json -Depth 3)
} catch {
    Write-Host "Documents sans slash FAILED: $_"
}

try {
    $docs2 = Invoke-RestMethod -Uri "$resolvedBase/api/documents/" -Method GET -Headers $commonHeaders -TimeoutSec 20
    Write-Host "Documents (avec slash):" ($docs2 | ConvertTo-Json -Depth 3)
} catch {
    Write-Host "Documents avec slash FAILED: $_"
}

$uploadDocId = $null
Write-Host "`n=== [4] Upload fichier test_upload.txt via curl.exe ==="
$repoPath = (Get-Location).Path
$testFile = Join-Path $repoPath 'test_upload.txt'
if (-not (Test-Path $testFile)) {
    'Ceci est un fichier de test pour EMERGENCE.' | Out-File -FilePath $testFile -Encoding UTF8
    Write-Host "Fichier $testFile cree."
}

try {
    $curlArgs = @('-s','-X','POST')
    $curlArgs += @('-H',("Authorization: Bearer {0}" -f $authSession.Token))
    $curlArgs += @('-H',("X-Session-Id: {0}" -f $authSession.SessionId))
    if ($authSession.UserId) {
        $curlArgs += @('-H',("X-User-Id: {0}" -f $authSession.UserId))
    }
    $curlArgs += @('-F',("file=@{0};type=text/plain" -f $testFile))
    $curlArgs += "$resolvedBase/api/documents/upload"
    Write-Host "Commande executee : curl.exe $($curlArgs -join ' ')"
    $uploadResp = & curl.exe @curlArgs
    if ($LASTEXITCODE -ne 0) {
        throw "curl exit code $LASTEXITCODE"
    }
    Write-Host "Reponse upload : $uploadResp"
    try {
        $uploadJson = $uploadResp | ConvertFrom-Json
        if ($uploadJson -is [System.Collections.IEnumerable]) {
            foreach ($entry in $uploadJson) {
                if ($null -eq $entry) { continue }
                if ($entry.id) {
                    $uploadDocId = [string]$entry.id
                    break
                }
                if ($entry.document -and $entry.document.id) {
                    $uploadDocId = [string]$entry.document.id
                    break
                }
            }
        } elseif ($uploadJson.id) {
            $uploadDocId = [string]$uploadJson.id
        } elseif ($uploadJson.document -and $uploadJson.document.id) {
            $uploadDocId = [string]$uploadJson.document.id
        }
        if ($uploadDocId) {
            Write-Host ("Document upload ID detecte: {0}" -f $uploadDocId)
        } else {
            Write-Host "Impossible de detecter l'ID du document upload (reponse non standard)."
        }
    } catch {
        Write-Host "Parse upload JSON FAILED: $_"
    }
} catch {
    Write-Host "Upload FAILED: $_"
}

Write-Host "`n=== [5] Suppression du document cree (si detecte) ==="
try {
    $targetDocId = if ($uploadDocId) { $uploadDocId } else { "1" }
    Invoke-RestMethod -Uri "$resolvedBase/api/documents/$targetDocId" -Method DELETE -Headers $commonHeaders -TimeoutSec 20 | Out-Null
    Write-Host ("Suppression du document {0} OK (si existait)." -f $targetDocId)
} catch {
    Write-Host "Suppression FAILED (peut etre normal si ID=1 n'existe pas): $_"
}

Write-Host "`n=== [6] Test memory:clear (pytest) ==="
$originalPythonPath = $env:PYTHONPATH
try {
    $srcPath = Join-Path $repoPath 'src'
    if ([string]::IsNullOrEmpty($originalPythonPath)) {
        $env:PYTHONPATH = $srcPath
    } else {
        $env:PYTHONPATH = "$srcPath;$originalPythonPath"
    }
    $pytestCmd = "python -m pytest tests/backend/features/test_memory_clear.py -q"
    Write-Host "Commande executee : $pytestCmd"
    iex $pytestCmd
} catch {
    Write-Host "memory:clear pytest FAILED: $_"
} finally {
    $env:PYTHONPATH = $originalPythonPath
}

Write-Host "`n=== [7] Test benchmarks matrix (pytest) ==="
try {
    $pytestCmd = "python -m pytest tests/test_benchmarks.py -q"
    Write-Host "Commande executee : $pytestCmd"
    iex $pytestCmd
} catch {
    Write-Host "benchmarks pytest FAILED: $_"
}
Write-Host "`n=== Tests termines ==="
