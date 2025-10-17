# ============================================================================
# PROD GUARDIAN SCHEDULER - Automated Production Monitoring
# ============================================================================
# Script dédié à la surveillance automatique de la production sur Google Cloud
# Exécute check_prod_logs.py toutes les 30 minutes
# Conçu pour être exécuté par le Task Scheduler Windows
# ============================================================================

param(
    [switch]$Force,
    [switch]$Verbose,
    [switch]$TestMode,
    [switch]$SetupScheduler  # Nouvelle option pour configurer automatiquement le Task Scheduler
)

# Configuration des couleurs pour les logs
$ColorSuccess = "Green"
$ColorWarning = "Yellow"
$ColorError = "Red"
$ColorInfo = "Cyan"

# Fonction pour logger avec timestamp
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"

    # Afficher dans la console avec couleur
    switch ($Level) {
        "SUCCESS" { Write-Host $logMessage -ForegroundColor $ColorSuccess }
        "WARNING" { Write-Host $logMessage -ForegroundColor $ColorWarning }
        "ERROR"   { Write-Host $logMessage -ForegroundColor $ColorError }
        default   { Write-Host $logMessage -ForegroundColor $ColorInfo }
    }

    # Écrire dans le fichier log
    $logFile = Join-Path $global:LogDir "prodguardian_scheduler_$(Get-Date -Format 'yyyy-MM').log"
    Add-Content -Path $logFile -Value $logMessage -ErrorAction SilentlyContinue
}

# ============================================================================
# FONCTION POUR CONFIGURER LE TASK SCHEDULER
# ============================================================================

function Setup-TaskScheduler {
    Write-Log "================================================================" "INFO"
    Write-Log "🔧 Configuration du Task Scheduler Windows" "INFO"
    Write-Log "================================================================" "INFO"

    # Nom de la tâche
    $TaskName = "ProdGuardian_AutoMonitor"
    $TaskPath = "\ÉMERGENCE\"

    # Vérifier si la tâche existe déjà
    try {
        $existingTask = Get-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -ErrorAction SilentlyContinue
        if ($existingTask) {
            Write-Log "La tâche '$TaskName' existe déjà" "WARNING"
            $response = Read-Host "Voulez-vous la recréer? (O/N)"
            if ($response -ne "O") {
                Write-Log "Configuration annulée" "INFO"
                return
            }
            Unregister-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -Confirm:$false
            Write-Log "Tâche existante supprimée" "SUCCESS"
        }
    } catch {
        # La tâche n'existe pas, continuer
    }

    # Créer l'action (exécuter ce script PowerShell)
    $scriptPath = $MyInvocation.ScriptName
    if (-not $scriptPath) {
        $scriptPath = $PSCommandPath
    }

    $Action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""

    # Créer le déclencheur (toutes les 30 minutes)
    $Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 30) -RepetitionDuration ([TimeSpan]::MaxValue)

    # Créer les paramètres de la tâche
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable

    # Créer le principal (exécuter avec l'utilisateur actuel)
    $Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive

    # Enregistrer la tâche
    try {
        Register-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description "Surveillance automatique de la production ÉMERGENCE sur Google Cloud toutes les 30 minutes"

        Write-Log "✅ Tâche planifiée créée avec succès!" "SUCCESS"
        Write-Log "   Nom: $TaskName" "INFO"
        Write-Log "   Chemin: $TaskPath" "INFO"
        Write-Log "   Fréquence: Toutes les 30 minutes" "INFO"
        Write-Log "   Script: $scriptPath" "INFO"
        Write-Log "" "INFO"
        Write-Log "💡 Pour gérer la tâche:" "INFO"
        Write-Log "   - Ouvrir le Planificateur de tâches (taskschd.msc)" "INFO"
        Write-Log "   - Naviguer vers: Bibliothèque du Planificateur de tâches > ÉMERGENCE" "INFO"
        Write-Log "   - Ou utiliser: Get-ScheduledTask -TaskName '$TaskName'" "INFO"

    } catch {
        Write-Log "❌ Erreur lors de la création de la tâche: $($_.Exception.Message)" "ERROR"
        Write-Log "💡 Assurez-vous d'exécuter PowerShell en tant qu'administrateur" "WARNING"
        exit 1
    }
}

# ============================================================================
# CONFIGURATION ET INITIALISATION
# ============================================================================

Write-Log "================================================================" "INFO"
Write-Log "🔍 PROD GUARDIAN SCHEDULER - Surveillance Production Automatique" "INFO"
Write-Log "================================================================" "INFO"

# Si l'option -SetupScheduler est activée, configurer le Task Scheduler et quitter
if ($SetupScheduler) {
    Setup-TaskScheduler
    exit 0
}

# Déterminer le répertoire racine du projet
$repoRoot = "C:\dev\emergenceV8"
if (-not (Test-Path $repoRoot)) {
    Write-Log "Erreur: Dépôt non trouvé à $repoRoot" "ERROR"
    exit 1
}

Set-Location $repoRoot
Write-Log "Répertoire de travail: $repoRoot" "INFO"

