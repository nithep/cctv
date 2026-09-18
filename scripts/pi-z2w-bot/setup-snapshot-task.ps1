# setup-snapshot-task.ps1 — ตั้ง scheduled task: snapshot ทุกชั่วโมง + หลังรีบูต/logon
# รันครั้งเดียวพอ:
#   powershell -ExecutionPolicy Bypass -File scripts\pi-z2w-bot\setup-snapshot-task.ps1
# ถ้าโดน Access denied ให้เปิด PowerShell เป็น Administrator แล้วรันอีกครั้ง
$ErrorActionPreference = "Stop"

$taskName = "CCTV Snapshot Hourly"
$script = Join-Path $PSScriptRoot "snapshot-hourly.ps1"
if (-not (Test-Path $script)) { Write-Warning "ไม่พบ $script"; exit 1 }

# Action: รันสคริปต์โหมด -once (ถ่ายรอบเดียวแล้วจบ — Task Scheduler เป็นคนจับเวลาทุกชั่วโมง)
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`" -once"

# Trigger 1: ทุกครั้งที่ logon (ครอบคลุมหลังรีบูต — รันใน session ของผู้ใช้ เพื่อเห็น Google Drive)
$user = "$env:USERDOMAIN\$env:USERNAME"
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn -User $user

# Trigger 2: เริ่มใน 1 นาที แล้วซ้ำทุกชั่วโมงตลอดไป
$triggerHourly = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Hours 1)
try { $triggerHourly.Repetition.Duration = [TimeSpan]::MaxValue } catch { Write-Warning "ตั้ง repeat ตลอดไปไม่ได้ — task จะซ้ำตามค่าเริ่มต้นของ Windows" }

# Settings: รับช่วงต่อถ้าพลาด, รันซ้ำไม่เกิน 1 instance, ตัด instance ค้างเกิน 10 นาที
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) `
    -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

Register-ScheduledTask -TaskName $taskName -Action $action `
    -Trigger $triggerLogon, $triggerHourly -Settings $settings `
    -Description "CCTV hourly snapshot จาก 192.168.1.21 ไป Google Drive (หา ffmpeg เอง, รันใหม่หลังรีบูต)" `
    -Force | Out-Null

Write-Host ""
Write-Host "ตั้ง task '$taskName' เรียบร้อย ✅"
Write-Host "  - ถ่ายครั้งแรกใน 1 นาที แล้วทุกชั่วโมง + ทุกครั้งที่ logon/รีบูต (user: $user)"
Write-Host "  - พลาดแล้ว retry เอง 3 ครั้ง (ห่างกัน 5 นาที), กันรันซ้อนหลาย instance"
Write-Host ""
Write-Host "ทดสอบเดี๋ยวนี้ : Start-ScheduledTask -TaskName '$taskName'"
Write-Host "ดูผลล่าสุด     : Get-ScheduledTaskInfo -TaskName '$taskName'"
Write-Host "ลบ task       : Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false"
