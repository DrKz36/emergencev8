<#
.SYNOPSIS
    Synchronise automatiquement la version dans tous les fichiers du projet ÉMERGENCE V8

.DESCRIPTION
    Ce script lit la version depuis src/version.js (source unique de vérité)
    et met à jour tous les fichiers qui doivent refléter cette version:
    - package.json
    - index.html
    - src/backend/features/monitoring/router.py (2 endroits)

.PARAMETER DryRun
    Mode simulation - affiche les modifications sans les appliquer

.EXAMPLE
    .\scripts\sync_version.ps1
    Synchronise toutes les versions

.EXAMPLE
    .\scripts\sync_version.ps1 -DryRun
    Affiche ce qui serait modifié sans appliquer les changements

.NOTES
    Auteur: ÉMERGENCE Guardian System
    Version: 1.0.0
    Date: 2025-10-17
#>

param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# Couleurs pour la sortie console
function Write-Success { param($Message) Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "[INFO] $Message" -ForegroundColor Cyan }
function Write-Warn { param($Message) Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Write-Err { param($Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }

Write-Info "EMERGENCE V8 - Synchronisation de version"
Write-Info "============================================"

# Chemins des fichiers
$rootDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path "$rootDir\src\version.js")) {
    $rootDir = Get-Location
}

$versionFile = Join-Path $rootDir "src\version.js"
$packageJson = Join-Path $rootDir "package.json"
$indexHtml = Join-Path $rootDir "index.html"
$monitoringRouter = Join-Path $rootDir "src\backend\features\monitoring\router.py"

# Vérification des fichiers
$files = @($versionFile, $packageJson, $indexHtml, $monitoringRouter)
foreach ($file in $files) {
    if (-not (Test-Path $file)) {
        Write-Err "Fichier introuvable: $file"
        exit 1
    }
}

Write-Success "Tous les fichiers requis sont présents"

# Extraction de la version depuis src/version.js
Write-Info "Lecture de la version source depuis src/version.js..."
$versionContent = Get-Content $versionFile -Raw

$sourceVersion = $null
$sourceName = $null
$sourceDate = $null

if ($versionContent -match "(?s)export const CURRENT_RELEASE\s*=\s*\{\s*version:\s*'([^']+)',\s*name:\s*'([^']+)',\s*date:\s*'([^']+)'\s*,?\s*\}") {
    $sourceVersion = $Matches[1]
    $sourceName = $Matches[2]
    $sourceDate = $Matches[3]
    Write-Success "Version source detectee: $sourceVersion"
    if ($sourceName) { Write-Info "  Libellé : $sourceName" }
    if ($sourceDate) { Write-Info "  Date    : $sourceDate" }
} elseif ($versionContent -match "export const VERSION = '([^']+)'") {
    $sourceVersion = $Matches[1]
    Write-Success "Version source detectee: $sourceVersion"
} else {
    Write-Err "Impossible d'extraire la version depuis src/version.js"
    exit 1
}

# Fonction pour mettre à jour un fichier avec remplacement
function Update-FileVersion {
    param(
        [string]$FilePath,
        [string]$Pattern,
        [string]$Replacement,
        [string]$Description
    )

    $content = Get-Content $FilePath -Raw
    $originalContent = $content

    if ($content -match $Pattern) {
        $oldVersion = $Matches[1]
        if ($oldVersion -eq $sourceVersion) {
            Write-Info "  $Description - deja a jour ($oldVersion)"
            return $false
        }

        Write-Warn "  -> $Description - mise a jour: $oldVersion -> $sourceVersion"

        if (-not $DryRun) {
            $content = $content -replace $Pattern, $Replacement
            Set-Content -Path $FilePath -Value $content -NoNewline -Encoding UTF8
            Write-Success "  $Description - mis a jour"
        } else {
            Write-Info "  [DRY-RUN] Modification simulee"
        }
        return $true
    } else {
        Write-Warn "  $Description - pattern non trouve dans le fichier"
        return $false
    }
}

# Compteur de modifications
$changesCount = 0
$modifiedFiles = @()

# 1. Mise à jour de package.json
Write-Info "`nMise à jour de package.json..."
$pattern = '"version":\s*"([^"]+)"'
$replacement = """version"": ""$sourceVersion"""
if (Update-FileVersion -FilePath $packageJson -Pattern $pattern -Replacement $replacement -Description "package.json") {
    $changesCount++
    $modifiedFiles += "package.json"
}

# 2. Mise à jour de index.html (app-version span)
Write-Info "`nMise à jour de index.html..."
$pattern = '<span class="app-version"[^>]*>([^<]+)</span>'
$replacement = '<span class="app-version" id="app-version-display" style="font-size: 0.65em; font-weight: 400; opacity: 0.6; letter-spacing: 0.05em;">' + $sourceVersion + '</span>'
if (Update-FileVersion -FilePath $indexHtml -Pattern $pattern -Replacement $replacement -Description "index.html") {
    $changesCount++
    $modifiedFiles += "index.html"
}

# 3. Mise à jour de monitoring/router.py - healthcheck endpoint (ligne 38)
Write-Info "`nMise à jour de monitoring/router.py (healthcheck)..."
$pattern = '"version":\s*"([^"]+)",\s*#\s*Synchronisé avec package\.json'
$replacement = """version"": ""$sourceVersion"",  # Synchronisé avec package.json"
if (Update-FileVersion -FilePath $monitoringRouter -Pattern $pattern -Replacement $replacement -Description "router.py (healthcheck)") {
    $changesCount++
    $modifiedFiles += "src/backend/features/monitoring/router.py (healthcheck)"
}

# 4. Mise à jour de monitoring/router.py - system/info endpoint (ligne 384)
Write-Info "`nMise à jour de monitoring/router.py (system/info)..."
$pattern = 'backend_version = os\.getenv\("BACKEND_VERSION",\s*"([^"]+)"\)'
$replacement = 'backend_version = os.getenv("BACKEND_VERSION", "' + $sourceVersion + '")'
if (Update-FileVersion -FilePath $monitoringRouter -Pattern $pattern -Replacement $replacement -Description "router.py (system/info)") {
    $changesCount++
    $modifiedFiles += "src/backend/features/monitoring/router.py (system/info)"
}

# Résumé
Write-Info "`n============================================"
if ($DryRun) {
    Write-Warn "MODE DRY-RUN: Aucune modification appliquee"
    Write-Info "$changesCount fichier(s) seraient modifies"
    if ($modifiedFiles.Count -gt 0) {
        Write-Info "`nFichiers impactés :"
        foreach ($file in ($modifiedFiles | Sort-Object -Unique)) {
            Write-Info "  • $file"
        }
    }
} else {
    if ($changesCount -eq 0) {
        Write-Success "Toutes les versions sont deja synchronisees sur $sourceVersion"
    } else {
        Write-Success "$changesCount fichier(s) mis a jour avec succes vers $sourceVersion"
        if ($modifiedFiles.Count -gt 0) {
            Write-Info "`nFichiers modifiés :"
            foreach ($file in ($modifiedFiles | Sort-Object -Unique)) {
                Write-Info "  • $file"
            }
        }
    }
}

Write-Info "`nSynchronisation terminee!"
exit 0
