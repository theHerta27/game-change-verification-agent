param(
    [string]$UnityEditor = "E:\Unity6\6000.3.19f1\Editor\Unity.exe",
    [string]$ProfilePath = "",
    [int]$BuildTimeoutSeconds = 300,
    [int]$RunTimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$UnityProject = Join-Path $RepoRoot "game-unity"
$RuntimeDir = Join-Path $RepoRoot "runtime-artifacts\unity-smoke"
$BuildLog = Join-Path $RuntimeDir "build.log"
$PlayerLog = Join-Path $RuntimeDir "player.log"
$RepeatPlayerLog = Join-Path $RuntimeDir "player_repeat.log"
$Telemetry = Join-Path $RuntimeDir "telemetry.json"
$RepeatTelemetry = Join-Path $RuntimeDir "telemetry_repeat.json"
$Player = Join-Path $UnityProject "Builds\Windows\GameConfigRuntimeDemo.exe"
$Contract = Join-Path $UnityProject "Assets\StreamingAssets\game_config.json"
if (-not $ProfilePath) { $ProfilePath = Join-Path $RepoRoot "scenarios\milestone1\starter_trial_baseline.json" }

if (-not (Test-Path -LiteralPath $UnityEditor)) {
    throw "Unity Editor not found: $UnityEditor"
}
if (-not (Test-Path -LiteralPath $ProfilePath)) {
    throw "Milestone 1 test profile not found: $ProfilePath"
}

$profile = Get-Content -LiteralPath $ProfilePath -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $profile.seed -or $profile.run_mode -ne "auto") {
    throw "Milestone 1 test profile must define an auto run with a fixed seed."
}
$Seed = [int]$profile.seed

New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

function Invoke-ProcessWithTimeout {
    param(
        [string]$FileName,
        [string]$Arguments,
        [string]$WorkingDirectory,
        [int]$TimeoutSeconds
    )

    $info = New-Object System.Diagnostics.ProcessStartInfo
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

$buildArgs = "-batchmode -nographics -quit -projectPath `"$UnityProject`" -executeMethod GameConfig.Editor.RuntimeDemoBuilder.BuildWindows -logFile `"$BuildLog`""
$buildExit = Invoke-ProcessWithTimeout -FileName $UnityEditor -Arguments $buildArgs -WorkingDirectory $RepoRoot -TimeoutSeconds $BuildTimeoutSeconds
if ($buildExit -ne 0) {
    $logText = if (Test-Path -LiteralPath $BuildLog) { Get-Content -LiteralPath $BuildLog -Raw } else { "" }
    if ($logText -match "Connection to channel .* refused|Licensing initialization failed|re-connection attempt was UN-successful") {
        throw "Unity batchmode could not communicate with the Licensing Client. Restart Unity Hub and retry. See $BuildLog"
    }
    if ($logText -match "Access token is unavailable|No valid Unity Editor license found|0 free entitlements") {
        throw "Unity Hub may show a Personal license, but batchmode did not receive its access token or entitlement. Open this project once from Unity Hub, keep Hub signed in, then retry. See $BuildLog"
    }
    throw "Unity build failed with exit code $buildExit. See $BuildLog"
}

if (-not (Test-Path -LiteralPath $Player)) { throw "Unity build did not create player: $Player" }
if (-not (Test-Path -LiteralPath (Join-Path $UnityProject "Assets\Resources\Characters\Placeholder.prefab"))) {
    throw "Placeholder prefab was not generated."
}
$buildText = Get-Content -LiteralPath $BuildLog -Raw
if ($buildText -notmatch "Character view resolver smoke passed") {
    throw "Character resolver branches were not validated. See $BuildLog"
}

$runArgs = "-batchmode -nographics --auto-run --seed $Seed --config-input `"$Contract`" --telemetry-output `"$Telemetry`" -logFile `"$PlayerLog`""
Remove-Item -LiteralPath $Telemetry -Force -ErrorAction SilentlyContinue
$runExit = Invoke-ProcessWithTimeout -FileName $Player -Arguments $runArgs -WorkingDirectory (Split-Path -Parent $Player) -TimeoutSeconds $RunTimeoutSeconds
if ($runExit -ne 0) { throw "Unity auto-run failed with exit code $runExit. See $PlayerLog" }
if (-not (Test-Path -LiteralPath $Telemetry)) { throw "Unity auto-run did not create telemetry: $Telemetry" }
$result = Get-Content -LiteralPath $Telemetry -Raw | ConvertFrom-Json
if ($result.status -ne "completed") { throw "Unity telemetry status was '$($result.status)', expected 'completed'." }
if ($result.random_seed -ne $Seed -or $result.run_mode -ne "auto") {
    throw "Unity telemetry did not preserve the fixed seed and auto run mode."
}

$repeatArgs = "-batchmode -nographics --auto-run --seed $Seed --config-input `"$Contract`" --telemetry-output `"$RepeatTelemetry`" -logFile `"$RepeatPlayerLog`""
Remove-Item -LiteralPath $RepeatTelemetry -Force -ErrorAction SilentlyContinue
$repeatExit = Invoke-ProcessWithTimeout -FileName $Player -Arguments $repeatArgs -WorkingDirectory (Split-Path -Parent $Player) -TimeoutSeconds $RunTimeoutSeconds
if ($repeatExit -ne 0) { throw "Unity repeated auto-run failed with exit code $repeatExit. See $RepeatPlayerLog" }
if (-not (Test-Path -LiteralPath $RepeatTelemetry)) { throw "Unity repeated auto-run did not create telemetry: $RepeatTelemetry" }

. (Join-Path $PSScriptRoot "common.ps1")
$ProjectPython = Resolve-ProjectPython -RepoRoot $RepoRoot
$PythonService = Join-Path $RepoRoot "services\agent-python"
Push-Location $PythonService
try {
    & $ProjectPython -m gameconfig_agent.cli evaluate_milestone1_testbed --profile $ProfilePath --telemetry $Telemetry --repeat-telemetry $RepeatTelemetry --output $RuntimeDir
    if ($LASTEXITCODE -ne 0) { throw "Milestone 1 repeatability evaluation failed. See $RuntimeDir\testbed_evaluation_report.md" }
}
finally {
    Pop-Location
}

Write-Host "Unity greybox build and fixed-seed repeatability smoke passed."
Write-Host "Primary telemetry: $Telemetry"
Write-Host "Repeat telemetry: $RepeatTelemetry"
Write-Host "Evaluation report: $RuntimeDir\testbed_evaluation_report.md"
