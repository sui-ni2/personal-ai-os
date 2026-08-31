[CmdletBinding()]
param(
    [ValidateSet("Install", "Update", "Rollback", "Status")]
    [string]$Action = "Install",
    [string]$PackagePath,
    [string]$InstallPath = (Join-Path $env:LOCALAPPDATA "Personal AI OS"),
    [switch]$CheckOnly,
    [switch]$NoLaunch
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptRoot = Split-Path -Parent $PSScriptRoot
$installRoot = [IO.Path]::GetFullPath($InstallPath)
$applicationRoot = Join-Path $installRoot "app"
$backupRoot = Join-Path $installRoot "backups"
$metadataPath = Join-Path $installRoot "installation.json"
$updateStatePath = Join-Path $installRoot "update-state.json"
$composeProject = "personal-ai-os"

function Assert-SafeInstallPath {
    $profileRoot = [IO.Path]::GetFullPath($env:USERPROFILE)
    $driveRoot = [IO.Path]::GetPathRoot($installRoot)
    if ($installRoot -eq $driveRoot -or $installRoot -eq $profileRoot) {
        throw "InstallPath must be a dedicated folder, not a drive or user-profile root."
    }
}

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

function Write-AtomicJson {
    param([string]$Path, [hashtable]$Value)
    $directory = Split-Path -Parent $Path
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    $temporary = Join-Path $directory ("." + [IO.Path]::GetFileName($Path) + "." + [Guid]::NewGuid().ToString("N") + ".tmp")
    try {
        [IO.File]::WriteAllText($temporary, ($Value | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
        Move-Item -LiteralPath $temporary -Destination $Path -Force
    } finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
    }
}

function Get-Distribution {
    param([string]$Path)
    if (-not $Path) { throw "PackagePath is required for Install or Update." }
    $resolved = [IO.Path]::GetFullPath($Path)
    if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) { throw "Distribution package was not found: $resolved" }
    $staging = Join-Path ([IO.Path]::GetTempPath()) ("personal-ai-os-package-" + [Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $staging | Out-Null
    Expand-Archive -LiteralPath $resolved -DestinationPath $staging
    $manifestPath = Join-Path $staging "personal-ai-os-release.json"
    $applicationArchive = Join-Path $staging "application.zip"
    if (-not (Test-Path -LiteralPath $manifestPath) -or -not (Test-Path -LiteralPath $applicationArchive)) { throw "Distribution is missing its manifest or application archive." }
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ($manifest.format -ne "personal-ai-os-windows-distribution-v1") { throw "Unsupported distribution format." }
    $actualHash = Get-Sha256 -Path $applicationArchive
    if ($actualHash -ne [string]$manifest.application_sha256) { throw "Application archive hash does not match the manifest." }
    [pscustomobject]@{ Staging = $staging; Manifest = $manifest; ApplicationArchive = $applicationArchive }
}

function Invoke-Compose {
    param([string[]]$Arguments)
    & docker compose --project-name $composeProject --file (Join-Path $applicationRoot "compose.yaml") @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose failed: $($Arguments -join ' ')" }
}

function Test-DockerRuntime {
    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $docker) { throw "Docker Desktop with Docker Compose is required for this distribution path. No Python, Node.js, or pnpm setup is required." }
    & $docker.Source compose version | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose is unavailable." }
}

function Invoke-HealthCheck {
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:8080/health" -TimeoutSec 3
            if ($health.status -eq "ok") { return $health }
        } catch { }
        Start-Sleep -Seconds 2
    }
    throw "The updated runtime did not pass its localhost health check."
}

function Save-DataBackup {
    param([string]$Destination)
    $containerId = (& docker compose --project-name $composeProject --file (Join-Path $applicationRoot "compose.yaml") ps -q personal-ai-os).Trim()
    if (-not $containerId) { throw "Cannot create a consistent update backup because the current runtime is not running." }
    $helper = Join-Path $applicationRoot "scripts\backup-data.py"
    if (-not (Test-Path -LiteralPath $helper)) { throw "Current application does not include the backup helper." }
    & docker cp $helper "$containerId`:/tmp/personal-ai-os-backup.py"
    if ($LASTEXITCODE -ne 0) { throw "Could not stage the backup helper in the runtime." }
    $insidePath = (& docker compose --project-name $composeProject --file (Join-Path $applicationRoot "compose.yaml") exec -T personal-ai-os python /tmp/personal-ai-os-backup.py --data-dir /data --output-dir /tmp).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $insidePath) { throw "Data backup failed before update." }
    & docker cp "$containerId`:$insidePath" $Destination
    if ($LASTEXITCODE -ne 0) { throw "Could not copy the verified data backup from the runtime." }
    if (-not (Test-Path -LiteralPath $Destination)) { throw "Update backup was not created." }
}

