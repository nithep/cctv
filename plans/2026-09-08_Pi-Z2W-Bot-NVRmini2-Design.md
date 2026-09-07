---
type: cctv_design
title: "ออกแบบระบบ NVRmini 2 เป็น Server บันทึก + IPC ส่งภาพ + บอทควบคุม (Dev: Matebook D2019 → Edge: Pi Z2W/อื่นๆ)"
date: 2026-09-08
updated: 2026-09-08
status: draft — แผน Pi Z2W พักไว้ก่อน ใช้ Matebook D2019 เป็น dev host
nvr: 192.168.1.31:8000 NUUO NVRmini 2 fw 03.11.0000.0005
ipc_example: 192.168.1.21 Seetong gSOAP/2.8
dev_host: Matebook D2019 (192.168.1.44, Windows 10 Home) — dev & staging
edge_target: Raspberry Pi Zero 2 W (พักก่อน ค่อย deploy ตามเหมาะสม)
---

# NVRmini 2 เป็น Server + IPC ส่งภาพ + บอทควบคุม — Dev บน Matebook D2019 ก่อน ค่อยลง Edge

> โจทย์: ใช้ **NVRmini 2 เป็น Server บันทึกทุกอย่าง (Storage/Raid)** อย่างเดียว, **IPC ทำหน้าที่จับภาพส่งอย่างเดียว (dumb camera)** , มี **Pi Zero 2 W รันบอทควบคุม** ได้ไหม
> **อัปเดต 2026-09-08:** ตัด Pi Z2W ออกก่อน — **ใช้ Matebook D2019 (192.168.1.44) เป็น dev host** รันบอททดสอบก่อน แล้วค่อย deploy ลง edge device (Pi Z2W / Pi 4 / Mini PC) ตามเหมาะสม — **ดีกว่า ✅**

**คำตอบสั้น: ทำได้จริง ✅ และใช้ Matebook D2019 เป็น dev ก่อนคือทางที่ถูก** — บอททำหน้าที่ “Control Plane” ไม่ใช่ “Data Plane” ทดสอบบน Matebook จะเร็วกว่า ดีบักง่ายกว่า ไม่ต้องห่วง SD พัง แล้วค่อย containerize ไปลง edge เมื่อนิ่ง

---

## 1) สถาปัตยกรรมที่แนะนำ (ใช้ได้จริง) — Dev บน Matebook ก่อน

```
[IPC Seetong 192.168.1.21:554 + IPC อื่นๆ] --RTSP/ONVIF--> [NUUO NVRmini 2 192.168.1.31:8000]
        |  dumb: ส่งภาพอย่างเดียว, ตั้ง Static IP, ปิด Cloud ถ้าไม่ใช้
        |
        v
   [NVRmini 2]  — บันทึก/เก็บ/RAID/Schedule/Playback/Export (Storage Server)
        |  lighttpd/PHP, LIVE_STREAM_MAX_CONN 64, SUPPORT_RAID true
        |
   [Matebook D2019 192.168.1.44] — Dev Host รันบอท (ชั่วคราว, ดีบักง่าย)
        |  Windows 10 Home + Python 3.11 venv + opencode/Muse Spark
        |--> ping/HTTP poll NVR (.31) + IPC (.21) ทุก 60s
        |--> ffmpeg probe RTSP, SQLite log, Telegram/LINE
        `--> ไม่เก็บวิดีโอ แค่ log/สถานะ — รันด้วย Task Scheduler หรือ WSL systemd
        |
        |  (เมื่อนิ่งแล้ว)  ──containerize──> [Edge Device ที่เหมาะสม]
        |                                      Pi Z2W (เบา/ถูก) / Pi 4 / Mini PC (แรง/AI)
        `------------------------------------> เลือกตาม load จริง
```

**ผัง IP ใหม่ (เฟส Dev):**

| อุปกรณ์ | IP | บทบาท | สถานะ |
|---|---|---|---|
| Gateway | 192.168.1.1 | — | — |
| Seetong IPC | 192.168.1.21 (00:4a:7b:3e:00:61) | dumb cam | ✅ Online |
| NUUO NVRmini 2 | 192.168.1.31 (94:de:80:9d:53:f1) | Recorder/Storage | ✅ Online |
| **Matebook D2019 (Dev Bot)** | **192.168.1.44** | **Dev Host — รันบอททดสอบ** | ✅ ใช้ก่อน |
| Pi Zero 2 W / Edge | 192.168.1.33 (จอง) | Edge Target — พักไว้ | ⏳ ค่อย deploy |
| IPC เพิ่มเติม | 192.168.1.101-150 | — | เผื่อขยาย |