# Définir les chemins
$global:PluginDir = Join-Path $repoRoot "claude-plugins\integrity-docs-guardian"
$global:ScriptsDir = Join-Path $global:PluginDir "scripts"
$global:LogDir = Join-Path $global:PluginDir "logs"
$global:ReportsDir = Join-Path $global:PluginDir "reports"

# Créer les répertoires s'ils n'existent pas
@($global:LogDir, $global:ReportsDir) | ForEach-Object {
    if (-not (Test-Path $_)) {
        New-Item -ItemType Directory -Path $_ -Force | Out-Null
        Write-Log "Répertoire créé: $_" "INFO"
    }
}

# ============================================================================
# VÉRIFICATION DES PRÉREQUIS
# ============================================================================

Write-Log "" "INFO"
Write-Log "📋 Vérification des prérequis..." "INFO"

# Vérifier Python
$pythonExe = $null
if (Test-Path "$repoRoot\.venv\Scripts\python.exe") {
    $pythonExe = "$repoRoot\.venv\Scripts\python.exe"
    Write-Log "Python trouvé dans venv: $pythonExe" "SUCCESS"
} else {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        $pythonExe = $pythonCmd.Source
        Write-Log "Python trouvé: $pythonExe" "SUCCESS"
    } else {
        Write-Log "Python non trouvé!" "ERROR"
        exit 1
    }
}

# Vérifier le script check_prod_logs.py
$checkProdScript = Join-Path $global:ScriptsDir "check_prod_logs.py"
if (-not (Test-Path $checkProdScript)) {
    Write-Log "Script check_prod_logs.py non trouvé: $checkProdScript" "ERROR"
    exit 1
}
Write-Log "Script de surveillance trouvé: check_prod_logs.py" "SUCCESS"

# Vérifier gcloud CLI
$gcloudCmd = Get-Command gcloud -ErrorAction SilentlyContinue
if (-not $gcloudCmd) {
    $gcloudCmd = Get-Command gcloud.cmd -ErrorAction SilentlyContinue
}

if ($gcloudCmd) {
    Write-Log "gcloud CLI trouvé: $($gcloudCmd.Source)" "SUCCESS"
} else {
    Write-Log "gcloud CLI non trouvé!" "WARNING"
    Write-Log "La surveillance de production nécessite gcloud CLI installé et authentifié" "WARNING"
    if (-not $TestMode) {
        exit 1
    }
}

# ============================================================================
# EXÉCUTION DE LA SURVEILLANCE PRODUCTION
# ============================================================================

Write-Log "" "INFO"
Write-Log "================================================================" "INFO"
Write-Log "🚀 Lancement de la surveillance production Google Cloud" "INFO"
Write-Log "================================================================" "INFO"
Write-Log "Service: emergence-app" "INFO"
Write-Log "Région: europe-west1" "INFO"
Write-Log "Fenêtre: 1 heure" "INFO"
Write-Log "" "INFO"

$prodCheckSuccess = $false
$prodStatus = "UNKNOWN"
$prodReport = $null

try {
    Write-Log "Exécution de check_prod_logs.py..." "INFO"

    # Exécuter le script Python
    $prodOutput = & $pythonExe $checkProdScript 2>&1
    $prodExitCode = $LASTEXITCODE

    if ($Verbose) {
        Write-Log "=== Sortie de check_prod_logs.py ===" "INFO"
        $prodOutput | ForEach-Object { Write-Host $_ }
        Write-Log "=== Fin de la sortie ===" "INFO"
    }

    # Analyser le code de sortie
    # 0 = OK, 1 = DEGRADED, 2 = CRITICAL
    switch ($prodExitCode) {
        0 {
            $prodStatus = "OK"
            $prodCheckSuccess = $true
            Write-Log "✅ Production Status: OK - Aucune anomalie détectée" "SUCCESS"
        }
        1 {
            $prodStatus = "DEGRADED"
            $prodCheckSuccess = $true
            Write-Log "⚠️ Production Status: DEGRADED - Avertissements détectés" "WARNING"
        }
        2 {
            $prodStatus = "CRITICAL"
            $prodCheckSuccess = $true
            Write-Log "🔴 Production Status: CRITICAL - Problèmes critiques détectés!" "ERROR"
        }
        default {
            $prodStatus = "ERROR"
            Write-Log "❌ Erreur lors de l'exécution de check_prod_logs.py (code: $prodExitCode)" "ERROR"
        }
    }

    # Trouver le rapport généré
    $prodReport = Join-Path $global:ReportsDir "prod_report.json"
    if (Test-Path $prodReport) {
        Write-Log "Rapport généré: prod_report.json" "SUCCESS"

        # Lire le rapport pour plus de détails
        try {
            $reportContent = Get-Content $prodReport -Raw | ConvertFrom-Json
            Write-Log "" "INFO"
            Write-Log "📊 Résumé du rapport:" "INFO"
            Write-Log "   Logs analysés: $($reportContent.logs_analyzed)" "INFO"
            Write-Log "   Erreurs: $($reportContent.summary.errors)" "INFO"
            Write-Log "   Warnings: $($reportContent.summary.warnings)" "INFO"
            Write-Log "   Signaux critiques: $($reportContent.summary.critical_signals)" "INFO"
            Write-Log "   Problèmes de latence: $($reportContent.summary.latency_issues)" "INFO"

            # Afficher les recommandations si présentes
            if ($reportContent.recommendations -and $reportContent.recommendations.Count -gt 0) {
                Write-Log "" "INFO"
                Write-Log "💡 Recommandations:" "INFO"
                foreach ($rec in $reportContent.recommendations) {
                    Write-Log "   [$($rec.priority)] $($rec.action)" "INFO"
                    if ($rec.details) {
                        Write-Log "      $($rec.details)" "INFO"
                    }
                    if ($rec.command) {
                        Write-Log "      Commande: $($rec.command)" "INFO"
                    }
                }
            }
        } catch {
            Write-Log "Impossible de lire le rapport JSON: $($_.Exception.Message)" "WARNING"
        }
    } else {
        Write-Log "Aucun rapport généré" "WARNING"
    }

} catch {
    Write-Log "Exception lors de l'exécution de la surveillance: $($_.Exception.Message)" "ERROR"
    $prodStatus = "ERROR"
}

