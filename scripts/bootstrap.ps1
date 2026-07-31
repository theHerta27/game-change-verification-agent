param(
    [switch]$SkipPython,
    [switch]$SkipWeb
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot "common.ps1")

if (-not $SkipPython) {
    $VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $VenvPython)) {
        $BasePython = Resolve-BasePython
        & $BasePython -m venv (Join-Path $RepoRoot ".venv")
        if ($LASTEXITCODE -ne 0) { throw "Failed to create project virtual environment." }
    }
    Push-Location (Join-Path $RepoRoot "services\agent-python")
    try {
        & $VenvPython -m pip install -e ".[dev]"
        if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed." }
    }
    finally {
        Pop-Location
    }
}

if (-not $SkipWeb) {
    Push-Location (Join-Path $RepoRoot "web-console")
    try {
        npm install
    }
    finally {
        Pop-Location
    }
}

Write-Host "Game Change Verification Agent dependencies are ready."
