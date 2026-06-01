param(
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$releaseRoot = Join-Path $repoRoot "dist\release"
$packageName = "RimDataAnalysis-v$Version-windows"
$packageDir = Join-Path $releaseRoot $packageName
$zipPath = Join-Path $releaseRoot "$packageName.zip"

python -m pip install -e .[dev]
python -B -m pytest -q

if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
}
if (Test-Path "dist\RimDataAnalysis") {
    Remove-Item -Recurse -Force "dist\RimDataAnalysis"
}
if (Test-Path $packageDir) {
    Remove-Item -Recurse -Force $packageDir
}
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

python -m PyInstaller `
    --noconfirm `
    --clean `
    --name RimDataAnalysis `
    --windowed `
    --collect-all rim_data_analysis `
    "scripts\launch_desktop.py"

New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null
Move-Item -Path "dist\RimDataAnalysis" -Destination $packageDir
Copy-Item -Path "USER-GUIDE.txt" -Destination (Join-Path $packageDir "USER-GUIDE.txt")
Copy-Item -Path "RELEASE-v$Version.md" -Destination (Join-Path $packageDir "RELEASE-v$Version.md")

Compress-Archive -Path (Join-Path $packageDir "*") -DestinationPath $zipPath -Force

Write-Host "Release package created:"
Write-Host $zipPath
