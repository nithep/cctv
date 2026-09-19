---
type: cctv_ip_map
title: "CCTV IP Map — ผังอุปกรณ์เครือข่ายกล้อง"
date: 2026-09-07
updated: 2026-09-20
---

# CCTV IP Map — ผังอุปกรณ์

> อัปเดตล่าสุด `2026-09-20` — แบ่งงานใหม่: **Z2W .20 = watchdog/poller หลัก**, **Gateway .94 = YOLO worker** (บอทบน Gateway ปิดแล้ว — Telegram poll ต้องมีผู้ poll ตัวเดียว)

| # | อุปกรณ์ | IP | MAC | พอร์ต | สถานะ | หมายเหตุ |
|---|---|---|---|---|---|---|
| 1 | **NUUO NVRmini 2** (lighttpd/PHP) | `192.168.1.31:8000` | `94:de:80:9d:53:f1` | 8000 (web), 80? | ✅ Online — login page `200 OK`, `TcpTestSucceeded` | `PROJECT_NAME=NVRmini 2 fw 03.11.0000.0005`, `LIVE_STREAM_MAX_CONN 64` |
| 2 | **Seetong IPC** (gSOAP/2.8) | `192.168.1.21:80` | `00:4A:7B:3E:00:61` | 80 (web), 554 (RTSP) | ✅ Online — `gSOAP/2.8 200 OK`, `554 open`, Cloud `1666840.seetong.com` Status 1 | Static IP, Gateway `192.168.1.1`, DNS `203.113.111.162`/`192.168.1.1`, ใช้ UC2 4.7 ตั้งค่า |
| 3 | **NVRmini 2 — Storage Server หลัก** | `192.168.1.31:8000` | `94:de:80:9d:53:f1` | 8000, RAID | ✅ ใช้เป็น Server เก็บ (IPC ส่งอย่างเดียว) | IPC → NVR เก็บ ไม่ต้องสร้าง .32 แยก |
| 4 | **Matebook D2019 — Dev Host** | `192.168.1.44` | MatebookD2019 | — | 🛠 Dev/เอกสาร | ไม่รันบอท runtime แล้ว (ย้ายไป Z2W 20/9) — ใช้ dev/ssh จัดการระบบ |
| 5 | **Pi Zero 2 W — Watchdog Bot (รันจริง)** | `192.168.1.20` | `2c:cf:67:8e:f2:b1` | — | ✅ **cctv-bot active (WiFi)** | health 60s + poll Telegram + /snapshot /clip (rtsp sub `/1`) + **/picam (OV5647 CSI local, rotation 180)** — สแกนคนฝาก Gateway; RAM 415MB จำกัด MemoryMax 320M, `record_on_person: false` กัน SD |
| 5b | **Edge สำรอง (จอง)** | `192.168.1.33` (จอง) | — | 8080 | ⏳ ว่าง | เผื่อ Frigate/MiniPC ในอนาคต |
| 6 | Gateway/Router | `192.168.1.1` | — | — | — | — |
| 7 | **hotel-gateway (RPi) — YOLO Worker + WG server** | `192.168.1.94:51820` | — | 51820/8000 | ✅ person_detect รับงานจาก Z2W ผ่าน SSH | บอท watchdog ปิด+disable แล้ว (20/9) — เหลือหน้าที่ YOLO (delegate_ssh) + WireGuard + cron cleanup /tmp |

## RTSP Path ที่ต้องทดสอบ

- Seetong `.21`: `rtsp://user:pass@192.168.1.21:554/ucast/11` / `/live/ch1` / `/stream1` (ลองด้วย VLC)
- NUUO `.31`: ดึงผ่าน NVR web หรือ `rtsp://user:pass@192.168.1.31:554/...` (ถ้าเปิด)

## สิ่งที่ต้องเติม

- [ ] ตำแหน่งติดตั้งจริงของ `.21` (เช่น หน้าอาคาร/โกดัง)
- [ ] User/Pass ของ `.21` และ `.31`
- [ ] IPC ตัวอื่นๆ ถ้ามี (สแกน `192.168.1.0/24` ด้วย `onvifscan`)
