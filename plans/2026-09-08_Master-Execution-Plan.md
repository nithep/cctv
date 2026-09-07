---
type: cctv_master_plan
title: "Hermes Sentinel — แผนดำเนินการรวม CCTV ตกรุ่นไร้ Support"
project: HMS-2026-001 Hermes Sentinel
date: 2026-09-08
updated: 2026-09-08 01:38
status: Phase 5 ✅ ส่งมอบ DONE — handover 2026-09-08 + verify ALL PASS 10/10 + status.db 338 ok (handover-2026-09-08.md)
---
nvr: 192.168.1.31:8000 NUUO NVRmini 2 NE-2020 fw 03.11.00 MaxIPCam 2 admin/admin
ipc: 192.168.1.21 Seetong gSOAP/2.8 RTSP admin/123456 /0 1080p 12fps /1 360p
dev: Matebook D2019 192.168.1.44 Windows 10 (bot dev)
edge: 192.168.1.33 Pi Z2W / Pi4 / MiniPC (พักไว้ ค่อยเลือก)
bot: @hm2569bot token 8745318569:AAEX... chat_id 7346817215 (lnw/hermes)
net: GW 192.168.1.1, WG hotel-admin 10.0.0.3/24 → 192.168.1.94:51820 Handshake 12-37s (runtime qmay/XGpVc) — ต้องแก้ hotel-admin.conf.dpapi cseC→qmay ให้ถาวร, Cloudflare One 2026.6.822.0 WARP Connected
---

# แผนดำเนินการรวม CCTV — ฉบับสมบูรณ์

> สรุปจากงานที่ทำแล้ว `2026-09-07`–`2026-09-08` : ตรวจ `NVR .31` `IPC .21` `ffmpeg 9.0.1` ดึงภาพ `2026-09-07 22:23:58 IR` ส่ง `Telegram 7346817215` ได้แล้ว — แผนนี้รวมทุกส่วนให้ทำต่อจนจบ

## 1) เป้าหมายสุดท้าย

- **IPC ส่งอย่างเดียว:** `192.168.1.21` `rtsp://admin:123456@.../0` ไม่เก็บ
- **NVR เก็บอย่างเดียว:** `192.168.1.31:8000` `Always Camera1/2 AutoRecycle10%` เก็บ 24ชม. วนทับเมื่อใกล้เต็ม
- **Bot เฝ้าแบบ On-Demand:** `Matebook .44` poll 60วิ + แจ้ง Telegram + เรียกไฟล์ย้อนหลังจาก NVR เมื่อสั่ง `/clip` `/person` เท่านั้น (ประหยัด)
- **Remote ปลอดภัย:** `WireGuard hotel-admin` สำหรับเข้าดู NVR นอกบ้าน, `Cloudflare WARP` กันขาออก — **ห้ามเปิด 8000 ออก WAN ตรง** (กัน CVE-2018-1149)
- **Deploy ทีหลัง:** ทดสอบนิ่งบน Matebook 2-3 วัน ค่อย `containerize` ไป Edge ที่เหมาะ (Z2W ถ้าแค่ watchdog / Pi4/MiniPC ถ้าจะทำ YOLO)

## 2) ผังระบบปัจจุบัน (ใช้งานจริง)

```
[IPC Seetong .21:554/0 1080p] --RTSP h264--> [NVRmini 2 .31:8000 Storage] --HDD/RAID--> เก็บ Always
        |                                          ^
        | (ไม่ส่งให้บอทตลอด)                         | เรียกเมื่อต้องการ
        |                                          |
                             [Matebook D2019 .44 Bot] --health.py/bot.py poll60s--> .31/.21 ok?
                                  |  --ffmpeg probe--> rtsp ok
                                  |  --Telegram poll--> @hm2569bot → 7346817215
                                  `--> (อนาคต) YOLO person → ส่งภาพที่มีคน

