param(
    [Parameter(Mandatory = $true)][string]$RepositoryRoot,
    [Parameter(Mandatory = $true)][string]$WorkspaceRoot,
    [Parameter(Mandatory = $true)][string]$ArtifactDir,
    [string]$UnityEditor = $env:GAMECHANGE_UNITY_EDITOR,
    [int]$BuildTimeoutSeconds = 300,
    [int]$RunTimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"
$UnityProject = Join-Path $WorkspaceRoot "game-unity"
$BuildLog = Join-Path $ArtifactDir "build.log"
$PlayerLog = Join-Path $ArtifactDir "player.log"
$RepeatPlayerLog = Join-Path $ArtifactDir "player_repeat.log"
$Telemetry = Join-Path $ArtifactDir "telemetry.json"
$RepeatTelemetry = Join-Path $ArtifactDir "telemetry_repeat.json"
$ResultPath = Join-Path $ArtifactDir "validation_result.json"
$Contract = Join-Path $UnityProject "Assets\StreamingAssets\game_config.json"
$Player = Join-Path $UnityProject "Builds\Windows\GameConfigRuntimeDemo.exe"
$Profile = Join-Path $RepositoryRoot "scenarios\milestone1\starter_trial_baseline.json"
$result = [ordered]@{
    passed = $false
    compilation_passed = $false
    editor_smoke_passed = $false
    player_runs_passed = $false
    repeatability_passed = $false
    repeatability_rate = $null
    runtime_target_pass_rate = $null
    error = $null
    completed_at = $null
}

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

try {
    if (-not (Test-Path -LiteralPath $UnityEditor)) { throw "Unity Editor not found. Set GAMECHANGE_UNITY_EDITOR or pass -UnityEditor explicitly. Received: $UnityEditor" }
    if (-not (Test-Path -LiteralPath $UnityProject)) { throw "Isolated Unity project not found: $UnityProject" }
    if (-not (Test-Path -LiteralPath $Profile)) { throw "Testbed profile not found: $Profile" }
    New-Item -ItemType Directory -Force -Path $ArtifactDir | Out-Null
    $profileData = Get-Content -LiteralPath $Profile -Raw -Encoding UTF8 | ConvertFrom-Json
    $seed = [int]$profileData.seed

    $buildArgs = "-batchmode -nographics -quit -projectPath `"$UnityProject`" -executeMethod GameConfig.Editor.RuntimeDemoBuilder.BuildWindows -logFile `"$BuildLog`""
    $buildExit = Invoke-ProcessWithTimeout -FileName $UnityEditor -Arguments $buildArgs -WorkingDirectory $RepositoryRoot -TimeoutSeconds $BuildTimeoutSeconds
    if ($buildExit -ne 0) {
        $failedBuildText = if (Test-Path -LiteralPath $BuildLog) { Get-Content -LiteralPath $BuildLog -Raw -Encoding UTF8 } else { "" }
        if ($failedBuildText -match "Access token is unavailable|No valid Unity Editor license found|0 free entitlements") {
            throw "Unity batchmode did not receive a valid Hub license token. Keep Unity Hub signed in, open the main game-unity project once, then retry. See $BuildLog"
        }
        throw "Unity isolated build failed with exit code $buildExit. See $BuildLog"
    }
    if (-not (Test-Path -LiteralPath $Player)) { throw "Unity build did not create player: $Player" }
    $buildText = Get-Content -LiteralPath $BuildLog -Raw -Encoding UTF8
    if ($buildText -notmatch "Combat range smoke passed" -or
        $buildText -notmatch "Runtime run settings smoke passed" -or
        $buildText -notmatch "Character view resolver smoke passed") {
        throw "Unity editor smoke evidence is incomplete. See $BuildLog"
    }
    $result.compilation_passed = $true
    $result.editor_smoke_passed = $true

    Remove-Item -LiteralPath $Telemetry,$RepeatTelemetry -Force -ErrorAction SilentlyContinue
    $runArgs = "-batchmode -nographics --auto-run --seed $seed --config-input `"$Contract`" --telemetry-output `"$Telemetry`" -logFile `"$PlayerLog`""
    $runExit = Invoke-ProcessWithTimeout -FileName $Player -Arguments $runArgs -WorkingDirectory (Split-Path -Parent $Player) -TimeoutSeconds $RunTimeoutSeconds
    if ($runExit -ne 0 -or -not (Test-Path -LiteralPath $Telemetry)) {
        throw "Primary fixed-seed Player run failed. See $PlayerLog"
    }
    $repeatArgs = "-batchmode -nographics --auto-run --seed $seed --config-input `"$Contract`" --telemetry-output `"$RepeatTelemetry`" -logFile `"$RepeatPlayerLog`""
    $repeatExit = Invoke-ProcessWithTimeout -FileName $Player -Arguments $repeatArgs -WorkingDirectory (Split-Path -Parent $Player) -TimeoutSeconds $RunTimeoutSeconds
    if ($repeatExit -ne 0 -or -not (Test-Path -LiteralPath $RepeatTelemetry)) {
        throw "Repeated fixed-seed Player run failed. See $RepeatPlayerLog"
    }
    $result.player_runs_passed = $true

    . (Join-Path $RepositoryRoot "scripts\common.ps1")
    $ProjectPython = Resolve-ProjectPython -RepoRoot $RepositoryRoot
    $PythonService = Join-Path $RepositoryRoot "services\agent-python"
    Push-Location $PythonService
    try {
        & $ProjectPython -m gameconfig_agent.cli evaluate_milestone1_testbed --profile $Profile --telemetry $Telemetry --repeat-telemetry $RepeatTelemetry --output $ArtifactDir
        if ($LASTEXITCODE -ne 0) { throw "Fixed-seed repeatability evaluation failed." }
        & $ProjectPython -m gameconfig_agent.cli evaluate_unity_runtime --contract $Contract --telemetry $Telemetry --output $ArtifactDir
    }
    finally {
        Pop-Location
    }
    $repeatability = Get-Content -LiteralPath (Join-Path $ArtifactDir "testbed_evaluation.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    $runtimeEvaluation = Get-Content -LiteralPath (Join-Path $ArtifactDir "runtime_evaluation.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    $result.repeatability_passed = [bool]$repeatability.passed
    $result.repeatability_rate = [double]$repeatability.repeatability_rate
    $result.runtime_target_pass_rate = [double]$runtimeEvaluation.runtime_target_pass_rate
    $result.passed = $result.compilation_passed -and $result.editor_smoke_passed -and $result.player_runs_passed -and $result.repeatability_passed
}
catch {
    $result.error = [ordered]@{
        type = $_.Exception.GetType().Name
        message = $_.Exception.Message
    }
}
finally {
    $result.completed_at = [DateTimeOffset]::UtcNow.ToString("o")
    $result | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $ResultPath -Encoding UTF8
}

if (-not $result.passed) { exit 1 }
Write-Host "Isolated C# patch validation passed. Evidence: $ArtifactDir"