function Restore-DataBackup {
    param([string]$Archive)
    if (-not (Test-Path -LiteralPath $Archive -PathType Leaf)) { throw "Rollback data backup was not found: $Archive" }
    $containerId = (& docker compose --project-name $composeProject --file (Join-Path $applicationRoot "compose.yaml") ps -q personal-ai-os).Trim()
    if (-not $containerId) { throw "The restored runtime is not running, so its compatible data snapshot cannot be applied." }
    $helper = Join-Path $applicationRoot "scripts\restore-data.py"
    if (-not (Test-Path -LiteralPath $helper)) { throw "Restored application does not include the restore helper." }
    & docker cp $helper "$containerId`:/tmp/personal-ai-os-restore.py"
    if ($LASTEXITCODE -ne 0) { throw "Could not stage the restore helper in the runtime." }
    & docker cp $Archive "$containerId`:/tmp/personal-ai-os-rollback.zip"
    if ($LASTEXITCODE -ne 0) { throw "Could not stage the compatible data backup in the runtime." }
    & docker compose --project-name $composeProject --file (Join-Path $applicationRoot "compose.yaml") exec -T personal-ai-os python /tmp/personal-ai-os-restore.py /tmp/personal-ai-os-rollback.zip --data-dir /data
    if ($LASTEXITCODE -ne 0) { throw "Compatible data restore failed during rollback." }
    Invoke-Compose -Arguments @("restart")
}

function Start-InstalledRuntime {
    Invoke-Compose -Arguments @("up", "--build", "--detach")
    return Invoke-HealthCheck
}

function Get-Installation {
    if (-not (Test-Path -LiteralPath $metadataPath)) { return $null }
    return Get-Content -LiteralPath $metadataPath -Raw | ConvertFrom-Json
}

Assert-SafeInstallPath

if ($Action -eq "Status") {
    $installation = Get-Installation
    [pscustomobject]@{
        Installed = [bool]$installation
        CurrentVersion = if ($installation) { $installation.current_version } else { $null }
        MigrationVersion = if ($installation) { $installation.migration_version } else { $null }
        BackupCompatibility = if ($installation) { $installation.backup_compatibility } else { $null }
        UpdateState = if (Test-Path -LiteralPath $updateStatePath) { (Get-Content -LiteralPath $updateStatePath -Raw | ConvertFrom-Json).status } else { "NONE" }
        Signing = if ($installation) { $installation.signing_status } else { "SIGNING_EXTERNAL_NOT_CONFIGURED" }
    } | Format-List
    exit 0
}

