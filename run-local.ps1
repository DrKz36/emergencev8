param(
  [int]$Port = 8000,
  [switch]$StopAfterTests = $false,
  [int]$MinTokenTtlMinutes = 5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$CURL = "curl.exe"
$BASE = "http://127.0.0.1:$Port"
$EnvFile = Join-Path $PSScriptRoot ".env.local"
$TokenFile = Join-Path $PSScriptRoot "id_token.txt"

function Load-DotEnv([string]$path) {
  if (Test-Path $path) {
    Write-Host "Loading .env.local"
    Get-Content -Path $path -Encoding UTF8 |
      Where-Object { $_ -match '^\s*[^#]\w+=.*' } |
      ForEach-Object {
        $kv = $_ -split '=', 2
        $name  = $kv[0].Trim()
        $value = $kv[1].Trim()
        [System.Environment]::SetEnvironmentVariable($name, $value, 'Process')
      }
  }
}

function Get-ListeningProcessOnPort([int]$p) {
  try {
    $conn = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction Stop | Select-Object -First 1
    if ($conn) { return Get-Process -Id $conn.OwningProcess -ErrorAction Stop }
  } catch {
    # Fallback netstat (plus rustique)
    $row = netstat -ano | Select-String -Pattern "LISTENING\s+$p\s+(\d+)$"
    if ($row) {
      $pid = [int]($row.Matches[0].Groups[1].Value)
      try { return Get-Process -Id $pid -ErrorAction Stop } catch {}
    }
  }
  return $null
}

function Start-Uvicorn([int]$p) {
  $existing = Get-ListeningProcessOnPort -p $p
  if ($existing) {
    Write-Host "Uvicorn already running on port $p (PID=$($existing.Id)). Reusing it."
    return $existing
  }
  Write-Host "Starting Uvicorn on port $p..."
  $args = "-m uvicorn --app-dir src backend.main:app --host 0.0.0.0 --port $p"
  $proc = Start-Process -FilePath "python" -ArgumentList $args -PassThru
  return $proc
}

function Wait-Health([string]$url) {
  Write-Host "Waiting for $url ..."
  $ok = $false
  for ($i=0; $i -lt 40; $i++) {
    try {
      $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
      if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch { Start-Sleep -Milliseconds 250 }
  }
  if (-not $ok) { throw "API not ready at $url" }
  Write-Host "Health OK"
}

function Curl-Head([string]$cmd) {
  $resp = Invoke-Expression $cmd
  $first = ($resp -split "`r?`n")[0]
  return $first
}

function ConvertFrom-Base64Url([string]$s) {
  $s = $s.Replace('-', '+').Replace('_', '/')
  switch ($s.Length % 4) {
    2 { $s += "==" }
    3 { $s += "=" }
  }
  $bytes = [System.Convert]::FromBase64String($s)
  return [System.Text.Encoding]::UTF8.GetString($bytes)
}

function Get-JwtExpUtc([string]$jwt) {
  # jwt = header.payload.signature
  $parts = $jwt -split '\.'
  if ($parts.Length -lt 2) { return $null }
  try {
    $payloadJson = ConvertFrom-Base64Url $parts[1]
    $payload = $payloadJson | ConvertFrom-Json
    if ($payload.exp) {
      $epoch = [DateTimeOffset]::FromUnixTimeSeconds([long]$payload.exp)
      return $epoch.UtcDateTime
    }
  } catch { return $null }
  return $null
}

function Get-Token() {
  # 1) fichier
  if (Test-Path $TokenFile) {
    $t = (Get-Content -Path $TokenFile -Encoding UTF8 | Select-Object -First 1).Trim()
    if ($t) { return $t }
  }
  # 2) presse-papiers
  try {
    $clip = (Get-Clipboard).Trim()
    if ($clip) { return $clip }
  } catch {}
  # 3) dev-auth
  Start-Process "$BASE/dev-auth.html"
  return (Read-Host "Paste your Google ID token")
}

# 1) ENV
Load-DotEnv $EnvFile

# 2) UVICORN
$proc = Start-Uvicorn -p $Port
Start-Sleep -Milliseconds 200

try {
  # 3) Health
  Wait-Health "$BASE/api/health"

  # 4) 401 attendu
  Write-Host "Test /api/documents/ without Authorization (expect 401)"
  $h401 = Curl-Head "$CURL -i -sS $BASE/api/documents/"
  Write-Host $h401
  if ($h401 -notmatch 'HTTP/1\.[01]\s+401') {
    Write-Warning "Expected 401. Check AUTH_DEV_MODE=0 in .env.local and clear any persistent env."
  }

  # 5) Token
  $token = Get-Token
  if (-not $token) { throw "No token provided." }

  # 6) Expiration
  $expUtc = Get-JwtExpUtc $token
  if ($expUtc) {
    $now = [DateTime]::UtcNow
    $mins = [int]([TimeSpan]::FromSeconds(($expUtc - $now).TotalSeconds).TotalMinutes)
    Write-Host ("Token TTL ~ {0} min (exp {1:u})" -f $mins, $expUtc)
    if ($mins -lt $MinTokenTtlMinutes) {
      Write-Warning "Token near expiry. Consider refreshing from /dev-auth.html."
    }
  } else {
    Write-Warning "Could not parse token expiry."
  }

  # 7) 200 attendu si allowlist OK
  Write-Host "Test /api/documents/ with Authorization (expect 200 if allowlist OK)"
  $cmd200 = "$CURL -i -sS $BASE/api/documents/ -H ""Authorization: Bearer $token"""
  $h200 = Curl-Head $cmd200
  Write-Host $h200

  if ($h200 -match 'HTTP/1\.[01]\s+403') {
    Write-Warning "Got 403 (Email not allowed). Add the user to auth_allowlist via /api/auth/admin/allowlist or the CLI."
  } elseif ($h200 -notmatch 'HTTP/1\.[01]\s+200') {
    Write-Warning "Unexpected response. Check logs."
  } else {
    Write-Host "OK"
  }

  # 8) Sauvegarde automatique du token (facultatif)
  if (-not (Test-Path $TokenFile)) {
    try {
      Set-Content -Path $TokenFile -Value $token -Encoding UTF8 -NoNewline
      Write-Host "Saved token to id_token.txt"
    } catch {}
  }
}
finally {
  if ($StopAfterTests -and $proc) {
    # Ne stoppe que si on est le lanceur (sinon on tuerait un autre Uvicorn réutilisé)
    $mine = $false
    if ($proc.HasExited -eq $false) { $mine = $true }
    if ($mine) {
      Write-Host "Stopping Uvicorn"
      try { Stop-Process -Id $proc.Id -Force } catch {}
    }
  } else {
    Write-Host "Uvicorn is still running. Press Ctrl+C in its window to stop."
  }
}