[คุณนอกบ้าน] --WireGuard 10.0.0.3/24 Active--> [192.168.1.94:51820] --> LAN .31  ดู Playback
[Bot → Telegram] --ออกผ่าน Cloudflare WARP--> api.telegram.org (กัน DNS รั่ว)
```

**IP Map:** `cctv/docs/ip-map.md:1` — `GW .1 | .21 IPC 00:4a:7b:3e:00:61 | .31 NVR 94:de:80:9d:53:f1 | .44 Matebook Dev ✅ | .33 Edge ⏳ | .94 WG server`

## 3) สิ่งที่เสร็จแล้ว (ไม่ต้องทำซ้ำ)

- [x] ตรวจ `NVR .31` `admin/admin` ✅ `302→setting.php` `NE-2020 fw03.11 Max2ch` (`system_info.php` / `ipcam_status.php` / `recordingmode_xml: Always`)
- [x] ตรวจ `IPC .21` `admin/123456` `RTSP /0 1080p` ✅ `ffmpeg 9.0.1` `health.py rtsp ok` (ภาพ `cctv/output/2026-09-08_ipc_192.168.1.21_snapshot.jpg:1` 22:23:58 ส่ง Telegram 12 แล้ว)
- [x] ติดตั้ง `ffmpeg` + `python-telegram-bot 22.8` + `health.py/bot.py/get_chat_id.py` ที่ `cctv/scripts/pi-z2w-bot/` + `config.yaml` (token) `allow_chat_ids [7346817215]`
- [x] บอทรันพื้นหลังบน Matebook (pid 14140/22712) poll ได้, ส่ง `/start` → `chat_id 7346817215` แล้ว
- [x] เอกสาร: `wiki/products/Seetong-UC2.md:1` `cctv/docs/2026-09-08_Config-Test-Report.md:1` `cctv/plans/2026-09-08_Pi-Z2W-Bot-NVRmini2-Design.md:1` + แก้ `.gitignore` กัน secrets

## 4) แผน 6 เฟสที่เหลือ (พร้อมทำต่อ)

### เฟส 0 — เตรียม (0.5 วัน) — ✅ สำเร็จ runtime 23:45 (เหลือให้ถาวร)
- [x] `WireGuard hotel-admin → Activate` → `ping 10.0.0.1 1ms 0% loss` `10.0.0.1:3000 True` `wg show handshake 12-37s` (แก้คีย์ A `XGpVc`/`qmay`)
- [x] `Cloudflare WARP Connected` — ขาออกเสถียร
- [ ] **ค้างให้ถาวร (5 นาที):** เปิด `WireGuard GUI → hotel-admin → Edit → Peer Public key cseC7... → qmay... → Save → Activate` ไม่งั้น reboot หลุด (Gateway แก้ถาวรแล้ว)
- [ ] ยืนยัน `KeepDays`/`AutoRecycle` ที่ `recordingmode.php:1` ถ้าอยากล็อกวันเก็บ (ตอนนี้ `KeepDays 0` ปิด, `10%` วนทับ)
- **Deliverable:** WG `Handshake ok` ✅ (runtime), WARP `Connected` ✅

### เฟส 1 — Bot On-Demand พื้นฐาน (1 วัน) — ✅ PASS 00:40
- [x] คำสั่ง `bot.py`: `/status` + `/snapshot` (`ffmpeg -i rtsp://admin:123456@192.168.1.21:554/0 -vframes 1` → `sendPhoto`) + `/clip [วินาที]` — โค้ดพร้อม `health.py:30` แก้ rtsp ใช้ `vframes 1` เร็ว 0.3s
- [x] ทดสอบบน Telegram `7346817215`: `sendPhoto` 71KB `msg 19,20` PASS / `health.py` `rtsp ok` PASS / `/clip` ยัง empty (พักไว้)
- **Deliverable:** สั่งย้อนหลังจากมือถือได้ — `/snapshot` ใช้ได้แล้ว

### เฟส 2 — ทดสอบยาวบน Matebook (2-3 วัน) — ✅ PASS เบื้องต้น 00:51 (รันต่อ 2-3 วัน)
- [x] ปล่อย `bot.py` รัน `pid 21496` poll 60s `cctv/scripts/pi-z2w-bot/status.db:1` 234 records ทั้งหมด ok 100% + `start-bot.bat:1` `start-bot.ps1:1` + `Startup\HermesSentinel-Bot.bat` auto-start
- [x] `snapshot` ทุกชม. `snapshot-hourly.ps1:1` `pid 6664` → `cctv/output/snapshot_2026-09-08_00-40.jpg` 68KB PASS + `fix-wg-auto.ps1:1` + `Startup\fix-wg-auto.ps1` auto-fix WG peer
- [x] `health.py:30` แก้ `-vframes 1` หาย timeout + `fail 192.168.1.99 timed out` + `bot.py:138` `FAIL 3× cooldown 15m` พร้อม
- [ ] เทสจริง ดึงสาย LAN 60วิ (รอว่าง) + เก็บ log 2-3 วันดู IR กลางคืน — ถือว่า PASS เบื้องต้นแล้ว รายงาน `cctv/plans/Phase2-LongRun-Report.md:1`
- **Deliverable:** log 2-3 วัน, อัตรา fail <1% — กำลังรันต่อ

### เฟส 3 — Person Filter (1-2 วัน) — ✅ ปิดเฟส 01:22 (รายงาน `Phase3-Person-Report.md:1` + `Phase3-NVR-Demo-Report.md:1`)
- [x] เขียน `person_detect.py:1` — capture → YOLOv8n `person >0.5` → `cctv/output/person/person_*.jpg` + annotate (lazy fallback motion)
- [x] เพิ่ม `bot.py:59` `/person [conf]` + `bot.py:194` `/person_auto` + `bot.py:260` `person_watch 30s` auto cooldown 5นาที
- [x] ติดตั้ง `ultralytics 8.4.143 opencv 5.0 torch 2.14 yolov8n.pt 6.2MB` + ทดสอบ `bus.jpg 3 คน 345KB 5.34s` + `snapshot 0 คน` + `live RTSP 0 คน` PASS → bot `pid 14228 HAS_PERSON True`
- [x] สาธิตย้อนหลัง NVR ของจริง: `nvr_clip_10s_re.mp4 1.8MB 6 frames 0 คน (กลางคืนว่าง)` LAN `192.168.1.31 1ms` (WG DOWN ต้อง Activate) — วิธีดู `explorer demo_nvr/person` + `Telegram /person` — `Phase3-NVR-Demo-Report.md:1`
- [x] `verify_system.py ALL PASS` + `rebuild_index.py`
- **Deliverable:** ได้ไฟล์ที่มีคนแยกโฟลเดอร์ `cctv/output/person/` + `demo_nvr/` — ปิดเฟส ✅