> อ้างอิงเดิม: `cctv/plans/2026-09-07_CCTV-Server-IPC-Plan.md:5` + `cctv/docs/ip-map.md:1` + `wiki/products/Seetong-UC2.md:1`

---

## 2) Pi Zero 2 W ไหวไหม — ขีดจำกัดที่ต้องรู้

| สเปก | ค่า | ผลกระทบ |
|---|---|---|
| **CPU BCM2710A1 4× Cortex-A53 @1GHz** | เร็วกว่า Zero W 5× multi-thread | พอรัน Python bot + cron + MQTT ได้ | 
| **RAM 512MB LPDDR2** | น้อย | ห้ามรัน Shinobi/Frigate/ZoneMinder บน Pi ตัวนี้ — จะ OOM |
| **WiFi 2.4GHz b/g/n + BT4.2** | สะดวกแต่ไม่เสถียรเท่า LAN | แนะนำ **USB OTG → Ethernet dongle** สำหรับงาน 24/7 |
| **Storage microSD** | ช้า พังง่ายถ้าเขียนบ่อย | ต้องใช้ **High-Endurance SD 32GB + log2ram + tmpfs** |
| **Power 5V 2.5A** | ดับง่าย | ต้องมี **UPS HAT หรือ Powerbank + smart plug** |
| **Decode 1080p30 H.264** | ทำได้ 1 ช่อง | เทส RTSP ได้แต่ไม่ควร decode ต่อเนื่องหลายกล้อง |

**สรุป:** Pi Z2W = **เหมาะเป็น “watchdog + bot”** ไม่เหมาะเป็น “NVR”

---

## 3) บอททำอะไรได้บ้าง (Control Plane)

### 3.1 หน้าที่หลัก (ต้องทำ)
- **Health Check ทุก 60s:** `ping` + `HTTP GET http://192.168.1.31:8000/` + `http://192.168.1.21/` + `RTSP probe` (`ffmpeg -rtsp_transport tcp -i rtsp://... -t 2 -f null -`)
- **Disk/RAID Check:** scrape หน้า NVR `System → Storage` หรือเรียก `cgi_system?cmd=getSataStatus` (ถ้า auth ได้) — ถ้าไม่ได้ให้ดูผ่าน `SUPPORT_ABNORMAL_DISK_EVENT` แล้วให้ Pi จับ event จาก log
- **Auto Recovery:** ถ้า NVR/IPC ไม่ตอบ 3 ครั้งติด → สั่ง **PoE port bounce** หรือ **Smart Plug power cycle** (ผ่าน Tuya Local / MQTT) + รอ 90s แล้วเช็คใหม่
- **แจ้งเตือน:** Telegram Bot หรือ LINE Notify (`SUPPORT_PUSHNOTIFICATION=true` บน NVR แต่ Pi จะส่งซ้ำให้ชัวร์)
- **Log + Dashboard:** เขียน `SQLite` + `log` หมุนเวียน, web เล็กๆ `Flask` ดูสถานะที่ `http://192.168.1.33:8080`

### 3.2 หน้าที่เสริม (ทำได้ถ้าต้องการ)
- **Schedule:** สั่ง `auto-reboot` ตามเวลาที่ NVR รองรับ (`SUPPORT_AUTO_REBOOT=1`) — ให้ Pi ตั้ง cron เรียก `cgi_system?cmd=reboot` ตอนตี 3
- **Backup Config:** ดูด config NVR คืนละครั้งเก็บที่ `/home/pi/backup/` + `cctv/output/`
- **NTP Watchdog:** ถ้าเวลากล้องเพี้ยน Pi จะเรียก `ntpdate` หรือแจ้ง
- **ควบคุมภายนอกแบบปลอดภัย:** Bot รับคำสั่ง `/status`, `/reboot nvr`, `/reboot ipc .21`, `/snapshot` ผ่าน Telegram (auth ด้วย chat_id whitelist)

### 3.3 สิ่งที่ Pi Z2W ไม่ควรทำ
- ❌ เก็บวิดีโอย้อนหลัง (ให้ NVR เก็บ)
- ❌ รัน Shinobi/Frigate, transcode หลายช่อง, AI detect (YOLO) — RAM ไม่พอ
- ❌ เปิดพอร์ตออกอินเทอร์เน็ตตรง — ให้เข้าผ่าน VPN/WireGuard ที่เราท์เตอร์

