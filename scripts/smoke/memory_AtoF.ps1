# scripts\smoke\memory_AtoF.ps1
# Orchestrateur Smokes Mémoire A→F avec pacing et passage du JWT au probe.
# Encodage UTF-8 (BOM) conseillé. PowerShell 5.1+.

[CmdletBinding()]
param(
  [string]$Base       = "http://127.0.0.1:8000",
  [string]$Token      = $env:EMERGENCE_ID_TOKEN,
  [int]   $PaceMs     = 12000,     # 12 s = ~5 req/min
  [int]   $TimeoutSec = 120,
  [string]$AgentNeo   = "neo",
  [string]$AgentAnima = "anima",
  [string]$AgentNexus = "nexus",
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Invoke-Probe {
  param(
    [Parameter(Mandatory)]
    [string]$Run,
    [Parameter(Mandatory)]
    [string]$Agent,
    [string]$Text = ""
  )
  $args = @("--base", $Base, "--timeout", $TimeoutSec, "--run", $Run, "--agent", $Agent)
  if ($Text) { $args += @("--text", $Text) }

  # 🔒 IMPORTANT : passage du JWT au client Python (qui le mettra en sous-protocole 'jwt,<JWT>' et/ou Authorization)
  if ($Token) { $args += @("--id-token", $Token) }

  Write-Host "▶ python scripts/smoke/memory_ws_probe.py $($args -join ' ')" -ForegroundColor DarkGray
  if (-not $DryRun) {
    & python "scripts/smoke/memory_ws_probe.py" @args
    if ($LASTEXITCODE -ne 0) { throw "Probe failed (exit $LASTEXITCODE)" }
    if ($PaceMs -gt 0) { Start-Sleep -Milliseconds $PaceMs }
  }
}

Write-Host "=== EMERGENCE :: Smoke mémoire A→F (pacing=${PaceMs}ms) ===" -ForegroundColor Green
Write-Host "Base: $Base"
if (-not $Token) {
  Write-Warning "Aucun ID token (-Token) détecté. Le WS exigera un JWT (Authorization ou sous-protocole)."
}

# A — STM (résumé de session)
Invoke-Probe -Run "A" -Agent $AgentNeo   -Text "Aujourd’hui je veux travailler sur la Roadmap V8 et corriger la latence."

# B — LTM (fait durable)
Invoke-Probe -Run "B" -Agent $AgentAnima -Text "Note durable: mot-code Anima et ville."

# C — Isolation par agent
Invoke-Probe -Run "C" -Agent $AgentAnima -Text "Isolation agent: Anima sait le mot-code."
Invoke-Probe -Run "C" -Agent $AgentNeo   -Text "Isolation agent: Neo doit l’ignorer."

# D — RAG OFF/ON (si le probe le gère en interne)
Invoke-Probe -Run "D" -Agent $AgentNeo   -Text "Compare RAG OFF vs ON (question brève)."

# E — Multi-session / cross-agent
Invoke-Probe -Run "E" -Agent $AgentNexus -Text "Préférence style (réponses courtes)."

# F — Robustesse signaux
Invoke-Probe -Run "F" -Agent $AgentNeo   -Text "Ping test signaux."
Write-Host "=== Terminé. Vérifie handshake WS + STM ===" -ForegroundColor Green
