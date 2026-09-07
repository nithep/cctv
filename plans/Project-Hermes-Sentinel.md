---
type: cctv_project
title: "Hermes Sentinel — โครงการคืนชีพ CCTV ตกรุ่นไร้ Support"
project_code: HMS-2026-001
date: 2026-09-08
status: Phase 5 ✅ DONE ส่งมอบ — handover 2026-09-08 + verify ALL PASS + status.db 338 ok (handover-2026-09-08.md)
updated: 2026-09-08 01:49
nvr: NUUO NVRmini 2 NE-2020 fw 03.11.00 (2020, EOL) Always 10% 338 records ok 100%
ipc: Seetong IPC LIVE555 gSOAP/2.8 IPCConfig 2.0.0.31 (2014, EOL) rtsp://admin:123456@192.168.1.21:554/0 1080p rtsp ok
agent: @hm2569bot (hermes) 7346817215 poll 60s + person_watch 30s YOLOv8n 8.4.143 (bus 3คน + demo 6เฟรม 0คน + handover)
wg: hotel-admin 10.0.0.3/24 → 192.168.1.94:51820 qmay.../XGpVc... DOWN (Manager Running ต้อง Activate GUI 5นาที) — LAN 192.168.1.31 1ms ใช้สาธิต — WARP Connected
---

# Hermes Sentinel — คืนชีพ NVR+IPC ตกรุ่นไร้ Support ด้วย Agent

> ชื่อโปรเจ็ค: **Hermes Sentinel** (ผู้ส่งสารเฝ้ายาม) — สื่อถึง `@hm2569bot hermes` ที่เฝ้า NVR/IPC เก่าให้กลับใช้งานได้ปลอดภัย
> ทางเลือกชื่อ: `NVR Revival — Sentinel Edge` / `T.C.Com CCTV Lifeline` — เลือก **Hermes Sentinel** เพราะตรงกับ bot ที่มีอยู่

## 1) วิเคราะห์ของตกรุ่น (ทำไมต้องมี Agent)

| อุปกรณ์ | อายุ / สถานะ | ความเสี่ยงหลัก | ผลกระทบถ้าไม่ทำอะไร |
|---|---|---|---|
| **NUUO NVRmini 2 fw 03.11.00 (2020)** `lighttpd 1.4.48 PHP7.4.1` | EOL 4-5 ปี, ไม่มี fw ใหม่, `SUPPORT_SYSTEM_SETTING true` แต่ `SUPPORT_TRIAL false` | **CVE-2018-1149 Peekaboo RCE** ผ่าน `cgi_system PHPSESSID` overflow + `handle_import_user.php` path traversal (Tenable TRA-2018-25, CVE-2011-5325 busybox 1.16.1) — ถ้าเปิด 8000 ออกเน็ต โดนยึดทั้งเครื่อง + รหัสกล้องหลุด plain text | โดนแฮก, กล้องดูไม่ได้, HDD เสียไม่รู้ |
| **Seetong IPC LIVE555 gSOAP/2.8 IPCConfig 2.0.0.31 (2014)** `2014-01-06` | 12 ปี, ไม่มี support, Web ต้อง ActiveX, DNS `203.113.111.162` TOT | RTSP `admin/123456` ยังใช้ได้แต่โค้ดเก่า, Cloud `1666840.seetong.com` ผูก TOT DNS — ถ้าเน็ตล่ม Cloud ดับ, ไม่มี AI, ไม่มี update | ภาพหาย, RTSP หลุด, ต้องพึ่ง UC2 4.7 ตัวเก่า |
| **ร่วมกัน** `MaxIPCam 2` `192.168.1.31:8000` `192.168.1.21:554` | 2 ช่องเท่านั้น, ขยายไม่ได้, `Always` ตลอด | ดิสก์เต็มวนทับ 10% ไม่มีแจ้งเตือนนอกสถานที่, ดูย้อนหลังต้อง ActiveX IE | เสียโอกาส, ส่งมอบไม่ได้ |

**สรุป:** ของเก่า **ใช้งานได้แต่เปราะ** — ต้องมี **Agent เฝ้าแทน vendor** (poll, แจ้งเตือน, ดึงไฟล์ On-Demand, กันภัย)

## 2) บทบาท Agent Hermes (ทำแทน Support ที่หายไป)

```
[Vendor เดิม หาย] → [Agent hermes @hm2569bot] ทำแทน:
  - Health Check 60s: tcp/http/rtsp (health.py)
  - แจ้งเตือน Telegram 7346817215 เมื่อ NVR/IPC ดับ
  - ดึงภาพล่าสุด / clip ย้อนหลัง On-Demand (ffmpeg rtsp://.../0)
  - กันภัย: ไม่เปิด 8000 ออก WAN, บังคับผ่าน WireGuard, WARP กัน DNS
  - เก็บ log/status.db แทน vendor log
```

