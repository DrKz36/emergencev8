# debug-frontend.ps1
# Script automatique pour debugger le frontend via Chrome DevTools Protocol
# Usage: pwsh -File scripts/debug-frontend.ps1 [action]
# Actions: listen, check, eval, help

param(
    [Parameter(Position=0)]
    [ValidateSet("listen", "check", "eval", "help")]
    [string]$Action = "listen",

    [Parameter(Position=1)]
    [string]$Expression = ""
)

$ErrorActionPreference = "Stop"

# Couleurs
$COLOR_INFO = "Cyan"
$COLOR_SUCCESS = "Green"
$COLOR_ERROR = "Red"
$COLOR_WARN = "Yellow"

function Write-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor $COLOR_INFO }
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor $COLOR_SUCCESS }
function Write-Error { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor $COLOR_ERROR }
function Write-Warn { param($msg) Write-Host "[WARN] $msg" -ForegroundColor $COLOR_WARN }

function Show-Help {
    Write-Host @"

🔧 DEBUG FRONTEND - Chrome DevTools Protocol
==============================================

Usage:
    pwsh -File scripts/debug-frontend.ps1 [action] [args]

Actions:
    listen      - Écoute les événements mémoire en temps réel (défaut)
    check       - Vérifie l'état actuel du frontend (EventBus, ChatModule, State)
    eval        - Exécute du JavaScript personnalisé dans la console
    help        - Affiche cette aide

Exemples:
    # Écouter les événements mémoire
    pwsh -File scripts/debug-frontend.ps1 listen

    # Vérifier l'état du frontend
    pwsh -File scripts/debug-frontend.ps1 check

    # Exécuter du JS custom
    pwsh -File scripts/debug-frontend.ps1 eval "console.log(window.state.get('chat.messages'))"

Prérequis:
    - Chrome lancé avec --remote-debugging-port=9222
    - Frontend lancé sur http://localhost:5173
    - Python 3 avec websockets installé (pip install websockets)

"@ -ForegroundColor White
}

function Get-ChromeDebugURL {
    Write-Info "Récupération de l'URL de debug Chrome..."

    try {
        $response = Invoke-RestMethod -Uri "http://localhost:9222/json" -Method Get
        $page = $response | Where-Object { $_.url -like "*localhost:5173*" -or $_.url -like "*localhost:8000*" } | Select-Object -First 1

        if ($page) {
            Write-Success "Page trouvée: $($page.title)"
            return $page.webSocketDebuggerUrl
        } else {
            Write-Error "Aucune page Emergence trouvée sur localhost:5173"
            Write-Info "Pages disponibles:"
            $response | ForEach-Object { Write-Host "  - $($_.title) : $($_.url)" }
            return $null
        }
    } catch {
        Write-Error "Impossible de se connecter à Chrome DevTools sur localhost:9222"
        Write-Info "Assurez-vous que Chrome est lancé avec --remote-debugging-port=9222"
        return $null
    }
}

