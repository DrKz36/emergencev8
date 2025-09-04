Param([string]$Region="europe-west1")

Write-Host "# Context"
$svcProd   = "emergence-app"
$svcCanary = "emergence-app-canary"

$revProdReady   = (gcloud run services describe $svcProd   --region $Region --format="value(status.latestReadyRevisionName)")
$revCanaryReady = (gcloud run services describe $svcCanary --region $Region --format="value(status.latestReadyRevisionName)")

Write-Host "Prod READY:   $revProdReady"
Write-Host "Canary READY: $revCanaryReady"

Write-Host "`n# Images"
$imgProd   = (gcloud run revisions describe $revProdReady   --region $Region --format="value(spec.containers[0].image)")
$imgCanary = (gcloud run revisions describe $revCanaryReady --region $Region --format="value(spec.containers[0].image)")
"Prod image:   $imgProd"
"Canary image: $imgCanary"

Write-Host "`n# TimeoutSeconds"
$toProd   = (gcloud run services describe $svcProd   --region $Region --format="value(spec.template.spec.timeoutSeconds)")
$toCanary = (gcloud run services describe $svcCanary --region $Region --format="value(spec.template.spec.timeoutSeconds)")
"Prod timeout:   $toProd"
"Canary timeout: $toCanary"

Write-Host "`n# ContainerConcurrency"
$ccProd   = (gcloud run revisions describe $revProdReady   --region $Region --format="value(spec.containerConcurrency)")
$ccCanary = (gcloud run revisions describe $revCanaryReady --region $Region --format="value(spec.containerConcurrency)")
"Prod cc:   $ccProd"
"Canary cc: $ccCanary"

Write-Host "`n# Resources (cpu/memory)"
$resProd = gcloud run revisions describe $revProdReady --region $Region `
  --format="flattened(spec.containers[].resources.limits[])"
$resCan  = gcloud run revisions describe $revCanaryReady --region $Region `
  --format="flattened(spec.containers[].resources.limits[])"
"== Prod ==";  $resProd
"== Canary =="; $resCan
"== Diff ==";  Compare-Object ($resCan -split "`n" | Sort-Object) ($resProd -split "`n" | Sort-Object) -IncludeEqual:$false

Write-Host "`n# Annotations utiles"
$annProd = gcloud run revisions describe $revProdReady --region $Region `
  --format="flattened(metadata.annotations[])"
$annCan  = gcloud run revisions describe $revCanaryReady --region $Region `
  --format="flattened(metadata.annotations[])"
"== Diff annotations ==";
Compare-Object ($annCan -split "`n" | Sort-Object) ($annProd -split "`n" | Sort-Object) -IncludeEqual:$false

Write-Host "`n# Envs (nom=val|secret)"
function Get-EnvFlat($rev){ 
  $env = gcloud run revisions describe $rev --region $Region --format="json" | ConvertFrom-Json
  $arr = @()
  foreach($e in $env.spec.containers[0].env){
    if($null -ne $e.value){
      $arr += "$($e.name)=$($e.value)"
    } elseif($null -ne $e.valueFrom.secretKeyRef.name){
      $arr += "$($e.name)=<secret:$($e.valueFrom.secretKeyRef.name)>"
    } else {
      $arr += "$($e.name)=<unset>"
    }
  }
  return ($arr | Sort-Object)
}

$envProd = Get-EnvFlat $revProdReady
$envCan  = Get-EnvFlat $revCanaryReady
"== Missing in PROD ==";  Compare-Object $envCan $envProd -PassThru | ? { $_.SideIndicator -eq "<=" }
"== Extra in PROD ==";    Compare-Object $envCan $envProd -PassThru | ? { $_.SideIndicator -eq "=>" }
