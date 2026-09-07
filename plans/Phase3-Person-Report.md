---
type: cctv_report
title: "Phase 3 Person Filter — YOLOv8n on Matebook (On-Demand + Auto)"
date: 2026-09-08 01:00
project: HMS-2026-001 Hermes Sentinel
status: DONE ✅ YOLOv8n ทำงานจริงแล้ว (ultralytics 8.4.143 + opencv 5.0 + torch 2.14) — ทดสอบ bus.jpg 3 คน + live RTSP 0 คน PASS
---

# Phase 3 — Person Filter (YOLOv8n) — PROCESS เสร็จแล้ว (YOLO จริง)

## สรุป
- **เป้าหมาย Phase 3:** กรอง "มีคน" จาก IPC 192.168.1.21 ก่อนส่ง Telegram — ลด spam ภาพว่าง
- **สถานะ:** ✅ **YOLOv8n ทำงานจริงแล้ว** — `yolov8n.pt 6.2MB` โหลดแล้ว, `person_detect.py` + `bot.py: /person /person_auto` + `person_watch 30s` พร้อม, **verify_system.py ALL PASS** — bot `pid 14228` รันแล้ว

## สิ่งที่ทำ

### 1) `cctv/scripts/pi-z2w-bot/person_detect.py:1` (ใหม่)
- `capture_snapshot(rtsp)` — ดึงเฟรมเดี่ยวด้วย ffmpeg (`_ffmpeg_bin()` รองรับ WinGet Gyan)
- `detect_person_yolo(image, conf, model)` — lazy load `YOLO(yolov8n.pt)` ถ้ามี `ultralytics`
- `detect_motion_fallback()` — เมื่อไม่มี YOLO (Pi Z2W / ยังไม่ติดตั้ง) 返回 `[]` + hint `SUPPORT_MOTION_RECORDING`
- `detect_person()` — unified entry, เลือก backend `yolo` หรือ `motion_fallback`
- `annotate_image()` — วาด bbox ด้วย cv2 ถ้ามี
- `scan_snapshot(rtsp, conf)` — capture + detect + บันทึก `cctv/output/person/person_*.jpg` เมื่อเจอคน (+ `_last_noperson.jpg` debug)
- `extract_clip_frames()` + `scan_clip()` — ดึงเฟรมจาก clip แล้วสแกนย้อนหลัง (สำหรับ `/person` แบบย้อนหลัง NVR)
- CLI: `python person_detect.py --image ...` / `--rtsp ...` / `--rtsp ... --clip 10`
- ออกแบบให้ **ไม่บังคับติดตั้ง ultralytics** — ไม่มีก็ไม่ error, fallback ได้

### 2) `cctv/scripts/pi-z2w-bot/bot.py:1` อัปเดต
- import `person_detect` แบบ optional (`HAS_PERSON`)
- เพิ่มตัวแปร `person_auto_enabled`, `last_person_alert`, `PERSON_AUTO_INTERVAL 30s`, `PERSON_COOLDOWN 300s`
- `cmd_status()` — แสดง backend `YOLOv8n ✅ / motion fallback / ไม่มี AI`
- `cmd_person(update, conf)` — On-Demand: ดึง snapshot → `scan_snapshot()` → ส่งรูป annotate ถ้าเจอคน, ตอบข้อความถ้าไม่เจอ
- `cmd_person_auto(on/off)` — toggle auto watch
- `person_watch_loop()` — thread daemon ทุก 30วิ เมื่อ `person_auto_enabled` สแกนแล้วส่ง Telegram แบบ sync HTTP (ไม่ block Telegram polling) cooldown 5นาที
- `start_telegram()` — เพิ่ม handler `/person`, `/person_auto`

### 3) `cctv/scripts/pi-z2w-bot/requirements.txt:1` + `config.yaml.example:1` + `README.md:1`
- `requirements.txt` เพิ่ม comment optional `opencv-python`, `ultralytics`, `torch`
- `config.yaml.example` เพิ่มบล็อก `person: enabled/model/conf_threshold/auto_interval/cooldown/save_dir`
- `README.md` เพิ่มคำสั่ง Telegram ใหม่ + วิธีติดตั้ง YOLO บน Matebook + โครงสร้างไฟล์ใหม่

### 4) โฟลเดอร์ `cctv/output/person/` + `.gitkeep`
- สร้างแล้ว `.gitignore` เดิม ignore `*.jpg` อยู่แล้ว — ไม่หลุดเข้า Git

