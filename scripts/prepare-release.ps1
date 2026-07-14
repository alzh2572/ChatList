#Requires -Version 5.1
<#
.SYNOPSIS
  Локальная подготовка артефактов для GitHub Release.

.EXAMPLE
  .\scripts\prepare-release.ps1
  .\scripts\prepare-release.ps1 -SkipBuild
#>
param(
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$version = python -c "from version import __version__; print(__version__)"
if (-not $version) {
    throw "Cannot read __version__ from version.py"
}

Write-Host "Preparing release v$version"

if (-not $SkipBuild) {
    & .\build.ps1
}

$artifacts = @(
    "dist/ChatList-$version-setup.exe",
    "dist/ChatList-$version.exe"
)

foreach ($file in $artifacts) {
    if (-not (Test-Path $file)) {
        throw "Artifact not found: $file"
    }
}

$checksumLines = foreach ($file in $artifacts) {
    $hash = (Get-FileHash $file -Algorithm SHA256).Hash
    "$hash  $(Split-Path $file -Leaf)"
}
$checksumLines | Set-Content -Encoding utf8 "dist/checksums.txt"
Write-Host "Created dist/checksums.txt"

$template = Get-Content ".github/RELEASE_NOTES.template.md" -Raw -Encoding UTF8
$notes = $template -replace '\{\{VERSION\}\}', $version
$notes | Set-Content -Encoding utf8 "dist/RELEASE_NOTES.md"
Write-Host "Created dist/RELEASE_NOTES.md"

Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Update 'What is new' section in dist/RELEASE_NOTES.md"
Write-Host "  2. git add version.py && git commit -m 'Release v$version'"
Write-Host "  3. git tag v$version && git push origin main --tags"
Write-Host "  4. GitHub Actions will publish Release automatically"
Write-Host ""
Write-Host "Or publish manually:"
Write-Host "  gh release create v$version dist/ChatList-$version-setup.exe dist/ChatList-$version.exe dist/checksums.txt --notes-file dist/RELEASE_NOTES.md"
