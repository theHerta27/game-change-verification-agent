$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$entries = New-Object System.Collections.Generic.List[object]

function Add-TreeMapping {
    param(
        [string]$SourceRoot,
        [string]$DestinationRoot,
        [string]$SourceName
    )
    $sourcePath = (Resolve-Path -LiteralPath $SourceRoot).Path
    Get-ChildItem -LiteralPath $sourcePath -Recurse -File -Force |
        Where-Object { $_.FullName -notmatch '\\__pycache__\\|\\.pytest_cache\\|\.pyc$' } |
        Sort-Object FullName |
        ForEach-Object {
            $relative = $_.FullName.Substring($sourcePath.Length).TrimStart([char]92)
            Add-FileMapping -SourceFile $_.FullName -DestinationFile (Join-Path $DestinationRoot $relative) -SourceName $SourceName
        }
}

function Add-FileMapping {
    param(
        [string]$SourceFile,
        [string]$DestinationFile,
        [string]$SourceName
    )
    $sourceHash = (Get-FileHash -LiteralPath $SourceFile -Algorithm SHA256).Hash.ToLowerInvariant()
    $destinationHash = if (Test-Path -LiteralPath $DestinationFile) {
        (Get-FileHash -LiteralPath $DestinationFile -Algorithm SHA256).Hash.ToLowerInvariant()
    } else { $null }
    $relativeDestination = $DestinationFile.Substring($RepoRoot.Length).TrimStart([char]92)
    $normalizedDestination = $relativeDestination.Replace([char]92, [char]47)
    $entries.Add([ordered]@{
        source_name = $SourceName
        source_path = $SourceFile
        destination_path = $normalizedDestination
        source_sha256 = $sourceHash
        destination_sha256 = $destinationHash
        adapted_after_import = $destinationHash -ne $null -and $destinationHash -ne $sourceHash
    })
}

$gameConfig = "D:\Desktop\GameConfig-Agent"
$devQuality = "D:\Desktop\DevQuality-Agent"
Add-TreeMapping "$gameConfig\gameconfig_agent" "$RepoRoot\services\agent-python\gameconfig_agent" "GameConfig-Agent"
Add-TreeMapping "$gameConfig\tests" "$RepoRoot\services\agent-python\tests" "GameConfig-Agent"
Add-TreeMapping "$gameConfig\examples" "$RepoRoot\services\agent-python\examples" "GameConfig-Agent"
Add-TreeMapping "$gameConfig\frontend\src" "$RepoRoot\web-console\src" "GameConfig-Agent"
foreach ($file in @('index.html','package.json','package-lock.json','postcss.config.js','tailwind.config.js','tsconfig.json','tsconfig.node.json','vite.config.ts')) {
    Add-FileMapping "$gameConfig\frontend\$file" "$RepoRoot\web-console\$file" "GameConfig-Agent"
}
foreach ($folder in @('Assets','Packages','ProjectSettings')) {
    Add-TreeMapping "$gameConfig\unity\GameConfigRuntimeDemo\$folder" "$RepoRoot\game-unity\$folder" "GameConfig-Agent"
}
Add-TreeMapping "$gameConfig\docs" "$RepoRoot\docs\source-gameconfig" "GameConfig-Agent"
foreach ($phase in @('phase0','phase1','phase2','phase3','final')) {
    Add-TreeMapping "$gameConfig\outputs\$phase" "$RepoRoot\artifacts-samples\gameconfig\$phase" "GameConfig-Agent"
}

Add-TreeMapping "$devQuality\agent_service\agent_service" "$RepoRoot\services\agent-python\agent_service" "DevQuality-Agent"
Add-TreeMapping "$devQuality\agent_service\tests" "$RepoRoot\services\agent-python\tests" "DevQuality-Agent"
Add-TreeMapping "$devQuality\agent_service\examples" "$RepoRoot\services\agent-python\examples" "DevQuality-Agent"
Add-TreeMapping "$devQuality\agent_service\real_llm_smoke_cases" "$RepoRoot\services\agent-python\real_llm_smoke_cases" "DevQuality-Agent"
Add-TreeMapping "$devQuality\docs" "$RepoRoot\docs\source-devquality" "DevQuality-Agent"

Add-FileMapping "D:\Desktop\MMD_REIMU.ZIP.zip" "$RepoRoot\local-assets\reimu\source\MMD_REIMU.ZIP.zip" "MMD_REIMU"

$content = ($entries | Sort-Object source_path | ForEach-Object { "$($_.source_path)|$($_.source_sha256)" }) -join "`n"
$bytes = [System.Text.Encoding]::UTF8.GetBytes($content)
$sha = [System.Security.Cryptography.SHA256]::Create()
$manifestHash = ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()
$manifest = [ordered]@{
    schema_version = "1.0"
    snapshot_time = (Get-Date).ToUniversalTime().ToString('o')
    source_vcs = "none"
    source_roots = @(
        [ordered]@{ name="GameConfig-Agent"; path=$gameConfig; excluded_paths=@('.env','.idea','.pytest_cache','frontend/node_modules','frontend/dist','unity/GameConfigRuntimeDemo/Library','unity/GameConfigRuntimeDemo/Temp','unity/GameConfigRuntimeDemo/Logs','unity/GameConfigRuntimeDemo/Builds','unity/GameConfigRuntimeDemo/UserSettings','outputs/runtime_runs') },
        [ordered]@{ name="DevQuality-Agent"; path=$devQuality; excluded_paths=@('.idea','backend','frontend','design-system','scripts','agent_service/.env','agent_service/.pytest_cache','agent_service/logs','agent_service/outputs') },
        [ordered]@{ name="MMD_REIMU"; path="D:\Desktop\MMD_REIMU.ZIP.zip"; excluded_paths=@() }
    )
    imported_file_count = $entries.Count
    manifest_sha256 = $manifestHash
    files = @($entries | Sort-Object source_path)
}
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $RepoRoot 'source-manifest.json') -Encoding UTF8
Write-Host "Source manifest generated with $($entries.Count) files."
