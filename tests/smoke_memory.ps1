<# 
  ÉMERGENCE — Smoke mémoire & WS (P1.5)
  tests\smoke_memory.ps1

  Ce script vérifie :
    1) REST mémoire : /api/memory/tend-garden (vide, {}, JSON invalide) => 200
       + /api/memory/status => last_run progresse
    2) WebSocket : handshake JWT, envoi chat.message, réception des frames :
       - ws:session_established (ou ws:auth_required)
       - ws:chat_stream_start / ws:chat_stream_chunk / ws:chat_stream_end
       - ws:model_info | ws:model_fallback (informative)
       - ws:memory_banner (OBLIGATOIRE)
       - ws:rag_status (facultatif ici, use_rag:false)

  Contrat WS (type + payload, événements namespacés ws:*) aligné sur 30-Contracts.md (V3.2).
  Usage:
    powershell -ExecutionPolicy Bypass -File tests\smoke_memory.ps1 -BaseUrl http://127.0.0.1:8000
    powershell -ExecutionPolicy Bypass -File tests\smoke_memory.ps1 -BaseUrl $env:RUNURL -IdToken (Get-Content .\id_token.txt)
#>

param(
  [Parameter(Mandatory=$true)][string]$BaseUrl,         # ex: http://127.0.0.1:8000  ou  https://<run>.run.app
  [string]$IdToken = ""                                 # ID token (GIS). Si vide: WS en mode invité doit être refusé (auth_required)
)

$ErrorActionPreference = "Stop"

### ---------- Utils ----------

function Write-Section($t){ Write-Host "`n=== $t ===" -ForegroundColor Cyan }
function OK($t){ Write-Host "✔ $t" -ForegroundColor Green }
function INFO($t){ Write-Host "• $t" -ForegroundColor Gray }
function FAIL($t){ Write-Host "✖ $t" -ForegroundColor Red }

function Assert-Equal($a,$b,$msg){
  if($a -ne $b){ throw "ASSERT FAIL: $msg (got=$a expected=$b)" }
}
function Assert-True($cond,$msg){
  if(-not $cond){ throw "ASSERT FAIL: $msg" }
}

function Invoke-Req($method, $path, $body = $null, $ctype = $null){
  $uri = "$BaseUrl$path"
  $headers = @{}
  if ($IdToken -ne "") { $headers["Authorization"] = "Bearer $IdToken" }
  if ($ctype) { $headers["Content-Type"] = $ctype }

  try{
    if ($null -ne $body){
      return Invoke-WebRequest -Method $method -Uri $uri -Headers $headers -Body $body -TimeoutSec 30 -UseBasicParsing
    } else {
      return Invoke-WebRequest -Method $method -Uri $uri -Headers $headers -TimeoutSec 30 -UseBasicParsing
    }
  } catch {
    if ($_.Exception.Response -ne $null){ return $_.Exception.Response }
    throw
  }
}

function Parse-Json($text){
  try{ return $text | ConvertFrom-Json }catch{ return $null }
}

### ---------- 0) Health ----------

Write-Section "Health"
$health = Invoke-Req -method GET -path "/api/health"
Assert-True ($health.StatusCode -in 200,204) "/api/health doit répondre 200/204"
OK "/api/health -> $($health.StatusCode)"

### ---------- Helpers mémoire ----------

function Get-MemStatus(){
  $resp = Invoke-Req -method GET -path "/api/memory/status"
  Assert-Equal $resp.StatusCode 200 "/api/memory/status doit répondre 200"
  return Parse-Json $resp.Content
}

### ---------- 1) REST mémoire ----------

Write-Section "Mémoire (REST)"
$st1 = Get-MemStatus
$lr1 = $null
if($st1 -and $st1.last_run){ $lr1 = Get-Date $st1.last_run }
INFO ("last_run(avant) = " + $(if($lr1){$lr1.ToString("o")}else{"—"}))

