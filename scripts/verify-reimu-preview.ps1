param(
    [string]$ImagePath = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not $ImagePath) { $ImagePath = Join-Path $RepoRoot "runtime-artifacts\reimu-import\reimu_runtime_preview.png" }
if (-not (Test-Path -LiteralPath $ImagePath)) { throw "Reimu preview image was not found: $ImagePath" }

Add-Type -AssemblyName System.Drawing
$bitmap = New-Object System.Drawing.Bitmap($ImagePath)
try {
    if ($bitmap.Width -lt 640 -or $bitmap.Height -lt 360) { throw "Reimu preview resolution is too small." }
    $background = $bitmap.GetPixel(0, 0)
    $sampleCount = 0
    $nonBackground = 0
    $redPixels = 0
    $brightCenterPixels = 0
    for ($y = 0; $y -lt $bitmap.Height; $y += 2) {
        for ($x = 0; $x -lt $bitmap.Width; $x += 2) {
            $pixel = $bitmap.GetPixel($x, $y)
            $sampleCount++
            $difference = [Math]::Abs($pixel.R - $background.R) + [Math]::Abs($pixel.G - $background.G) + [Math]::Abs($pixel.B - $background.B)
            if ($difference -gt 24) { $nonBackground++ }
            if ($pixel.R -gt 150 -and $pixel.R -gt ($pixel.G * 1.25) -and $pixel.R -gt ($pixel.B * 1.15)) { $redPixels++ }
            $inCenter = $x -ge ($bitmap.Width * 0.38) -and $x -le ($bitmap.Width * 0.62) -and $y -ge ($bitmap.Height * 0.42) -and $y -le ($bitmap.Height * 0.78)
            if ($inCenter -and ($pixel.R + $pixel.G + $pixel.B) -gt 420) { $brightCenterPixels++ }
        }
    }
    $nonBackgroundRate = $nonBackground / $sampleCount
    if ($nonBackgroundRate -lt 0.08) { throw "Reimu preview appears blank or severely under-rendered." }
    if ($redPixels -lt 250) { throw "Reimu preview does not contain enough red presentation pixels." }
    if ($brightCenterPixels -lt 100) { throw "Reimu character is not visibly framed near the center." }

    $report = [ordered]@{
        status = "passed"
        image_path = (Resolve-Path -LiteralPath $ImagePath).Path
        width = $bitmap.Width
        height = $bitmap.Height
        sample_count = $sampleCount
        non_background_rate = $nonBackgroundRate
        red_pixels = $redPixels
        bright_center_pixels = $brightCenterPixels
    }
    $reportPath = Join-Path (Split-Path -Parent $ImagePath) "preview_pixel_report.json"
    $report | ConvertTo-Json | Set-Content -LiteralPath $reportPath -Encoding UTF8
    Write-Host "Reimu preview pixel validation passed."
    Write-Host "Report: $reportPath"
}
finally {
    $bitmap.Dispose()
}
