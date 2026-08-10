$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
$ManifestPath = Join-Path $RepoRoot "source-manifest.json"

if (-not (Test-Path -LiteralPath $ManifestPath)) { throw "Missing source-manifest.json" }
$manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
if ($manifest.schema_version -ne '1.1') {
    throw "source-manifest.json must use the public schema_version 1.1."
}
foreach ($file in $manifest.files) {
    if ([string]::IsNullOrWhiteSpace($file.source_name) -or
        [string]::IsNullOrWhiteSpace($file.source_relative_path) -or
        [string]::IsNullOrWhiteSpace($file.destination_path)) {
        throw "Source manifest contains an incomplete public entry."
    }
    if ([System.IO.Path]::IsPathRooted($file.source_relative_path) -or
        [System.IO.Path]::IsPathRooted($file.destination_path)) {
        throw "Source manifest contains an absolute path."
    }
    if ($file.source_relative_path -match '(^|/)\.\.(/|$)' -or
        $file.destination_path -match '(^|/)\.\.(/|$)') {
        throw "Source manifest contains a path traversal segment."
    }
    if ($file.source_sha256 -notmatch '^[0-9a-f]{64}$') {
        throw "Source manifest contains an invalid SHA256 value."
    }
}

$nestedGit = Get-ChildItem -LiteralPath $RepoRoot -Directory -Recurse -Force |
    Where-Object { $_.Name -eq '.git' -and $_.Parent.FullName -ne $RepoRoot }
if ($nestedGit) { throw "Nested .git directories found: $($nestedGit.FullName -join ', ')" }

foreach ($forbidden in @(
    "services\agent-python\backend",
    "services\agent-python\frontend",
    "services\agent-python\design-system"
)) {
    if (Test-Path -LiteralPath (Join-Path $RepoRoot $forbidden)) { throw "Forbidden migrated component found: $forbidden" }
}

$realEnv = Get-ChildItem -LiteralPath $RepoRoot -Recurse -File -Force -Filter '.env' |
    Where-Object { $_.FullName -notmatch '\\node_modules\\' }
$unignoredEnv = @()
foreach ($envFile in $realEnv) {
    $relative = $envFile.FullName.Substring($RepoRoot.Length).TrimStart('\').Replace('\', '/')
    & git -c "safe.directory=$($RepoRoot.Replace('\', '/'))" -C $RepoRoot check-ignore --quiet -- $relative
    if ($LASTEXITCODE -ne 0) { $unignoredEnv += $envFile.FullName }
}
if ($unignoredEnv) { throw "Unignored .env files found: $($unignoredEnv -join ', ')" }

$assets = Join-Path $RepoRoot "game-unity\Assets"
Get-ChildItem -LiteralPath $assets -Recurse -File |
    Where-Object { $_.Extension -ne '.meta' -and $_.FullName -notmatch '\\LocalThirdParty\\' } |
    ForEach-Object {
        if (-not (Test-Path -LiteralPath ($_.FullName + '.meta'))) { throw "Unity asset is missing .meta: $($_.FullName)" }
    }

if (Test-Path -LiteralPath (Join-Path $RepoRoot '.git')) {
    $safeRepoRoot = $RepoRoot.Replace('\', '/')
    $tracked = & git -c "safe.directory=$safeRepoRoot" -C $RepoRoot ls-files
    if ($LASTEXITCODE -ne 0) { throw "git ls-files failed with exit code $LASTEXITCODE." }
    $badTracked = $tracked | Where-Object {
        $_ -match '(^|/)(local-assets|runtime-artifacts|node_modules|dist)(/|$)' -or
        $_ -match '\.egg-info/' -or
        $_ -match '^web-console/vite\.config\.(js|d\.ts)$' -or
        $_ -match 'Assets/Resources/LocalThirdParty/' -or
        $_ -eq '.env'
    }
    if ($badTracked) { throw "Ignored files are tracked: $($badTracked -join ', ')" }
}

Write-Host "Repository cleanliness and source immutability checks passed."
