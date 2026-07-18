param(
    [string]$UnityEditor = "E:\Unity6\6000.3.19f1\Editor\Unity.exe",
    [int]$TimeoutSeconds = 300
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$UnityProject = Join-Path $RepoRoot "game-unity"
$ConversionRoot = Join-Path $RepoRoot "local-assets\reimu\converted\spring"
$SourceFbx = Join-Path $ConversionRoot "Reimu_Spring.fbx"
$SourceTextures = Join-Path $ConversionRoot "Textures"
$LocalModelRoot = Join-Path $UnityProject "Assets\Resources\LocalThirdParty\Reimu\Model"
$RuntimeRoot = Join-Path $RepoRoot "runtime-artifacts\reimu-import"
$UnityLog = Join-Path $RuntimeRoot "unity_import.log"
$UnityReport = Join-Path $RuntimeRoot "unity_import_report.json"

if (-not (Test-Path -LiteralPath $UnityEditor)) { throw "Unity Editor not found: $UnityEditor" }
if (-not (Test-Path -LiteralPath $SourceFbx)) { throw "Converted Reimu FBX is missing. Run scripts\convert-reimu.ps1 first." }

New-Item -ItemType Directory -Force -Path $LocalModelRoot, $RuntimeRoot | Out-Null
Copy-Item -LiteralPath $SourceFbx -Destination (Join-Path $LocalModelRoot "Reimu_Spring.fbx") -Force
if (Test-Path -LiteralPath $SourceTextures) {
    Get-ChildItem -LiteralPath $SourceTextures -File | Copy-Item -Destination $LocalModelRoot -Force
}

$arguments = "-batchmode -nographics -quit -projectPath `"$UnityProject`" -executeMethod GameConfig.Editor.LocalReimuImporter.ImportAndValidate --reimu-report `"$UnityReport`" -logFile `"$UnityLog`""
$info = New-Object System.Diagnostics.ProcessStartInfo
$info.FileName = $UnityEditor
$info.Arguments = $arguments
$info.WorkingDirectory = $RepoRoot
$info.UseShellExecute = $false
$info.CreateNoWindow = $true
$process = [System.Diagnostics.Process]::Start($info)
if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
    $process.Kill()
    throw "Unity Reimu import timed out after $TimeoutSeconds seconds."
}
if ($process.ExitCode -ne 0) { throw "Unity Reimu import failed with exit code $($process.ExitCode). See $UnityLog" }
if (-not (Test-Path -LiteralPath $UnityReport)) { throw "Unity did not create the Reimu import report: $UnityReport" }

$report = Get-Content -LiteralPath $UnityReport -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $report.resolver_uses_local_asset -or $report.renderer_count -lt 1) {
    throw "Unity Reimu import report failed structural validation."
}

Write-Host "Unity local Reimu import passed."
Write-Host "Prefab: $UnityProject\Assets\Resources\LocalThirdParty\Reimu\Reimu.prefab"
Write-Host "Report: $UnityReport"
