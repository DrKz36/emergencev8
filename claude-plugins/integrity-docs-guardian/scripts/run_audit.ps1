# ============================================================================
# GUARDIAN AUDIT - Audit global manuel complet
# ============================================================================
# Lance tous les agents Guardian en séquence pour audit approfondi
# Usage: .\run_audit.ps1 [-EmailReport] [-EmailTo "admin@example.com"]
# ============================================================================

param(
    [switch]$EmailReport,
    [string]$EmailTo = ""
)

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "🔍 GUARDIAN AUDIT GLOBAL - ÉMERGENCE V8" -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

$repoRoot = "C:\dev\emergenceV8"
$scriptsDir = "$repoRoot\claude-plugins\integrity-docs-guardian\scripts"
$reportsDir = "$repoRoot\claude-plugins\integrity-docs-guardian\reports"

# Timestamp de début
$startTime = Get-Date
Write-Host "🕐 Démarrage: $($startTime.ToString('yyyy-MM-dd HH:mm:ss'))`n" -ForegroundColor Gray

# Résultats
$results = @{
    agents = @()
    global_status = "OK"
    critical_count = 0
    warning_count = 0
}

# ============================================================================
# FONCTION D'EXÉCUTION D'AGENT
# ============================================================================
function Run-Agent {
    param(
        [string]$Name,
        [string]$ScriptName,
        [string]$Emoji
    )

    Write-Host "[$($results.agents.Count + 1)/6] $Emoji $Name..." -ForegroundColor Yellow

    $agentStart = Get-Date
    $scriptPath = "$scriptsDir\$ScriptName"

    if (-not (Test-Path $scriptPath)) {
        Write-Host "   ❌ Script introuvable: $scriptPath`n" -ForegroundColor Red
        $results.agents += @{
            name = $Name
            status = "ERROR"
            error = "Script not found"
            duration = 0
        }
        $results.global_status = "ERROR"
        return $false
    }

    try {
        $output = & python $scriptPath 2>&1
        $exitCode = $LASTEXITCODE
        $duration = ((Get-Date) - $agentStart).TotalSeconds

        if ($exitCode -eq 0) {
            Write-Host "   ✅ Terminé avec succès ($([math]::Round($duration, 1))s)`n" -ForegroundColor Green
            $results.agents += @{
                name = $Name
                status = "OK"
                duration = $duration
            }
            return $true
        } else {
            Write-Host "   ⚠️  Terminé avec des avertissements ($([math]::Round($duration, 1))s)`n" -ForegroundColor Yellow
            $results.agents += @{
                name = $Name
                status = "WARNING"
                duration = $duration
            }
            $results.warning_count++
            if ($results.global_status -eq "OK") {
                $results.global_status = "WARNING"
            }
            return $false
        }
    } catch {
        Write-Host "   ❌ Erreur: $_`n" -ForegroundColor Red
        $results.agents += @{
            name = $Name
            status = "ERROR"
            error = $_.Exception.Message
            duration = ((Get-Date) - $agentStart).TotalSeconds
        }
        $results.global_status = "ERROR"
        $results.critical_count++
        return $false
    }
}

# ============================================================================
# EXÉCUTION SÉQUENTIELLE DES AGENTS
# ============================================================================

Write-Host "🚀 Exécution des agents Guardian...`n" -ForegroundColor White

# 1. Anima (DocKeeper) - Vérification documentation
Run-Agent -Name "Anima (DocKeeper)" -ScriptName "scan_docs.py" -Emoji "📚"

# 2. Neo (IntegrityWatcher) - Vérification intégrité backend/frontend
Run-Agent -Name "Neo (IntegrityWatcher)" -ScriptName "check_integrity.py" -Emoji "🔍"

# 3. ProdGuardian - Logs production Cloud Run
Run-Agent -Name "ProdGuardian" -ScriptName "check_prod_logs.py" -Emoji "☁️"

# 4. Argus (optionnel) - Logs dev locaux
if (Test-Path "$scriptsDir\argus_analyzer.py") {
    Run-Agent -Name "Argus (DevLogs)" -ScriptName "argus_analyzer.py" -Emoji "👁️"
}

# 5. Nexus (Coordinator) - Génération rapport unifié
Run-Agent -Name "Nexus (Coordinator)" -ScriptName "generate_report.py" -Emoji "📊"

# 6. Master Orchestrator - Rapport global
Run-Agent -Name "Master Orchestrator" -ScriptName "master_orchestrator.py" -Emoji "🤖"

# ============================================================================
# ANALYSE DES RAPPORTS
# ============================================================================

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "📊 ANALYSE DES RAPPORTS" -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# Lire le rapport unifié
$unifiedReportPath = "$reportsDir\unified_report.json"
if (Test-Path $unifiedReportPath) {
    try {
        $unifiedReport = Get-Content $unifiedReportPath -Raw | ConvertFrom-Json

        Write-Host "📄 Rapport Unifié (Nexus):" -ForegroundColor White
        if ($unifiedReport.executive_summary) {
            $summary = $unifiedReport.executive_summary
            Write-Host "   Status: $($summary.status)" -ForegroundColor $(
                switch ($summary.status) {
                    "ok" { "Green" }
                    "warning" { "Yellow" }
                    "critical" { "Red" }
                    default { "Gray" }
                }
            )
            Write-Host "   Issues totaux: $($summary.total_issues)" -ForegroundColor Gray
            Write-Host "   Critiques: $($summary.critical)" -ForegroundColor $(if ($summary.critical -gt 0) { "Red" } else { "Green" })
            Write-Host "   Warnings: $($summary.warnings)" -ForegroundColor $(if ($summary.warnings -gt 0) { "Yellow" } else { "Green" })
        }
        Write-Host ""
    } catch {
        Write-Host "   ⚠️  Impossible de parser le rapport unifié`n" -ForegroundColor Yellow
    }
}

