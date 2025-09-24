# tests/run_all.ps1 - v1.3 (compatibilite PowerShell 5.1)
# Teste les endpoints cles du backend EMERGENCE.
# Usage : lancer depuis la racine du projet avec le backend demarre sur localhost:8000

$baseUrl = "http://localhost:8000"

Write-Host "=== [1] Test /api/health ==="
try {
    $health = Invoke-RestMethod -Uri "$baseUrl/api/health" -Method GET
    Write-Host "Health OK:" ($health | ConvertTo-Json -Depth 3)
} catch {
    Write-Host "Health check FAILED: $_"
}

Write-Host "`n=== [2] Test /api/dashboard/costs/summary ==="
try {
    $dashboard = Invoke-RestMethod -Uri "$baseUrl/api/dashboard/costs/summary" -Method GET
    Write-Host "Dashboard summary:" ($dashboard | ConvertTo-Json -Depth 3)
} catch {
    Write-Host "Dashboard check FAILED: $_"
}

Write-Host "`n=== [3] Test /api/documents (avec et sans slash) ==="
try {
    $docs1 = Invoke-RestMethod -Uri "$baseUrl/api/documents" -Method GET
    Write-Host "Documents (sans slash):" ($docs1 | ConvertTo-Json -Depth 3)
} catch {
    Write-Host "Documents sans slash FAILED: $_"
}

try {
    $docs2 = Invoke-RestMethod -Uri "$baseUrl/api/documents/" -Method GET
    Write-Host "Documents (avec slash):" ($docs2 | ConvertTo-Json -Depth 3)
} catch {
    Write-Host "Documents avec slash FAILED: $_"
}

Write-Host "`n=== [4] Upload fichier test_upload.txt via curl.exe ==="
# Verifier que test_upload.txt existe
$testFile = Join-Path (Get-Location) "test_upload.txt"
if (-Not (Test-Path $testFile)) {
    "Ceci est un fichier de test pour EMERGENCE." | Out-File -FilePath $testFile -Encoding UTF8
    Write-Host "Fichier $testFile cree."
}

try {
    $uploadCmd = "curl.exe -s -X POST -F `"file=@$testFile;type=text/plain`" $baseUrl/api/documents/upload"
    Write-Host "Commande executee : $uploadCmd"
    iex $uploadCmd
} catch {
    Write-Host "Upload FAILED: $_"
}

Write-Host "`n=== [5] Suppression du document ID=1 (si existe) ==="
try {
    Invoke-RestMethod -Uri "$baseUrl/api/documents/1" -Method DELETE
    Write-Host "Suppression du document 1 OK (si existait)."
} catch {
    Write-Host "Suppression FAILED (peut etre normal si ID=1 n'existe pas): $_"
}

Write-Host "`n=== [6] Test memory:clear (pytest) ==="
$originalPythonPath = $env:PYTHONPATH
try {
    $repoPath = (Get-Location).Path
    $srcPath = Join-Path $repoPath "src"
    if ([string]::IsNullOrEmpty($originalPythonPath)) {
        $env:PYTHONPATH = $srcPath
    } else {
        $env:PYTHONPATH = "$srcPath;${originalPythonPath}"
    }
    $pytestCmd = "python -m pytest tests/backend/features/test_memory_clear.py -q"
    Write-Host "Commande executee : $pytestCmd"
    iex $pytestCmd
} catch {
    Write-Host "memory:clear pytest FAILED: $_"
} finally {
    $env:PYTHONPATH = $originalPythonPath
}

Write-Host "`n=== Tests termines ==="
