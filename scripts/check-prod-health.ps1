#!/usr/bin/env pwsh
# check-prod-health.ps1 - Production Health Check avec JWT Auth
# Usage: pwsh -File scripts/check-prod-health.ps1 [-Verbose]

param(
    [switch]$Verbose,
    [string]$OutputPath = "reports/prod-health-report.md"
)

$ErrorActionPreference = "Stop"

# ============================================================================
# CONFIGURATION
# ============================================================================

$PROD_URL = "https://emergence-app-486095406755.europe-west1.run.app"
$SERVICE_NAME = "emergence-app"
$REGION = "europe-west1"
$PROJECT_ID = "emergence-469005"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")

    $colors = @{
        "Green" = "`e[32m"
        "Yellow" = "`e[33m"
        "Red" = "`e[31m"
        "Blue" = "`e[34m"
        "White" = "`e[37m"
        "Reset" = "`e[0m"
    }

    Write-Host "$($colors[$Color])$Message$($colors['Reset'])"
}

function Get-JWTFromEnv {
    Write-ColorOutput "🔑 Génération JWT depuis .env..." "Blue"

    # Lire .env pour JWT_SECRET
    $envFile = ".env"
    if (-not (Test-Path $envFile)) {
        Write-ColorOutput "⚠️  Fichier .env introuvable. Cherche AUTH_JWT_SECRET..." "Yellow"
        $envFile = $null
    }

    $jwtSecret = $null
    if ($envFile) {
        $envContent = Get-Content $envFile -ErrorAction SilentlyContinue
        foreach ($line in $envContent) {
            if ($line -match '^(JWT_SECRET|AUTH_JWT_SECRET)=(.+)$') {
                $jwtSecret = $Matches[2].Trim('"').Trim("'")
                break
            }
        }
    }

    # Fallback: variable d'environnement
    if (-not $jwtSecret) {
        $jwtSecret = $env:JWT_SECRET
        if (-not $jwtSecret) {
            $jwtSecret = $env:AUTH_JWT_SECRET
        }
    }

    if (-not $jwtSecret) {
        Write-ColorOutput "❌ JWT_SECRET introuvable dans .env ou variables d'environnement" "Red"
        Write-ColorOutput "   Crée un fichier .env avec: JWT_SECRET=<ton_secret>" "Yellow"
        exit 1
    }

    if ($Verbose) {
        Write-ColorOutput "   Secret trouvé (${($jwtSecret.Length)} caractères)" "Green"
    }

    # Générer JWT avec Python (plus simple que PowerShell pur)
    $pythonScript = @"
import jwt
import sys
from datetime import datetime, timedelta, timezone

secret = sys.argv[1]
issuer = "emergence.local"
audience = "emergence-app"
user_id = "admin-healthcheck"

now = datetime.now(timezone.utc)
expires = now + timedelta(minutes=60)

payload = {
    "iss": issuer,
    "aud": audience,
    "sub": user_id,
    "email": "admin@emergence.local",
    "role": "admin",
    "sid": "healthcheck-session",
    "iat": int(now.timestamp()),
    "exp": int(expires.timestamp())
}

token = jwt.encode(payload, secret, algorithm="HS256")
print(token)
"@

    # Détecter OS et choisir commande Python appropriée
    # Windows: python (standard) ou python3 (WindowsApps)
    # Linux/Mac: python3 (standard)
    $pythonCmd = if ($IsWindows) {
        # Windows: Essayer python d'abord (plus fiable pour PyJWT)
        if (Get-Command python -ErrorAction SilentlyContinue) {
            "python"
        }
        elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
            "python3"
        }
        else {
            $null
        }
    }
    else {
        # Linux/Mac: python3 standard
        if (Get-Command python3 -ErrorAction SilentlyContinue) {
            "python3"
        }
        elseif (Get-Command python -ErrorAction SilentlyContinue) {
            "python"
        }
        else {
            $null
        }
    }

    if (-not $pythonCmd) {
        Write-ColorOutput "❌ Python non trouvé. Installe Python 3.8+" "Red"
        exit 1
    }

    if ($Verbose) {
        Write-ColorOutput "   Utilise: $pythonCmd" "Green"
    }

    try {
        $token = & $pythonCmd -c $pythonScript $jwtSecret 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-ColorOutput "❌ Erreur génération JWT: $token" "Red"

            # Message d'aide contextuel selon OS
            if ($IsWindows) {
                Write-ColorOutput "   Installe PyJWT: python -m pip install pyjwt" "Yellow"
                Write-ColorOutput "   Ou: py -m pip install pyjwt" "Yellow"
            }
            else {
                Write-ColorOutput "   Installe PyJWT: pip3 install pyjwt" "Yellow"
                Write-ColorOutput "   Ou: python3 -m pip install pyjwt" "Yellow"
            }
    try {
        $token = python3 -c $pythonScript $jwtSecret 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-ColorOutput "❌ Erreur génération JWT: $token" "Red"
            Write-ColorOutput "   Installe PyJWT: pip install pyjwt" "Yellow"
            exit 1
        }

        if ($Verbose) {
            Write-ColorOutput "   ✅ JWT généré avec succès" "Green"
        }

        return $token.Trim()
    }
    catch {
        Write-ColorOutput "❌ Erreur Python: $_" "Red"
        exit 1
    }
}

