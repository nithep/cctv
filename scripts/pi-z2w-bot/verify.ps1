# verify.ps1 — ตรวจทั้งหมดในคำสั่งเดียว: ffmpeg + python deps + syntax + config.yaml + pytest
# ใช้:
#   powershell -ExecutionPolicy Bypass -File scripts\pi-z2w-bot\verify.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\pi-z2w-bot\verify.ps1 -full   (+ เช็ค network จริง: health.py)
param([switch]$full)
$ErrorActionPreference = "Continue"
$scriptDir = $PSScriptRoot
$results = @()

function Step($name, $ok, $detail) {
    $script:results += [pscustomobject]@{ Step = $name; OK = $ok; Detail = $detail }
    $mark = if ($ok) { "PASS" } else { "FAIL" }
    Write-Host ("[{0}] {1} — {2}" -f $mark, $name, $detail)
}

Write-Host "=== CCTV Bot Verify ==="
Write-Host ""

# --- 1) ffmpeg ---
$ff = (Get-Command ffmpeg -ErrorAction SilentlyContinue).Source
if (-not $ff) {
    $ff = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg*\ffmpeg-*\bin\ffmpeg.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1).FullName
}
if ($ff) {
    $ver = (& $ff -version 2>&1 | Select-Object -First 1)
    Step "ffmpeg" $true "$ff ($ver)"
} else {
    Step "ffmpeg" $false "not found — run: powershell -ExecutionPolicy Bypass -File scripts\pi-z2w-bot\install-deps.ps1"
}

# --- 2) python + packages ---
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $py) {
    Step "python" $false "python not found — install from python.org (tick Add to PATH)"
} else {
    Step "python" $true $py
    $missing = @()
    foreach ($m in @("yaml", "requests", "telegram")) {
        & $py -c "import $m" 2>$null
        if ($LASTEXITCODE -ne 0) { $missing += $m }
    }
    if ($missing.Count -eq 0) {
        Step "python deps" $true "yaml, requests, telegram OK"
    } else {
        Step "python deps" $false "missing: $($missing -join ', ') — run install-deps.ps1"
    }
    # pytest: ไม่มีก็ติดตั้งให้เลย
    & $py -c "import pytest" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "       pytest ไม่มี — ติดตั้งให้อัตโนมัติ..."
        & $py -m pip install -q pytest
    }
    & $py -c "import pytest" 2>$null
    Step "pytest" ($LASTEXITCODE -eq 0) "pytest ready"

    # --- 3) syntax check (py_compile — ไม่รันโค้ด) ---
    & $py -m py_compile (Join-Path $scriptDir "bot.py") (Join-Path $scriptDir "health.py") (Join-Path $scriptDir "check-config.py") 2>$null
    Step "syntax (py_compile)" ($LASTEXITCODE -eq 0) "bot.py, health.py, check-config.py"

    # --- 4) config.yaml เทียบ example ---
    & $py -X utf8 (Join-Path $scriptDir "check-config.py")
    Step "config.yaml vs example" ($LASTEXITCODE -eq 0) "รายละเอียดด้านบน (❌ = คีย์ขาด, ⚠️ = ควรเพิ่ม)"

    # --- 5) pytest health alert ---
    & $py -X utf8 -m pytest (Join-Path $scriptDir "test_health_alerts.py") -v --tb=short
    Step "pytest health alerts" ($LASTEXITCODE -eq 0) "ดูผลด้านบน"
}

# --- 6) (ทางเลือก -full) เช็ค network จริงผ่าน health.py ---
if ($full -and $py) {
    Write-Host ""
    Write-Host "=== [-full] network check: health.py (NVR + IPC + RTSP probe) ==="
    Push-Location $scriptDir
    & $py -X utf8 health.py
    Step "network (health.py)" ($LASTEXITCODE -eq 0) "ผลจริงด้านบน"
    Pop-Location
}

# --- สรุป ---
Write-Host ""
Write-Host "=== SUMMARY ==="
$fail = 0
foreach ($r in $results) {
    $mark = if ($r.OK) { "✅" } else { $fail++; "❌" }
    Write-Host "$mark $($r.Step)"
}
if ($fail -eq 0) {
    Write-Host ""
    Write-Host "ผ่านทั้งหมด 🎉 — เริ่มบอท: powershell -ExecutionPolicy Bypass -File scripts\pi-z2w-bot\start-bot.ps1"
    exit 0
} else {
    Write-Host ""
    Write-Host "มี $fail รายการไม่ผ่าน — แก้ตาม detail ด้านบน หรือก๊อป output ทั้งหมดให้ Buffy แก้ให้"
    exit 1
}
