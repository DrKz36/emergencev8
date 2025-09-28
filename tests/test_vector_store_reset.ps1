# tests/test_vector_store_reset.ps1 — v1.2
# Valide l’auto-reset Chroma du VectorService en simulant une corruption de schéma SQLite.
# À exécuter depuis la racine du repo. Nécessite le backend démarré pour l'upload initial.
# Changelog v1.2:
# - Option -AutoBackend pour démarrer/arrêter uvicorn automatiquement lors du scénario
# - Attente /api/health pour fiabiliser les uploads en mode auto
# - Libération forcée du fichier SQLite avant corruption afin d'éviter les conflits de port
# - Journalisation minimale sur chaque étape auto pour faciliter le debug CI
# Changelog v1.1:
# - UTF-8 console output (évite l'affichage corrompu des accents)
# - Détection/verrouillage du fichier: attend que le backend soit arrêté avant la corruption
# - Tronquage via FileMode.Truncate (accès exclusif)

param(
    [switch]$AutoBackend,
    [string]$BackendHost = '127.0.0.1',
    [int]$BackendPort = 8000,
    [int]$BackendStartupTimeoutSec = 60
)

# --- Préambule encodage UTF-8 ---
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Resolve-PythonExe {
    param([string]$RepoRoot)
    $venvPython = Join-Path $RepoRoot '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $venvPython) {
        return $venvPython
    }
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        return $pythonCmd.Path
    }
    return 'python'
}

function Wait-BackendReady {
    param([string]$BaseUrl, [int]$TimeoutSec = 60)
    $healthUrl = "$BaseUrl/api/health"
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $res = Invoke-RestMethod -Uri $healthUrl -Method GET -TimeoutSec 5
            if ($res -and ($res.status -eq 'ok' -or $res.status -eq 'healthy')) {
                return $true
            }
        } catch {}
        Start-Sleep -Milliseconds 700
    }
    return $false
}

$script:BackendProcess = $null
$script:BackendWasStarted = $false

function Start-AutoBackend {
    param(
        [string]$RepoRoot,
        [string]$ListenHost,
        [int]$Port,
        [string]$BaseUrl,
        [int]$TimeoutSec
    )
    if ($script:BackendProcess -and -not $script:BackendProcess.HasExited) {
        throw "Un backend est déjà actif (PID $($script:BackendProcess.Id))."
    }
    $pythonExe = Resolve-PythonExe -RepoRoot $RepoRoot
    $args = @('-m','uvicorn','--app-dir','src','backend.main:app','--host',$ListenHost,'--port',$Port.ToString())
    Write-Host ("[AUTO] Démarrage backend ($pythonExe $($args -join ' ')).") -ForegroundColor DarkGray
    $proc = Start-Process -FilePath $pythonExe -ArgumentList $args -WorkingDirectory $RepoRoot -PassThru -NoNewWindow
    Start-Sleep -Milliseconds 250
    if (-not (Wait-BackendReady -BaseUrl $BaseUrl -TimeoutSec $TimeoutSec)) {
        try { if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } } catch {}
        throw "Le backend n'a pas répondu sur $BaseUrl/api/health après $TimeoutSec seconde(s)."
    }
    $script:BackendProcess = $proc
    $script:BackendWasStarted = $true
    Write-Host '[AUTO] Backend prêt.' -ForegroundColor Green
}

