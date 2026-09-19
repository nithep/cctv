---
type: cctv_plan
title: "Frigate Trial Plan — ทดลอง Software NVR แทนสมองเก่า เก็บตาเดิม"
date: 2026-09-20
status: ❌ CANCELLED 2026-09-20 — ยกเลิกการทดลอง Frigate ใช้ระบบเดิมต่อ (Z2W watchdog + Gateway YOLO worker + NUUO อัดเทป)
> **บันทึกการยกเลิก (2026-09-20):** ตัดสินใจไม่ทดลอง Frigate — เหตุผล: Gateway .94 (Pi 4 1GB) มีงาน snc ชุดใหญ่อยู่แล้วรับเพิ่มไม่ได้,
> Pi 4 ใหม่ 4GB ต้องลงทุนเสริม (ไฟแท้/Coral) และระบบเดิม (Z2W + delegate YOLO + NUUO) ทำงานครบทุกฟังก์ชันแล้ว
> — แผนเดิมคงไว้เป็นข้อมูลอ้างอิงหากกลับมาพิจารณาในอนาคต (folder frigate-pi4/ ลบออก ดูประวัติ commit 92d6058 ได้)
parent: 2026-09-08_Master-Execution-Plan.md
related: Phase4-Edge-Deploy-Report.md, docs/ip-map.md
---

# Frigate Trial Plan — เปลี่ยน "สมอง" เก็บ "ตา"

> แนวคิด: สิ่งที่ "ตายจริง" ของระบบเดิมคือ NVR firmware + Web UI (ActiveX) ของ NUUO —
> **กล้องยังไม่ตาย** เพราะพูด RTSP มาตรฐานได้ Frigate (open-source NVR + AI ในตัว) กิน stream เดิมได้เลย
> หลักการ: รัน **ขนานกับ NUUO 1-2 สัปดาห์** ไม่กระทบระบบที่ใช้งานอยู่ → นิ่งแล้วค่อยย้ายงานบันทึก

## 1) ทำไมเป็น Frigate

| ปัญหาเดิม | Frigate แก้ |
|---|---|
| ดูย้อนหลังต้อง ActiveX/IE (NUUO Web UI 2020) | UI ทันสมัย ดูได้ทั้งเบราว์เซอร์/มือถือ ไม่ต้องติดตั้ง |
| Person detect ต้องพึ่งบอท + YOLO บน CPU (5.34s/เฟรม บน Matebook) | AI ในตัว + detector เฉพาะ (OpenVINO บน iGPU Intel = ไม่ต้องซื้อเสริม) |
| Retention วนทับ 10% ตั้งยาก | ตั้ง retain ตามวัน/motion ชัดเจน เช่น 14 วัน |
| เปลี่ยนกล้องใหม่ = ผูก NVR รุ่นเดิม | กล้อง RTSP/ONVIF อะไรก็ต่อได้ อนาคตไม่ถูกล็อก |
| Vendor หาย = ระบบตาย | Open source, config เป็นไฟล์, backup ง่าย |

## 2) Hardware ที่แนะนำ

| ตัวเลือก | สเปก | ประเมิน |
|---|---|---|
| **MiniPC N100** ⭐ | 8GB+ SSD, ~3,500-5,000฿ | ดีสุด — OpenVINO ใช้ iGPU ตรวจคนได้โดยไม่ต้องซื้อ accelerator, NIC บางรุ่น 2 ตัวแยก VLAN กล้องได้ |
| Pi 4 4GB | + Coral USB ~1,800฿ + USB SSD ~1,200฿ | ได้จริงแต่ต้องเสริม 2 ชิ้น, Pi 4 ไม่ใช่แนวแนะนำหลักของ Frigate แล้ว (ยัง support) |
| Pi 5 | + Hailo/PCIe | เกินจำเป็นสำหรับ 1-2 กล้อง |

**จอง IP:** `192.168.1.33` (ตาม ip-map — ช่องว่างเตรียมไว้แล้ว)

## 2b) รันบน Pi 4 4GB — ตัวเลือก "ทำได้ทันที"

> Frigate ยังรองรับ Pi 4 อย่างเป็นทางการ (image arm64 เดียวกัน) เหมาะกับ **1-2 กล้องเท่านั้น** — เงื่อนไข 3 ข้อ:

