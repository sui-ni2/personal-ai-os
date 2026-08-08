$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing .venv. Create it and install requirements-dev.txt first."
}

Set-Location -LiteralPath $repoRoot
$uvicornArgs = @("-m", "uvicorn", "personal_ai_os.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000")
if (Test-Path -LiteralPath (Join-Path $repoRoot ".env")) {
    $uvicornArgs += @("--env-file", ".env")
}
& $python @uvicornArgs
