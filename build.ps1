#Requires -Version 5.1
$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

$version = python -c "from version import __version__; print(__version__)"
if (-not $version) {
    throw "Не удалось прочитать __version__ из version.py"
}

$appName = "ChatList"
$exeName = "$appName-$version"

Write-Host "Сборка $appName версии $version..."

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

Write-Host "Исполняемый файл: dist\$exeName.exe"

$iscc = Get-Command iscc -ErrorAction SilentlyContinue
if ($iscc) {
    Write-Host "Сборка установщика..."
    & iscc "/DAppVersion=$version" installer.iss
    Write-Host "Установщик: dist\$appName-$version-setup.exe"
}
else {
    Write-Host "Inno Setup (iscc) не найден — установщик не собран."
    Write-Host "Установите Inno Setup и добавьте iscc в PATH для сборки установщика."
}
