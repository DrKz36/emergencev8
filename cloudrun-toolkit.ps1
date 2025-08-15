<# =======================================================================
  Cloud Run Toolkit – Emergence
  Utilitaires PowerShell pour piloter le service Cloud Run “emergence-app”
  Tested with: PS 7.x / Windows PowerShell 5.1 + gcloud SDK
======================================================================= #>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

#region ====== PARAMÈTRES GLOBAUX (modifiable) ==========================
$GLOBAL:PROJECT = 'emergence-469005'
$GLOBAL:REGION  = 'europe-west1'
$GLOBAL:SERVICE = 'emergence-app'
$GLOBAL:SA      = 'emergence-app-run-sa@emergence-469005.iam.gserviceaccount.com'
$GLOBAL:REPO    = 'europe-west1-docker.pkg.dev/emergence-469005/emergence-repo'
$GLOBAL:IMAGE_BASENAME = 'emergence-app'
#endregion ===============================================================

function Set-Globals {
    param(
        [string]$Project = $GLOBAL:PROJECT,
        [string]$Region  = $GLOBAL:REGION,
        [string]$Service = $GLOBAL:SERVICE,
        [string]$ServiceAccount = $GLOBAL:SA,
        [string]$Repo = $GLOBAL:REPO,
        [string]$ImageBaseName = $GLOBAL:IMAGE_BASENAME
    )
    $GLOBAL:PROJECT = $Project
    $GLOBAL:REGION  = $Region
    $GLOBAL:SERVICE = $Service
    $GLOBAL:SA      = $ServiceAccount
    $GLOBAL:REPO    = $Repo
    $GLOBAL:IMAGE_BASENAME = $ImageBaseName
}

function Show-Globals {
    Write-Host "PROJECT : $($GLOBAL:PROJECT)"
    Write-Host "REGION  : $($GLOBAL:REGION)"
    Write-Host "SERVICE : $($GLOBAL:SERVICE)"
    Write-Host "SA      : $($GLOBAL:SA)"
    Write-Host "REPO    : $($GLOBAL:REPO)"
    Write-Host "IMAGE   : $($GLOBAL:REPO)/$($GLOBAL:IMAGE_BASENAME):<tag>"
}

function Get-ServiceUrl {
    gcloud run services describe $GLOBAL:SERVICE `
      --region $GLOBAL:REGION `
      --format 'value(status.url)'
}

function Get-AuthHeader {
    $token = gcloud auth print-identity-token
    return @{ Authorization = "Bearer $token" }
}

function Invoke-Api {
    param(
        [Parameter(Mandatory=$true)][string]$Path,   # ex: "/api/health"
        [ValidateSet('GET','POST','DELETE','PUT','PATCH')] [string]$Method='GET',
        [hashtable]$Headers,
        [object]$Body
    )
    $url = (Get-ServiceUrl) + $Path
    if (-not $Headers) { $Headers = Get-AuthHeader }
    if ($null -ne $Body) {
        return Invoke-RestMethod -Uri $url -Method $Method -Headers $Headers -Body ($Body | ConvertTo-Json -Depth 10) -ContentType 'application/json'
    } else {
        return Invoke-RestMethod -Uri $url -Method $Method -Headers $Headers
    }
}

# Upload multipart/forme (compatible FastAPI "file")
Add-Type -AssemblyName System.Net.Http | Out-Null
function Upload-Document {
    param(
        [Parameter(Mandatory=$true)][string]$FilePath,
        [string]$ContentType # si vide: déduit de l’extension simple
    )
    if (!(Test-Path $FilePath)) { throw "Fichier introuvable: $FilePath" }
    if (-not $ContentType) {
        switch ([IO.Path]::GetExtension($FilePath).ToLower()) {
            '.txt'  { $ContentType = 'text/plain' }
            '.pdf'  { $ContentType = 'application/pdf' }
            '.docx' { $ContentType = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }
            default { $ContentType = 'application/octet-stream' }
        }
    }

    $url = (Get-ServiceUrl) + '/api/documents/upload'
    $token = gcloud auth print-identity-token

    $handler = [System.Net.Http.HttpClientHandler]::new()
    $client  = [System.Net.Http.HttpClient]::new($handler)
    $client.DefaultRequestHeaders.Authorization =
        [System.Net.Http.Headers.AuthenticationHeaderValue]::new('Bearer', $token)

    $form = [System.Net.Http.MultipartFormDataContent]::new()
    $fs = [System.IO.File]::OpenRead($FilePath)
    $sc = [System.Net.Http.StreamContent]::new($fs)
    $sc.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse($ContentType)

    $cd = [System.Net.Http.Headers.ContentDispositionHeaderValue]::new('form-data')
    $cd.Name = 'file'
    $cd.FileName = [System.IO.Path]::GetFileName($FilePath)
    $sc.Headers.ContentDisposition = $cd

    $form.Add($sc)
    $resp = $client.PostAsync($url, $form).Result
    $body = $resp.Content.ReadAsStringAsync().Result

    $fs.Dispose(); $form.Dispose(); $client.Dispose()

    if (-not $resp.IsSuccessStatusCode) {
        throw "Upload FAILED ($($resp.StatusCode)) -> $body"
    }
    return ($body | ConvertFrom-Json)
}

