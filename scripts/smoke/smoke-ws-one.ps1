param(
  [string]$WsHost   = "127.0.0.1",
  [int]   $Port     = 8000,
  [string]$UserId   = "FG",
  [string]$AgentId  = "anima",
  [string]$Text     = "Ping WS (no RAG).",
  [string]$MsgType  = "ws:chat_send"  # si backend renvoie encore 'incomplet', essaie: chat:send
)

# --- WS SessionId guard (autogen) ---
if (-not (Get-Variable -Name SessionId -Scope 0 -ErrorAction SilentlyContinue)) {
  Set-Variable -Name SessionId -Value ([guid]::NewGuid().ToString()) -Scope 0
}
# --- end guard ---

try { [void][System.Net.WebSockets.ClientWebSocket]::new() } catch {
  try { Add-Type -AssemblyName 'System.Net.WebSockets.Client' } catch { }
}

# URI robuste + ?user_id=
$ub = [System.UriBuilder]::new()
$ub.Scheme='ws'; $ub.Host=$WsHost; $ub.Port=$Port; $ub.Path="/ws/$SessionId"; $ub.Query="user_id=$UserId"
$uri = $ub.Uri
Write-Host ">> Connecting to $($uri.AbsoluteUri)"

$ws  = [System.Net.WebSockets.ClientWebSocket]::new()
$ws.Options.KeepAliveInterval = [TimeSpan]::FromSeconds(5)

# Handshake
try { $ws.ConnectAsync($uri, [Threading.CancellationToken]::None).Wait() } catch {
  Write-Error "Connect failed: $($_.Exception.Message)"; return
}
if ($ws.State -ne [System.Net.WebSockets.WebSocketState]::Open) {
  Write-Error "Handshake failed. WS state=$($ws.State)"; return
}

# ENVELOPPE attendue par le backend
$envelope = @{
  type    = $MsgType
  payload = @{
    use_rag  = $false
    agent_id = $AgentId
    text     = $Text
  }
} | ConvertTo-Json -Compress

Write-Host ">> Sending envelope: $envelope"
$bytesOut = [Text.Encoding]::UTF8.GetBytes($envelope)
$segOut   = [System.ArraySegment[byte]]::new($bytesOut)
$ws.SendAsync($segOut, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, [Threading.CancellationToken]::None).Wait()

# Réception sûre : timeout et sortie sur 'ws:chat_stream_end' ou 'ws:error'
$buffer = New-Object byte[] 16384
$endSeen = $false
while ($ws.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
  try {
    $recvCts = [Threading.CancellationTokenSource]::new(15000)  # 15 s max
    $segIn   = [System.ArraySegment[byte]]::new($buffer)
    $result  = $ws.ReceiveAsync($segIn, $recvCts.Token).GetAwaiter().GetResult()
    if ($result.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) { break }
    if ($result.Count -gt 0) {
      $msg = [Text.Encoding]::UTF8.GetString($buffer, 0, $result.Count)
      Write-Host "RECV: $msg"
      try {
        $obj  = $msg | ConvertFrom-Json -ErrorAction Stop
        $type = $obj.type
        if ($type -eq 'ws:chat_stream_end' -or $type -eq 'ws:error') { $endSeen = $true; break }
      } catch { }
    }
  } catch [System.OperationCanceledException] {
    Write-Warning "Receive timeout (no more data)"; break
  } catch {
    Write-Warning "Receive stopped: $($_.Exception.GetType().Name) - $($_.Exception.Message)"; break
  }
}

try { $ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "done", [Threading.CancellationToken]::None).Wait() } catch { }
Write-Host ">> Done. WS State: $($ws.State) | EndSeen=$endSeen"
