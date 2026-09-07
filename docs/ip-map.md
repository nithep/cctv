---
type: cctv_ip_map
title: "CCTV IP Map — ผังอุปกรณ์เครือข่ายกล้อง"
date: 2026-09-07
updated: 2026-09-07
---

# CCTV IP Map — ผังอุปกรณ์

> อัปเดตล่าสุด `2026-09-07` จากผลตรวจจริง + ภาพ UC2 4.7

| # | อุปกรณ์ | IP | MAC | พอร์ต | สถานะ | หมายเหตุ |
|---|---|---|---|---|---|---|
| 1 | **NUUO NVRmini 2** (lighttpd/PHP) | `192.168.1.31:8000` | `94:de:80:9d:53:f1` | 8000 (web), 80? | ✅ Online — login page `200 OK`, `TcpTestSucceeded` | `PROJECT_NAME=NVRmini 2 fw 03.11.0000.0005`, `LIVE_STREAM_MAX_CONN 64` |
| 2 | **Seetong IPC** (gSOAP/2.8) | `192.168.1.21:80` | `00:4A:7B:3E:00:61` | 80 (web), 554 (RTSP) | ✅ Online — `gSOAP/2.8 200 OK`, `554 open`, Cloud `1666840.seetong.com` Status 1 | Static IP, Gateway `192.168.1.1`, DNS `203.113.111.162`/`192.168.1.1`, ใช้ UC2 4.7 ตั้งค่า |
| 3 | **NVRmini 2 — Storage Server หลัก** | `192.168.1.31:8000` | `94:de:80:9d:53:f1` | 8000, RAID | ✅ ใช้เป็น Server เก็บ (IPC ส่งอย่างเดียว) | IPC → NVR เก็บ ไม่ต้องสร้าง .32 แยก |
| 4 | **Matebook D2019 — Dev Host (Bot)** | `192.168.1.44` | MatebookD2019 | — | ✅ **Dev ก่อน** | รัน `cctv/scripts/pi-z2w-bot/bot.py` บน Windows 10 + venv ดีบักง่าย |
| 5 | **Edge Target (Pi Z2W / อื่นๆ)** | `192.168.1.33` (จอง) | — | 8080 | ⏳ พักไว้ ค่อย deploy | เมื่อบอทนิ่งค่อยย้ายจาก Matebook → Edge ที่เหมาะสม |
| 6 | Gateway/Router | `192.168.1.1` | — | — | — | — |

## RTSP Path ที่ต้องทดสอบ

- Seetong `.21`: `rtsp://user:pass@192.168.1.21:554/ucast/11` / `/live/ch1` / `/stream1` (ลองด้วย VLC)
- NUUO `.31`: ดึงผ่าน NVR web หรือ `rtsp://user:pass@192.168.1.31:554/...` (ถ้าเปิด)

## สิ่งที่ต้องเติม

- [ ] ตำแหน่งติดตั้งจริงของ `.21` (เช่น หน้าอาคาร/โกดัง)
- [ ] User/Pass ของ `.21` และ `.31`
- [ ] IPC ตัวอื่นๆ ถ้ามี (สแกน `192.168.1.0/24` ด้วย `onvifscan`)
