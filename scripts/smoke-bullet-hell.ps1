param(
    [string]$UnityEditor = $env:GAMECHANGE_UNITY_EDITOR,
    [int]$BuildTimeoutSeconds = 300,
    [int]$RunTimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$UnityProject = Join-Path $RepoRoot "game-unity"
$RuntimeDir = Join-Path $RepoRoot "runtime-artifacts\bullet-hell-smoke"
$BuildLog = Join-Path $RuntimeDir "build.log"
$Player = Join-Path $UnityProject "Builds\BulletHellWindows\BulletHellDemo.exe"
$Config = Join-Path $RepoRoot "configs\bullet-hell\baseline.json"
$Telemetry = Join-Path $RuntimeDir "telemetry.json"
$RepeatTelemetry = Join-Path $RuntimeDir "telemetry_repeat.json"
$PlayerLog = Join-Path $RuntimeDir "player.log"
$RepeatPlayerLog = Join-Path $RuntimeDir "player_repeat.log"
$Seed = 20260727

if (-not (Test-Path -LiteralPath $UnityEditor)) {
    throw "Unity Editor not found. Set GAMECHANGE_UNITY_EDITOR or pass -UnityEditor explicitly. Received: $UnityEditor"
}
if (-not (Test-Path -LiteralPath $Config)) {
    throw "Bullet Hell baseline config not found: $Config"
}
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

function Invoke-BoundedProcess {
    param(
        [string]$FileName,
        [string]$Arguments,
        [string]$WorkingDirectory,
        [int]$TimeoutSeconds
    )

    $info = [System.Diagnostics.ProcessStartInfo]::new()
    $info.FileName = $FileName
    $info.Arguments = $Arguments
    $info.WorkingDirectory = $WorkingDirectory
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $process = [System.Diagnostics.Process]::Start($info)
    if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
        $process.Kill()
        throw "Process timed out after $TimeoutSeconds seconds: $FileName"
    }
    return $process.ExitCode
}

function Get-UnityLicenseFailure {
    if (-not (Test-Path -LiteralPath $BuildLog)) { return $null }
    $text = Get-Content -LiteralPath $BuildLog -Raw
    if ($text -match "No valid Unity Editor license found|Found 0 entitlement groups and 0 free entitlements|Application will terminate with return code 198") {
        return "Unity batch mode did not receive a valid Hub access token. Open this project once from Unity Hub, keep Hub signed in, close the Editor, and retry."
    }
    if (
        $text -match "Access token is unavailable" -and
        $text -notmatch "License group:" -and
        $text -notmatch "Successfully resolved entitlement details"
    ) {
        return "Unity batch mode could not resolve a license after the Hub access-token warning. Open this project once from Unity Hub, keep Hub signed in, close the Editor, and retry."
    }
    return $null
}

Remove-Item -LiteralPath $Player -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path (Split-Path -Parent $Player) "runtime_version.txt") -Force -ErrorAction SilentlyContinue
$buildArgs = "-batchmode -nographics -quit -projectPath `"$UnityProject`" -executeMethod GameConfig.Editor.BulletHellDemoBuilder.BuildWindows -logFile `"$BuildLog`""
$buildExit = Invoke-BoundedProcess -FileName $UnityEditor -Arguments $buildArgs -WorkingDirectory $RepoRoot -TimeoutSeconds $BuildTimeoutSeconds
$licenseFailure = Get-UnityLicenseFailure
if ($licenseFailure) {
    throw "$licenseFailure Build log: $BuildLog"
}
if ($buildExit -ne 0) {
    throw "Bullet Hell Unity build failed with exit code $buildExit. Build log: $BuildLog"
}
if (-not (Test-Path -LiteralPath $Player)) {
    throw "Unity returned success but did not create BulletHellDemo.exe. Treating this as a failed build. Build log: $BuildLog"
}

function Invoke-BulletRun {
    param([string]$Output, [string]$Log)
    Remove-Item -LiteralPath $Output -Force -ErrorAction SilentlyContinue
    $args = "-batchmode -nographics --bullet-hell --auto-run --seed $Seed --config-input `"$Config`" --telemetry-output `"$Output`" -logFile `"$Log`""
    $exitCode = Invoke-BoundedProcess -FileName $Player -Arguments $args -WorkingDirectory (Split-Path -Parent $Player) -TimeoutSeconds $RunTimeoutSeconds
    if ($exitCode -ne 0) { throw "Bullet Hell auto run failed with exit code $exitCode. Player log: $Log" }
    if (-not (Test-Path -LiteralPath $Output)) { throw "Bullet Hell auto run did not create telemetry: $Output" }
    return Get-Content -LiteralPath $Output -Raw -Encoding UTF8 | ConvertFrom-Json
}

$first = Invoke-BulletRun -Output $Telemetry -Log $PlayerLog
$second = Invoke-BulletRun -Output $RepeatTelemetry -Log $RepeatPlayerLog

foreach ($result in @($first, $second)) {
    if ($result.status -ne "completed") { throw "Expected completed telemetry, got '$($result.status)'." }
    if ($result.random_seed -ne $Seed -or $result.run_mode -ne "auto") {
        throw "Telemetry did not preserve fixed seed $Seed and auto mode."
    }
    if ($result.bullet_hell_contract_version -ne "1.0") {
        throw "Unexpected Bullet Hell contract version: $($result.bullet_hell_contract_version)"
    }
}

$stableFields = @(
    "scenario_id",
    "status",
    "random_seed",
    "total_bullets_spawned",
    "peak_alive_bullets",
    "player_hits",
    "exception_log_count"
)
foreach ($field in $stableFields) {
    if ($first.$field -ne $second.$field) {
        throw "Fixed-seed repeatability failed for '$field': '$($first.$field)' vs '$($second.$field)'."
    }
}
if ($first.phase_results.Count -ne $second.phase_results.Count) {
    throw "Fixed-seed repeatability failed for phase count."
}
$stablePhaseFields = @("phase_id", "pattern_type", "bullets_spawned", "player_hits", "peak_alive_bullets")
for ($index = 0; $index -lt $first.phase_results.Count; $index++) {
    foreach ($field in $stablePhaseFields) {
        $firstValue = $first.phase_results[$index].$field
        $secondValue = $second.phase_results[$index].$field
        if ($firstValue -ne $secondValue) {
            throw "Fixed-seed repeatability failed for phase[$index].$field`: '$firstValue' vs '$secondValue'."
        }
    }
}

$summary = [ordered]@{
    passed = $true
    seed = $Seed
    stable_fields = $stableFields
    stable_phase_fields = $stablePhaseFields
    phase_count = $first.phase_results.Count
    telemetry = $Telemetry
    repeat_telemetry = $RepeatTelemetry
    evidence_scope = "Fixed seed and fixed trajectory regression evidence; not a complete measure of player experience."
}
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $RuntimeDir "repeatability_summary.json") -Encoding UTF8

Write-Host "Bullet Hell Unity build and fixed-seed repeatability smoke passed."
Write-Host "Evidence: $RuntimeDir"