function Invoke-ListenMemoryEvents {
    Write-Info "Démarrage de l'écoute des événements mémoire..."

    $wsUrl = Get-ChromeDebugURL
    if (-not $wsUrl) { exit 1 }

    $script = @"
# -*- coding: utf-8 -*-
import asyncio
import websockets
import json
import sys
from datetime import datetime

# Fix encoding pour Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def listen_memory_events():
    uri = "$wsUrl"

    print("[INFO] Connexion a Chrome DevTools...")
    async with websockets.connect(uri) as ws:
        # Enable Runtime & Console
        await ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
        await ws.recv()
        await ws.send(json.dumps({"id": 2, "method": "Console.enable"}))
        await ws.recv()
        await ws.send(json.dumps({"id": 3, "method": "Log.enable"}))
        await ws.recv()

        print("[OK] Connecte - Ecoute des logs console...")
        print("[INFO] Filtres: memory, banner, handleMemoryBanner, ws:memory_banner")
        print("[INFO] Envoie un message dans le chat pour voir les evenements\n")

        while True:
            msg = await ws.recv()
            data = json.loads(msg)

            # Console logs
            if data.get('method') == 'Runtime.consoleAPICalled':
                params = data.get('params', {})
                log_type = params.get('type', 'log')
                args = params.get('args', [])

                # Format les arguments
                log_parts = []
                for arg in args:
                    if arg.get('type') == 'string':
                        log_parts.append(arg.get('value', ''))
                    elif arg.get('type') == 'object':
                        log_parts.append(f"<{arg.get('className', 'Object')}>")
                    else:
                        log_parts.append(str(arg.get('value', '')))

                log_text = ' '.join(log_parts)

                # Filtrer les logs pertinents
                keywords = ['memory', 'banner', 'handlememorybanner', 'ws:memory', 'chunks', 'ltm', 'stm']
                if any(kw in log_text.lower() for kw in keywords):
                    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                    prefix = {'log': '[LOG]', 'warn': '[WARN]', 'error': '[ERROR]', 'info': '[INFO]'}.get(log_type, '[LOG]')
                    print(f"[{timestamp}] {prefix} {log_text}")

asyncio.run(listen_memory_events())
"@

    $script | python -
}

function Invoke-CheckState {
    Write-Info "Vérification de l'état du frontend..."

    $wsUrl = Get-ChromeDebugURL
    if (-not $wsUrl) { exit 1 }

    $script = @"
import asyncio
import websockets
import json

async def check_state():
    uri = "$wsUrl"

    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
        await ws.recv()

        cmd = '''
const report = {
    timestamp: new Date().toISOString(),
    eventBus: typeof window.eventBus !== 'undefined',
    chatModule: typeof window.chatModule !== 'undefined',
    state: typeof window.state !== 'undefined',
    handlers: window.chatModule?._H ? Object.keys(window.chatModule._H) : [],
    currentAgent: window.state?.get('chat.currentAgentId'),
    messages: {},
    memoryBanner: window.state?.get('chat.memoryBannerAt')
};

if (window.state) {
    const msgs = window.state.get('chat.messages') || {};
    for (const [key, val] of Object.entries(msgs)) {
        report.messages[key] = Array.isArray(val) ? val.length : 0;
    }
}

JSON.stringify(report, null, 2);
'''

        await ws.send(json.dumps({
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {"expression": cmd, "returnByValue": True}
        }))

        response = await ws.recv()
        data = json.loads(response)

        if 'result' in data and 'value' in data['result']:
            print("[OK] Etat du frontend:")
            print(data['result']['value'])
        else:
            print("[ERROR] Erreur:", json.dumps(data, indent=2))

asyncio.run(check_state())
"@

    $script | python -
}

function Invoke-EvalJS {
    param([string]$jsCode)

    if (-not $jsCode) {
        Write-Error "Aucune expression JavaScript fournie"
        Write-Info "Usage: debug-frontend.ps1 eval 'console.log(window.state)'"
        exit 1
    }

    Write-Info "Exécution de JavaScript dans la console..."

    $wsUrl = Get-ChromeDebugURL
    if (-not $wsUrl) { exit 1 }

    $script = @"
import asyncio
import websockets
import json

async def eval_js():
    uri = "$wsUrl"

    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
        await ws.recv()

        await ws.send(json.dumps({
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {
                "expression": '''$jsCode''',
                "returnByValue": True
            }
        }))

        response = await ws.recv()
        data = json.loads(response)

        print(json.dumps(data, indent=2))

asyncio.run(eval_js())
"@

    $script | python -
}

# ========== MAIN ==========

Write-Host ""
Write-Host "🔧 DEBUG FRONTEND - Emergence V8" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

switch ($Action) {
    "help" {
        Show-Help
    }
    "listen" {
        Invoke-ListenMemoryEvents
    }
    "check" {
        Invoke-CheckState
    }
    "eval" {
        Invoke-EvalJS -jsCode $Expression
    }
    default {
        Write-Error "Action inconnue: $Action"
        Show-Help
        exit 1
    }
}
