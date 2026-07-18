$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $PSScriptRoot)).Path
$ManifestPath = Join-Path $RepoRoot "source-manifest.json"

if (-not (Test-Path -LiteralPath $ManifestPath)) { throw "Missing source-manifest.json" }
$manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
foreach ($file in $manifest.files) {
    if (-not (Test-Path -LiteralPath $file.source_path)) { throw "Source file disappeared: $($file.source_path)" }
    $actual = (Get-FileHash -LiteralPath $file.source_path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $file.source_sha256) { throw "Source file changed after snapshot: $($file.source_path)" }
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
if ($realEnv) { throw "Unignored .env files found: $($realEnv.FullName -join ', ')" }

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
