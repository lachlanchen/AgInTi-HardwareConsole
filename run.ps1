param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$AppRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvRoot = Join-Path $AppRoot ".venv"
$Python = Join-Path $VenvRoot "Scripts\python.exe"
$ReadyMarker = Join-Path $VenvRoot ".hardware-console-ready"

if (-not (Test-Path $Python)) {
    python -m venv $VenvRoot
}

if (-not $SkipInstall -and -not (Test-Path $ReadyMarker)) {
    & $Python -m pip install --upgrade pip
    & $Python -m pip install -r (Join-Path $AppRoot "requirements.txt")
    New-Item -ItemType File -Force -Path $ReadyMarker | Out-Null
}

& $Python (Join-Path $AppRoot "main.py")