# POST vide
$r1 = Invoke-Req -method POST -path "/api/memory/tend-garden"
Assert-Equal $r1.StatusCode 200 "tend-garden (vide) doit répondre 200"
OK "POST /tend-garden (vide) -> 200"

# POST {}
$r2 = Invoke-Req -method POST -path "/api/memory/tend-garden" -body "{}" -ctype "application/json"
Assert-Equal $r2.StatusCode 200 "tend-garden ({}) doit répondre 200"
OK "POST /tend-garden ({}) -> 200"

# POST JSON invalide
$r3 = Invoke-Req -method POST -path "/api/memory/tend-garden" -body "{not:json}" -ctype "application/json"
Assert-Equal $r3.StatusCode 200 "tend-garden (JSON invalide) doit répondre 200"
OK "POST /tend-garden (JSON invalide) -> 200"

Start-Sleep -Seconds 1
$st2 = Get-MemStatus
$lr2 = $null
if($st2 -and $st2.last_run){ $lr2 = Get-Date $st2.last_run }
INFO ("last_run(après) = " + $(if($lr2){$lr2.ToString("o")}else{"—"}))

if($lr1 -and $lr2){
  Assert-True ($lr2 -ge $lr1) "last_run doit être >= avant"
}else{
  Assert-True ($st2 -ne $null) "status doit renvoyer un JSON parseable"
}
OK "REST mémoire OK (anti-422 + status)"

### ---------- 2) WebSocket (contrat frames type/payload) ----------

Write-Section "WebSocket (chat + mémoire_banner)"

# Construction de l’URL WS
# Supporte http(s) -> ws(s)
$wsUrl = $BaseUrl -replace '^http','ws'
# Ajoute un UUID aléatoire au path /ws/{uuid}
$wsId = [guid]::NewGuid().ToString()
if($wsUrl.TrimEnd('/').ToLower().EndsWith('/api')){
  # Si backend préfixe /api, on remonte d’un cran pour /ws/
  $wsBase = $wsUrl -replace '/api$',''
  $wsEndpoint = "$wsBase/ws/$wsId"
}else{
  $wsEndpoint = "$wsUrl/ws/$wsId"
}
INFO "WS endpoint: $wsEndpoint"

# Ouvre ClientWebSocket
$cs = [System.Net.WebSockets.ClientWebSocket]::new()

# Subprotocol 'jwt' si on a un token (contrat côté serveur)
if($IdToken -ne ""){
  $cs.Options.AddSubProtocol("jwt")
  $cs.Options.SetRequestHeader("Authorization", "Bearer $IdToken")
}

# Timeout de handshake et lecture
$cts = New-Object System.Threading.CancellationTokenSource
$cts.CancelAfter(15000) # 15s

try{
  $uri = [System.Uri]$wsEndpoint
  $task = $cs.ConnectAsync($uri, $cts.Token)
  $task.Wait()
  Assert-Equal $cs.State ([System.Net.WebSockets.WebSocketState]::Open) "WebSocket doit être ouvert"
  OK "WS connecté"
}catch{
  throw "Échec connexion WS: $($_.Exception.Message)"
}

# Buffer lecture
$buffer = New-Object Byte[] 65536

function Read-Frame([int]$timeoutMs = 10000){
  $ctsRead = New-Object System.Threading.CancellationTokenSource
  $ctsRead.CancelAfter($timeoutMs)
  $segment = New-Object System.ArraySegment[byte] -ArgumentList (,$buffer)
  $sb = New-Object System.Text.StringBuilder
  do{
    $res = $cs.ReceiveAsync($segment, $ctsRead.Token).GetAwaiter().GetResult()
    if($res.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close){
      throw "WS fermé par le serveur"
    }
    $chunk = [System.Text.Encoding]::UTF8.GetString($buffer, 0, $res.Count)
    [void]$sb.Append($chunk)
  } while(-not $res.EndOfMessage)
  return $sb.ToString()
}

