[CmdletBinding()]
param(
    [switch]$NoLaunch
)

$ErrorActionPreference = "Stop"
$AppRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Pythonw = Join-Path $AppRoot ".venv\Scripts\pythonw.exe"
$EntryPoint = Join-Path $AppRoot "main.py"
$Icon = Join-Path $AppRoot "assets\aginti-hardware-console.ico"

foreach ($required in ($Pythonw, $EntryPoint, $Icon)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required application file is missing: $required"
    }
}

function New-AppShortcut {
    param([Parameter(Mandatory)][string]$Path)
    $folder = Split-Path -Parent $Path
    New-Item -ItemType Directory -Force -Path $folder | Out-Null
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($Path)
    $shortcut.TargetPath = $Pythonw
    $shortcut.Arguments = '"' + $EntryPoint + '"'
    $shortcut.WorkingDirectory = $AppRoot
    $shortcut.IconLocation = $Icon + ",0"
    $shortcut.Description = "AgInTi laboratory hardware digital twin and control workbench"
    $shortcut.WindowStyle = 1
    $shortcut.Save()
}

$DesktopLink = Join-Path ([Environment]::GetFolderPath("Desktop")) "AgInTi Hardware Console.lnk"
$StartLink = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\AgInTi Hardware Console.lnk"
New-AppShortcut -Path $DesktopLink
New-AppShortcut -Path $StartLink

$Pinned = $false
try {
    $shellApp = New-Object -ComObject Shell.Application
    $folder = $shellApp.Namespace((Split-Path -Parent $StartLink))
    $item = $folder.ParseName((Split-Path -Leaf $StartLink))
    $pinVerb = $item.Verbs() | Where-Object {
        ($_.Name -replace "&", "") -match "(?i)pin to taskbar|固定到任务栏"
    } | Select-Object -First 1
    if ($pinVerb) {
        $pinVerb.DoIt()
        $Pinned = $true
    }
} catch {
    $Pinned = $false
}

Write-Output "DesktopShortcut=$DesktopLink"
Write-Output "StartMenuShortcut=$StartLink"
Write-Output "TaskbarPinRequested=$Pinned"

if (-not $NoLaunch) {
    Start-Process -FilePath $DesktopLink
}