**ด้านความปลอดภัย:** NVRmini 2 fw `03.11.0000.0005` อยู่ในตระกูลที่เคยมี **CVE-2018-1149 (Peekaboo) RCE ผ่าน `cgi_system` PHPSESSID** — ต้อง **ห้ามเปิดพอร์ต 8000 ออก WAN** และให้ Pi อยู่ใน VLAN เดียวกันเท่านั้น (ดู Tenable TRA-2018-25)

---

## 4) Software Stack สำหรับ Pi Z2W (เบา, เสถียร)

```
OS: Raspberry Pi OS Lite (Bookworm) 64-bit
Python: 3.11 + venv
Service: systemd (cctv-bot.service) + watchdog
Libs: requests, python-telegram-bot==20.x, paho-mqtt, schedule, pyyaml, ffmpeg (apt)
Storage: SQLite (status.db) + log2ram (tmpfs /var/log) + logrotate
Hardware: USB-Ethernet (optional), Smart Plug (Tuya/Sonoff) สำหรับ power cycle, UPS 5V
```

**โครงสร้างไฟล์บน Pi:**
```
/home/pi/cctv-bot/
  config.yaml          # ip, user/pass (ไม่ commit), chat_id, plug ip
  bot.py               # main loop + Telegram handler
  health.py            # check_nvr(), check_ipc(), check_rtsp()
  actions.py           # reboot_nvr(), reboot_ipc(), power_cycle()
  requirements.txt
  status.db            # SQLite
  logs/ -> /var/log/cctv-bot (tmpfs)
```

**ตัวอย่าง `config.yaml` (เก็บนอก Git ตาม `.gitignore`):**
```yaml
nvr:
  ip: 192.168.1.31
  port: 8000
  user: admin
  pass: "***"
  check_interval: 60
ipc:
  - ip: 192.168.1.21
    rtsp: "rtsp://admin:***@192.168.1.21:554/ucast/11"
    port: 80
telegram:
  token: "***"
  allow_chat_ids: [123456789]
smart_plug:
  nvr_plug_ip: 192.168.1.40  # Tuya local
  ipc_plug_ip: 192.168.1.41
```

---

## 5) ตัวอย่างบอท (โค้ดต้นแบบ — รันได้จริงบน Pi Z2W)

วางต้นแบบไว้ที่ `cctv/scripts/pi-z2w-bot/` — ดูไฟล์ `bot.py` + `health.py` ที่สร้างให้แล้ว สามารถ `scp` ขึ้น Pi แล้ว `pip install -r requirements.txt` ได้เลย

**พฤติกรรม:**
- ลูปทุก 60s → `health.py` เช็ค 3 อย่าง (ping, HTTP, RTSP)
- ถ้า fail 3 ครั้งติด → `actions.py` สั่ง power cycle + ส่ง Telegram
- รับคำสั่ง `/status` → ตอบสถานะล่าสุด + uptime + disk (scrape จาก NVR ถ้า login ได้)
- เขียน log แบบ `log2ram` กัน SD พัง

> โค้ดเต็มดูใน `cctv/scripts/pi-z2w-bot/bot.py:1` และ `cctv/scripts/pi-z2w-bot/health.py:1`

---

## 6) วิธีติดตั้ง — เฟส Dev บน Matebook D2019 (5 นาที) แล้วค่อยลง Edge

### 6A. รันบน Matebook D2019 (Windows 10) — แนะนำตอนนี้

```powershell
# PowerShell — รันจาก Vault นี้เลย (192.168.1.44)
python -m venv .venv-cctv
.\.venv-cctv\Scripts\Activate.ps1
pip install -r cctv/scripts/pi-z2w-bot/requirements.txt
Copy-Item cctv/scripts/pi-z2w-bot/config.yaml.example cctv/scripts/pi-z2w-bot/config.yaml
notepad cctv/scripts/pi-z2w-bot/config.yaml  # ใส่ pass/token จริง (ไม่ commit)
python cctv/scripts/pi-z2w-bot/health.py    # เทสก่อน — ต้องได้ NVR+IPC ✅

# รันบอทยาว (dev)
python cctv/scripts/pi-z2w-bot/bot.py
# หรือรันเป็น background: Start-Process python -ArgumentList "cctv/scripts/pi-z2w-bot/bot.py"
# หรือตั้ง Task Scheduler ให้รันตอน login
```

> ข้อดี Matebook: ดีบักง่าย, ไม่ห่วง SD, มี opencode/Muse Spark รัน `verify_system.py` ได้ทันที, แก้โค้ดแล้วเทสซ้ำเร็ว

### 6B. เมื่อนิ่งแล้วค่อย Deploy ลง Edge (15 นาที)

