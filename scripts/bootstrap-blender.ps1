param(
    [string]$BlenderVersion = "4.5.11",
    [string]$MmdToolsVersion = "v4.5.10"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$ToolsRoot = Join-Path $RepoRoot "local-tools"
$Downloads = Join-Path $ToolsRoot "downloads"
$BlenderArchive = Join-Path $Downloads "blender-$BlenderVersion-windows-x64.zip"
$BlenderRoot = Join-Path $ToolsRoot "blender-$BlenderVersion-windows-x64"
$BlenderExe = Join-Path $BlenderRoot "blender.exe"
$MmdArchiveName = "blender_mmd_tools-$($MmdToolsVersion.TrimStart('v')).zip"
$MmdArchive = Join-Path $Downloads $MmdArchiveName
$MmdExtract = Join-Path $ToolsRoot "mmd-tools-$($MmdToolsVersion.TrimStart('v'))"
$BlenderUserScripts = Join-Path $ToolsRoot "blender-user-scripts"
$BlenderAddonRoot = Join-Path $BlenderUserScripts "addons"
$BlenderConfigRoot = Join-Path $BlenderRoot "4.5\config"
$BlenderUrl = "https://download.blender.org/release/Blender4.5/blender-$BlenderVersion-windows-x64.zip"
$MmdUrl = "https://github.com/MMD-Blender/blender_mmd_tools/archive/refs/tags/$MmdToolsVersion.zip"
$LockPath = Join-Path $ToolsRoot "toolchain-lock.json"

New-Item -ItemType Directory -Force -Path $Downloads, $BlenderAddonRoot, $BlenderConfigRoot | Out-Null

function Assert-WithinToolsRoot {
    param([string]$Path)
    $resolvedRoot = [IO.Path]::GetFullPath($ToolsRoot).TrimEnd('\') + '\'
    $resolvedPath = [IO.Path]::GetFullPath($Path)
    if (-not $resolvedPath.StartsWith($resolvedRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to modify a path outside local-tools: $resolvedPath"
    }
}

function Receive-File {
    param([string]$Uri, [string]$Destination)
    if (Test-Path -LiteralPath $Destination) { return }
    $partial = "$Destination.part"
    Remove-Item -LiteralPath $partial -Force -ErrorAction SilentlyContinue
    Write-Host "Downloading $Uri"
    Invoke-WebRequest -Uri $Uri -OutFile $partial -UseBasicParsing
    Move-Item -LiteralPath $partial -Destination $Destination
}

Receive-File -Uri $BlenderUrl -Destination $BlenderArchive
if (-not (Test-Path -LiteralPath $BlenderExe)) {
    Write-Host "Extracting Blender $BlenderVersion"
    Expand-Archive -LiteralPath $BlenderArchive -DestinationPath $ToolsRoot -Force
}
if (-not (Test-Path -LiteralPath $BlenderExe)) { throw "Blender executable was not found after extraction: $BlenderExe" }

Receive-File -Uri $MmdUrl -Destination $MmdArchive
if (Test-Path -LiteralPath $MmdExtract) {
    Assert-WithinToolsRoot -Path $MmdExtract
    Remove-Item -LiteralPath $MmdExtract -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $MmdExtract | Out-Null
Expand-Archive -LiteralPath $MmdArchive -DestinationPath $MmdExtract -Force
$MmdSource = Get-ChildItem -LiteralPath $MmdExtract -Directory |
    ForEach-Object { Join-Path $_.FullName "mmd_tools" } |
    Where-Object { Test-Path -LiteralPath $_ } |
    Select-Object -First 1
if (-not $MmdSource) { throw "mmd_tools package was not found in $MmdArchive" }

$MmdDestination = Join-Path $BlenderAddonRoot "mmd_tools"
if (Test-Path -LiteralPath $MmdDestination) {
    Assert-WithinToolsRoot -Path $MmdDestination
    Remove-Item -LiteralPath $MmdDestination -Recurse -Force
}
Copy-Item -LiteralPath $MmdSource -Destination $MmdDestination -Recurse -Force

$MmdCommit = $null
if (Test-Path -LiteralPath $LockPath) {
    $existingLock = Get-Content -LiteralPath $LockPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($existingLock.mmd_tools.version -eq $MmdToolsVersion) { $MmdCommit = $existingLock.mmd_tools.commit }
}
if (-not $MmdCommit) {
    $apiHeaders = @{ "User-Agent" = "agentic-game-rd-toolchain-bootstrap" }
    $tagRef = Invoke-RestMethod -Uri "https://api.github.com/repos/MMD-Blender/blender_mmd_tools/git/ref/tags/$MmdToolsVersion" -Headers $apiHeaders
    $MmdCommit = $tagRef.object.sha
    if ($tagRef.object.type -eq "tag") {
        $tagObject = Invoke-RestMethod -Uri "https://api.github.com/repos/MMD-Blender/blender_mmd_tools/git/tags/$MmdCommit" -Headers $apiHeaders
        $MmdCommit = $tagObject.object.sha
    }
}
if (-not $MmdCommit) { throw "Unable to resolve the MMD Tools release commit." }

$versionOutput = & $BlenderExe --version
if ($LASTEXITCODE -ne 0) { throw "Blender executable failed its version check." }
$lock = [ordered]@{
    generated_at_utc = [DateTime]::UtcNow.ToString("O")
    blender = [ordered]@{
        version = $BlenderVersion
        executable = $BlenderExe
        archive = $BlenderArchive
        archive_sha256 = (Get-FileHash -LiteralPath $BlenderArchive -Algorithm SHA256).Hash.ToLowerInvariant()
        version_output = @($versionOutput)
    }
    mmd_tools = [ordered]@{
        version = $MmdToolsVersion
        commit = $MmdCommit
        archive = $MmdArchive
        archive_sha256 = (Get-FileHash -LiteralPath $MmdArchive -Algorithm SHA256).Hash.ToLowerInvariant()
        addon_path = $MmdDestination
        blender_user_scripts = $BlenderUserScripts
    }
}
$lock | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $LockPath -Encoding UTF8

Write-Host "Blender toolchain ready."
Write-Host "Blender: $BlenderExe"
Write-Host "MMD Tools: $MmdToolsVersion ($MmdCommit)"
Write-Host "Local lock: $LockPath"