| เงื่อนไข | รายละเอียด | งบเพิ่ม |
|---|---|---|
| **USB SSD** (บังคับ) | SD เก็บ OS อย่างเดียว — เทปวิดีโอเขียนลง SD แล้วพังในไม่กี่เดือน; mount แบบ ext4 | ~1,000-1,500฿ |
| **แหล่งจ่ายไฟแท้ 5.1V/3A** | จ่ายไม่พอ → crash กลางคืน + throttle (ตรวจ `vcgencmd get_throttled`) | ถ้าไม่มี ~400฿ |
| **Coral USB TPU** (แนะนำ) | CPU detector บน Pi4 ได้ ~0.5-1 fps (พอ 1 กล้อง fps 5 แบบหยั่งรู้); Coral ทำ ~10-20ms เต็มสมรรถนะ — ใช้โมเดล default (ssdlite mobilenet) **YOLOv8n ไม่รันบน Coral** | ~1,800฿ |

**docker-compose เฉพาะ Pi 4** (ต่างจาก MiniPC ที่ device):

```yaml
# /opt/frigate/docker-compose.yml บน .33 (Pi 4)
services:
  frigate:
    image: ghcr.io/blakeblackshear/frigate:stable
    container_name: frigate
    restart: unless-stopped
    privileged: true
    shm_size: "128mb"          # 1-2 กล้องพอ
    devices:
      - /dev/video11:/dev/video11   # VideoCore v4l2m2m (h264 hw decode ของ Pi)
    volumes:
      - ./config:/config
      - /mnt/frigate-media:/media/frigate   # USB SSD — บังคับ ห้ามเก็บลง SD
      - /etc/localtime:/etc/localtime:ro
    ports:
      - "5000:5000"
      - "8554:8554"
```

**config.yml เฉพาะ Pi 4** (เพิ่มทับส่วน detectors/ffmpeg ของ §5):

```yaml
ffmpeg:
  hwaccel_args: preset-rpi-64-h264   # ใช้ VideoCore decode แทน CPU — ขาดตัวนี้ CPU ล้นทันที
detectors:
  coral:
    type: edgetpu
    device: usb
  # ถ้ายังไม่มี Coral: ลบ detectors ออกทั้งหมด → Frigate ใช้ CPU detector เอง (ช้ากว่าแต่ใช้ได้ทดลอง)
```

**ข้อจำกัดที่ต้องรับรู้ (vs MiniPC):** RAM 4GB ใกล้เพดานถ้าเปิด UI ตลอด + หลายกล้อง, ขยายเกิน 2-3 กล้องไม่ไหว,
และเอกสารทางการ Frigate เลิกเป็นแนวแนะนำหลักของ Pi 4 แล้ว (ยัง support) — **ถ้าเป็นแค่ทดลอง 1 กล้อง 2 สัปดาห์: ใช้ได้เต็มที่**

## 3) ขั้นตอนทดลอง (ขนาน ไม่แตะระบบเดิม)

### สัปดาห์ 1 — ติดตั้ง + ดูภาพ
- [ ] ติดตั้ง Raspberry Pi OS Lite 64-bit (Debian 13) + Docker บน Pi 4 `.33` (static IP + DHCP reservation) — OS ลง SD เท่านั้น, mount USB SSD ที่ `/mnt/frigate-media`
- [ ] รัน stack: `go2rtc` (RTSP gateway) + `Frigate` (docker-compose ด้านล่าง)
- [ ] ต่อ stream กล้อง Seetong: detect ใช้ sub `/1` (360p เบา), record ใช้ main `/0` (1080p)
- [ ] ต่อ USB HDD/SSD เก็บเทป (ห้ามเก็บลง SD)
- [ ] ทดสอบ: ดูสด, เหตุการณ์ motion/person, playback ย้อนหลังบนมือถือ