function Stop-AutoBackend {
    param(
        [string]$Reason = 'Arrêt automatique du backend',
        [switch]$Quiet
    )
    $proc = $script:BackendProcess
    if (-not $proc) { return }
    if (-not $Quiet) {
        Write-Host ("[AUTO] $Reason (PID $($proc.Id)).") -ForegroundColor DarkGray
    }
    try {
        if (-not $proc.HasExited) {
            Stop-Process -Id $proc.Id -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 400
        }
        if (-not $proc.HasExited) {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
        $proc.WaitForExit()
    } catch {
        if (-not $Quiet) {
            Write-Warning ("Impossible d'arrêter le backend auto : $($_.Exception.Message)")
        }
    } finally {
        $proc.Dispose()
        $script:BackendProcess = $null
    }
}

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

function Wait-FileUnlocked {
    param([string]$Path, [int]$TimeoutSec = 45)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-FileUnlocked -Path $Path) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

$baseUrl    = "http://${BackendHost}:${BackendPort}"
$repoRoot   = (Get-Location).Path
$vectorDir  = Join-Path $repoRoot 'src\backend\data\vector_store'
$smokeUserId = 'vector-reset'
$smokeSessionId = 'vsreset-' + ([Guid]::NewGuid().ToString('N'))

Write-Host '=== [Préflight] Vérifications de base ==='
if (-not (Test-Path $vectorDir)) {
    throw "Répertoire vector_store introuvable : $vectorDir"
}

try {
    if ($AutoBackend) {
        Write-Host "`n=== [0] Démarrage auto du backend ==="
        Start-AutoBackend -RepoRoot $repoRoot -ListenHost '0.0.0.0' -Port $BackendPort -BaseUrl $baseUrl -TimeoutSec $BackendStartupTimeoutSec
    }

    # 1) Upload initial (crée le store si absent)
    Write-Host "`n=== [1] Upload initial pour amorcer le store ==="
    $testFile = Join-Path $repoRoot 'test_upload.txt'
    if (-not (Test-Path $testFile)) {
        'Ceci est un fichier de test pour ÉMERGENCE.' | Out-File -FilePath $testFile
        Write-Host "Fichier créé : $testFile"
    }

    try {
        $curlArgs = @(
            '-s',
            '-X','POST',
            '-H',"X-Session-Id: $smokeSessionId",
            '-H',"X-User-Id: $smokeUserId",
            '-H','X-Dev-Bypass: 1',
            '-F',"file=@$testFile;type=text/plain",
            "$baseUrl/api/documents/upload"
        )
        $resp1 = & curl.exe @curlArgs
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
        throw 'Impossible de poursuivre sans fichier SQLite.'
    }

    Write-Host "Fichier SQLite ciblé : $($sqliteCandidate.FullName)"
    Write-Host "Taille avant corruption : $($sqliteCandidate.Length) octets"

    if ($AutoBackend) {
        Stop-AutoBackend -Reason 'Arrêt backend pour libérer le store'
        if (-not (Wait-FileUnlocked -Path $sqliteCandidate.FullName -TimeoutSec 30)) {
            throw 'Le fichier SQLite reste verrouillé après l''arrêt auto du backend.'
        }
        Write-Host 'Fichier libéré.'
    } else {
        if (-not (Test-FileUnlocked -Path $sqliteCandidate.FullName)) {
            Write-Host "`nLe fichier SQLite est actuellement **verrouillé** (backend probablement en cours)."
            Write-Host '👉 Arrête le backend (Ctrl+C), puis je réessaie jusqu''à ce qu''il soit libéré...'
            do {
                Start-Sleep -Seconds 1
            } until (Test-FileUnlocked -Path $sqliteCandidate.FullName)
            Write-Host 'OK, fichier libéré.'
        }
    }

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
        throw 'La corruption n''a pas abouti (taille != 0). Abandon.'
    }

    # 3) Relance backend
    Write-Host "`n=== [3] Relance requise du backend ==="
    if ($AutoBackend) {
        Start-AutoBackend -RepoRoot $repoRoot -ListenHost '0.0.0.0' -Port $BackendPort -BaseUrl $baseUrl -TimeoutSec $BackendStartupTimeoutSec
    } else {
        Write-Host '👉 Relance maintenant le backend dans une autre fenêtre :'
        Write-Host "   uvicorn --app-dir src backend.main:app --host 0.0.0.0 --port $BackendPort"
        [void](Read-Host 'Appuie sur Entrée quand le backend est relancé et prêt')
    }

    # 4) Vérifications : existence d'un backup + upload à nouveau
    Write-Host "`n=== [4] Vérification du backup + upload post-reset ==="
    $backups = Get-ChildItem -Path (Split-Path $vectorDir -Parent) -Directory -Filter 'vector_store_backup_*' `
               | Sort-Object Name -Descending

    if ($backups.Count -eq 0) {
        Write-Warning 'Aucun dossier vector_store_backup_* détecté. Vérifie les logs backend (auto-reset attendu).'
    } else {
        Write-Host "Dernier backup détecté : $($backups[0].FullName)"
    }

    try {
        $curlArgs2 = @(
            '-s',
            '-X','POST',
            '-H',"X-Session-Id: $smokeSessionId",
            '-H',"X-User-Id: $smokeUserId",
            '-H','X-Dev-Bypass: 1',
            '-F',"file=@$testFile;type=text/plain",
            "$baseUrl/api/documents/upload"
        )
        $resp2 = & curl.exe @curlArgs2
        Write-Host "Réponse upload après reset : $resp2"
        Write-Host "`n=== ✅ Test terminé : auto-reset validé si backup créé et upload OK ==="
    } catch {
        Write-Error 'Upload après reset a échoué. Consulte les logs backend.'
        throw
    }
}
finally {
    if ($AutoBackend) {
        Stop-AutoBackend -Quiet
    }
}


