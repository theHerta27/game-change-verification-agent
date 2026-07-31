param(
    [string]$UnrealEditor = "D:\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Project = Join-Path $RepoRoot "game-unreal\BulletHellUE\BulletHellUE.uproject"
$Archive = Join-Path $RepoRoot "game-unreal\BulletHellUE\Builds\Windows"
$Player = Join-Path $Archive "BulletHellUE.exe"

if (-not (Test-Path -LiteralPath $UnrealEditor)) {
    throw "Unreal Editor not found: $UnrealEditor"
}
if (-not (Test-Path -LiteralPath $Project)) {
    throw "Unreal project not found: $Project"
}
$EngineRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $UnrealEditor))
$RunUAT = Join-Path $EngineRoot "Build\BatchFiles\RunUAT.bat"
if (-not (Test-Path -LiteralPath $RunUAT)) {
    throw "RunUAT.bat not found: $RunUAT"
}

& $RunUAT BuildCookRun "-project=$Project" -noP4 -platform=Win64 `
    -clientconfig=Development -build -cook -stage -pak -archive `
    "-archivedirectory=$Archive" -utf8output -unattended
if ($LASTEXITCODE -ne 0) {
    throw "UE5 BuildCookRun failed with exit code $LASTEXITCODE."
}
if (-not (Test-Path -LiteralPath $Player)) {
    throw "UE5 build reported success but did not create the registered Player: $Player"
}
Write-Host "UE5 Windows Player build passed."
Write-Host "Player: $Player"
