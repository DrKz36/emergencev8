# =======================
# ops\switch-cert.ps1
# Bascule le proxy HTTPS sur le cert multi-domaine (cert-4), vérifie, puis supprime l'ancien (cert-2).
# Conformité PSScriptAnalyzer : verbes approuvés.
# Usage:
#   .\switch-cert.ps1           # exécution normale (avec confirmation pour la suppression)
#   .\switch-cert.ps1 -Force    # suppression sans confirmation
# =======================

[CmdletBinding()]
param(
  [switch]$Force
)

$ErrorActionPreference = "Stop"

# --- Paramètres projet ---
$ProxyName = "emergence-app-https-proxy"
$NewCert   = "emergence-app-cert-4"
$OldCert   = "emergence-app-cert-2"

function Get-CertInfo {
  [CmdletBinding()]
  param([Parameter(Mandatory)][string]$Name)

  gcloud compute ssl-certificates describe $Name --global `
    --format="yaml(name,managed.status,managed.domainStatus,creationTimestamp,expireTime)"
}

function Get-CertStatus {
  [CmdletBinding()]
  param([Parameter(Mandatory)][string]$Name)

  $json = gcloud compute ssl-certificates describe $Name --global `
    --format="json(managed.status,managed.domainStatus)"
  $json | ConvertFrom-Json
}

function Test-NewCertReady {
  [CmdletBinding()]
  param([Parameter(Mandatory)][string]$Name)

  Write-Host "→ Vérification de l'état du certificat '$Name'..."
  $status  = Get-CertStatus -Name $Name
  $global  = $status.managed.status
  $domains = $status.managed.domainStatus.PSObject.Properties | ForEach-Object {
    [PSCustomObject]@{ Domain = $_.Name; State = $_.Value }
  }

  $allActive = ($domains | Where-Object { $_.State -ne "ACTIVE" }).Count -eq 0
  [PSCustomObject]@{
    GlobalStatus    = $global
    AllDomainsActive= $allActive
    Domains         = $domains
  }
}

function Wait-UntilActive {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory)][string]$Name,
    [int]$MaxTries = 80,
    [int]$DelaySec = 15
  )

  for ($i=1; $i -le $MaxTries; $i++) {
    $info = Test-NewCertReady -Name $Name
    $domainsStr = ($info.Domains | ForEach-Object { "$($_.Domain)=$($_.State)" }) -join ", "
    Write-Host ("  [{0}/{1}] managed.status={2} | {3}" -f $i, $MaxTries, $info.GlobalStatus, $domainsStr)

    if ($info.GlobalStatus -eq "ACTIVE" -and $info.AllDomainsActive) {
      Write-Host "✓ Certificat globalement ACTIVE avec tous les domaines ACTIVE."
      return $true
    }
    Start-Sleep -Seconds $DelaySec
  }
  return $false
}

function Set-ProxyCertificate {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory)][string]$Proxy,
    [Parameter(Mandatory)][string]$Certificate
  )
  Write-Host "→ Bascule du proxy '$Proxy' vers le certificat '$Certificate'..."
  gcloud compute target-https-proxies update $Proxy `
    --ssl-certificates="$Certificate" --global | Out-Null
}

function Test-ProxyCertificate {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory)][string]$Proxy,
    [Parameter(Mandatory)][string]$ExpectedCertificate
  )
  $current = gcloud compute target-https-proxies describe $Proxy --global `
    --format="value(sslCertificates)"
  if ($current -notmatch $ExpectedCertificate) {
    throw "Le proxy n'expose pas '$ExpectedCertificate'. Actuel: $current"
  }
  Write-Host "✓ Proxy expose bien '$ExpectedCertificate'."
}

function Remove-SSLCertificate {
  [CmdletBinding(SupportsShouldProcess)]
  param(
    [Parameter(Mandatory)][string]$Name,
    [switch]$ForceLocal
  )

  if (-not $ForceLocal) {
    $ok = Read-Host "Supprimer le certificat '$Name' ? (y/N)"
    if ($ok -ne "y") { Write-Host "↷ Suppression annulée."; return }
  }
  if ($PSCmdlet.ShouldProcess($Name, "Delete SSL certificate")) {
    Write-Host "→ Suppression du certificat '$Name'..."
    gcloud compute ssl-certificates delete $Name --global --quiet | Out-Null
    Write-Host "✓ Certificat '$Name' supprimé."
  }
}

# --- Sécurité de base ---
if ($NewCert -eq $OldCert) { throw "NEW_CERT et OLD_CERT ne doivent pas être identiques." }

Write-Host "=== ÉTAT INITIAL ==="
Write-Host (Get-CertInfo -Name $NewCert)
Write-Host "===================="

# 1) Attendre ACTIVE (global + domaines)
$ready = Wait-UntilActive -Name $NewCert
if (-not $ready) {
  throw "Le certificat '$NewCert' n'a pas atteint l'état ACTIVE global dans le temps imparti."
}

# 2) Bascule proxy
Set-ProxyCertificate -Proxy $ProxyName -Certificate $NewCert
Test-ProxyCertificate -Proxy $ProxyName -ExpectedCertificate $NewCert

# 3) Sanity HTTP (best effort)
try {
  Start-Process "https://emergence-app.ch/api/health"
  Start-Process "https://www.emergence-app.ch/api/health"
} catch { Write-Host "Info: ouverture des URLs sautée (environnement headless ?)" }

# 4) Suppression ancien certificat
Remove-SSLCertificate -Name $OldCert -ForceLocal:$Force

Write-Host "✓✓ Bascule terminée."
