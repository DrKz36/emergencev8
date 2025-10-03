Set-StrictMode -Version Latest

function Resolve-SmokeBaseUrl {
    param([string]$BaseUrl)

    $candidate = $BaseUrl
    if ([string]::IsNullOrWhiteSpace($candidate)) {
        $candidate = 'http://127.0.0.1:8000'
    }

    $candidate = $candidate.Trim()
    if ($candidate -notmatch '^[a-z]+://') {
        $candidate = "http://$candidate"
    }

    while ($candidate.Length -gt 0 -and $candidate.EndsWith('/')) {
        $candidate = $candidate.Substring(0, $candidate.Length - 1)
    }

    return $candidate
}

function Resolve-SmokeCredentials {
    param(
        [string]$Email,
        [string]$Password
    )

    $emailCandidate = $Email
    if ([string]::IsNullOrWhiteSpace($emailCandidate)) {
        $emailCandidate = $env:EMERGENCE_SMOKE_EMAIL
    }
    if ([string]::IsNullOrWhiteSpace($emailCandidate)) {
        $emailCandidate = $env:EMERGENCE_ADMIN_EMAIL
    }
    if ([string]::IsNullOrWhiteSpace($emailCandidate)) {
        $emailCandidate = 'gonzalefernando@gmail.com'
    }

    $emailCandidate = $emailCandidate.Trim().ToLowerInvariant()

    if (-not $emailCandidate) {
        throw 'Smoke email missing. Provide -SmokeEmail or set EMERGENCE_SMOKE_EMAIL.'
    }

    $passwordCandidate = $Password
    if ([string]::IsNullOrWhiteSpace($passwordCandidate)) {
        $passwordCandidate = $env:EMERGENCE_SMOKE_PASSWORD
    }
    if ([string]::IsNullOrWhiteSpace($passwordCandidate)) {
        $passwordCandidate = $env:EMERGENCE_ADMIN_PASSWORD
    }
    if ([string]::IsNullOrWhiteSpace($passwordCandidate)) {
        $passwordCandidate = 'WinipegMad2015'
    }

    if ([string]::IsNullOrWhiteSpace($passwordCandidate)) {
        throw 'Smoke password missing. Provide -SmokePassword or set EMERGENCE_SMOKE_PASSWORD.'
    }

    return [pscustomobject]@{
        Email    = $emailCandidate
        Password = $passwordCandidate
    }
}

function New-SmokeAuthSession {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$BaseUrl,
        [string]$Email,
        [string]$Password,
        [string]$Source = 'smoke-tests',
        [string]$UserAgent = 'emergence-smoke-tests'
    )

    $resolvedBase = Resolve-SmokeBaseUrl -BaseUrl $BaseUrl
    $creds = Resolve-SmokeCredentials -Email $Email -Password $Password

    $loginUri = "$resolvedBase/api/auth/login"

    $meta = @{
        source    = $Source
        timestamp = (Get-Date).ToUniversalTime().ToString('o')
    }

    if ($UserAgent) {
        $meta.user_agent = $UserAgent
    }

    $payload = @{
        email    = $creds.Email
        password = $creds.Password
        meta     = $meta
    }

    $jsonBody = $payload | ConvertTo-Json -Depth 4

    try {
        $response = Invoke-RestMethod -Uri $loginUri -Method Post -ContentType 'application/json' -Body $jsonBody -TimeoutSec 30
    } catch {
        $message = "Login failed for $($creds.Email) on $loginUri."
        $statusCode = $null
        $statusText = $null
        $responseBody = $null

        $exception = $_.Exception
        $webResponse = $null
        if ($exception -is [System.Net.WebException]) {
            $webResponse = $exception.Response
        } elseif ($exception.PSObject.Properties['Response']) {
            $webResponse = $exception.Response
        }

        if ($webResponse) {
            try { $statusCode = $webResponse.StatusCode.value__ } catch {}
            try { $statusText = $webResponse.StatusDescription } catch {}
            try {
                $stream = $webResponse.GetResponseStream()
                if ($stream) {
                    $reader = New-Object System.IO.StreamReader($stream)
                    $responseBody = $reader.ReadToEnd()
                    $reader.Dispose()
                }
            } catch {}
        }

        if ($statusCode) {
            $message += " HTTP $statusCode"
            if ($statusText) {
                $message += " $statusText"
            }
            $message += '.'
        }
        if ($responseBody) {
            $message += " Response: $responseBody"
        }

        $message += ' Provide valid credentials via -SmokeEmail/-SmokePassword or environment variables EMERGENCE_SMOKE_EMAIL / EMERGENCE_SMOKE_PASSWORD.'
        throw (New-Object System.Exception($message, $exception))
    }

    if (-not $response.token) {
        throw 'Login succeeded but response has no token.'
    }
    if (-not $response.session_id) {
        throw 'Login succeeded but response has no session_id.'
    }

    $headers = @{
        Authorization = "Bearer $($response.token)"
        'X-Session-Id' = $response.session_id
    }

    return [pscustomobject]@{
        BaseUrl   = $resolvedBase
        Email     = $response.email
        UserId    = $response.user_id
        Role      = $response.role
        SessionId = $response.session_id
        Token     = $response.token
        ExpiresAt = $response.expires_at
        Headers   = $headers
    }
}
