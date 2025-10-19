# quick-debug.ps1
# Helper rapide pour debug frontend - utilisé par Claude Code
# Usage interne uniquement

param(
    [Parameter(Position=0)]
    [ValidateSet("check", "listen", "errors")]
    [string]$Mode = "check"
)

$ErrorActionPreference = "Stop"

function Quick-Check {
    Write-Host "[DEBUG] Quick check frontend..." -ForegroundColor Cyan

    # Récupère l'URL de debug
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:9222/json" -Method Get -ErrorAction Stop
        $page = $response | Where-Object { $_.url -like "*localhost:5173*" } | Select-Object -First 1

        if (-not $page) {
            Write-Host "❌ Aucune page Emergence sur localhost:5173" -ForegroundColor Red
            return
        }

        $wsUrl = $page.webSocketDebuggerUrl

        # Script Python inline pour check rapide
        $script = @"
import asyncio
import websockets
import json
import sys

async def quick_check():
    uri = "$wsUrl"

    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
        await ws.recv()

        cmd = '''
const report = {
    timestamp: new Date().toISOString(),
    modules: {
        eventBus: typeof window.eventBus !== 'undefined',
        chatModule: typeof window.chatModule !== 'undefined',
        state: typeof window.state !== 'undefined'
    },
    currentAgent: window.state?.get('chat.currentAgentId') || 'none',
    messageBuckets: {},
    memoryBannerAt: window.state?.get('chat.memoryBannerAt') || null
};

if (window.state) {
    const msgs = window.state.get('chat.messages') || {};
    for (const [key, val] of Object.entries(msgs)) {
        report.messageBuckets[key] = Array.isArray(val) ? val.length : 0;
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
            print(data['result']['value'])
        else:
            print(json.dumps(data, indent=2))

asyncio.run(quick_check())
"@

        $output = $script | python - 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ État frontend:" -ForegroundColor Green
            Write-Host $output
        } else {
            Write-Host "❌ Erreur Python:" -ForegroundColor Red
            Write-Host $output
        }

    } catch {
        Write-Host "❌ Chrome DevTools non accessible sur localhost:9222" -ForegroundColor Red
        Write-Host "Assure-toi que Chrome tourne avec --remote-debugging-port=9222" -ForegroundColor Yellow
    }
}

function Quick-Listen {
    Write-Host "[DEBUG] Listening to console (15s timeout)..." -ForegroundColor Cyan

    try {
        $response = Invoke-RestMethod -Uri "http://localhost:9222/json" -Method Get -ErrorAction Stop
        $page = $response | Where-Object { $_.url -like "*localhost:5173*" } | Select-Object -First 1

        if (-not $page) {
            Write-Host "❌ Aucune page Emergence" -ForegroundColor Red
            return
        }

        $wsUrl = $page.webSocketDebuggerUrl

        $script = @"
import asyncio
import websockets
import json
from datetime import datetime

async def listen():
    uri = "$wsUrl"

    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
        await ws.recv()
        await ws.send(json.dumps({"id": 2, "method": "Console.enable"}))
        await ws.recv()

        print("Listening for 15s (memory, banner, error keywords)...")

        async def timeout_listener():
            await asyncio.sleep(15)
            return "TIMEOUT"

        listener_task = asyncio.create_task(timeout_listener())

        while not listener_task.done():
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=0.5)
                data = json.loads(msg)

                if data.get('method') == 'Runtime.consoleAPICalled':
                    params = data.get('params', {})
                    log_type = params.get('type', 'log')
                    args = params.get('args', [])

                    log_parts = []
                    for arg in args:
                        if arg.get('type') == 'string':
                            log_parts.append(arg.get('value', ''))
                        elif arg.get('type') == 'object':
                            log_parts.append(f"<{arg.get('className', 'Object')}>")
                        else:
                            log_parts.append(str(arg.get('value', '')))

                    log_text = ' '.join(log_parts)

                    keywords = ['memory', 'banner', 'error', 'failed', 'warning']
                    if any(kw in log_text.lower() for kw in keywords):
                        ts = datetime.now().strftime('%H:%M:%S')
                        print(f"[{ts}] [{log_type.upper()}] {log_text}")

            except asyncio.TimeoutError:
                continue

asyncio.run(listen())
"@

        $script | python -

    } catch {
        Write-Host "❌ Erreur: $_" -ForegroundColor Red
    }
}

function Quick-Errors {
    Write-Host "[DEBUG] Checking for errors..." -ForegroundColor Cyan

    try {
        $response = Invoke-RestMethod -Uri "http://localhost:9222/json" -Method Get -ErrorAction Stop
        $page = $response | Where-Object { $_.url -like "*localhost:5173*" } | Select-Object -First 1

        if (-not $page) {
            Write-Host "❌ Aucune page" -ForegroundColor Red
            return
        }

        $wsUrl = $page.webSocketDebuggerUrl

        $script = @"
import asyncio
import websockets
import json

async def check_errors():
    uri = "$wsUrl"

    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
        await ws.recv()

        cmd = '''
const errors = [];
const origError = console.error;
const origWarn = console.warn;

// Collect recent errors from memory if available
if (window._recentErrors) {
    errors.push(...window._recentErrors);
}

JSON.stringify({
    hasErrors: errors.length > 0,
    count: errors.length,
    errors: errors.slice(-5)
}, null, 2);
'''

        await ws.send(json.dumps({
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {"expression": cmd, "returnByValue": True}
        }))

        response = await ws.recv()
        data = json.loads(response)

        if 'result' in data and 'value' in data['result']:
            result = json.loads(data['result']['value'])
            if result['hasErrors']:
                print(f"Found {result['count']} errors:")
                print(json.dumps(result['errors'], indent=2))
            else:
                print("No errors detected")

asyncio.run(check_errors())
"@

        $script | python -

    } catch {
        Write-Host "❌ Erreur: $_" -ForegroundColor Red
    }
}

# Main
switch ($Mode) {
    "check" { Quick-Check }
    "listen" { Quick-Listen }
    "errors" { Quick-Errors }
}