# Lire le rapport de production
$prodReportPath = "$reportsDir\prod_report.json"
if (Test-Path $prodReportPath) {
    try {
        $prodReport = Get-Content $prodReportPath -Raw | ConvertFrom-Json

        Write-Host "☁️  Production Cloud Run:" -ForegroundColor White
        if ($prodReport.summary) {
            $prodSummary = $prodReport.summary
            Write-Host "   Status: $($prodSummary.status)" -ForegroundColor $(
                switch ($prodSummary.status) {
                    "HEALTHY" { "Green" }
                    "WARNING" { "Yellow" }
                    "CRITICAL" { "Red" }
                    default { "Gray" }
                }
            )
            Write-Host "   Erreurs (1h): $($prodSummary.error_count_1h)" -ForegroundColor $(if ($prodSummary.error_count_1h -gt 0) { "Yellow" } else { "Green" })
            Write-Host "   Dernière vérif: $($prodSummary.last_check)" -ForegroundColor Gray
        }
        Write-Host ""
    } catch {
        Write-Host "   ⚠️  Impossible de parser le rapport prod`n" -ForegroundColor Yellow
    }
}

# ============================================================================
# RÉSUMÉ EXÉCUTION
# ============================================================================

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "📋 RÉSUMÉ DE L'AUDIT" -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

$duration = ((Get-Date) - $startTime).TotalSeconds
$successCount = ($results.agents | Where-Object { $_.status -eq "OK" }).Count
$totalCount = $results.agents.Count

Write-Host "⏱️  Durée totale: $([math]::Round($duration, 1))s" -ForegroundColor Gray
Write-Host "🎯 Agents exécutés: $totalCount" -ForegroundColor White
Write-Host "   ✅ Succès: $successCount" -ForegroundColor Green
Write-Host "   ⚠️  Warnings: $($results.warning_count)" -ForegroundColor $(if ($results.warning_count -gt 0) { "Yellow" } else { "Green" })
Write-Host "   ❌ Erreurs: $($results.critical_count)" -ForegroundColor $(if ($results.critical_count -gt 0) { "Red" } else { "Green" })
Write-Host ""

Write-Host "📊 Status global: $($results.global_status)" -ForegroundColor $(
    switch ($results.global_status) {
        "OK" { "Green" }
        "WARNING" { "Yellow" }
        "ERROR" { "Red" }
        default { "Gray" }
    }
)
Write-Host ""

# ============================================================================
# RAPPORTS GÉNÉRÉS
# ============================================================================

Write-Host "📁 Rapports disponibles:" -ForegroundColor White
Get-ChildItem "$reportsDir\*.json" | Sort-Object LastWriteTime -Descending | Select-Object -First 10 | ForEach-Object {
    $age = ((Get-Date) - $_.LastWriteTime).TotalMinutes
    $ageStr = if ($age -lt 60) {
        "$([math]::Round($age, 0))min"
    } else {
        "$([math]::Round($age / 60, 1))h"
    }
    Write-Host "   • $($_.Name) (modifié il y a $ageStr)" -ForegroundColor Gray
}
Write-Host ""

# ============================================================================
# EMAIL REPORT (optionnel)
# ============================================================================

if ($EmailReport -or $EmailTo) {
    Write-Host "📧 Envoi du rapport par email..." -ForegroundColor Yellow

    $emailScript = "$scriptsDir\send_guardian_reports_email.py"
    if (Test-Path $emailScript) {
        try {
            $emailArgs = @($emailScript)
            if ($EmailTo) {
                $emailArgs += "--to"
                $emailArgs += $EmailTo
            }

            & python @emailArgs 2>&1 | Out-Null

            if ($LASTEXITCODE -eq 0) {
                Write-Host "   ✅ Email envoyé avec succès" -ForegroundColor Green
                if ($EmailTo) {
                    Write-Host "      Destinataire: $EmailTo" -ForegroundColor Gray
                }
            } else {
                Write-Host "   ⚠️  Erreur lors de l'envoi de l'email" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "   ⚠️  Email non configuré ou erreur: $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host "   ⚠️  Script email introuvable" -ForegroundColor Yellow
    }
    Write-Host ""
}

# ============================================================================
# ACTIONS RECOMMANDÉES
# ============================================================================

if ($results.global_status -ne "OK") {
    Write-Host "⚡ Actions recommandées:" -ForegroundColor Yellow

    if ($results.critical_count -gt 0) {
        Write-Host "   🔴 Des erreurs critiques ont été détectées" -ForegroundColor Red
        Write-Host "      → Consultez les rapports dans: $reportsDir" -ForegroundColor Gray
    }

    if ($results.warning_count -gt 0) {
        Write-Host "   🟡 Des avertissements ont été détectés" -ForegroundColor Yellow
        Write-Host "      → Revue recommandée des rapports" -ForegroundColor Gray
    }

    Write-Host ""
}

# ============================================================================
# CODE DE SORTIE
# ============================================================================

Write-Host "================================================================`n" -ForegroundColor Cyan

switch ($results.global_status) {
    "OK" {
        Write-Host "✅ Audit terminé: Tout est OK`n" -ForegroundColor Green
        exit 0
    }
    "WARNING" {
        Write-Host "⚠️  Audit terminé: Warnings détectés`n" -ForegroundColor Yellow
        exit 0
    }
    "ERROR" {
        Write-Host "❌ Audit terminé: Erreurs critiques`n" -ForegroundColor Red
        exit 1
    }
}