function Test-Endpoint {
    param(
        [string]$Url,
        [string]$Token,
        [string]$Name
    )

    try {
        $headers = @{
            "Authorization" = "Bearer $Token"
            "Accept" = "application/json"
        }

        $response = Invoke-WebRequest -Uri $Url -Headers $headers -Method Get -TimeoutSec 10

        $result = @{
            "Success" = $true
            "StatusCode" = $response.StatusCode
            "Body" = $response.Content | ConvertFrom-Json
        }

        return $result
    }
    catch {
        $statusCode = if ($_.Exception.Response) { $_.Exception.Response.StatusCode.value__ } else { 0 }

        $result = @{
            "Success" = $false
            "StatusCode" = $statusCode
            "Error" = $_.Exception.Message
        }

        return $result
    }
}

function Get-CloudRunMetrics {
    Write-ColorOutput "📊 Récupération métriques Cloud Run..." "Blue"

    try {
        $serviceInfo = gcloud run services describe $SERVICE_NAME --region=$REGION --format=json 2>&1 | ConvertFrom-Json

        if ($LASTEXITCODE -eq 0) {
            return @{
                "Success" = $true
                "Data" = $serviceInfo
            }
        }
        else {
            return @{
                "Success" = $false
                "Error" = "gcloud CLI non configuré ou service introuvable"
            }
        }
    }
    catch {
        return @{
            "Success" = $false
            "Error" = $_.Exception.Message
        }
    }
}

function Get-CloudRunLogs {
    param([int]$Limit = 20)

    Write-ColorOutput "📜 Récupération logs récents..." "Blue"

    try {
        $logs = gcloud run services logs read $SERVICE_NAME --region=$REGION --limit=$Limit --format=json 2>&1

        if ($LASTEXITCODE -eq 0) {
            return @{
                "Success" = $true
                "Logs" = ($logs | ConvertFrom-Json)
            }
        }
        else {
            return @{
                "Success" = $false
                "Error" = "gcloud CLI non configuré"
            }
        }
    }
    catch {
        return @{
            "Success" = $false
            "Error" = $_.Exception.Message
        }
    }
}

# ============================================================================
# MAIN SCRIPT
# ============================================================================

Write-ColorOutput "🏥 Production Health Check - $SERVICE_NAME" "Blue"
Write-ColorOutput "=" * 60 "Blue"

$startTime = Get-Date

# 1. Générer JWT
$jwt = Get-JWTFromEnv

# 2. Healthchecks
Write-ColorOutput "`n🔍 Healthchecks avec authentification..." "Blue"

$healthResults = @()

# /ready endpoint
Write-ColorOutput "   Testing /ready..." "Blue"
$readyResult = Test-Endpoint -Url "$PROD_URL/ready" -Token $jwt -Name "/ready"
$healthResults += @{
    "Endpoint" = "/ready"
    "Result" = $readyResult
}

if ($readyResult.Success) {
    Write-ColorOutput "   ✅ /ready: OK (${($readyResult.StatusCode)})" "Green"
}
else {
    Write-ColorOutput "   ❌ /ready: FAIL (${($readyResult.StatusCode)}) - $($readyResult.Error)" "Red"
}

# /api/monitoring/health endpoint (optionnel, peut nécessiter auth différente)
Write-ColorOutput "   Testing /api/monitoring/health..." "Blue"
$healthResult = Test-Endpoint -Url "$PROD_URL/api/monitoring/health" -Token $jwt -Name "/api/monitoring/health"
$healthResults += @{
    "Endpoint" = "/api/monitoring/health"
    "Result" = $healthResult
}

if ($healthResult.Success) {
    Write-ColorOutput "   ✅ /api/monitoring/health: OK" "Green"
}
else {
    Write-ColorOutput "   ⚠️  /api/monitoring/health: FAIL (${($healthResult.StatusCode)})" "Yellow"
}

# 3. Métriques Cloud Run (optionnel)
$metricsData = $null
if (Get-Command gcloud -ErrorAction SilentlyContinue) {
    $metricsResult = Get-CloudRunMetrics
    if ($metricsResult.Success) {
        $metricsData = $metricsResult.Data
        Write-ColorOutput "   ✅ Métriques Cloud Run récupérées" "Green"
    }
    else {
        Write-ColorOutput "   ⚠️  Métriques Cloud Run: $($metricsResult.Error)" "Yellow"
    }
}
else {
    Write-ColorOutput "   ⚠️  gcloud CLI non disponible, skip métriques" "Yellow"
}

