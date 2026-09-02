[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory,
    [string]$Version
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$outputRoot = [IO.Path]::GetFullPath($OutputDirectory)
$timestamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")

if (git -C $repoRoot status --porcelain) {
    throw "Refusing to build a distribution from a dirty working tree. Commit or clear only intended changes first."
}
if (-not $Version) {
    $Version = (git -C $repoRoot describe --tags --always).Trim()
}

New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null
$staging = Join-Path $outputRoot ("personal-ai-os-windows-" + $timestamp)
$applicationArchive = Join-Path $staging "application.zip"
$manifestPath = Join-Path $staging "personal-ai-os-release.json"
$packagePath = Join-Path $outputRoot ("personal-ai-os-windows-" + $Version.Replace('/', '-') + ".zip")
New-Item -ItemType Directory -Force -Path $staging | Out-Null

function Get-Sha256 {
    param([string]$Path)
    $native = Get-Command Get-FileHash -ErrorAction SilentlyContinue
    if ($native) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($Path)
    try {
        return ([BitConverter]::ToString($algorithm.ComputeHash($stream))).Replace("-", "").ToLowerInvariant()
    } finally {
        $stream.Dispose()
        $algorithm.Dispose()
    }
}

try {
    git -C $repoRoot archive --format=zip --output=$applicationArchive HEAD
    if ($LASTEXITCODE -ne 0) { throw "git archive failed." }
    $applicationHash = Get-Sha256 -Path $applicationArchive
    $manifest = [ordered]@{
        format = "personal-ai-os-windows-distribution-v1"
        version = $Version
        application_sha256 = $applicationHash
        migration_version = 8
        backup_compatibility = "personal-ai-os-data-backup-v1"
        signing_status = "SIGNING_EXTERNAL_NOT_CONFIGURED"
        created_at = [DateTime]::UtcNow.ToString("o")
        source_commit = (git -C $repoRoot rev-parse HEAD).Trim()
    }
    [IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 4), [Text.UTF8Encoding]::new($false))
    if (Test-Path -LiteralPath $packagePath) { throw "Refusing to overwrite an existing distribution: $packagePath" }
    Compress-Archive -LiteralPath @($applicationArchive, $manifestPath) -DestinationPath $packagePath -CompressionLevel Optimal
    $packageHash = Get-Sha256 -Path $packagePath
    [pscustomobject]@{
        Package = $packagePath
        SHA256 = $packageHash
        Version = $Version
        Signing = "SIGNING_EXTERNAL_NOT_CONFIGURED"
    } | Format-List
} finally {
    if (Test-Path -LiteralPath $staging) {
        Remove-Item -LiteralPath $staging -Recurse -Force
    }
}
