# ============================================================================
# UNIFIED GUARDIAN SCHEDULER - Phase 3 (Version Simple)
# ============================================================================
# Script unifie qui orchestre:
# 1. Guardian d'integrite (verifications des documents)
# 2. ProdGuardian (surveillance production)
# 3. Generation de rapports consolides
# 4. AutoSync pour mises a jour automatiques
#
# Concu pour etre execute par le Task Scheduler Windows
# ============================================================================

param(
    [switch]$Force,
    [switch]$Verbose,
    [switch]$TestMode
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

    # Ecrire dans le fichier log
    $logFile = Join-Path $global:LogDir "unified_scheduler_$(Get-Date -Format 'yyyy-MM').log"
    Add-Content -Path $logFile -Value $logMessage -ErrorAction SilentlyContinue
}

# ============================================================================
# CONFIGURATION ET INITIALISATION
# ============================================================================

Write-Log "================================================================" "INFO"
Write-Log "UNIFIED GUARDIAN SCHEDULER - Phase 3" "INFO"
Write-Log "================================================================" "INFO"

# Determiner le repertoire racine du projet
$repoRoot = "C:\dev\emergenceV8"
if (-not (Test-Path $repoRoot)) {
    Write-Log "Erreur: Depot non trouve a $repoRoot" "ERROR"
    exit 1
}

Set-Location $repoRoot
Write-Log "Repertoire de travail: $repoRoot" "INFO"

# Definir les chemins
$global:PluginDir = Join-Path $repoRoot "claude-plugins\integrity-docs-guardian"
$global:LogDir = Join-Path $global:PluginDir "logs"
$global:ReportsDir = Join-Path $global:PluginDir "reports"
$global:AgentsDir = Join-Path $global:PluginDir "agents"

# Creer les repertoires s'ils n'existent pas
@($global:LogDir, $global:ReportsDir) | ForEach-Object {
    if (-not (Test-Path $_)) {
        New-Item -ItemType Directory -Path $_ -Force | Out-Null
        Write-Log "Repertoire cree: $_" "INFO"
    }
}

# ============================================================================
# VERIFICATION DES PREREQUIS
# ============================================================================

Write-Log "" "INFO"
Write-Log "Verification des prerequis..." "INFO"

# Verifier Python
$pythonExe = $null
if (Test-Path "$repoRoot\.venv\Scripts\python.exe") {
    $pythonExe = "$repoRoot\.venv\Scripts\python.exe"
    Write-Log "Python trouve dans venv: $pythonExe" "SUCCESS"
} else {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        $pythonExe = $pythonCmd.Source
        Write-Log "Python trouve: $pythonExe" "SUCCESS"
    } else {
        Write-Log "Python non trouve!" "ERROR"
        exit 1
    }
}

# Verifier les scripts des agents
$guardianScript = Join-Path $global:AgentsDir "guardian_agent.py"
$prodGuardianScript = Join-Path $global:AgentsDir "prodguardian_agent.py"
$autoSyncScript = Join-Path $global:PluginDir "scripts\auto_sync.py"

$scriptsOk = $true
foreach ($script in @($guardianScript, $prodGuardianScript, $autoSyncScript)) {
    if (Test-Path $script) {
        Write-Log "Script trouve: $(Split-Path $script -Leaf)" "SUCCESS"
    } else {
        Write-Log "Script manquant: $script" "WARNING"
        $scriptsOk = $false
    }
}

if (-not $scriptsOk -and -not $TestMode) {
    Write-Log "Certains scripts sont manquants. Utiliser -TestMode pour continuer quand meme." "WARNING"
}

# ============================================================================
# EXECUTION DU GUARDIAN D'INTEGRITE
# ============================================================================

Write-Log "" "INFO"
Write-Log "================================================================" "INFO"
Write-Log "ETAPE 1: Guardian d'Integrite - Verification des documents" "INFO"
Write-Log "================================================================" "INFO"

$guardianSuccess = $false
$guardianReport = $null

