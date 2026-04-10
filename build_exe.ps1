param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Set-Location $ProjectRoot

if ($Clean) {
    Remove-Item -LiteralPath "$ProjectRoot\build" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath "$ProjectRoot\dist" -Recurse -Force -ErrorAction SilentlyContinue
}

python -m pip install --upgrade -r requirements-build.txt
pyinstaller --clean --noconfirm douyin_downloader.spec

Write-Host ""
Write-Host "Build finished."
Write-Host "EXE path: $ProjectRoot\dist\douyin-collection-downloader.exe"
