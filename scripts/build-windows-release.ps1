param(
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$desktopRoot = Join-Path $repoRoot "desktop\app"
$backendDist = Join-Path $desktopRoot "build\backend"
$electronRelease = Join-Path $desktopRoot "release"
$pyinstallerWork = Join-Path $repoRoot "build\pyinstaller-web-api"
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$python = if (Test-Path $venvPython) { $venvPython } else { "python" }

function Invoke-Checked {
    param(
        [string]$Description,
        [scriptblock]$Command
    )

    Write-Host $Description
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE"
    }
}

Set-Location $repoRoot

Invoke-Checked "Installing Python package and release tooling..." {
    & $python -m pip install -e ".[dev]"
}

Invoke-Checked "Running Python tests..." {
    & $python -B -m pytest -q
}

if (Test-Path $backendDist) {
    Remove-Item -Recurse -Force $backendDist
}
if (Test-Path $pyinstallerWork) {
    Remove-Item -Recurse -Force $pyinstallerWork
}
if (Test-Path $electronRelease) {
    Remove-Item -Recurse -Force $electronRelease
}

Invoke-Checked "Building packaged Python API backend..." {
    & $python -m PyInstaller `
        --noconfirm `
        --clean `
        --name rim-analysis-web-api `
        --onefile `
        --console `
        --collect-all rim_data_analysis `
        --distpath $backendDist `
        --workpath $pyinstallerWork `
        --specpath $pyinstallerWork `
        "scripts\launch_web_api.py"
}

Set-Location $desktopRoot

Invoke-Checked "Installing Electron dependencies..." {
    npm install
}

Invoke-Checked "Running Electron typecheck..." {
    npm run typecheck
}

$env:RIM_DATA_ANALYSIS_RELEASE_VERSION = $Version
Invoke-Checked "Building Windows desktop application..." {
    npm run dist:win
}

$unpackedDir = Join-Path $electronRelease "win-unpacked"
$zipPath = Join-Path $electronRelease "RimDataAnalysis-v$Version-windows-x64.zip"
if (!(Test-Path $unpackedDir)) {
    throw "Electron unpacked output was not created: $unpackedDir"
}
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

Write-Host "Creating release zip..."
Compress-Archive -Path (Join-Path $unpackedDir "*") -DestinationPath $zipPath -Force

Write-Host "Release package created:"
Write-Host $zipPath
