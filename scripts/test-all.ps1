$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "test-python.ps1")
& (Join-Path $PSScriptRoot "test-web.ps1")
$repoRoot = Split-Path -Parent $PSScriptRoot
$localReimuPrefab = Join-Path $repoRoot "game-unity\Assets\Resources\LocalThirdParty\Reimu\Reimu.prefab"
if (Test-Path -LiteralPath $localReimuPrefab) {
    & (Join-Path $PSScriptRoot "smoke-reimu-presentation.ps1")
}
else {
& (Join-Path $PSScriptRoot "smoke-unity.ps1")
}
& (Join-Path $PSScriptRoot "smoke-bullet-hell.ps1")
$unrealPlayer = Join-Path $repoRoot "game-unreal\BulletHellUE\Builds\Windows\BulletHellUE.exe"
if (Test-Path -LiteralPath $unrealPlayer) {
    & (Join-Path $PSScriptRoot "smoke-unreal.ps1")
}
else {
    Write-Host "Skipping smoke-unreal.ps1: no local UE5 Player."
}
& (Join-Path $PSScriptRoot "verify-repo-clean.ps1")
Write-Host "All Game Change Verification Agent checks passed."
