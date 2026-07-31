param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ServiceRoot = Join-Path $RepoRoot "services\agent-python"
. (Join-Path $PSScriptRoot "common.ps1")
$PythonExe = Resolve-ProjectPython -RepoRoot $RepoRoot

Write-Host "Starting Game Change Verification Agent backend..."
Write-Host "API: http://127.0.0.1:$Port"
Write-Host "OpenAPI: http://127.0.0.1:$Port/docs"

Push-Location $ServiceRoot
try {
    & $PythonExe -m uvicorn api.server:app --host 127.0.0.1 --port $Port
    if ($LASTEXITCODE -ne 0) { throw "Backend exited with code $LASTEXITCODE." }
}
finally {
    Pop-Location
}
