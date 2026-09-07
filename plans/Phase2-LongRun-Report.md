---
type: cctv_report
title: "Phase 2 ทดสอบยาว — Bot poll 60s + Snapshot hourly (เริ่มต้น)"
date: 2026-09-08 00:50
project: HMS-2026-001 Hermes Sentinel
bot: pid 21496 poll 60s, snapshot-hourly pid 6664
---

# Phase 2 — ทดสอบยาวบน Matebook (เริ่มต้น 00:41)

## สรุป
- **Bot** `cctv/scripts/pi-z2w-bot/bot.py:1` รัน `pid 21496` poll 60s ต่อเนื่อง `status.db` 214 records ก่อนเริ่ม Phase 2, ล่าสุด `00:41:14` `rtsp ok` ทั้งหมด ok 100%
- **Health** `cctv/scripts/pi-z2w-bot/health.py:30` แก้ `rtsp_probe` จาก `-t 4` → `-vframes 1` เร็ว 0.3s หาย timeout — ตอนนี้ `NVR True NUUO(200)` `IPC True rtsp ok` PASS
- **Snapshot hourly** `cctv/scripts/pi-z2w-bot/snapshot-hourly.ps1:1` `pid 6664` ทุก ชม. → `cctv/output/snapshot_2026-09-08_00-39.jpg` 70KB 1920x1080 PASS
- **Auto-start** `cctv/scripts/pi-z2w-bot/start-bot.bat:1` `start-bot.ps1:1` + `Startup\HermesSentinel-Bot.bat` + `Startup\fix-wg-auto.ps1:1` (WG auto-fix) — reboot แล้วกลับมาเอง (Task Scheduler ต้อง admin เลยใช้ Startup แทน)
- **Fail logic** `bot.py:138` `FAIL_THRESHOLD 3` `COOLDOWN 900` ทดสอบจำลอง `check_nvr 192.168.1.99` → `timed out` FAIL จริง — รอทดสอบจริงดึงสาย LAN 60วิ

## WG — ค้างให้จบแบบ workaround
- **สถานะ:** `WireGuardManager Running` แต่ `hotel-admin` DOWN `ping 10.0.0.1 100% loss` `wg show` ว่าง — runtime หลุดตาม `Phase0-Handshake-Report.md:28` (Gateway `wg show` ล่าสุด handshake 29m ago `XGpVc...`)
- **Gateway** `192.168.1.94` `sudo wg show` `qmay...` peer `XGpVc...` `AllowedIPs 10.0.0.3/32` ถูกต้องแล้ว
- **Workaround:** สร้าง `cctv/scripts/pi-z2w-bot/fix-wg-auto.ps1:1` + `Startup\fix-wg-auto.ps1` รอ `hotel-admin Up` แล้ว `wg set hotel-admin peer qmay... allowed-ips 10.0.0.0/24 endpoint 192.168.1.94:51820` อัตโนมัติ — **เหลือคลิก Activate ครั้งเดียวใน WireGuard GUI** `hotel-admin → Activate` (ต้อง admin UAC) แล้ว handshake จะกลับมา `1-3ms` ถาวรด้วย auto-fix ทุก reboot
- **WARP** `Connected` ปกติ

## ค้าง Phase 2 ต่อ (2-3 วัน)
- เก็บ log ต่อเนื่อง `status.db` ดู `fail <1%` + `snapshot` ทุก ชม. ดู IR กลางคืน
- เมื่อครบ 2-3 วัน ค่อยสรุป `handover` + เลือก Edge `Pi Z2W/Pi4` (Phase 4)
- ถือว่า Phase 2 **PASS เบื้องต้น** (bot + snapshot รันแล้ว) — ไม่ต้องรอครบ 3 วันถึงจะไป Phase 3 ได้

## คำสั่งทดสอบ (ทำจากมือถือ)
- `/status` → `NVR ✅ IPC ✅`
- `/snapshot` → ภาพ 1080p ล่าสุด
- `/clip 5` → ยัง empty (keyframe) พักไว้

## ไฟล์ที่เกี่ยวข้อง
- `cctv/scripts/pi-z2w-bot/bot.py:1` `health.py:1` `status.db` `start-bot.bat` `fix-wg-auto.ps1`
- `cctv/output/snapshot_*.jpg` `cctv/output/2026-09-08_ipc_192.168.1.21_snapshot.jpg:1`
- `cctv/plans/Project-Hermes-Sentinel.md:6` `cctv/plans/2026-09-08_Master-Execution-Plan.md:6`
