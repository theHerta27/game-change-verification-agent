param(
    [int]$Port = 5173,
    [int]$BackendPort = 8000
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$WebRoot = Join-Path $RepoRoot "web-console"

Push-Location $WebRoot
try {
    if (-not (Test-Path -LiteralPath "node_modules")) {
        npm install
        if ($LASTEXITCODE -ne 0) { throw "npm install failed with code $LASTEXITCODE." }
    }
    Write-Host "Starting Web Console: http://127.0.0.1:$Port"
    Write-Host "Proxying API requests to: http://127.0.0.1:$BackendPort"
    $env:VITE_API_TARGET = "http://127.0.0.1:$BackendPort"
    $Vite = Join-Path $WebRoot "node_modules\.bin\vite.cmd"
    & $Vite --host 127.0.0.1 --port $Port
    if ($LASTEXITCODE -ne 0) { throw "Web Console exited with code $LASTEXITCODE." }
}
finally {
    Pop-Location
}
