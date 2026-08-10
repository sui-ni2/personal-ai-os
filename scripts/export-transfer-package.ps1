[CmdletBinding()]
param(
    [string]$OutputDirectory = "transfer-packages"
)

$ErrorActionPreference = "Stop"
$repoRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$outputRoot = [IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDirectory))
if (-not $outputRoot.StartsWith($repoRoot + [IO.Path]::DirectorySeparatorChar)) {
    throw "OutputDirectory must stay inside the Personal AI OS repository."
}

Set-Location -LiteralPath $repoRoot
if (git status --porcelain) {
    throw "Commit or otherwise clear the Git working tree before exporting a transfer package."
}

$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "The project virtual environment is missing."
}

New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null
$timestamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")
$archivePath = Join-Path $outputRoot "personal-ai-os-transfer-$timestamp.zip"
$temporaryRoot = [IO.Path]::GetFullPath((Join-Path ([IO.Path]::GetTempPath()) ("personal-ai-os-transfer-" + [Guid]::NewGuid().ToString("N"))))
$systemTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
if (-not $temporaryRoot.StartsWith($systemTemp)) {
    throw "Unsafe temporary path."
}

try {
    $sourceZip = Join-Path $temporaryRoot "source.zip"
    $packageRoot = Join-Path $temporaryRoot "personal-ai-os"
    New-Item -ItemType Directory -Force -Path $temporaryRoot | Out-Null
    git archive --format=zip --output=$sourceZip HEAD
    if ($LASTEXITCODE -ne 0) { throw "git archive failed." }
    Expand-Archive -LiteralPath $sourceZip -DestinationPath $packageRoot

    $dataBackupDirectory = Join-Path $packageRoot "transfer-data"
    & $python (Join-Path $repoRoot "scripts\backup-data.py") --data-dir (Join-Path $repoRoot "data") --output-dir $dataBackupDirectory | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Data backup failed." }

    Compress-Archive -LiteralPath $packageRoot -DestinationPath $archivePath -CompressionLevel Optimal
    $hash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash
    [pscustomobject]@{
        Archive = $archivePath
        SHA256 = $hash
        Commit = (git rev-parse HEAD)
    } | Format-List
} finally {
    if (Test-Path -LiteralPath $temporaryRoot) {
        $resolvedTemporary = [IO.Path]::GetFullPath($temporaryRoot)
        if (-not $resolvedTemporary.StartsWith($systemTemp)) {
            throw "Refusing to remove an unsafe temporary path."
        }
        Remove-Item -LiteralPath $resolvedTemporary -Recurse -Force
    }
}
