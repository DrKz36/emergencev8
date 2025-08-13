Param(
  [Parameter(Mandatory=$true)][string]$RepoRoot,
  [Parameter(Mandatory=$true)][string]$ArboFile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# --- Normalisation chemins
$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)
if (-not (Test-Path -LiteralPath $RepoRoot -PathType Container)) { throw "RepoRoot introuvable: $RepoRoot" }
$ArboFile = if ([System.IO.Path]::IsPathRooted($ArboFile)) { $ArboFile } else { Join-Path $RepoRoot $ArboFile }
if (-not (Test-Path -LiteralPath $ArboFile -PathType Leaf)) { throw "ArboFile introuvable: $ArboFile" }

# --- Utils
function New-HashSet([System.StringComparer]$cmp = [System.StringComparer]::OrdinalIgnoreCase) {
  New-Object 'System.Collections.Generic.HashSet[string]' ($cmp)
}
function Add-Set($set, [string]$value) { [void]$set.Add($value); $true }

# --- Parse ARBO 'tree /F /A' -> chemins relatifs complets
function Get-ArboRelativePaths {
  Param([string]$ArboPath)

  $paths = New-HashSet
  $stack = New-Object System.Collections.Generic.List[string]
  $rx = '^(?<indent>(?:\|   |    )*)(?:\+---|\\---)\s(?<name>.+)$'

  $lines = Get-Content -LiteralPath $ArboPath -Encoding UTF8
  foreach ($line in $lines) {
    if ($line -notmatch $rx) { continue }
    $indent = $Matches['indent']; $name = $Matches['name'].Trim()
    $level  = [int]($indent.Length / 4)

    while ($stack.Count -gt $level) { $stack.RemoveAt($stack.Count - 1) }

    $isFile = ($name -match '\.')
    if ($isFile) {
      $rel = if ($stack.Count -gt 0) { (Join-Path ($stack -join '\') $name) } else { $name }
      # On ne garde que les .py et __init__.py sous src\
      if ($rel -like 'src\*' -and ($rel -like '*.py' -or $rel -like '*\__init__.py')) {
        Add-Set $paths $rel | Out-Null
      }
    } else {
      $stack.Add($name) | Out-Null
    }
  }
  return $paths
}

# --- Base module depuis un .py
function Get-ModuleBaseFromFile {
  Param([string]$fileFullPath, [string]$RepoRoot)
  $rel = $fileFullPath.Substring($RepoRoot.Length).TrimStart('\')
  if ($rel -notmatch '^src\\(.+)$') { return $null }
  $relFromSrc = $Matches[1]
  $parts = $relFromSrc -split '\\'
  if ($parts.Count -lt 2) { return $null }
  $fileName = $parts[-1]
  $pkgParts = $parts[0..($parts.Count-2)]
  $base = ($pkgParts -join '.')
  if ($fileName -ne '__init__.py') {
    $modName = [System.IO.Path]::GetFileNameWithoutExtension($fileName)
    $base = "$base.$modName"
  }
  return $base
}

# --- Résolution import -> modules candidats
function Resolve-ImportedModules {
  Param([string]$importModule, [string[]]$importNames, [string]$currentModuleBase)

  $candidates = New-Object System.Collections.Generic.List[string]

  if ($importModule.StartsWith('.')) {
    $dots = ([regex]::Match($importModule, '^\.+')).Value.Length
    $rest = $importModule.Substring($dots)
    $baseParts = $currentModuleBase -split '\.'
    if ($baseParts.Count -ge 1) { $baseParts = $baseParts[0..($baseParts.Count-2)] } # repartir du package
    if ($dots -gt $baseParts.Count) { $dots = $baseParts.Count }
    $anchor = if ($dots -gt 0) { $baseParts[0..($baseParts.Count-$dots-1)] } else { $baseParts }
    $anchorStr = ($anchor -join '.')
    $restStr = $rest.Trim('.')
    if ($restStr -ne '') { $prefix = if ($anchorStr -ne '') { "$anchorStr.$restStr" } else { $restStr } }
    else { $prefix = $anchorStr }
  } else {
    $prefix = $importModule
  }

  if ($null -eq $importNames -or $importNames.Count -eq 0) {
    $candidates.Add($prefix) | Out-Null
  } else {
    foreach ($n in $importNames) {
      $n2 = ($n.Trim() -split '\s+as\s+')[0]
      if ($n2 -eq '*') { $candidates.Add($prefix) | Out-Null } else { $candidates.Add("$prefix.$n2") | Out-Null }
    }
  }
  return $candidates
}

# --- Lire imports (simple/rapide)
function Get-ImportsFromFile {
  Param([string]$file)
  $results = @()
  $text = Get-Content -LiteralPath $file -Encoding UTF8
  for ($i=0; $i -lt $text.Count; $i++) {
    $line = $text[$i] -replace '#.*$',''
    $line = $line.Trim()
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    $m1 = [regex]::Match($line, '^\s*from\s+([A-Za-z0-9_\.]+|\.+[A-Za-z0-9_\.]*)\s+import\s+(.+)$')
    if ($m1.Success) {
      $names = @(); foreach ($chunk in ($m1.Groups[2].Value -split ',')) { $names += $chunk.Trim() }
      $results += [pscustomobject]@{ Type='from'; Module=$m1.Groups[1].Value; Names=$names; Line=$i+1 }
      continue
    }
    $m2 = [regex]::Match($line, '^\s*import\s+([A-Za-z0-9_\.]+)(?:\s+as\s+\w+)?')
    if ($m2.Success) {
      $results += [pscustomobject]@{ Type='import'; Module=$m2.Groups[1].Value; Names=@(); Line=$i+1 }
      continue
    }
  }
  return $results
}

# --- Module -> chemins ARBO candidats
function ModuleToArboCandidates {
  Param([string]$module)
  $relDir = ($module -replace '\.','\')
  $rel1 = (Join-Path 'src' $relDir) + '.py'
  $rel2 = Join-Path (Join-Path 'src' $relDir) '__init__.py'
  return @($rel1, $rel2)
}

# === Chargement ARBO
$arboSet = Get-ArboRelativePaths -ArboPath $ArboFile
if ($null -eq $arboSet) {
  $arboSet = New-HashSet
}
Write-Host ("[ARBO] Entrees chargees: {0}" -f $arboSet.Count)
if ($arboSet.Count -lt 5) {
  Write-Warning "ARBO vide ou minuscule. Verifie le fichier snapshot."
}

# === Scan code
$pyFiles = Get-ChildItem -LiteralPath (Join-Path $RepoRoot 'src') -Recurse -File -Filter '*.py' |
           Where-Object { $_.FullName -notmatch '\\__pycache__\\' }

$internalNamespaces = @('backend','frontend','data')

# Stats
$allImports = @()
$internalImports = @()
$unresolved = New-Object System.Collections.Generic.List[object]
$resolvedCount = 0

Write-Host ("[1/3] Scan .py sous src\ ({0} fichiers)..." -f $pyFiles.Count)
Write-Host "[2/3] Resolution des imports internes contre ARBO..."

foreach ($file in $pyFiles) {
  $imports = Get-ImportsFromFile -file $file.FullName
  $allImports += $imports
  $currentBase = Get-ModuleBaseFromFile -fileFullPath $file.FullName -RepoRoot $RepoRoot

  foreach ($imp in $imports) {
    $isInternal = $false
    if ($imp.Module.StartsWith('.')) { $isInternal = $true }
    else { foreach ($ns in $internalNamespaces) { if ($imp.Module -like "$ns*") { $isInternal = $true; break } } }
    if (-not $isInternal) { continue }

    $internalImports += $imp
    $cands = Resolve-ImportedModules -importModule $imp.Module -importNames $imp.Names -currentModuleBase $currentBase

    $ok = $false
    $reason = "No path in ARBO / MissingBoth"
    foreach ($cand in $cands) {
      $paths = ModuleToArboCandidates -module $cand
      # Test ARBO-LOCK
      foreach ($p in $paths) {
        if ($arboSet.Contains($p)) { $ok = $true; break }
      }
      if ($ok) { break }

      # Optionnel: diag snapshot obsolète
      $onDisk = $false
      foreach ($p in $paths) {
        $abs = Join-Path $RepoRoot $p
        if (Test-Path -LiteralPath $abs -PathType Leaf) { $onDisk = $true; break }
      }
      if ($onDisk) { $reason = "ExistsOnDiskNotInARBO" }
    }

    if ($ok) { $resolvedCount++ }
    else {
      $unresolved.Add([pscustomobject]@{
        File    = $file.FullName
        Line    = $imp.Line
        Module  = ($cands -join ' | ')
        Import  = (if ($imp.Type -eq 'from') { "from $($imp.Module) import $([string]::Join(', ',$imp.Names))" } else { "import $($imp.Module)" })
        Reason  = $reason
      }) | Out-Null
    }
  }
}

# === Rapports
$audDir = Join-Path $RepoRoot 'audit'
if (-not (Test-Path -LiteralPath $audDir)) { [void](New-Item -ItemType Directory -Path $audDir) }

$rawPath  = Join-Path $audDir 'audit_imports_raw.txt'
$unresPath= Join-Path $audDir 'audit_imports_internal_unresolved.txt'
$sumPath  = Join-Path $audDir 'audit_summary.txt'

# RAW
$raw = New-Object System.Collections.Generic.List[string]
foreach ($file in $pyFiles) {
  $imports = Get-ImportsFromFile -file $file.FullName
  foreach ($imp in $imports) {
    $line = "{0}`t{1}`t{2}" -f $file.FullName, $imp.Line, (if ($imp.Type -eq 'from') { "from $($imp.Module) import $([string]::Join(', ',$imp.Names))" } else { "import $($imp.Module)" })
    $raw.Add($line) | Out-Null
  }
}
$raw | Set-Content -LiteralPath $rawPath -Encoding UTF8

# UNRESOLVED (CSV)
$csv = $unresolved | Select-Object File,Line,Module,Import,Reason | ConvertTo-Csv -NoTypeInformation
$csv | Set-Content -LiteralPath $unresPath -Encoding UTF8

# SUMMARY
$sum  = "=== AUDIT IMPORTS - Summary ===`r`n"
$sum += "Repo          : $RepoRoot`r`n"
$sum += "ARBO snapshot : $ArboFile`r`n"
$sum += "Namespaces    : {0}`r`n" -f ($internalNamespaces -join ', ')
$sum += ("ARBO entries               : {0}`r`n" -f $arboSet.Count)
$sum += "`r`n"
$sum += ("Total imports found         : {0}`r`n" -f $allImports.Count)
$sum += ("Internal imports analyzed   : {0}`r`n" -f $internalImports.Count)
$sum += ("Resolved OK                 : {0}`r`n" -f $resolvedCount)
$sum += ("UNRESOLVED (to fix)         : {0}`r`n" -f $unresolved.Count)
$sum += "`r`nFiles written under: $audDir`r`n"
$sum | Set-Content -LiteralPath $sumPath -Encoding UTF8

Write-Host "[3/3] Ecriture des rapports..."
Write-Host "=== Done. Ouvre audit\audit_summary.txt ==="
