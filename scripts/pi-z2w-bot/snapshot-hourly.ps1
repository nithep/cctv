# snapshot-hourly.ps1 - hourly snapshot to Google Drive (auto-find ffmpeg, survives reinstall)
# โหมดปกติ (ไม่ใส่ flag): ถ่ายแล้ววนลูปทุกชั่วโมง — ใช้รันมือเอง
# โหมด -once: ถ่ายครั้งเดียวแล้วออก — ใช้กับ scheduled task (task เป็นคนจับเวลาทุกชั่วโมงเอง)
param([switch]$once)
$ErrorActionPreference = "Continue"

# find ffmpeg: PATH first, then any Gyan.FFmpeg version under WinGet folder
$ff = (Get-Command ffmpeg -ErrorAction SilentlyContinue).Source
if (-not $ff) {
    $ff = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg*\ffmpeg-*\bin\ffmpeg.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1).FullName
}
if (-not $ff) { Write-Warning "ffmpeg not found - run install-deps.ps1 first"; exit 1 }

$drive = "$env:USERPROFILE\ไดรฟ์ของฉัน (cnithep@gmail.com)\T.C.Com\cctv\output"
New-Item -ItemType Directory -Force -Path $drive | Out-Null

function Take-Snapshot {
    $ts = Get-Date -Format "yyyy-MM-dd_HH-mm"
    $out = Join-Path $drive "snapshot_$ts.jpg"
    & $ff -y -hide_banner -loglevel error -rtsp_transport tcp -i rtsp://admin:123456@192.168.1.21:554/0 -vframes 1 -q:v 2 "$out" 2>&1 | Out-Null
    if (Test-Path "$out") {
        Write-Host "$(Get-Date -Format HH:mm) snapshot $out $((Get-Item "$out").Length) bytes"
        return $true
    }
    Write-Warning "$(Get-Date -Format HH:mm) snapshot FAILED (RTSP no answer)"
    return $false
}

if ($once) {
    Take-Snapshot | Out-Null
    exit 0
}

while ($true) {
    Take-Snapshot | Out-Null
    Start-Sleep -Seconds 3600
}