if (Test-Path $guardianScript) {
    try {
        Write-Log "Execution du guardian_agent.py..." "INFO"

        $guardianOutput = & $pythonExe $guardianScript --mode scheduled 2>&1
        $guardianExitCode = $LASTEXITCODE

        if ($Verbose) {
            Write-Log "Sortie du guardian:" "INFO"
            $guardianOutput | ForEach-Object { Write-Log $_ "INFO" }
        }

        if ($guardianExitCode -eq 0) {
            Write-Log "Guardian d'integrite execute avec succes" "SUCCESS"
            $guardianSuccess = $true

            # Trouver le rapport le plus recent
            $reports = Get-ChildItem -Path $global:ReportsDir -Filter "guardian_report_*.json" -ErrorAction SilentlyContinue |
                       Sort-Object LastWriteTime -Descending

            if ($reports.Count -gt 0) {
                $guardianReport = $reports[0].FullName
                Write-Log "Rapport genere: $(Split-Path $guardianReport -Leaf)" "SUCCESS"
            }
        } else {
            Write-Log "Erreur lors de l'execution du guardian (code: $guardianExitCode)" "ERROR"
        }
    } catch {
        Write-Log "Exception lors de l'execution du guardian: $($_.Exception.Message)" "ERROR"
    }
} else {
    Write-Log "Guardian script non trouve, etape ignoree" "WARNING"
}

# ============================================================================
# EXECUTION DU PRODGUARDIAN
# ============================================================================

Write-Log "" "INFO"
Write-Log "================================================================" "INFO"
Write-Log "ETAPE 2: ProdGuardian - Surveillance Production" "INFO"
Write-Log "================================================================" "INFO"

$prodGuardianSuccess = $false
$prodGuardianReport = $null

if (Test-Path $prodGuardianScript) {
    try {
        Write-Log "Execution du prodguardian_agent.py..." "INFO"

        $prodGuardianOutput = & $pythonExe $prodGuardianScript --mode scheduled 2>&1
        $prodGuardianExitCode = $LASTEXITCODE

        if ($Verbose) {
            Write-Log "Sortie du ProdGuardian:" "INFO"
            $prodGuardianOutput | ForEach-Object { Write-Log $_ "INFO" }
        }

        if ($prodGuardianExitCode -eq 0) {
            Write-Log "ProdGuardian execute avec succes" "SUCCESS"
            $prodGuardianSuccess = $true

            # Trouver le rapport le plus recent
            $reports = Get-ChildItem -Path $global:ReportsDir -Filter "prodguardian_report_*.json" -ErrorAction SilentlyContinue |
                       Sort-Object LastWriteTime -Descending

            if ($reports.Count -gt 0) {
                $prodGuardianReport = $reports[0].FullName
                Write-Log "Rapport genere: $(Split-Path $prodGuardianReport -Leaf)" "SUCCESS"
            }
        } else {
            Write-Log "Erreur lors de l'execution du ProdGuardian (code: $prodGuardianExitCode)" "ERROR"
        }
    } catch {
        Write-Log "Exception lors de l'execution du ProdGuardian: $($_.Exception.Message)" "ERROR"
    }
} else {
    Write-Log "ProdGuardian script non trouve, etape ignoree" "WARNING"
}

# ============================================================================
# GENERATION DU RAPPORT CONSOLIDE
# ============================================================================

Write-Log "" "INFO"
Write-Log "================================================================" "INFO"
Write-Log "ETAPE 3: Generation du rapport consolide" "INFO"
Write-Log "================================================================" "INFO"

$consolidatedReport = @{
    timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    execution_mode = if ($TestMode) { "test" } else { "scheduled" }
    results = @{
        guardian = @{
            executed = $guardianSuccess
            report_path = $guardianReport
            status = if ($guardianSuccess) { "success" } else { "failed" }
        }
        prodguardian = @{
            executed = $prodGuardianSuccess
            report_path = $prodGuardianReport
            status = if ($prodGuardianSuccess) { "success" } else { "failed" }
        }
    }
    summary = @{
        total_checks = 2
        successful_checks = @($guardianSuccess, $prodGuardianSuccess).Where({$_}).Count
        failed_checks = @($guardianSuccess, $prodGuardianSuccess).Where({-not $_}).Count
    }
}

# Sauvegarder le rapport consolide
$consolidatedReportPath = Join-Path $global:ReportsDir "consolidated_report_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
try {
    $consolidatedReport | ConvertTo-Json -Depth 10 | Out-File -FilePath $consolidatedReportPath -Encoding UTF8
    Write-Log "Rapport consolide sauvegarde: $(Split-Path $consolidatedReportPath -Leaf)" "SUCCESS"
} catch {
    Write-Log "Erreur lors de la sauvegarde du rapport consolide: $($_.Exception.Message)" "ERROR"
}

# ============================================================================
# AUTOSYNC - MISE A JOUR AUTOMATIQUE DE LA DOCUMENTATION
# ============================================================================

