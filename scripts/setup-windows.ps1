param(
    [switch]$CheckOnly,
    [switch]$SkipSmoke
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot

function Assert-LastExitCode {
    param([string]$Step)
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE."
    }
}

if ([System.Environment]::OSVersion.Platform -ne [System.PlatformID]::Win32NT) {
    throw "This bootstrap is for Windows. Use the manual setup instructions on other platforms."
}

$requiredFiles = @(
    ".env.example",
    "requirements-dev.txt",
    "package.json",
    "pnpm-lock.yaml",
    "scripts/release-provider-smoke.py"
)
foreach ($relativePath in $requiredFiles) {
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $relativePath))) {
        throw "Missing required repository file: $relativePath"
    }
}

$pythonCommand = Get-Command py -ErrorAction SilentlyContinue
$pythonPrefix = @()
if ($pythonCommand) {
    $pythonExe = $pythonCommand.Source
    $pythonPrefix = @("-3")
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Python 3.11+ is required. Install Python, reopen the terminal, and run this script again."
    }
    $pythonExe = $pythonCommand.Source
}

$pythonProbeArgs = @() + $pythonPrefix + @(
    "-c",
    "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
)
$pythonVersionText = (& $pythonExe @pythonProbeArgs).Trim()
Assert-LastExitCode "Python version check"
try {
    $pythonVersion = [version]$pythonVersionText
} catch {
    throw "Could not parse Python version: $pythonVersionText"
}
if ($pythonVersion.Major -ne 3 -or $pythonVersion.Minor -lt 11) {
    throw "Python 3.11+ is required; found $pythonVersionText."
}

$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCommand) {
    throw "Node.js 20+ is required. Install Node.js, reopen the terminal, and run this script again."
}
$nodeVersionText = (& $nodeCommand.Source --version).Trim().TrimStart("v")
Assert-LastExitCode "Node.js version check"
try {
    $nodeVersion = [version]$nodeVersionText
} catch {
    throw "Could not parse Node.js version: $nodeVersionText"
}
if ($nodeVersion.Major -lt 20) {
    throw "Node.js 20+ is required; found v$nodeVersionText."
}

$pnpmCommand = Get-Command pnpm -ErrorAction SilentlyContinue
if (-not $pnpmCommand) {
    throw "pnpm 11 is required. Install or activate pnpm, reopen the terminal, and run this script again."
}
$pnpmVersionText = (& $pnpmCommand.Source --version).Trim()
Assert-LastExitCode "pnpm version check"
try {
    $pnpmVersion = [version]$pnpmVersionText
} catch {
    throw "Could not parse pnpm version: $pnpmVersionText"
}
if ($pnpmVersion.Major -ne 11) {
    throw "pnpm 11 is required to match this repository's package-manager line; found $pnpmVersionText."
}
if ($pnpmVersionText -ne "11.16.0") {
    Write-Warning "Repository packageManager is pinned to pnpm 11.16.0; found $pnpmVersionText. Continuing within pnpm 11."
}

Write-Host "[PASS] Windows prerequisites: Python $pythonVersionText, Node.js v$nodeVersionText, pnpm $pnpmVersionText"

if ($CheckOnly) {
    Write-Host "[PASS] Check-only mode completed without changing the working tree or installing dependencies."
    exit 0
}

$envPath = Join-Path $repoRoot ".env"
if (-not (Test-Path -LiteralPath $envPath)) {
    Copy-Item -LiteralPath (Join-Path $repoRoot ".env.example") -Destination $envPath
    Write-Host "Created .env from .env.example. No provider credential was added."
} else {
    Write-Host "Existing .env preserved; it was not overwritten."
}

$venvPath = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    $venvArgs = @() + $pythonPrefix + @("-m", "venv", ".venv")
    & $pythonExe @venvArgs
    Assert-LastExitCode "Virtual environment creation"
    Write-Host "Created .venv."
} else {
    Write-Host "Existing .venv preserved."
}

& $venvPython -m pip install -r requirements-dev.txt
Assert-LastExitCode "Python dependency installation"

& $pnpmCommand.Source install --frozen-lockfile
Assert-LastExitCode "JavaScript dependency installation"

if (-not $SkipSmoke) {
    & $venvPython scripts/release-provider-smoke.py --provider openai --no-key-only
    Assert-LastExitCode "No-key readiness check"
}

Write-Host ""
Write-Host "Setup complete. No paid provider model call was made by this bootstrap."
Write-Host "Start the API in terminal 1:  .\scripts\dev-api.ps1"
Write-Host "Start the web app in terminal 2: .\scripts\dev-web.ps1"
Write-Host "Then open http://localhost:3000"
