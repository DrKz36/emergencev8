#requires -Version 5.1
Param(
  [string]$WssBase = "wss://emergence-app.ch", # FQDN Cloud Run / LB
  [string]$UserId  = "FG",
  [string]$AgentId = "anima",
  [string]$Text    = "Hello from WSS (Cloud Run).",
  [string]$IdTokenPath = ".\id_token.txt",
  [int]$TotalSeconds = 20
)

Add-Type -AssemblyName System.Net.WebSockets
if (-not (Test-Path $IdTokenPath)) { throw "ID token introuvable: $IdTokenPath" }
$token = (Get-Content $IdTokenPath -Raw).Trim()

$uri = [Uri]("$WssBase/ws?user_id=" + [Uri]::EscapeDataString($UserId))
$ws  = [System.Net.WebSockets.ClientWebSocket]::new()
$ws.Options.SetRequestHeader("Authorization","Bearer $token")

Write-Host ">> Connecting to $($uri.AbsoluteUri) with Authorization: Bearer <token>"
$ws.ConnectAsync($uri, [Threading.CancellationToken]::None).Wait()

$payload = @{ agent_id = $AgentId; use_rag = $false; text = $Text } | ConvertTo-Json -Compress
$bytes   = [System.Text.Encoding]::UTF8.GetBytes($payload)
$segOut  = [ArraySegment[byte]]::new($bytes)
$ws.SendAsync($segOut, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, [Threading.CancellationToken]::None).Wait()

$deadline = [DateTime]::UtcNow.AddSeconds($TotalSeconds)
$buffer   = New-Object byte[] 8192
while ([DateTime]::UtcNow -lt $deadline -and $ws.State -eq 'Open') {
  $seg = [ArraySegment[byte]]::new($buffer)
  $t = $ws.ReceiveAsync($seg,[Threading.CancellationToken]::None)
  if (-not $t.Wait(1000)) { continue }
  $res = $t.Result
  if ($res.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) { break }
  $txt = [System.Text.Encoding]::UTF8.GetString($buffer,0,$res.Count)
  $stamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss.fff")
  Write-Host "[$stamp] $txt"
}
if ($ws.State -eq 'Open') { $ws.Dispose() }
