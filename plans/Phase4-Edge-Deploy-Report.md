---
type: cctv_report
title: "Phase 4 — เลือก Edge และเตรียม Deploy (Z2W vs Pi4 vs MiniPC)"
date: 2026-09-08 01:38
project: HMS-2026-001 Hermes Sentinel
status: ✅ DEPLOYED 2026-09-20 — Z2W .20 = watchdog/poller (poll Telegram ตัวเดียว) + Gateway .94 = YOLO worker (delegate SSH) — รายละเอียดด้านล่าง
edge_ip: 192.168.1.20 (Pi Z2W — deploy แล้ว)
matebook: 192.168.1.44 Dev host (ไม่รันบอท runtime แล้ว)
---

# Phase 4 — Edge Deploy Plan

> **อัปเดต 2026-09-20 — deploy จริงเสร็จ (สถาปัตยกรรม 2 ระดับ):**
>
> | เครื่อง | บทบาทจริง | สถานะ |
> |---|---|---|
> | **Pi Z2W `192.168.1.20`** (user `admin`, WiFi) | **Watchdog + poller หลัก** — `cctv-bot.service` (unit: `cctv-bot-z2w.service`, MemoryMax 320M) health 60s + Telegram poll + /status /snapshot /clip (ใช้ rtsp sub `/1` 360p — main `/0` 1080p ล้มบน WiFi) | ✅ active/enabled — health NVR/IPC/rtsp ผ่านครบ |
> | **Gateway `192.168.1.94`** (RPi 1GB, user `ecs-agent`) | **YOLO worker** — บอท watchdog **ปิด + disable แล้ว** (poll ต้องมีตัวเดียว) — รับงาน `/person` `/person_auto` จาก Z2W ผ่าน SSH (`person.delegate_ssh`) + cron `/etc/cron.d/cctv-tmp-cleanup` เก็บกวาด /tmp ทุกชม. (ไฟล์เกิน 24ชม.) | ✅ RAM คืน ~160MB หลังปิดบอท |
>
> แผนเดิมด้านล่างคือบันทึกกระบวนการ (benchmark ยังใช้อ้างอิงได้) — ทางเลือกที่เลือกจริงคือ A ผสม B: Z2W ทำ watchdog แต่ **ไม่โหลด torch** ส่งงาน YOLO ข้ามเครื่องแทน (ฟีเจอร์ delegate ใน `bot.py` + เอกสาร `README.md` §delegate)

> ต่อจาก Phase 3 ที่ YOLO บน Matebook ทำงานแล้ว (bus 3 คน 5.34s) — Phase 4 ต้องย้าย bot จาก Matebook (dev) → Edge 24/7
> แผนนี้สรุปตัวเลือกตาม benchmark จริง + เตรียม deploy script + service

## 1) Benchmark ที่มีแล้ว

| อุปกรณ์ | สเปก | YOLOv8n bus.jpg | ผลประเมิน |
|---|---|---|---|
| **Matebook D2019** (Windows 10, Python 3.12, CPU) | i5-8265U 8GB | **5.34s / 3 คน conf 0.85** + annotated 345KB | ✅ On-Demand พอได้ แต่ auto ทุก 30s กิน CPU หนัก |
| **Pi Zero 2 W** (คาดการณ์) | BCM2710A1 512MB quad A53 1GHz | **>10-15s + RAM ไม่พอ torch** (512MB ต้อง swap) | ❌ ไม่เหมาะ YOLO ต่อเนื่อง — ใช้ fallback motion ได้ |
| **Pi 4 4GB** (คาดการณ์) | BCM2711 4GB quad A72 1.5GHz | **~2-3s / frame** (จาก community bench) | ✅ พอสำหรับ `person_watch 30s interval` |
| **MiniPC x86** (N100 / i3) | 8GB+ | **<1s / frame** | ✅ ดีสุดถ้าต้องการ auto ถี่ |

**สรุป:** ถ้าแค่ `watchdog + /snapshot + /clip` → **Pi Z2W พอ** (512MB ไม่ต้องโหลด torch, ใช้ `motion_fallback` + `health.py`). ถ้าต้องการ `/person_auto` YOLO จริง → **ต้อง Pi 4 4GB+ หรือ MiniPC**

## 2) ทางเลือกที่เสนอ

### ทางเลือก A: Z2W แบบประหยัด (watchdog only)
- ใช้ `person_detect.py` fallback `motion` — ไม่ติดตั้ง `ultralytics/torch` บน Z2W
- หน้าที่: `health.py 60s` + `bot poll 60s` + `/snapshot` + `/clip` + แจ้งเตือน Telegram
- ข้อดี: กินไฟน้อย, SD High-Endurance 32GB + log2ram ก็ทน
- ข้อเสีย: ไม่มี YOLO auto — ต้องสั่ง `/person` แล้วไปรัน YOLO บน Matebook หรือ NVR motion แทน