Write-Log "" "INFO"
Write-Log "================================================================" "INFO"
Write-Log "ETAPE 4: AutoSync - Detection et mise a jour automatique" "INFO"
Write-Log "================================================================" "INFO"

$autoSyncSuccess = $false

# Verifier si AUTO_APPLY est active
$autoApplyEnabled = $env:AUTO_APPLY -eq "1"
Write-Log "AUTO_APPLY: $(if ($autoApplyEnabled) { 'ACTIVE' } else { 'DESACTIVE' })" "INFO"

if (Test-Path $autoSyncScript) {
    try {
        Write-Log "Execution du auto_sync.py..." "INFO"

        # Passer les rapports en argument si disponibles
        $autoSyncArgs = @("--source", "scheduled")
        if ($guardianReport -and (Test-Path $guardianReport)) {
            $autoSyncArgs += @("--guardian-report", $guardianReport)
        }
        if ($prodGuardianReport -and (Test-Path $prodGuardianReport)) {
            $autoSyncArgs += @("--prodguardian-report", $prodGuardianReport)
        }

        $autoSyncOutput = & $pythonExe $autoSyncScript @autoSyncArgs 2>&1
        $autoSyncExitCode = $LASTEXITCODE

        if ($Verbose) {
            Write-Log "Sortie du AutoSync:" "INFO"
            $autoSyncOutput | ForEach-Object { Write-Log $_ "INFO" }
        }

        if ($autoSyncExitCode -eq 0) {
            Write-Log "AutoSync execute avec succes" "SUCCESS"
            $autoSyncSuccess = $true
        } else {
            Write-Log "Erreur lors de l'execution du AutoSync (code: $autoSyncExitCode)" "ERROR"
        }
    } catch {
        Write-Log "Exception lors de l'execution du AutoSync: $($_.Exception.Message)" "ERROR"
    }
} else {
    Write-Log "AutoSync script non trouve, etape ignoree" "WARNING"
}

# ============================================================================
# NETTOYAGE DES ANCIENS RAPPORTS
# ============================================================================

Write-Log "" "INFO"
Write-Log "Nettoyage des anciens rapports (> 30 jours)..." "INFO"

try {
    $cutoffDate = (Get-Date).AddDays(-30)
    $oldReports = Get-ChildItem -Path $global:ReportsDir -Filter "*.json" |
                  Where-Object { $_.LastWriteTime -lt $cutoffDate }

    if ($oldReports.Count -gt 0) {
        $oldReports | ForEach-Object {
            Remove-Item $_.FullName -Force
            Write-Log "Rapport supprime: $($_.Name)" "INFO"
        }
        Write-Log "$($oldReports.Count) ancien(s) rapport(s) supprime(s)" "SUCCESS"
    } else {
        Write-Log "Aucun ancien rapport a supprimer" "INFO"
    }
} catch {
    Write-Log "Erreur lors du nettoyage: $($_.Exception.Message)" "WARNING"
}

# ============================================================================
# RESUME FINAL
# ============================================================================

Write-Log "" "INFO"
Write-Log "================================================================" "INFO"
Write-Log "EXECUTION TERMINEE" "INFO"
Write-Log "================================================================" "INFO"

Write-Log "" "INFO"
Write-Log "Resume de l'execution:" "INFO"
Write-Log "  Guardian d'integrite: $(if ($guardianSuccess) { 'SUCCESS' } else { 'FAILED' })" "INFO"
Write-Log "  ProdGuardian: $(if ($prodGuardianSuccess) { 'SUCCESS' } else { 'FAILED' })" "INFO"
Write-Log "  AutoSync: $(if ($autoSyncSuccess) { 'SUCCESS' } else { 'FAILED' })" "INFO"
Write-Log "" "INFO"

$totalSuccess = @($guardianSuccess, $prodGuardianSuccess, $autoSyncSuccess).Where({$_}).Count
$totalSteps = 3

Write-Log "Taux de reussite: $totalSuccess/$totalSteps etapes reussies" "INFO"
Write-Log "Rapport consolide: $consolidatedReportPath" "INFO"
Write-Log "" "INFO"

# Code de sortie base sur le succes global
$exitCode = if ($totalSuccess -eq $totalSteps) { 0 } else { 1 }

Write-Log "================================================================" "INFO"
Write-Log "Fin de l'execution (code: $exitCode)" "INFO"
Write-Log "================================================================" "INFO"

exit $exitCode