# ============================================================================
# GÉNÉRATION DU RAPPORT D'EXÉCUTION
# ============================================================================

Write-Log "" "INFO"
Write-Log "📝 Génération du rapport d'exécution..." "INFO"

$executionReport = @{
    timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    execution_mode = if ($TestMode) { "test" } else { "scheduled" }
    production_status = $prodStatus
    success = $prodCheckSuccess
    report_path = $prodReport
    exit_code = $prodExitCode
}

# Sauvegarder le rapport d'exécution
$executionReportPath = Join-Path $global:ReportsDir "prodguardian_execution_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
try {
    $executionReport | ConvertTo-Json -Depth 10 | Out-File -FilePath $executionReportPath -Encoding UTF8
    Write-Log "Rapport d'exécution sauvegardé: $(Split-Path $executionReportPath -Leaf)" "SUCCESS"
} catch {
    Write-Log "Erreur lors de la sauvegarde du rapport d'exécution: $($_.Exception.Message)" "ERROR"
}

# ============================================================================
# NETTOYAGE DES ANCIENS RAPPORTS
# ============================================================================

Write-Log "" "INFO"
Write-Log "🧹 Nettoyage des anciens rapports (> 7 jours)..." "INFO"

try {
    $cutoffDate = (Get-Date).AddDays(-7)
    $oldReports = Get-ChildItem -Path $global:ReportsDir -Filter "prodguardian_execution_*.json" |
                  Where-Object { $_.LastWriteTime -lt $cutoffDate }

    if ($oldReports.Count -gt 0) {
        $oldReports | ForEach-Object {
            Remove-Item $_.FullName -Force
            Write-Log "Rapport supprimé: $($_.Name)" "INFO"
        }
        Write-Log "$($oldReports.Count) ancien(s) rapport(s) supprimé(s)" "SUCCESS"
    } else {
        Write-Log "Aucun ancien rapport à supprimer" "INFO"
    }
} catch {
    Write-Log "Erreur lors du nettoyage: $($_.Exception.Message)" "WARNING"
}

# ============================================================================
# ALERTES (optionnel - peut être étendu avec notifications par email/Slack)
# ============================================================================

if ($prodStatus -eq "CRITICAL") {
    Write-Log "" "INFO"
    Write-Log "🚨 ALERTE CRITIQUE: Production en état critique!" "ERROR"
    Write-Log "Actions recommandées:" "ERROR"
    Write-Log "  1. Consulter le rapport: $prodReport" "ERROR"
    Write-Log "  2. Vérifier les logs Cloud Run: gcloud logging read ..." "ERROR"
    Write-Log "  3. Contacter l'équipe de développement si nécessaire" "ERROR"

    # TODO: Ajouter ici l'envoi d'email ou notification Slack si configuré
}

# ============================================================================
# RÉSUMÉ FINAL
# ============================================================================

Write-Log "" "INFO"
Write-Log "================================================================" "INFO"
Write-Log "✅ SURVEILLANCE TERMINÉE" "INFO"
Write-Log "================================================================" "INFO"
Write-Log "" "INFO"
Write-Log "📊 Résumé:" "INFO"
Write-Log "  Status Production: $prodStatus" "INFO"
Write-Log "  Exécution: $(if ($prodCheckSuccess) { '✅ SUCCESS' } else { '❌ FAILED' })" "INFO"
Write-Log "  Rapport: $prodReport" "INFO"
Write-Log "  Prochaine exécution: Dans 30 minutes (via Task Scheduler)" "INFO"
Write-Log "" "INFO"

# Code de sortie
$exitCode = if ($prodCheckSuccess) { 0 } else { 1 }

Write-Log "================================================================" "INFO"
Write-Log "Fin de l'exécution (code: $exitCode)" "INFO"
Write-Log "================================================================" "INFO"

exit $exitCode