# ===================== Opérations Cloud Run / API =======================

function CR-AddInvoker-AllAuthenticatedUsers {
    gcloud run services add-iam-policy-binding $GLOBAL:SERVICE `
      --region $GLOBAL:REGION `
      --member "allAuthenticatedUsers" `
      --role "roles/run.invoker"
}

function CR-AddInvoker-User {
    param([Parameter(Mandatory=$true)][string]$Email)
    gcloud run services add-iam-policy-binding $GLOBAL:SERVICE `
      --region $GLOBAL:REGION `
      --member "user:$Email" `
      --role "roles/run.invoker"
}

function CR-Logs {
    param([int]$Limit = 100)
    gcloud run services logs read $GLOBAL:SERVICE `
      --region $GLOBAL:REGION `
      --limit $Limit
}

function CR-DescribeLatestReady {
    gcloud run services describe $GLOBAL:SERVICE `
      --region $GLOBAL:REGION `
      --format 'value(status.latestReadyRevisionName)'
}

function API-Health { Invoke-Api -Path '/api/health' }
function API-DebateList { Invoke-Api -Path '/api/debate/' }
function API-DocsList { Invoke-Api -Path '/api/documents' }
function API-DocsDeleteLast {
    $docs = API-DocsList
    if ($null -eq $docs -or $docs.Count -eq 0) { Write-Host "Aucun document."; return }
    $last = $docs[-1]
    Invoke-Api -Path "/api/documents/$($last.id)" -Method 'DELETE' | Out-Host
}

# ======================== Déploiement / Build ===========================

function CR-Deploy {
    param(
        [Parameter(Mandatory=$true)][string]$Image,
        [int]$MinInstances = 1
    )
    gcloud run deploy $GLOBAL:SERVICE `
      --image $Image `
      --service-account $GLOBAL:SA `
      --region $GLOBAL:REGION `
      --no-allow-unauthenticated `
      --memory=2Gi `
      --cpu=2 `
      --timeout=900 `
      --set-env-vars=CHROMA_TELEMETRY_ENABLED=FALSE `
      "--set-secrets=OPENAI_API_KEY=OPENAI_API_KEY:latest,GOOGLE_API_KEY=GOOGLE_API_KEY:latest,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest" `
      --min-instances=$MinInstances
}

function CR-BuildAndDeploy {
    param(
        [string]$Tag = (Get-Date -Format 'yyyyMMdd-HHmmss'),
        [int]$MinInstances = 1
    )
    $image = "$($GLOBAL:REPO)/$($GLOBAL:IMAGE_BASENAME):$Tag"
    Write-Host ">> Build: $image"
    gcloud builds submit --tag $image
    Write-Host ">> Deploy: $image"
    CR-Deploy -Image $image -MinInstances $MinInstances
}

# ========================= Raccourcis utiles ===========================

function CR-QuickDiagnostics {
    Write-Host "=== Globals ==="; Show-Globals; Write-Host ""
    $url = Get-ServiceUrl
    Write-Host "Service URL:" $url
    Write-Host "`n=== Health ==="
    try { API-Health | Out-Host } catch { Write-Warning $_ }
    Write-Host "`n=== LatestReadyRevision ==="
    try { CR-DescribeLatestReady | Out-Host } catch { Write-Warning $_ }
    Write-Host "`n=== Last logs (100) ==="
    try { CR-Logs -Limit 100 | Out-Host } catch { Write-Warning $_ }
}

# ============================== Aide ===================================

function CR-Help {
@"
Cloud Run Toolkit – Commandes principales
----------------------------------------
Set-Globals -Project <p> -Region <r> -Service <s> -ServiceAccount <sa> -Repo <r> -ImageBaseName <name>
Show-Globals

# Diagnostics & info
Get-ServiceUrl
Get-AuthHeader
API-Health
CR-DescribeLatestReady
CR-Logs -Limit 200
CR-QuickDiagnostics

# IAM
CR-AddInvoker-AllAuthenticatedUsers
CR-AddInvoker-User -Email <user@domaine.tld>

# API Documents
API-DocsList
Upload-Document -FilePath <path> [-ContentType <mime>]
API-DocsDeleteLast

# Déploiement
CR-Deploy -Image "<repo>/<name>:<tag>" [-MinInstances 1]
CR-BuildAndDeploy [-Tag auto] [-MinInstances 1]
"@ | Write-Host
}

# Message d’accueil
Write-Host "Cloud Run Toolkit chargé. Tape 'Show-Globals' puis 'CR-Help' pour l’aide."
