<#
  Usage:
    .\scripts\load-codex-prompt.ps1 | Set-Clipboard
    # Puis colle (Ctrl+V) dans le chat Codex / Windsurf
#>
$root = Split-Path -Parent $PSScriptRoot
$promptPath = Join-Path $root 'CODEX_SYSTEM_PROMPT.md'

if (-not (Test-Path $promptPath)) {
    Write-Error "CODEX_SYSTEM_PROMPT.md introuvable à l'emplacement attendu: $promptPath"
    exit 1
}

Get-Content -Path $promptPath -Raw -Encoding UTF8