## 3) ผล Phase 0 (สำเร็จ 2026-09-08 23:45 — รายงาน `Phase0-Handshake-Report.md:1`)

| ตรวจ | ผล | แปล |
|---|---|---|
| `WireGuard hotel-admin` `Get-Service Running` `NetAdapter hotel-admin Up 10.0.0.3/24` | ✅ **Tunnel Up แต่ Peer เงียบ (ก่อนแก้)** `ping 10.0.0.1 100% loss` | Interface ติดแล้ว แต่ key ไม่ตรง — Peer เงียบ |
| **หลังแก้คีย์ A** `wg show both latest handshake 12-37s` `transfer 1KiB` | ✅ **Handshake สำเร็จ** `ping 10.0.0.1 1-3ms 0% loss` `Test-NetConnection 10.0.0.1:3000 True` | Gateway `XGpVc...` ↔ Matebook `qmay...` ตรงแล้ว ผ่าน WG ถึง `hotel-app:3000` ได้ |
| `Cloudflare WARP` `Process 7152 Running` `warp-cli status: Connected` | ✅ **WARP Connected** | ขาออก Bot→Telegram เสถียร |
| `NVR .31` `admin/admin` `IPC .21` `admin/123456` `ffmpeg /0 1080p` | ✅ ยังเข้าได้ | ของเก่ายังรอด |

**Phase 0 สรุป:** `WARP พร้อม, WG Handshake สำเร็จ (runtime)` — **ค้างให้ถาวร:** ต้องแก้ `hotel-admin.conf.dpapi` ใน WireGuard GUI `Peer Public key cseC7... → qmay...` ไม่งั้น reboot แล้วหลุด (Gateway แก้ถาวรแล้ว `wg0.conf` มี `XGpVc...`)

## 4) แผนต่อ (ตาม Master Plan 6 เฟส — อัปเดต 01:49 Phase 5 DONE)

- **เฟส 0 ต่อ (ค้างให้ถาวร 5 นาที):** แก้ `hotel-admin.conf.dpapi` ใน GUI `cseC7... → qmay...` → Save → Activate → ยืนยัน `wg show handshake` หลัง reboot (สาธิตย้อนหลังผ่าน LAN แล้ว — WG ทำให้ดูจากนอกบ้านได้) — รายละเอียด `handover-2026-09-08.md:3`
- **เฟส 1 ✅ PASS (00:40):** `/snapshot` 71KB `ffmpeg -vframes 1` → `sendPhoto 7346817215 msg 19,20` สำเร็จ, `health.py:30` แก้ fallback ffmpeg + `_ffmpeg_bin()` แล้ว `rtsp ok`
- **เฟส 2 ✅ PASS เบื้องต้น (00:51):** บอท `pid 21496` poll 60s + `snapshot-hourly.ps1 pid 6664` ทุก ชม. → `cctv/output/snapshot_*.jpg` + `status.db` 338 records ทั้งหมด ok 100%, รายงาน `Phase2-LongRun-Report.md:1`
- **เฟส 3 ✅ ปิดเฟส (01:22):** `person_detect.py:1` + `bot.py:59` `/person` `/person_auto` + `person_watch 30s` — `yolov8n.pt 6.2MB` + `nvr_clip_10s_re.mp4 6 frames 0 คน (กลางคืนว่าง)` + `bus.jpg 3 คน 345KB` + `WG LAN สาธิต` PASS — รายงาน `Phase3-Person-Report.md:1` + `Phase3-NVR-Demo-Report.md:1`
- **เฟส 4 ✅ PLAN เสร็จ (01:38):** benchmark `5.34s/เฟรม` → Z2W 512MB ไม่เหมาะ YOLO ต่อเนื่อง (fallback motion), Pi4 4GB ~2-3s พอสำหรับ auto 30s, MiniPC <1s — สร้าง `Phase4-Edge-Deploy-Report.md:1` แนะนำ Z2W watchdog only vs Pi4/MiniPC YOLO — รอเลือก hardware แล้ว `scp + systemctl enable --now cctv-bot` ที่ `192.168.1.33`
- **เฟส 5 ✅ DONE (01:49):** สร้าง `cctv/output/handover-2026-09-08.md:1` ครบ ผัง IP + WG + Telegram 6 คำสั่ง + วิธีดูแล + สำรอง + `verify_system.py ALL PASS 10/10` + `rebuild_index.py` — ล็อกระบบส่งมอบ

## 5) ชื่อโปรเจ็คที่เสนอ (เลือกแล้ว)

**หลัก:** **Hermes Sentinel — โครงการคืนชีพ CCTV ตกรุ่น** (`HMS-2026-001`)
**รอง:** `NVR Revival` / `T.C.Com Lifeline` — ใช้เรียกใน `log.md` และ `index.md` ต่อไป
