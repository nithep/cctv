---
type: cctv_ops_log
title: "PiCam CSI Install Log — Z2W 2026-09-20 01:08-01:39"
edge: 192.168.1.20 (pi-z2w, user admin)
camera: OV5647 CSI (2592x1944) — local, ไม่ผ่าน RTSP
status: done
---

# ติดตั้งกล้อง PiCam บน Z2W — 2026-09-20

## ฮาร์ดแวร์
- กล้องโมดูล OV5647 เสียบ CSI ตรงเข้า Z2W (ไม่ใช่กล้อง IP — สแกน LAN ไม่เจอถูกต้องแล้ว)
- `rpicam-hello --list-cameras` → `0 : ov5647 [2592x1944]` ✅
- ถ่ายมือติด: `rpicam-still -o /tmp/test.jpg --timeout 2000` → 1.2M ✅

## งานโค้ด (ใน `scripts/pi-z2w-bot/`)
- ใหม่ `picam.py` — `capture()` ผ่าน `rpicam-still`
- `bot.py` — คำสั่งใหม่ `/picam` + `PiCam:` ใน `/status` + `_shrink_for_tg()` + Telegram timeout 15/30/30 + lock กันถ่ายชน

## บั๊กที่เจอ + วิธีแก้
| อาการ | สาเหตุ | แก้ |
|---|---|---|
| `-n` แล้วค้าง `EXIT:143` ไม่ได้ไฟล์ | `--nopreview` บน Z2W+ov5647 ค้างหลัง configure streams | ถอด `-n` ออก |
| `exit=-15` ผ่านบอท (ถ่ายมือติด) | pipeline ช้าตอนบอทรัน เฟรมกระดึ๊บแค่ #42 เกิน subprocess timeout 17 วิ โดน kill เอง | `--immediate` + เผื่อ timeout 60 วิ + lock กัน `/picam` ชนกัน |
| `picam error: Timed out` ตอนส่ง | รูปเต็ม 1.2MB อัปโหลดผ่าน WiFi ไม่ทัน PTB default ~5 วิ | ย่อ ffmpeg `scale=960` (~43KB) + timeout 30 วิ |
| ภาพกลับหัว (ตัวหนังสือตีลังกา) | ติดกล้องกลับหัว | `--rotation 180` ใน `picam.py` (`ROTATION`) |

## ผลสุดท้าย
- `/picam` ได้รูป `43KB 01:39` ใช้เวลา ~5 วิ ✅
- `/status` มี `PiCam: ✅ พร้อม /picam` ✅
- ค้าง: เทียบแสงกลางวัน + จัดมุมกล้องจริงหน้างาน (ภาพเทสต์มืดเพราะตี 1)

## Deploy ค้าง (รอบสุดท้าย)
- `scp picam.py` (rotation 180) ขึ้น Z2W + `sudo systemctl restart cctv-bot` แล้ว `/picam` อีกรอบต้องตั้งตรง
- ยังไม่ commit/push — บอกให้ push เมื่อพร้อม
