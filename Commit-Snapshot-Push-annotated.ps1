# === EMERGENCE — Commit+Snapshot+Push (annotated) ============================
# Usage: powershell -ExecutionPolicy Bypass -File .\Commit-Snapshot-Push-annotated.ps1
# Effects: ARBO-LOCK snapshot, BUILDSTAMP, commit annotated with Cloud Run info, push.
# ============================================================================

$ErrorActionPreference = "Stop"

# --- Instance params ---------------------------------------------------------
$VERSION   = "7.5.3"
$IMG_TAG   = "authws-v753-20250914092003"
$SNAP_NAME = "arborescence_synchronisee_20250914.txt"  # ASCII name
$BRANCH    = "main"

# --- GCP params --------------------------------------------------------------
$PROJECT = if ($env:GCP_PROJECT) { $env:GCP_PROJECT } else { "emergence-469005" }
$REGION  = if ($env:GCP_REGION ) { $env:GCP_REGION  } else { "europe-west1" }
$SERVICE = if ($env:GCP_RUN_SERVICE) { $env:GCP_RUN_SERVICE } else { "emergence-app" }

# --- Tool prechecks ----------------------------------------------------------
git --version   | Out-Null
gcloud --version | Out-Null

# --- Repo & branch -----------------------------------------------------------
$gitTop = (git rev-parse --show-toplevel 2>$null)
if (-not $gitTop) { throw "Not a git repository." }
Set-Location $gitTop

$currentBranch = (git rev-parse --abbrev-ref HEAD).Trim()
if ($currentBranch -ne $BRANCH) {
  Write-Warning ("Current branch = '{0}' (expected: '{1}')." -f $currentBranch, $BRANCH)
  Write-Host ("Checkout {0}? [Y/n] " -f $BRANCH) -NoNewline
  $ans = Read-Host
  if ($ans -match '^(|y|Y)$') { git checkout $BRANCH } else { throw "Aborted." }
}

Write-Host "-> Sync upstream..." -ForegroundColor Cyan
git fetch --all --prune
git pull --rebase

# --- BUILDSTAMP (create/overwrite) -------------------------------------------
$stamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss 'Europe/Zurich'")
$buildLines = @(
  "version=$VERSION",
  "image=$IMG_TAG",
  "datetime=$stamp"
)
$buildLines | Set-Content -Encoding UTF8 ".\BUILDSTAMP.txt"
Write-Host "OK BUILDSTAMP.txt written." -ForegroundColor Green

# --- ARBO-LOCK snapshot ------------------------------------------------------
Write-Host ("-> Generating ARBO-LOCK snapshot: {0}" -f $SNAP_NAME) -ForegroundColor Cyan
# ASCII tree (/A) including files (/F)
(tree /F /A | Out-String) | Set-Content -Encoding UTF8 ".\$SNAP_NAME"
Write-Host "OK ARBO-LOCK snapshot refreshed." -ForegroundColor Green

# --- Stage with guards -------------------------------------------------------
git add -A
$deny = @("node_modules", ".venv", "cloud-run-source-deploy", ".pytest_cache", "dist", "build")
$staged = (git diff --cached --name-only)
foreach ($d in $deny) {
  if ($staged | Where-Object { $_ -like "$d/*" -or $_ -like "$d\*" }) {
    throw ("Blocked: staged unwanted path pattern '{0}'. Clean then re-run." -f $d)
  }
}

# --- Cloud Run annotation (JSON parse) ---------------------------------------
$latestReadyRev = "(unknown)"
$serviceUrl     = "(unknown)"
try {
  $jsonRaw = gcloud run services describe $SERVICE --project $PROJECT --region $REGION --format json
  if ($null -ne $jsonRaw -and $jsonRaw.Trim().Length -gt 0) {
    $json = $jsonRaw | ConvertFrom-Json
    if ($null -ne $json.status) {
      if ($json.status.latestReadyRevisionName) { $latestReadyRev = $json.status.latestReadyRevisionName }
      if ($json.status.url)                      { $serviceUrl     = $json.status.url }
    }
  }
} catch {
  Write-Warning "Could not read Cloud Run metadata for commit annotation."
}

# --- Commit message (ASCII only, no here-strings) ----------------------------
$subject = "[deploy] v$VERSION - authws-v753 (snapshot 20250914)"
$lines = @()
$lines += "Cloud Run:"
$lines += "Project : $PROJECT"
$lines += "Region  : $REGION"
$lines += "Service : $SERVICE"
$lines += "Revision: $latestReadyRev"
$lines += "URL     : $serviceUrl"
$lines += ""
$lines += "Image   : $IMG_TAG"
$lines += "Snapshot: $SNAP_NAME"
$lines += "Date    : $stamp"
$body = ($lines -join "`r`n")

$tmpMsg = Join-Path $env:TEMP ("commit_msg_{0}.txt" -f ([guid]::NewGuid().ToString("N")))
($subject + "`r`n`r`n" + $body) | Set-Content -Encoding UTF8 $tmpMsg

# --- Commit if needed --------------------------------------------------------
git diff --cached --quiet
$hasStagedChanges = ($LASTEXITCODE -ne 0)
if ($hasStagedChanges) {
  git commit -F "$tmpMsg"
} else {
  Write-Host "No staged changes (BUILDSTAMP/snapshot identical?)." -ForegroundColor Yellow
}

# --- Push --------------------------------------------------------------------
git push origin $BRANCH

# --- Cleanup & summary -------------------------------------------------------
Remove-Item $tmpMsg -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "================== SUMMARY =================" -ForegroundColor Magenta
Write-Host "Version   : $VERSION"
Write-Host "Image tag : $IMG_TAG"
Write-Host "Snapshot  : $SNAP_NAME (regenerated)"
Write-Host "Branch    : $BRANCH"
Write-Host "Revision  : $latestReadyRev"
Write-Host "URL       : $serviceUrl"
Write-Host "============================================" -ForegroundColor Magenta
