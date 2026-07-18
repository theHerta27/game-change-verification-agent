$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ServiceRoot = Join-Path $RepoRoot "services\agent-python"
. (Join-Path $PSScriptRoot "common.ps1")
$PythonExe = Resolve-ProjectPython -RepoRoot $RepoRoot

Push-Location $ServiceRoot
try {
    & $PythonExe -m pytest tests
    if ($LASTEXITCODE -ne 0) { throw "Python tests failed with exit code $LASTEXITCODE." }
}
finally {
    Pop-Location
}
