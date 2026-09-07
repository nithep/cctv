---
type: cctv_test_report
title: "รายงานทดสอบคอนฟิก NVR + IPC + RTSP + Telegram"
date: 2026-09-08
tester: Matebook D2019 (192.168.1.44)
nvr: 192.168.1.31:8000 NUUO NVRmini 2 fw 03.11.00
ipc: 192.168.1.21 Seetong gSOAP/2.8
---

# รายงานทดสอบคอนฟิก — 2026-09-08 22:00 ICT

> ทดสอบตามคำสั่ง: ลอง `admin/admin`, `admin/123456`, ตั้ง Telegram `@hm2569bot` (hermes), probe RTSP จริง — รันบน Matebook D2019

## 1) NUUO NVRmini 2 — 192.168.1.31:8000

| ทดสอบ | ผล | หมายเหตุ |
|---|---|---|
| `admin/admin` POST `login.php` | ✅ **สำเร็จ** `302 Location: setting.php` `Set-Cookie PHPSESSID` + `lang=en` | เข้า `setting.php` / `system_info.php` / `ipcam_status.php` ได้, `NE-2020` product, `fw 03.11.00`, `MaxIPCam=2` (จาก `js/status.js`) |
| `admin/123456` | ❌ `302 → /?cmd=loginfail` | รหัสนี้ไม่ใช่ของ NVR |
| `HTTP GET /` ไม่ login | `200 lighttpd/1.4.48 PHP/7.4.1 NUUO login` | ต้อง login ก่อนถึงเข้า config ได้ |
| `system_info.php` (หลัง login) | `200` `Linux` `CPU/Temp/Fan` (โหลดผ่าน JS `system.js`) | ใช้ได้ |
| `ipcam_status.php` | `200` `MaxIPCam 2` `warningBitrate 40000` | NVR นี้รองรับสูงสุด 2 กล้อง (สำคัญต่อการขยาย) |

**สรุป NVR:** ใช้ `admin/admin` — เข้า config ได้แล้ว ดู/ตั้งค่ากล้อง, บันทึก, RAID, network ได้ที่ `http://192.168.1.31:8000/setting.php` (ต้อง login ก่อน)

## 2) Seetong IPC — 192.168.1.21:80/554

| ทดสอบ | ผล |
|---|---|
| `HTTP GET /` (ไม่ auth) | ✅ `200 gSOAP/2.8 IPCConfig v2.0.0.31` — ไม่ต้องใส่รหัสก็เห็นหน้า config (เบื้องต้น) |
| `admin/admin` HTTP Basic | ✅ `200` เหมือนกัน (ไม่ต่าง) |
| `admin/123456` HTTP Basic | ✅ `200` เหมือนกัน |
| `RTSP DESCRIBE` (raw socket + Digest `LIVE555`) `admin/admin` | ❌ `401 Unauthorized` (ทุก path) |
| `RTSP DESCRIBE` `admin/123456` | ✅ `401 → เปลี่ยนเป็น Auth แล้วได้ 200/404` — **รหัสนี้ถูก** |
| `ffmpeg probe` `admin:admin@.../ucast/11` | ❌ `401` |
| `ffmpeg probe` `admin:123456@.../ucast/11` | ❌ `404 Stream Not Found` (auth ผ่านแล้วแต่ path ผิด) |

### RTSP Path ที่ probe ด้วย `ffmpeg 9.0.1` + `admin:123456` (auth ผ่าน)

| Path | ผล | รายละเอียด |
|---|---|---|
| `/ucast/11`, `/ucast/12`, `/live/ch1`, `/ch1`, `/11`, `/12`, `/video1` | `404` | auth ผ่านแต่ไม่มีสตรีมชื่อนี้ |
| **`/stream1`** | ✅ **200** `h264 Baseline 1920x1080 12fps` | **Main stream ใช้ได้** |
| **`/h264`** | ✅ **200** `1920x1080 12fps` | ใช้ได้ |
| **`/0`** | ✅ **200** `1920x1080 12fps` | **Main stream (แนะนำ)** |
| **`/1`** | ✅ **200** `480x360 30fps` | **Sub stream (แนะนำ)** |

**สรุป IPC:** HTTP เปิด, **RTSP ต้องใช้ `admin/123456`** (ไม่ใช่ `admin/admin`) และใช้ path **`/0` (1080p main) / `/1` (360p sub)** หรือ `/stream1` / `/h264` — บอทตั้ง `rtsp://admin:123456@192.168.1.21:554/0` แล้ว probe ผ่าน

## 3) Telegram Bot — @hm2569bot

- **Token:** `8745318569:AAEX...WvU` ✅ `getMe` = `id 8745318569 is_bot true first_name hermes username hm2569bot`
- **getUpdates:** `0` รายการ — **ยังไม่มีใครส่ง `/start` ให้บอท** เลยยังไม่มี `chat_id` ของคุณ (`hermes`)
- **ลองส่ง:** `sendMessage chat_id=@hermes` → `400 chat not found`, `chat_id=8745318569` → `403 can't send to bot` (ปกติ)
- **วิธีแก้:** ให้คุณ **เปิด Telegram → ค้นหา `@hm2569bot` → กด Start → พิมพ์ `/start` หรือ `hello`** แล้วบอทจะจับ `chat_id` ได้และส่งทดสอบกลับ

> บอทบน Matebook พร้อมแล้ว (`cctv/scripts/pi-z2w-bot/bot.py:1` + `config.yaml`) — รอ `chat_id` ของ `hermes` เพื่อใส่ใน `allow_chat_ids`

## 4) Probe RTSP จริงบน Matebook

- ติดตั้ง `ffmpeg 9.0.1-full_build` ผ่าน `winget Gyan.FFmpeg` แล้ว, เพิ่ม PATH แล้ว
- `health.py` ตอนนี้ `rtsp: (True, 'rtsp ok')` — ทั้ง NVR และ IPC online
- คำสั่งทดสอบด้วยมือ:
  ```powershell
  ffmpeg -rtsp_transport tcp -i rtsp://admin:123456@192.168.1.21:554/0 -t 2 -f null -
  ffplay rtsp://admin:123456@192.168.1.21:554/0
  ```

## 5) สิ่งที่ต้องทำต่อ (หลังคุณส่ง /start)

- [ ] คุณส่ง `/start` → ผมรัน `getUpdates` จับ `chat_id` → ใส่ใน `config.yaml allow_chat_ids` → ส่งข้อความทดสอบ `CCTV Bot online — NVR .31 admin/admin OK, IPC .21 rtsp://.../0 OK` → คุณยืนยันว่าได้รับ
- [ ] จากนั้นรัน `bot.py` ค้างบน Matebook (foreground หรือ Task Scheduler) เพื่อมอนิเตอร์ 60s/ครั้ง
- [ ] ลบ `ffmpeg` probe ออกจาก health ถ้าไม่ต้องการ decode ต่อเนื่อง (ตอนนี้ probe เบาๆ 2 วินาที ไม่หนัก)

## ไฟล์ที่เกี่ยวข้อง

- `cctv/scripts/pi-z2w-bot/config.yaml` (มี `admin/admin` + `admin:123456@.../0` + token — อยู่ใน `.gitignore`)
- `cctv/scripts/pi-z2w-bot/health.py:1` + `bot.py:1`
- `C:\Users\Nithep\AppData\Local\Temp\opencode\nvr_setting.html` / `nvr_system_info.html` (snapshot หลัง login)
