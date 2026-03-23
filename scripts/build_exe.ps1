param(
    [string]$Python = "python",
    [string]$Name = "instaDow"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repoRoot
try {
    & $Python -m pip install -e ".[build]"
    & $Python -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --name $Name `
        --paths src `
        --collect-all yt_dlp `
        --collect-all instaloader `
        src/instadow/__main__.py

    Write-Host ""
    Write-Host "Build xong: dist\$Name.exe"
}
finally {
    Pop-Location
}
