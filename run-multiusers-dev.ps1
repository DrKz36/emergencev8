# ================================
# Script DEV Multi-Users (Alice & Bob)
# ================================

# Nettoyage éventuel
deactivate 2>$null
$ErrorActionPreference = "Stop"

# Activer venv
& C:/dev/emergenceV8/.venv/Scripts/Activate.ps1

# Variables ENV
$env:AUTH_DEV_MODE="1"                  # Mode dev → user_id manuel autorisé
$env:CHROMA_DISABLE_TELEMETRY="1"       # Silence Chroma
$env:OPENAI_API_KEY="sk-xxx"            # Mets ta clé si besoin

Write-Host "=== Lancement backend en mode DEV avec AUTH_DEV_MODE=1 ==="

# Lancer le serveur (en arrière-plan)
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd C:\dev\emergenceV8; & C:/dev/emergenceV8/.venv/Scripts/Activate.ps1; python -m uvicorn --app-dir src backend.main:app --host 0.0.0.0 --port 8000"
)

Start-Sleep -Seconds 5

# URLs WebSocket (Alice & Bob)
$aliceUrl = "ws://127.0.0.1:8000/ws/test-alice?user_id=alice"
$bobUrl   = "ws://127.0.0.1:8000/ws/test-bob?user_id=bob"

Write-Host "=== Sessions de test ==="
Write-Host "Alice → $aliceUrl"
Write-Host "Bob   → $bobUrl"

# Ouvrir deux consoles WebSocket (via wscat si installé)
# → npm install -g wscat
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "wscat -c $aliceUrl"
)
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "wscat -c $bobUrl"
)

Write-Host "`nEnvoie des messages dans Alice et Bob séparément."
Write-Host "Ensuite, lance la consolidation :"
Write-Host '  curl.exe -sS -H "Authorization: Bearer testtoken" "http://127.0.0.1:8000/api/memory/tend-garden"'
Write-Host "`nPuis teste une nouvelle session Alice avec MAGNESIA et Bob avec CARBONE NOIR pour vérifier l'isolation."
