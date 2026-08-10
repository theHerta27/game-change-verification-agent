function Resolve-BasePython {
    $candidates = @()
    if ($env:AGENTIC_GAME_RD_PYTHON) { $candidates += $env:AGENTIC_GAME_RD_PYTHON }
    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($command) { $candidates += $command.Source }

    foreach ($candidate in $candidates | Select-Object -Unique) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) { return $candidate }
    }
    throw "Python >= 3.10 was not found. Set AGENTIC_GAME_RD_PYTHON to python.exe."
}

function Resolve-ProjectPython {
    param([string]$RepoRoot)
    $venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython) { return $venvPython }
    return Resolve-BasePython
}