if ($Action -eq "Rollback") {
    $state = if (Test-Path -LiteralPath $updateStatePath) { Get-Content -LiteralPath $updateStatePath -Raw | ConvertFrom-Json } else { $null }
    if (-not $state -or -not $state.previous_application_path -or -not (Test-Path -LiteralPath $state.previous_application_path)) { throw "No rollback application snapshot is available." }
    Test-DockerRuntime
    Invoke-Compose -Arguments @("down")
    $failedPath = Join-Path $backupRoot ("failed-app-" + [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ"))
    if (Test-Path -LiteralPath $applicationRoot) { Move-Item -LiteralPath $applicationRoot -Destination $failedPath }
    Move-Item -LiteralPath $state.previous_application_path -Destination $applicationRoot
    try {
        Start-InstalledRuntime | Out-Null
        Restore-DataBackup -Archive $state.data_backup
        $health = Invoke-HealthCheck
        $installation = Get-Installation
        Write-AtomicJson -Path $metadataPath -Value @{ current_version = $state.previous_version; available_version = $installation.available_version; migration_version = $installation.migration_version; backup_compatibility = $installation.backup_compatibility; signing_status = $installation.signing_status; last_update_status = "ROLLED_BACK"; updated_at = [DateTime]::UtcNow.ToString("o") }
        Write-AtomicJson -Path $updateStatePath -Value @{ status = "UPDATE_FAILED_SAFE"; rollback_available = $false; restored_version = $state.previous_version; data_backup = $state.data_backup; updated_at = [DateTime]::UtcNow.ToString("o") }
        $health | Format-List
    } catch {
        Write-AtomicJson -Path $updateStatePath -Value @{ status = "UPDATE_FAILED_SAFE"; rollback_available = $true; previous_application_path = $state.previous_application_path; data_backup = $state.data_backup; error = "Rollback startup did not pass health"; updated_at = [DateTime]::UtcNow.ToString("o") }
        throw
    }
    exit 0
}

$distribution = $null
try {
    $distribution = Get-Distribution -Path $PackagePath
    if ($CheckOnly) {
        [pscustomobject]@{ Package = $PackagePath; Version = $distribution.Manifest.version; MigrationVersion = $distribution.Manifest.migration_version; Signing = $distribution.Manifest.signing_status; Verification = "PASS" } | Format-List
        exit 0
    }
    Test-DockerRuntime
    New-Item -ItemType Directory -Force -Path $installRoot, $backupRoot | Out-Null
    $existing = Get-Installation
    if ($Action -eq "Install" -and $existing) { throw "An existing installation was found. Use -Action Update or inspect with -Action Status." }
    if ($Action -eq "Update" -and -not $existing) { throw "No existing installation was found. Use -Action Install." }

    $candidate = Join-Path $installRoot ("candidate-" + [Guid]::NewGuid().ToString("N"))
    Expand-Archive -LiteralPath $distribution.ApplicationArchive -DestinationPath $candidate
    if (-not (Test-Path -LiteralPath (Join-Path $candidate "compose.yaml"))) { throw "Distribution application archive is incomplete." }

    if ($Action -eq "Install") {
        Move-Item -LiteralPath $candidate -Destination $applicationRoot
        $health = Start-InstalledRuntime
        Write-AtomicJson -Path $metadataPath -Value @{ current_version = $distribution.Manifest.version; available_version = $distribution.Manifest.version; migration_version = $distribution.Manifest.migration_version; backup_compatibility = $distribution.Manifest.backup_compatibility; signing_status = $distribution.Manifest.signing_status; last_update_status = "INSTALLED"; updated_at = [DateTime]::UtcNow.ToString("o") }
        if (-not $NoLaunch) { Start-Process "http://127.0.0.1:8080" }
        $health | Format-List
        exit 0
    }

    $timestamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")
    $dataBackup = Join-Path $backupRoot ("data-before-update-" + $timestamp + ".zip")
    $previousApp = Join-Path $backupRoot ("app-" + $existing.current_version + "-" + $timestamp)
    Save-DataBackup -Destination $dataBackup
    Write-AtomicJson -Path $updateStatePath -Value @{ status = "UPDATING"; rollback_available = $true; previous_application_path = $previousApp; previous_version = $existing.current_version; previous_migration_version = $existing.migration_version; data_backup = $dataBackup; target_version = $distribution.Manifest.version; updated_at = [DateTime]::UtcNow.ToString("o") }
    Invoke-Compose -Arguments @("down")
    Move-Item -LiteralPath $applicationRoot -Destination $previousApp
    Move-Item -LiteralPath $candidate -Destination $applicationRoot
    try {
        $health = Start-InstalledRuntime
        Write-AtomicJson -Path $metadataPath -Value @{ current_version = $distribution.Manifest.version; available_version = $distribution.Manifest.version; migration_version = $distribution.Manifest.migration_version; backup_compatibility = $distribution.Manifest.backup_compatibility; signing_status = $distribution.Manifest.signing_status; last_update_status = "UPDATED"; updated_at = [DateTime]::UtcNow.ToString("o") }
        Write-AtomicJson -Path $updateStatePath -Value @{ status = "UPDATED"; rollback_available = $true; previous_application_path = $previousApp; previous_version = $existing.current_version; previous_migration_version = $existing.migration_version; data_backup = $dataBackup; updated_at = [DateTime]::UtcNow.ToString("o") }
        $health | Format-List
    } catch {
        $failedPath = Join-Path $backupRoot ("failed-app-" + $timestamp)
        if (Test-Path -LiteralPath $applicationRoot) { Move-Item -LiteralPath $applicationRoot -Destination $failedPath }
        Move-Item -LiteralPath $previousApp -Destination $applicationRoot
        $restored = $false
        try { Start-InstalledRuntime | Out-Null; Restore-DataBackup -Archive $dataBackup; Invoke-HealthCheck | Out-Null; $restored = $true } catch { }
        Write-AtomicJson -Path $updateStatePath -Value @{ status = "UPDATE_FAILED_SAFE"; rollback_available = $true; previous_application_path = $applicationRoot; previous_version = $existing.current_version; previous_migration_version = $existing.migration_version; data_backup = $dataBackup; automatic_runtime_restore = $restored; failed_application_path = $failedPath; updated_at = [DateTime]::UtcNow.ToString("o") }
        throw "Update failed safely. The previous application and its compatible data snapshot were restored: $restored. Data backup retained at $dataBackup."
    }
} finally {
    if ($distribution -and (Test-Path -LiteralPath $distribution.Staging)) { Remove-Item -LiteralPath $distribution.Staging -Recurse -Force }
}
