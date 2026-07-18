$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "test-python.ps1")
& (Join-Path $PSScriptRoot "test-web.ps1")
& (Join-Path $PSScriptRoot "smoke-unity.ps1")
& (Join-Path $PSScriptRoot "verify-repo-clean.ps1")
Write-Host "All Agentic Game R&D Lab checks passed."

