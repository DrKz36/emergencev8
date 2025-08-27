param(
  [string]$WsHost   = "127.0.0.1",
  [int]   $Port     = 8000,
  [string]$UserId   = "FG",
  [string]$AgentId  = "anima",
  [string]$MsgType  = "ws:chat_send"
)

# --- WS SessionId guard (autogen) ---
if (-not (Get-Variable -Name SessionId -Scope 0 -ErrorAction SilentlyContinue)) {
  Set-Variable -Name SessionId -Value ([guid]::NewGuid().ToString()) -Scope 0
}
# --- end guard ---

try { [void][System.Net.WebSockets.ClientWebSocket]::new() } catch {
  try { Add-Type -AssemblyName 'System.Net.WebSockets.Client' } catch { }
}

$ub = [System.UriBuilder]::new()
$ub.Scheme='ws'; $ub.Host=$WsHost; $ub.Port=$Port; $ub.Path="/ws/$SessionId"; $ub.Query="user_id=$UserId"
$uri = $ub.Uri
Write-Host ">> Connecting to $($uri.AbsoluteUri)"

$ws  = [System.Net.WebSockets.ClientWebSocket]::new()
$ws.Options.KeepAliveInterval = [TimeSpan]::FromSeconds(5)
try { $ws.ConnectAsync($uri, [Threading.CancellationToken]::None).Wait() } catch { Write-Error "Connect failed: $($_.Exception.Message)"; return }
if ($ws.State -ne [System.Net.WebSockets.WebSocketState]::Open) { Write-Error "Handshake failed. WS state=$($ws.State)"; return }

function Send-WS([string]$txt) {
  $env = @{ type=$MsgType; payload=@{ use_rag=$false; agent_id=$AgentId; text=$txt } } | ConvertTo-Json -Compress
  Write-Host ">> Send: $env"
  $bytes = [Text.Encoding]::UTF8.GetBytes($env)
  $ws.SendAsync([System.ArraySegment[byte]]::new($bytes), [System.Net.WebSockets.WebSocketMessageType]::Text, $true, [Threading.CancellationToken]::None).Wait()
}

Send-WS "Msg 1: contexte."
Start-Sleep -Milliseconds 200
Send-WS "Msg 2: approfondis."
Start-Sleep -Milliseconds 200
Send-WS "Msg 3: synthèse ?"

$buffer = New-Object byte[] 16384
$ends   = 0
while ($ws.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
  try {
    $recvCts = [Threading.CancellationTokenSource]::new(15000)
    $segIn   = [System.ArraySegment[byte]]::new($buffer)
    $result  = $ws.ReceiveAsync($segIn, $recvCts.Token).GetAwaiter().GetResult()
    if ($result.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) { break }
    if ($result.Count -gt 0) {
      $msg  = [Text.Encoding]::UTF8.GetString($buffer, 0, $result.Count)
      Write-Host "RECV: $msg"
      try {
        $obj  = $msg | ConvertFrom-Json -ErrorAction Stop
        if ($obj.type -eq 'ws:chat_stream_end') { $ends++ ; if ($ends -ge 1) { break } } # 1 fin suffit pour le smoke
        if ($obj.type -eq 'ws:error') { break }
      } catch { }
    }
  } catch [System.OperationCanceledException] { Write-Warning "Receive timeout"; break } catch { Write-Warning $_; break }
}

try { $ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "done", [Threading.CancellationToken]::None).Wait() } catch { }
Write-Host ">> Done. WS State: $($ws.State) | Ends=$ends"
