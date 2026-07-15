[CmdletBinding()]
param(
    [string]$Version = "0.1.0"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$BuildVenv = Join-Path $Root ".build-venv"
$Python = Join-Path $BuildVenv "Scripts\python.exe"
$PyInstaller = Join-Path $BuildVenv "Scripts\pyinstaller.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    $Bootstrap = (Get-Command python.exe -ErrorAction Stop).Source
    & $Bootstrap -m venv $BuildVenv
}

& $Python -m pip install --disable-pip-version-check -r (Join-Path $Root "requirements-build.txt")
& $Python (Join-Path $Root "scripts\build_icon.py")

Push-Location $Root
try {
    & $PyInstaller --noconfirm --clean --windowed --onedir `
        --contents-directory . `
        --name "AgInTi-HardwareConsole" `
        --icon "assets\aginti-hardware-console.ico" `
        --add-data "assets;assets" `
        --add-data "device_profiles;device_profiles" `
        --add-data "schemas;schemas" `
        --hidden-import "serial.tools.list_ports" `
        "main.py"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $Release = Join-Path $Root "release"
    New-Item -ItemType Directory -Force -Path $Release | Out-Null
    $Zip = Join-Path $Release "AgInTi-HardwareConsole-windows-x64-v$Version.zip"
    Remove-Item -LiteralPath $Zip -Force -ErrorAction SilentlyContinue
    Compress-Archive -Path (Join-Path $Root "dist\AgInTi-HardwareConsole\*") -DestinationPath $Zip -CompressionLevel Optimal
    Write-Output $Zip
} finally {
    Pop-Location
}
