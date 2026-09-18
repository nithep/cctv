# ติดตั้ง dependencies ทั้งหมดของ CCTV bot บน Windows (ffmpeg + Python packages)
# ใช้: powershell -ExecutionPolicy Bypass -File scripts\pi-z2w-bot\install-deps.ps1
$ErrorActionPreference = "Continue"

function Find-FFmpeg {
    $c = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    $p = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg*\ffmpeg-*\bin\ffmpeg.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1
    if ($p) { return $p.FullName }
    return $null
}

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if (-not $py) {
    Write-Warning "ไม่พบ python — ติดตั้งจาก https://www.python.org/downloads/ (ติ๊ก Add to PATH) แล้วรันสคริปต์นี้ใหม่"
    exit 1
}

Write-Host "== 1) ffmpeg =="
$ff = Find-FFmpeg
if ($ff) {
    Write-Host "พบอยู่แล้ว: $ff"
} else {
    Write-Host "ไม่พบ ffmpeg — ติดตั้งผ่าน winget (Gyan.FFmpeg) ..."
    winget install --id Gyan.FFmpeg -e --source winget --accept-source-agreements --accept-package-agreements
    $ff = Find-FFmpeg
    if ($ff) { Write-Host "ติดตั้งสำเร็จ: $ff" }
    else { Write-Warning "ติดตั้ง ffmpeg ไม่สำเร็จ — รัน 'winget install Gyan.FFmpeg' เอง แล้วรันสคริปต์นี้ใหม่" }
}

Write-Host ""
Write-Host "== 2) Python packages (requirements.txt) =="
& $py.Source -X utf8 -m pip install --upgrade pip
& $py.Source -X utf8 -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")

Write-Host ""
Write-Host "== 3) (ทางเลือก) AI ตรวจจับคน YOLOv8n =="
$ans = Read-Host "ติดตั้ง ultralytics + opencv-python ด้วยไหม (สำหรับ /person, ดาวน์โหลด ~2GB)? [y/N]"
if ($ans -match '^[Yy]') {
    & $py.Source -X utf8 -m pip install ultralytics opencv-python
}

Write-Host ""
Write-Host "== 4) ตรวจสอบ =="
if ($ff) { & $ff -version | Select-Object -First 1 }
& $py.Source -X utf8 -c "import yaml, requests, telegram; print('python deps OK')"

Write-Host ""
Write-Host "เสร็จ — เริ่มบอทด้วย start-bot.ps1 (หา ffmpeg เองอัตโนมัติ ไม่ต้องแก้ path)"
