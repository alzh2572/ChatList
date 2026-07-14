#Requires -Version 5.1
$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

function Get-IsccPath {
    $cmd = Get-Command iscc -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) {
            return $path
        }
    }
    return $null
}

$version = python -c "from version import __version__; print(__version__)"
if (-not $version) {
    throw "Cannot read __version__ from version.py"
}

$appName = "ChatList"
$exeName = "$appName-$version"

Write-Host "Building $appName $version..."

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    pip install pyinstaller
}

pyinstaller `
    --noconfirm `
    --onefile `
    --windowed `
    --name $exeName `
    --icon app.ico `
    main.py

Write-Host "Executable: dist\$exeName.exe"

$iscc = Get-IsccPath
if (-not $iscc) {
    throw "Inno Setup not found. Run: winget install JRSoftware.InnoSetup"
}

Write-Host "Building installer..."
& $iscc "/DAppVersion=$version" installer.iss
Write-Host "Installer: dist\$appName-$version-setup.exe"