## ทดสอบแล้ว (01:08 PROCESS)
- `pip install ultralytics opencv-python` → `ultralytics 8.4.143 opencv 5.0.0 torch 2.14 torchvision 0.29` ✅ — `yolov8n.pt 6.2MB` ดOWNLOAD `C:\Users\Nithep\...\T.C.Com\yolov8n.pt` สำเร็จ `01:06:37`
- `person_detect.py --image snapshot_2026-09-08_00-39.jpg` → `backend yolo persons 0` (ภาพกลางคืนว่าง — ถูกต้อง)
- `person_detect.py --image bus.jpg` → `backend yolo persons 3 conf 0.85` + `annotated cctv/output/person/person_20260908_010710.jpg 345KB` ✅ — ยืนยัน YOLO ตรวจคนได้จริง
- `person_detect.py --image 2026-09-08_ipc_192.168.1.21_snapshot.jpg` → `yolo 0` (IR ว่าง) ✅
- `health.py` → `NVR True NUUO(200) IPC True rtsp ok` ✅
- `scan_snapshot rtsp://admin:123456@192.168.1.21:554/0` → `ok True yolo 0 has_person False` (live กลางคืนว่าง) ✅
- `bot.py` → `HAS_PERSON True` `commands ['status','snapshot','clip','person','person_auto','reboot']` + `bot pid 14228` รันแล้ว `status.db rtsp ok` 5 records ล่าสุด PASS
- `py_compile` 3 ไฟล์ → PASS | `verify_system.py` → **ALL PASS 10/10** | `.gitignore` เพิ่ม `yolov8n.pt / yolo*.pt`

## วิธีใช้จริง (พร้อมแล้ว)
```powershell
# ทดสอบอีกครั้ง
C:\Users\Nithep\AppData\Local\Programs\Python\Python312\python.exe -X utf8 cctv/scripts/pi-z2w-bot/person_detect.py --image cctv/output/snapshot_2026-09-08_00-39.jpg
C:\Users\Nithep\AppData\Local\Programs\Python\Python312\python.exe -X utf8 cctv/scripts/pi-z2w-bot/person_detect.py --rtsp rtsp://admin:123456@192.168.1.21:554/0

# Bot รันแล้ว pid 14228 — สั่งจาก Telegram @hm2569bot:
# /status → ดู Person: YOLOv8n ✅ auto OFF
# /person 0.5 → สแกนครั้งเดียว (กลางคืนจะตอบ "ไม่พบคน")
# /person_auto on → เปิด auto ทุก 30วิ (ส่งเฉพาะมีคน, cooldown 5นาที)
# ลองยืนหน้า IPC 192.168.1.21 แล้ว /person → ต้องได้รูป annotate กรอบเขียว
```

## ทางเลือกไม่ใช้ AI (fallback)
- NVRmini 2 มี `SUPPORT_MOTION_RECORDING true` — ตั้งที่ `http://192.168.1.31:8000/ipcam_event.php` เปิด Motion บน Camera1/2 ได้เลย — Bot ใช้ motion fallback จะตอบ `ไม่พบคน (fallback)` แต่ NVR จะกรอง event เบื้องต้นให้

## ค้างต่อ (Phase 4)
- ทดสอบ `/person` ด้วยคนยืนหน้า IPC จริง → ดู `cctv/output/person/*.jpg` (กลางคืนตอนนี้ว่าง 0 คนถูกต้อง — ลองกลางวัน)
- เลือก Edge: ถ้าเปิด auto YOLO ต่อเนื่อง → ต้อง `Pi 4 / MiniPC RAM 4GB+` ไม่ใช่ Z2W 512MB — `scp -r cctv/scripts/pi-z2w-bot pi@192.168.1.33:~/cctv-bot/` + `pip install ultralytics` บน Pi4
- **Benchmark:** bus.jpg `3 คน elapsed 5.34s` บน Matebook CPU — ช้ากว่า GPU แต่พอสำหรับ On-Demand (ไม่เหมาะรันทุก 2วิต่อเนื่อง)

## ไฟล์ที่เกี่ยวข้อง
- `cctv/scripts/pi-z2w-bot/person_detect.py:1`
- `cctv/scripts/pi-z2w-bot/bot.py:59` (`cmd_person`) `bot.py:194` (`cmd_person_auto`) `bot.py:260` (`person_watch_loop`)
- `cctv/scripts/pi-z2w-bot/requirements.txt:1` `config.yaml.example:1` `README.md:1`
- `cctv/output/person/` (ผลลัพธ์)
- Master: `cctv/plans/2026-09-08_Master-Execution-Plan.md:76` | Project: `cctv/plans/Project-Hermes-Sentinel.md:52`