### สัปดาห์ 2 — เทียบผลกับระบบเดิม
- [ ] รันคู่ NUUO จริง — เทียบ: ภาพหายไหม, ตรวจคนแม่นกว่า YOLO-CPU กี่เท่า, CPU/RAM ใช้เท่าไร
- [ ] เชื่อม Telegram: Frigate webhook → bot แจ้งเหตุการณ์ (คง @hm2569bot เป็นหน้าด้านเดียว)
- [ ] ตั้ง retain: เช่น motion 14 วัน + continuous 7 วัน (ปรับตาม HDD)
- [ ] Backup config + ทดสอบ restore 1 ครั้ง

### จบสัปดาห์ 2 — ตัดสินใจ
- [ ] เกณฑ์ย้ายงานบันทึก: รันนิ่ง ≥7 วัน, 0 ภาพหาย, ตรวจคนแม่นกว่าเดิมชัดเจน
- [ ] ถ้าย้าย: NUUO เปลี่ยนบทบาทเป็นตู้ HDD สำรอง (อัดต่อก็ได้ 2 ชั้นกันเหลือ) — Z2W watchdog คงอยู่
- [ ] ถ้าไม่ผ่าน: ระบบเดิมยังอยู่ครบ ลบ container จบ

## 4) docker-compose (ตัวเริ่มต้น)

```yaml
# /opt/frigate/docker-compose.yml บน .33
services:
  frigate:
    image: ghcr.io/blakeblackshear/frigate:stable
    container_name: frigate
    restart: unless-stopped
    privileged: true   # จำเป็นสำหรับ OpenVINO/iGPU
    shm_size: "128mb"  # 1-2 กล้องพอ
    devices:
      - /dev/dri:/dev/dri   # Intel iGPU (hw decode + OpenVINO)
    volumes:
      - ./config:/config
      - /mnt/frigate-media:/media/frigate   # USB SSD/HDD
      - /etc/localtime:/etc/localtime:ro
    ports:
      - "5000:5000"   # UI
      - "8554:8554"   # RTSP restream
```

## 5) config.yml สำหรับกล้อง Seetong (ตัวเริ่มต้น)

```yaml
mqtt: enabled: false          # ยังไม่ใช้ HA
detectors:
  ov:
    type: openvino
    device: GPU
    model: { path: /config/model_cache/yolov8n-320 }

cameras:
  seetong_front:
    ffmpeg:
      inputs:
        - path: rtsp://admin:123456@192.168.1.21:554/1   # sub 360p → detect (เบา)
          roles: [detect]
        - path: rtsp://admin:123456@192.168.1.21:554/0   # main 1080p → record
          roles: [record]
    detect: { fps: 5, enabled: true }
    objects: { track: [person] }
    record:
      enabled: true
      retain: { days: 14, mode: motion }
    snapshots: { enabled: true, retain: { default: 14 } }
```

> หมายเหตุ: กล้องนี้รับ client ซ้ำบางลอจึงให้ go2rtc restream แล้ว Frigate ดึงจาก go2rtc จะเสถียรกว่า (ดู docs Frigate §restream)

## 6) ความเสี่ยงและวิธีกัน

| เสี่ยง | กัน |
|---|---|
| กล้องรับ 2 client (NUUO + Frigate) ไม่ไหว | ให้ Frigate ดึงผ่าน go2rtc restream ตัวเดียว ไม่ดึงตรงซ้ำ |
| ระบบเดิมพังระหว่างทดลอง | ทดลองแบบ read-only — Frigate ไม่สั่งอะไรกล้อง/NUUO |
| HDD เสียจากเขียนหนัก | ใช้ HDD surveillance หรือ SSD + retain จำกัดวัน |
| ลืมระบบเดิมรั่ว (Seetong cloud) | ทำ hardening ตามแผน D ควบคู่ (เปลี่ยน pass กล้อง + ปิด cloud) |

## 7) เชื่อมกับบอทเดิม

- Z2W watchdog (`cctv-bot`) คงเดิม — health ต่อ NVR/IPC ตรง ๆ ไม่เกี่ยว Frigate
- หลัง Frigate นิ่ง: เพิ่ม health ฝั่ง Frigate (`http://.33:5000/api/stats`) ใน `health.py` อีก 1 target
- แจ้งเตือน: Frigate webhook → บอท (หรือส่ง Telegram ตรง) — รวมศูนย์ที่ @hm2569bot ตามเดิม