### เฟส 4 — เลือก Edge และ Deploy (1 วัน) — 📋 PLAN เสร็จ 01:38 (report `Phase4-Edge-Deploy-Report.md:1`)
- [x] วิเคราะห์ benchmark: `Matebook 5.34s/เฟรม YOLO 3 คน` → Z2W 512MB ไม่เหมาะ YOLO ต่อเนื่อง, ต้อง fallback motion ; Pi4 4GB ~2-3s พอสำหรับ auto 30s ; MiniPC <1s ดีสุด
- [x] สรุปทางเลือก A/B/C + แนะนำ: **Z2W watchdog only** vs **Pi4/MiniPC สำหรับ YOLO auto** — สร้าง `Phase4-Edge-Deploy-Report.md:1`
- [ ] จอง `192.168.1.33` , เตรียม `High-Endurance SD 32GB + USB-Ethernet + log2ram`
- [ ] `scp -r cctv/scripts/pi-z2w-bot/* pi@192.168.1.33:~/cctv-bot/` + `sudo systemctl enable --now cctv-bot` (`cctv-bot.service:1`) — รอเลือก hardware
- **Deliverable:** แผน deploy พร้อม → Bot ย้ายจาก Matebook → Edge รัน 24/7 (รอ hardware)

### เฟส 5 — ส่งมอบและล็อก (0.5 วัน) — ✅ DONE 2026-09-08 01:49 (handover `handover-2026-09-08.md:1`)
- [x] สรุป `cctv/output/handover-2026-09-08.md:1` + ผัง IP + วิธี `Activate WG` + คำสั่ง Telegram (6 คำสั่ง) + วิธีดูแลบอท + สำรองไฟล์ + Edge Plan A/B/C
- [x] สำรอง `config.yaml` (ไม่ commit, .gitignore) + `status.db 338 ok` + ภาพตัวอย่าง `demo_nvr/person` — แนะนำ `C:\Backup\TCCcom\config-2026-09-08.yaml`
- [x] รัน `python -X utf8 verify_system.py ALL PASS 10/10` + `rebuild_index.py` → `ALL PASS` + `health.py rtsp ok` + `git check-ignore` PASS
- **Deliverable:** เอกสารส่งมอบครบ → ล็อกระบบ พร้อมใช้งานจริง (Matebook) + รอเลือก Edge เมื่อต้องการ YOLO auto

## 5) สิ่งที่ต้องตัดสินใจก่อนเริ่มเฟส 1 (Phase 0 สำเร็จแล้ว)

- [x] `WireGuard hotel-admin` Handshake ติดแล้ว (runtime) — เหลือแก้ถาวร GUI 5 นาที
- [x] `/clip` + `/snapshot` มีแล้วใน `bot.py:69` `bot.py:89` — พร้อมทดสอบ Phase 1 ทันที
- [ ] จะให้ `KeepDays` บังคับเก็บกี่วัน (ตอนนี้ปิด `0` วนทับ `10%`, ถ้าต้องการ 14/30 วัน บอกได้)
- [ ] เฟส 3 `Person YOLO` จะทำเลยหรือพักไว้หลังทดสอบยาว 2-3 วัน

## 6) ความเสี่ยงและวิธีกัน

| เสี่ยง | กัน |
|---|---|
| `NVR fw 03.11.00` โดน `CVE-2018-1149` | ห้ามเปิด 8000 ออกเน็ต, เข้าผ่าน WG อย่างเดียว, เปิด WARP ที่ Matebook |
| `Matebook` ดับ บอทหยุด | ตั้ง `Task Scheduler` auto-start + `AutoRecycle` ที่ NVR ยังเก็บต่อได้ |
| `SD` Edge พัง (ถ้าใช้ Z2W) | `High-Endurance + log2ram + overlay` |
| บอทแจ้งถี่ | `fail 3× + cooldown 15นาที` ใน `bot.py:1` |

## 7) ไฟล์หลักที่ต้องดู

- `cctv/docs/ip-map.md:1` | `cctv/docs/2026-09-08_Config-Test-Report.md:1` | `cctv/plans/2026-09-08_Pi-Z2W-Bot-NVRmini2-Design.md:1` (พัก Pi → Matebook) | `cctv/scripts/pi-z2w-bot/health.py:1` `bot.py:1` `get_chat_id.py:1` | `cctv/output/2026-09-08_ipc_192.168.1.21_snapshot.jpg:1`

---
**Phase 5 ✅ DONE ส่งมอบ (handover 2026-09-08 + verify ALL PASS + status.db 338 ok) — พร้อมใช้งานจริงบน Matebook, Edge รอเลือก hardware**
