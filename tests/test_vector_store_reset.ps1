# tests/test_vector_store_reset.ps1 — v1.1
# Valide l’auto-reset Chroma du VectorService en simulant une corruption de schéma SQLite.
# À exécuter depuis la racine du repo. Nécessite le backend démarré pour l'upload initial.
# Changelog v1.1:
# - UTF-8 console output (évite l'affichage corrompu des accents)
# - Détection/verrouillage du fichier: attend que le backend soit arrêté avant la corruption
# - Tronquage via FileMode.Truncate (accès exclusif)

# --- Préambule encodage UTF-8 ---
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'

$ErrorActionPreference = "Stop"
$baseUrl    = "http://localhost:8000"
$repoRoot   = (Get-Location).Path
$vectorDir  = Join-Path $repoRoot "src\backend\data\vector_store"

Write-Host "=== [Préflight] Vérifications de base ==="
if (-not (Test-Path $vectorDir)) {
    throw "Répertoire vector_store introuvable : $vectorDir"
}

# 1) Upload initial (crée le store si absent)
Write-Host "`n=== [1] Upload initial pour amorcer le store ==="
$testFile = Join-Path $repoRoot "test_upload.txt"
if (-not (Test-Path $testFile)) {
    "Ceci est un fichier de test pour ÉMERGENCE." | Out-File -FilePath $testFile
    Write-Host "Fichier créé : $testFile"
}

try {
    $resp1 = & curl.exe -s -X POST -F "file=@$testFile;type=text/plain" "$baseUrl/api/documents/upload"
    Write-Host "Réponse upload initial : $resp1"
} catch {
    Write-Warning "Upload initial a échoué. Le backend est-il démarré sur $baseUrl ?"
    throw
}

# 2) Cible SQLite à corrompre
Write-Host "`n=== [2] Corruption ciblée du store SQLite ==="
$sqliteCandidate = Get-ChildItem -Path $vectorDir -Recurse -File -Include *.sqlite* |
                   Sort-Object Length -Descending | Select-Object -First 1

if (-not $sqliteCandidate) {
    Write-Warning "Aucun fichier *.sqlite* trouvé sous $vectorDir. Le store Chroma a-t-il été créé ?"
    Write-Host "Astuce : relance l'upload initial puis ré-exécute ce script."
    throw "Impossible de poursuivre sans fichier SQLite."
}

Write-Host "Fichier SQLite ciblé : $($sqliteCandidate.FullName)"
Write-Host "Taille avant corruption : $($sqliteCandidate.Length) octets"

# 2.a) Vérifier si le fichier est verrouillé -> demander d'arrêter le backend si besoin
function Test-FileUnlocked {
    param([string]$Path)
    try {
        $fs = [System.IO.File]::Open($Path,
                                     [System.IO.FileMode]::Open,
                                     [System.IO.FileAccess]::ReadWrite,
                                     [System.IO.FileShare]::None)
        $fs.Close()
        return $true
    } catch {
        return $false
    }
}

if (-not (Test-FileUnlocked -Path $sqliteCandidate.FullName)) {
    Write-Host "`nLe fichier SQLite est actuellement **verrouillé** (backend probablement en cours)."
    Write-Host "👉 Arrête le backend (Ctrl+C), puis je réessaie jusqu'à ce qu'il soit libéré..."
    do {
        Start-Sleep -Seconds 1
    } until (Test-FileUnlocked -Path $sqliteCandidate.FullName)
    Write-Host "OK, fichier libéré."
}

# 2.b) Tronquer proprement (0 octet) avec accès exclusif
try {
    $fs = [System.IO.File]::Open($sqliteCandidate.FullName,
                                 [System.IO.FileMode]::Truncate,
                                 [System.IO.FileAccess]::ReadWrite,
                                 [System.IO.FileShare]::None)
    $fs.Close()
} catch {
    throw "Échec du tronquage exclusif de $($sqliteCandidate.FullName) : $($_.Exception.Message)"
}

$after = (Get-Item $sqliteCandidate.FullName).Length
Write-Host "Taille après corruption : $after octets"
if ($after -ne 0) {
    throw "La corruption n'a pas abouti (taille != 0). Abandon."
}

# 3) Pause technique : relance manuelle du backend (pour déclencher l'auto-reset à l'init)
Write-Host "`n=== [3] Relance requise du backend ==="
Write-Host "👉 Relance maintenant le backend dans une autre fenêtre :"
Write-Host "   uvicorn --app-dir src backend.main:app --host 0.0.0.0 --port 8000"
[void](Read-Host "Appuie sur Entrée quand le backend est relancé et prêt")

# 4) Vérifications : existence d'un backup + upload à nouveau
Write-Host "`n=== [4] Vérification du backup + upload post-reset ==="
$backups = Get-ChildItem -Path (Split-Path $vectorDir -Parent) -Directory -Filter "vector_store_backup_*" `
           | Sort-Object Name -Descending

if ($backups.Count -eq 0) {
    Write-Warning "Aucun dossier vector_store_backup_* détecté. Vérifie les logs backend (auto-reset attendu)."
} else {
    Write-Host "Dernier backup détecté : $($backups[0].FullName)"
}

try {
    $resp2 = & curl.exe -s -X POST -F "file=@$testFile;type=text/plain" "$baseUrl/api/documents/upload"
    Write-Host "Réponse upload après reset : $resp2"
    Write-Host "`n=== ✅ Test terminé : auto-reset validé si backup créé et upload OK ==="
} catch {
    Write-Error "Upload après reset a échoué. Consulte les logs backend."
    throw
}
