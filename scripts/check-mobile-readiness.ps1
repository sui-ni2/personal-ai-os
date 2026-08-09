[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateNotNullOrEmpty()]
    [string]$BaseUrl,

    [switch]$AllowInsecureLocalhost,

    [switch]$RequireRealtimeConfigured
)

$ErrorActionPreference = "Stop"

try {
    $baseUri = [Uri]($BaseUrl.TrimEnd("/") + "/")
} catch {
    throw "BaseUrl must be an absolute HTTP or HTTPS URL."
}

if (-not $baseUri.IsAbsoluteUri -or $baseUri.Scheme -notin @("http", "https")) {
    throw "BaseUrl must be an absolute HTTP or HTTPS URL."
}

$isLocalhost = $baseUri.Host -in @("localhost", "127.0.0.1", "::1")
if ($baseUri.Scheme -ne "https" -and -not ($AllowInsecureLocalhost -and $isLocalhost)) {
    throw "A phone deployment must use HTTPS. Use -AllowInsecureLocalhost only for local production checks."
}

function Get-AppResponse {
    param([Parameter(Mandatory)][string]$Path)
    $uri = [Uri]::new($baseUri, $Path.TrimStart("/"))
    $response = Invoke-WebRequest -UseBasicParsing -Uri $uri -TimeoutSec 15
    if ($response.StatusCode -ne 200) {
        throw "$Path returned HTTP $($response.StatusCode)."
    }
    return $response
}

function Get-ResponseText {
    param([Parameter(Mandatory)]$Response)
    if ($Response.Content -is [byte[]]) {
        return [Text.Encoding]::UTF8.GetString($Response.Content)
    }
    return [string]$Response.Content
}

$homeResponse = Get-AppResponse -Path "/"
$chat = Get-AppResponse -Path "/chat?new=1&mode=live"
$manifestResponse = Get-AppResponse -Path "/manifest.webmanifest"
$serviceWorker = Get-AppResponse -Path "/sw.js"
$realtimeResponse = Get-AppResponse -Path "/api/realtime/status"

$manifest = (Get-ResponseText -Response $manifestResponse) | ConvertFrom-Json
$realtime = (Get-ResponseText -Response $realtimeResponse) | ConvertFrom-Json
$serviceWorkerText = Get-ResponseText -Response $serviceWorker
$iconSizes = @($manifest.icons | ForEach-Object { $_.sizes })

if ($manifest.display -ne "standalone" -or $manifest.start_url -ne "/") {
    throw "The web manifest is not configured as a standalone root-scoped app."
}
if ("192x192" -notin $iconSizes -or "512x512" -notin $iconSizes) {
    throw "The web manifest must expose 192x192 and 512x512 app icons."
}
if ($serviceWorkerText -notmatch 'url\.pathname\.startsWith\("/api/"\)') {
    throw "The service worker does not visibly exclude API requests from its cache strategy."
}
if ($realtime.transport -ne "webrtc" -or -not $realtime.model -or -not $realtime.transcription_model) {
    throw "The Realtime status contract is incomplete."
}
if ($RequireRealtimeConfigured -and -not $realtime.configured) {
    throw "Realtime is not configured on this deployment."
}

[pscustomobject]@{
    BaseUrl = $baseUri.AbsoluteUri.TrimEnd("/")
    SecureContext = if ($baseUri.Scheme -eq "https") { "ready" } else { "local-only" }
    Home = $homeResponse.StatusCode
    LiveRoute = $chat.StatusCode
    Manifest = "standalone"
    ServiceWorker = "api-excluded"
    Realtime = if ($realtime.configured) { "configured" } else { "not-configured" }
    RealtimeProvider = $realtime.provider
    RealtimeModel = $realtime.model
} | Format-List