# 4. Logs récents (optionnel)
$logsData = $null
if (Get-Command gcloud -ErrorAction SilentlyContinue) {
    $logsResult = Get-CloudRunLogs -Limit 20
    if ($logsResult.Success) {
        $logsData = $logsResult.Logs
        Write-ColorOutput "   ✅ Logs récents récupérés" "Green"
    }
    else {
        Write-ColorOutput "   ⚠️  Logs: $($logsResult.Error)" "Yellow"
    }
}

# ============================================================================
# GÉNÉRATION RAPPORT MARKDOWN
# ============================================================================

$endTime = Get-Date
$duration = ($endTime - $startTime).TotalSeconds

Write-ColorOutput "`n📝 Génération rapport markdown..." "Blue"

# Créer répertoire reports si nécessaire
$reportsDir = Split-Path $OutputPath -Parent
if (-not (Test-Path $reportsDir)) {
    New-Item -ItemType Directory -Path $reportsDir -Force | Out-Null
}

# Construire le rapport
$report = @"
# Production Health Report - $SERVICE_NAME

**Date:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss") UTC
**URL:** $PROD_URL
**Region:** $REGION
**Duration:** $([math]::Round($duration, 2))s

---

## 🔍 Healthchecks

"@

foreach ($check in $healthResults) {
    $endpoint = $check.Endpoint
    $result = $check.Result

    if ($result.Success) {
        $report += "### ✅ $endpoint`n`n"
        $report += "**Status:** $($result.StatusCode) OK`n`n"

        if ($result.Body) {
            $jsonBody = $result.Body | ConvertTo-Json -Depth 5 -Compress
            $report += "**Response:**`n``````json`n$jsonBody`n```````n`n"
        }
    }
    else {
        $report += "### ❌ $endpoint`n`n"
        $report += "**Status:** $($result.StatusCode) FAIL`n`n"
        $report += "**Error:** $($result.Error)`n`n"
    }
}

# Métriques Cloud Run
if ($metricsData) {
    $report += "---`n`n## 📊 Métriques Cloud Run`n`n"

    # Extraire infos pertinentes
    if ($metricsData.status) {
        $conditions = $metricsData.status.conditions
        if ($conditions) {
            $report += "**Conditions:**`n"
            foreach ($condition in $conditions) {
                $status = if ($condition.status -eq "True") { "✅" } else { "❌" }
                $report += "- $status $($condition.type): $($condition.status)`n"
            }
            $report += "`n"
        }
    }

    if ($metricsData.spec.template.spec.containers) {
        $container = $metricsData.spec.template.spec.containers[0]
        $report += "**Container:**`n"
        $report += "- Image: $($container.image)`n"
        $report += "- Resources: CPU $($container.resources.limits.cpu), Memory $($container.resources.limits.memory)`n`n"
    }
}

# Logs récents
if ($logsData -and $logsData.Count -gt 0) {
    $report += "---`n`n## 📜 Logs Récents (20 derniers)`n`n"
    $report += "``````log`n"

    foreach ($logEntry in $logsData | Select-Object -First 20) {
        $timestamp = if ($logEntry.timestamp) { $logEntry.timestamp } else { "" }
        $severity = if ($logEntry.severity) { $logEntry.severity } else { "INFO" }
        $message = if ($logEntry.textPayload) { $logEntry.textPayload } else { $logEntry.jsonPayload | ConvertTo-Json -Compress }

        $report += "[$timestamp] $severity - $message`n"
    }

    $report += "```````n`n"
}

# Verdict final
$report += "---`n`n## 🎯 Verdict`n`n"

$criticalEndpoints = $healthResults | Where-Object { $_.Endpoint -eq "/ready" }
$allCriticalOK = ($criticalEndpoints | Where-Object { $_.Result.Success }).Count -eq $criticalEndpoints.Count

if ($allCriticalOK) {
    $report += "### ✅ PRODUCTION HEALTHY`n`n"
    $report += "Tous les healthchecks critiques passent. La production est opérationnelle.`n"
    $exitCode = 0
}
else {
    $report += "### ❌ PRODUCTION DEGRADED`n`n"
    $report += "⚠️  Certains healthchecks critiques échouent. Vérifier les logs et métriques.`n"
    $exitCode = 1
}

# Sauvegarder rapport
$report | Out-File -FilePath $OutputPath -Encoding UTF8

Write-ColorOutput "   ✅ Rapport sauvegardé: $OutputPath" "Green"

# Afficher verdict
Write-ColorOutput "`n$("=" * 60)" "Blue"
if ($exitCode -eq 0) {
    Write-ColorOutput "✅ PRODUCTION HEALTHY" "Green"
}
else {
    Write-ColorOutput "❌ PRODUCTION DEGRADED" "Red"
}
Write-ColorOutput "$("=" * 60)" "Blue"

exit $exitCode
