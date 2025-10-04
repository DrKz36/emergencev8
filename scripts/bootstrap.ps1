#!/usr/bin/env pwsh
[CmdletBinding()]
param(
    [string]$RemoteName = "origin",
    [string]$RemoteUrl,
    [switch]$SkipStart,
    [string]$StartScript = "start"
)

$ErrorActionPreference = "Stop"
$DefaultRemoteUrl = "https://github.com/DrKz36/emergencev8.git"

if (-not $RemoteUrl) {
    $RemoteUrl = $DefaultRemoteUrl
}

if (-not (Test-Path -Path ".git")) {
    throw "This script must run from the repository root."
}

try {
    git rev-parse --is-inside-work-tree | Out-Null
} catch {
    throw "Current directory is not a git repository."
}

$remoteExists = $false
try {
    $remotes = git remote
    $remoteExists = $remotes -contains $RemoteName
} catch {
    throw "Unable to list git remotes. Ensure git is installed."
}

if (-not $remoteExists) {
    git remote add $RemoteName $RemoteUrl
    Write-Host "Added remote '$RemoteName' -> $RemoteUrl"
} else {
    $currentUrl = git remote get-url $RemoteName
    if ($currentUrl -ne $RemoteUrl) {
        git remote set-url $RemoteName $RemoteUrl
        Write-Host "Updated remote '$RemoteName' -> $RemoteUrl"
    }
}

if (-not $SkipStart) {
    Write-Host "Starting npm script '$StartScript'..."
    & npm run $StartScript
}
