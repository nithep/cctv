# start-bot.ps1 — start CCTV bot (auto-find ffmpeg, survives winget version changes / reinstall)
$ErrorActionPreference = "Continue"

# 1) find ffmpeg: PATH first, then any Gyan.FFmpeg version under WinGet folder
$ffPath = (Get-Command ffmpeg -ErrorAction SilentlyContinue).Source
if (-not $ffPath) {
    $ffPath = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg*\ffmpeg-*\bin\ffmpeg.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1).FullName
}
if ($ffPath) {
    $env:Path += ';' + (Split-Path $ffPath -Parent)
    Write-Host "ffmpeg: $ffPath"
} else {
    Write-Warning "ffmpeg not found - run install-deps.ps1 first (bot still starts, but /snapshot /clip won't work)"
}

# 2) cd to the root the bot expects (supports both T.C.Com\cctv layout and plain repo)
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (Test-Path (Join-Path (Split-Path $repo -Parent) 'cctv')) {
    Set-Location (Split-Path $repo -Parent)   # old layout: T.C.Com\cctv\...
    $botRel = 'cctv/scripts/pi-z2w-bot/bot.py'
    $logDir = 'cctv/output/logs'
} else {
    Set-Location $repo
    $botRel = 'scripts/pi-z2w-bot/bot.py'
    $logDir = 'output/logs'
}

# 3) start bot + append log
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
python -X utf8 $botRel 2>&1 | Tee-Object -Append (Join-Path $logDir 'bot.log')
