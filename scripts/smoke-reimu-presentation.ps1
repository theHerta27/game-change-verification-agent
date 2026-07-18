param(
    [string]$UnityEditor = "E:\Unity6\6000.3.19f1\Editor\Unity.exe",
    [int]$RunTimeoutSeconds = 60
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$UnityProject = Join-Path $RepoRoot "game-unity"
$Player = Join-Path $UnityProject "Builds\Windows\GameConfigRuntimeDemo.exe"
$Contract = Join-Path $UnityProject "Assets\StreamingAssets\game_config.json"
$Prefab = Join-Path $UnityProject "Assets\Resources\LocalThirdParty\Reimu\Reimu.prefab"
$RuntimeRoot = Join-Path $RepoRoot "runtime-artifacts\reimu-import"
$Screenshot = Join-Path $RuntimeRoot "reimu_runtime_preview.png"
$PlayerLog = Join-Path $RuntimeRoot "reimu_preview_player.log"
$PlaceholderScreenshot = Join-Path $RuntimeRoot "placeholder_fallback_preview.png"
$PlaceholderLog = Join-Path $RuntimeRoot "placeholder_fallback_player.log"

if (-not (Test-Path -LiteralPath $Prefab)) { throw "Local Reimu prefab is missing. Run scripts\import-reimu-unity.ps1 first." }
& (Join-Path $PSScriptRoot "smoke-unity.ps1") -UnityEditor $UnityEditor
if ($LASTEXITCODE -ne 0) { throw "Milestone 1 regression failed while validating the Reimu presentation." }
if (-not (Test-Path -LiteralPath $Player)) { throw "Unity player was not built: $Player" }

Remove-Item -LiteralPath $Screenshot -Force -ErrorAction SilentlyContinue
$arguments = "-force-d3d11 --config-input `"$Contract`" --screenshot-output `"$Screenshot`" --screenshot-only -logFile `"$PlayerLog`""
$info = New-Object System.Diagnostics.ProcessStartInfo
$info.FileName = $Player
$info.Arguments = $arguments
$info.WorkingDirectory = Split-Path -Parent $Player
$info.UseShellExecute = $false
$info.CreateNoWindow = $true
$process = [System.Diagnostics.Process]::Start($info)
if (-not $process.WaitForExit($RunTimeoutSeconds * 1000)) {
    $process.Kill()
    throw "Reimu preview capture timed out after $RunTimeoutSeconds seconds."
}
if ($process.ExitCode -ne 0) { throw "Reimu preview player failed with exit code $($process.ExitCode). See $PlayerLog" }
if (-not (Test-Path -LiteralPath $Screenshot)) { throw "Reimu runtime preview was not created: $Screenshot" }
& (Join-Path $PSScriptRoot "verify-reimu-preview.ps1") -ImagePath $Screenshot
if ($LASTEXITCODE -ne 0) { throw "Reimu runtime preview pixel validation failed." }

Remove-Item -LiteralPath $PlaceholderScreenshot -Force -ErrorAction SilentlyContinue
$placeholderArguments = "-force-d3d11 --force-placeholder --config-input `"$Contract`" --screenshot-output `"$PlaceholderScreenshot`" --screenshot-only -logFile `"$PlaceholderLog`""
$placeholderInfo = New-Object System.Diagnostics.ProcessStartInfo
$placeholderInfo.FileName = $Player
$placeholderInfo.Arguments = $placeholderArguments
$placeholderInfo.WorkingDirectory = Split-Path -Parent $Player
$placeholderInfo.UseShellExecute = $false
$placeholderInfo.CreateNoWindow = $true
$placeholderProcess = [System.Diagnostics.Process]::Start($placeholderInfo)
if (-not $placeholderProcess.WaitForExit($RunTimeoutSeconds * 1000)) {
    $placeholderProcess.Kill()
    throw "Placeholder fallback preview timed out after $RunTimeoutSeconds seconds."
}
if ($placeholderProcess.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $PlaceholderScreenshot)) {
    throw "Placeholder fallback runtime validation failed. See $PlaceholderLog"
}

Write-Host "Reimu presentation smoke passed."
Write-Host "Preview: $Screenshot"
Write-Host "Placeholder fallback preview: $PlaceholderScreenshot"