```bash
# บน Edge ที่เลือก (Pi Z2W / Pi 4 / Mini PC — Raspberry Pi OS)
sudo apt update && sudo apt install -y python3-venv python3-pip ffmpeg sqlite3 log2ram
python3 -m venv ~/cctv-bot/venv && source ~/cctv-bot/venv/bin/activate
pip install -r cctv/scripts/pi-z2w-bot/requirements.txt
scp -r cctv/scripts/pi-z2w-bot/* pi@192.168.1.33:~/cctv-bot/ && nano ~/cctv-bot/config.yaml
sudo cp ~/cctv-bot/cctv-bot.service /etc/systemd/system/
sudo systemctl enable --now cctv-bot && journalctl -u cctv-bot -f
# ทดสอบ: บนมือถือพิมพ์ /status ใน Telegram bot
```

**ทดสอบก่อนใช้งานจริง (ทำบน Matebook ได้เลย):**
1. ดึงสาย LAN NVR ออก 60s → บอทต้องแจ้งเตือน + ลอง power cycle
2. ปิด IPC .21 → บอทต้องแจ้ง `IPC .21 RTSP fail`
3. สั่ง `/reboot nvr` จาก Telegram → NVR ต้อง reboot (ถ้า auth ถูก)

---

## 7) ข้อดี/ข้อเสีย vs ทางเลือกอื่น

| ทางเลือก | ข้อดี | ข้อเสีย |
|---|---|---|
| **Pi Z2W เป็น Bot (แบบนี้)** | ถูก (~500บ), กินไฟน้อย, ทำ watchdog ได้ 24/7, แยกจาก NVR ไม่กระทบ | WiFi ไม่เสถียรเท่า LAN, SD พังง่าย, ทำ AI/เก็บวิดีโอไม่ได้ |
| **Pi 4 / Pi 5 เป็น NVR** | แรงพอรัน Frigate/Shinobi ได้ | แพงกว่า 3-4×, กินไฟ, ต้องดูแล storage เอง |
| **ไม่ใช้ Pi เลย ให้ NVR ส่งเมลอย่างเดียว** | ง่าย | ไม่มี auto-recovery, ไม่มี dashboard, พึ่ง NVR อย่างเดียว |

> ถ้าต้องการ AI detect คน/รถ แนะนำเพิ่ม **Pi 5 หรือ Mini PC** แยกอีกตัว ไม่ใช่ Z2W

---

## 8) ความเสี่ยงและวิธีลด

| ความเสี่ยง | วิธีลด |
|---|---|
| SD card พัง | ใช้ High-Endurance + log2ram + อ่านอย่างเดียว (`overlayfs`) |
| WiFi หลุด | ใช้ USB-Ethernet + ตั้ง `watchdog` reboot ถ้า ping GW ไม่ได้ 5 นาที |
| ไฟดับ | UPS 5V + ตั้ง NVR `SUPPORT_AUTO_REBOOT` + Pi auto-start service |
| NVR fw เก่าโดน hack | ห้ามเปิด 8000 ออกเน็ต, ใส่ VLAN, อัปเดต fw เป็น `3.9.1+` หรือ `03.11.0000.0016+` ถ้ามี |
| Bot ส่งแจ้งเตือนรัว | ใส่ cooldown 15 นาที + สรุปเป็น digest |

---

## 9) ขั้นถัดไป (Dev-first) — ทำบน Matebook ก่อน

- [x] ตัดสินใจ: **พัก Pi Z2W ไว้ก่อน ใช้ Matebook D2019 (192.168.1.44) เป็น dev host** — ดีกว่า (ดีบักเร็ว, ไม่ต้องดูแล SD)
- [ ] หา user/pass NVR `.31` และ IPC `.21` ใส่ `cctv/scripts/pi-z2w-bot/config.yaml` (ไม่ commit) แล้วรัน `health.py` บน Matebook
- [ ] รัน `bot.py` บน Matebook แบบ foreground ทดสอบ 24-48 ชม. ดู log/SQLite
- [ ] เมื่อนิ่ง: เลือก Edge ที่เหมาะ (Pi Z2W ถ้าแค่ watchdog เบาๆ / Pi 4/Mini PC ถ้าจะเพิ่ม AI) แล้ว containerize/deploy — ค่อยจอง IP `192.168.1.33` + เตรียม SD/USB-Ethernet ตอนนั้น

---

**ไฟล์ที่เกี่ยวข้อง:** `cctv/docs/ip-map.md:1` | `wiki/products/Seetong-UC2.md:1` | `cctv/docs/2026-09-07_Seetong-IPC-192.168.1.21-Config.md:1` | `cctv/scripts/pi-z2w-bot/bot.py:1`