function Send-Frame($obj){
  $json = ($obj | ConvertTo-Json -Depth 10 -Compress)
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
  $segment = New-Object System.ArraySegment[byte] -ArgumentList (,$bytes)
  $cs.SendAsync($segment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, [Threading.CancellationToken]::None).GetAwaiter().GetResult()
}

# Attendus
$gotEstablished = $false
$gotAuthRequired = $false
$gotStart = $false
$gotChunk = $false
$gotEnd = $false
$gotModelInfoOrFallback = $false
$gotMemoryBanner = $false

# Lecture initiale: session_established / auth_required
$first = Read-Frame 10000
$firstObj = Parse-Json $first
Assert-True ($firstObj -ne $null) "Frame 1 JSON invalide"
Assert-True ($firstObj.type -ne $null) "Frame 1 doit avoir un champ 'type'"

switch ($firstObj.type){
  "ws:session_established" { $gotEstablished = $true; OK "Réception: ws:session_established" }
  "ws:auth_required"       { $gotAuthRequired = $true; OK "Réception: ws:auth_required (mode protégé)" }
  default { FAIL "Frame inattendue: $($firstObj.type)"; throw "Contrat WS: frame d'ouverture invalide" }
}

# Si auth_required alors il faut un IdToken
if($gotAuthRequired -and $IdToken -eq ""){
  throw "WS protégé: fournis -IdToken pour passer le gating JWT"
}

# Si auth ok, on envoie un chat.message minimal (RAG OFF)
# Contrat client -> serveur (type + payload)
# payload: { text, agent_id, use_rag }
$chat = @{
  type = "chat.message"
  payload = @{
    text = "Smoke test mémoire — vérifier ws:memory_banner"
    agent_id = "anima"
    use_rag = $false
  }
}
Send-Frame $chat
OK "Envoi: chat.message (anima, use_rag=false)"

# On collecte les frames pendant un court laps
$deadline = (Get-Date).AddSeconds(15)
while((Get-Date) -lt $deadline -and (-not ($gotStart -and $gotEnd -and $gotMemoryBanner))){
  $raw = Read-Frame 5000
  $obj = Parse-Json $raw
  if(-not $obj){ continue }
  $t = "$($obj.type)"

  switch ($t){
    "ws:model_info"      { $gotModelInfoOrFallback = $true; INFO "ws:model_info: provider=$($obj.payload.provider) model=$($obj.payload.model)" }
    "ws:model_fallback"  { $gotModelInfoOrFallback = $true; INFO "ws:model_fallback: $($obj.payload.from_provider) -> $($obj.payload.to_provider)" }
    "ws:chat_stream_start" { $gotStart = $true; OK "ws:chat_stream_start" }
    "ws:chat_stream_chunk" { if(-not $gotChunk){ $gotChunk = $true; OK "ws:chat_stream_chunk (1er)" } }
    "ws:chat_stream_end"   { $gotEnd = $true; OK "ws:chat_stream_end" }
    "ws:memory_banner"     {
        # payload attendu: { agent_id, has_stm, ltm_items, injected_into_prompt }
        $gotMemoryBanner = $true
        $p = $obj.payload
        OK ("ws:memory_banner (agent="+$p.agent_id+"; has_stm="+$p.has_stm+"; ltm_items="+$p.ltm_items+"; injected="+$p.injected_into_prompt+")")
      }
    "ws:rag_status"        { INFO "ws:rag_status: $($obj.payload.status)" }
    "ws:error"             { FAIL ("ws:error: "+$obj.payload.message); throw "Erreur WS émise par le serveur" }
    default                { INFO "Frame ignorée: $t" }
  }
}

# Assertions finales WS
Assert-True $gotStart "ws:chat_stream_start non reçu"
Assert-True $gotEnd "ws:chat_stream_end non reçu"
Assert-True $gotMemoryBanner "ws:memory_banner non reçu (exigé par contrat mémoire)"

try{
  $cs.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "done", [Threading.CancellationToken]::None).GetAwaiter().GetResult()
}catch{}

OK "`nSMOKE OK — REST + WS (mémoire opérationnelle)"
exit 0