### ทางเลือก B: Pi 4 4GB (แนะนำถ้าจะใช้ Person)
- ติดตั้ง `ultralytics 8.4.143 + opencv + torch (aarch64)` บน Pi 4
- รัน `person_watch 30s` ได้จริง — cooldown 5 นาที กัน spam
- คาดว่าช้ากว่า Matebook ~ครึ่งนึง แต่พอสำหรับ 30s interval

### ทางเลือก C: MiniPC (ดีสุด)
- ถ้ามี MiniPC เหลือ → รัน YOLO เร็วสุด, เสถียร, ไม่ห่วง SD พัง
- ใช้ SSD แทน SD — ทนกว่า

> **คำแนะนำ:** เริ่มด้วย **A** (Z2W) ถ้ามีของอยู่แล้ว ทดสอบ watchdog 2-3 วัน — ถ้าพอใจค่อยอัปเกรดเป็น **B/C** เมื่อต้องการ YOLO auto จริง

## 3) เตรียมอุปกรณ์ (ก่อน deploy)

- [ ] จอง `192.168.1.33` บน Router (DHCP reservation)
- [ ] เตรียม `High-Endurance SD 32GB` + `USB-Ethernet` (Z2W WiFi ไม่เสถียร) + `log2ram` + `overlay` กัน SD พัง
- [ ] ติดตั้ง `Raspberry Pi OS Lite 64-bit` + `python3.11 + pip + ffmpeg`
- [ ] เปิด `WireGuard` บน Edge (ถ้าต้องดู NVR จาก Edge) หรือให้ Edge อยู่ LAN เดียวกับ NVR ก็ไม่ต้อง

## 4) Deploy Steps (เมื่อเลือกแล้ว)

```bash
# บน Matebook (dev) — เตรียมไฟล์
scp -r cctv/scripts/pi-z2w-bot pi@192.168.1.33:~/cctv-bot/
# ใช้ config.yaml.example เป็นต้นแบบ — อย่า copy token จริงผ่าน git
ssh pi@192.168.1.33
  cd ~/cctv-bot
  cp config.yaml.example config.yaml   # แล้วเติม token/chat_id เอง
  pip install -r requirements.txt       # ถ้าเลือก B/C เพิ่ม ultralytics
  # Pi4: pip install ultralytics opencv-python
  python3 health.py                     # ตรวจ rtsp ok ก่อน
  sudo cp cctv-bot.service /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable --now cctv-bot
  sudo systemctl status cctv-bot
  journalctl -u cctv-bot -f
```

`cctv-bot.service:1` มีแล้ว:
```
[Unit] Description=Hermes Sentinel Bot After=network.target
[Service] ExecStart=/usr/bin/python3 /home/pi/cctv-bot/bot.py Restart=always
[Install] WantedBy=multi-user.target
```

## 5) ทดสอบหลัง deploy

- [ ] `ssh pi@192.168.1.33 "systemctl is-active cctv-bot"` → active
- [ ] Telegram `@hm2569bot` → `/status` → `Person: YOLO/motion` + `NVR ok`
- [ ] `/snapshot` → ได้ภาพ 70KB
- [ ] `/person` → (ถ้า B/C) ได้ annotated ถ้ามีคน / (ถ้า A) ได้ fallback message
- [ ] ดึงสาย LAN 60s → bot ควร `FAIL 3× cooldown 15m` แล้วกลับมา ok

## 6) ความเสี่ยงและวิธีกัน

| เสี่ยง | กัน |
|---|---|
| SD พัง (Z2W) | High-Endurance + log2ram + ไม่เขียน log ถี่ |
| YOLO กิน RAM | เลือก B/C ถ้าจะ auto, A ใช้ fallback |
| WG หลุดหลัง reboot | `fix-wg-auto.ps1` บน Matebook / `wg-quick@wg0` บน Pi |
| Matebook ดับก่อนย้าย | NVR ยังเก็บ `Always 10%` ต่อ — ไม่หาย |

## 7) ไฟล์ที่เกี่ยวข้อง

- `cctv/scripts/pi-z2w-bot/cctv-bot.service:1`
- `cctv/scripts/pi-z2w-bot/config.yaml.example:1`
- `cctv/scripts/pi-z2w-bot/requirements.txt:1`
- `cctv/scripts/pi-z2w-bot/README.md:1`
- `cctv/docs/ip-map.md:1`
- `cctv/plans/2026-09-08_Master-Execution-Plan.md:84` (Phase 4 checklist)
- `cctv/plans/Project-Hermes-Sentinel.md:57`

## 8) ถัดไป (Phase 5)

- เมื่อ Edge รันนิ่ง 2-3 วัน → สร้าง `cctv/output/handover-2026-09-xx.md` + ส่งมอบ + `verify_system.py ALL PASS`
