param(
    [string]$BlenderVersion = "4.5.11",
    [string]$SourcePmx = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$BlenderRoot = Join-Path $RepoRoot "local-tools\blender-$BlenderVersion-windows-x64"
$BlenderExe = Join-Path $BlenderRoot "blender.exe"
$BlenderUserScripts = Join-Path $RepoRoot "local-tools\blender-user-scripts"
$ConversionRoot = Join-Path $RepoRoot "local-assets\reimu\converted\spring"
$Fbx = Join-Path $ConversionRoot "Reimu_Spring.fbx"
$Blend = Join-Path $ConversionRoot "Reimu_Spring.blend"
$Textures = Join-Path $ConversionRoot "Textures"
$Report = Join-Path $ConversionRoot "conversion_report.json"
$ConversionLog = Join-Path $ConversionRoot "conversion.log"
$Converter = Join-Path $PSScriptRoot "blender\convert_reimu.py"
if (-not $SourcePmx) {
    $SourcePmx = Join-Path $RepoRoot "local-assets\reimu\extracted\MMD_REIMU\R_spring.pmx"
}

if (-not (Test-Path -LiteralPath $BlenderExe)) {
    throw "Blender portable is missing. Run scripts\bootstrap-blender.ps1 first."
}
if (-not (Test-Path -LiteralPath $SourcePmx)) { throw "Reimu PMX was not found: $SourcePmx" }
if (-not (Test-Path -LiteralPath $Converter)) { throw "Blender conversion script was not found: $Converter" }

New-Item -ItemType Directory -Force -Path $ConversionRoot, $Textures | Out-Null
$env:BLENDER_USER_SCRIPTS = $BlenderUserScripts
& $BlenderExe --background --factory-startup --log-file $ConversionLog --python $Converter -- `
    --input $SourcePmx `
    --fbx $Fbx `
    --blend $Blend `
    --textures $Textures `
    --report $Report
if ($LASTEXITCODE -ne 0) { throw "Blender PMX conversion failed with exit code $LASTEXITCODE. See $ConversionLog" }
if (-not (Test-Path -LiteralPath $Report)) { throw "Blender did not create a conversion report: $Report" }

$result = Get-Content -LiteralPath $Report -Raw -Encoding UTF8 | ConvertFrom-Json
if ($result.status -ne "completed" -or $result.model.mesh_count -lt 1 -or $result.model.armature_count -lt 1) {
    throw "Reimu conversion report did not pass structural validation."
}

Write-Host "Reimu PMX conversion passed."
Write-Host "FBX: $Fbx"
Write-Host "Report: $Report"
