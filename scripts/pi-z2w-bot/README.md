# Pi Z2W Bot — วิธีใช้

> บอทเบาสำหรับ Pi Zero 2 W (512MB) — มอนิเตอร์ NVRmini 2 + Seetong IPC ไม่เก็บวิดีโอ

## ติดตั้งบน Pi

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip ffmpeg sqlite3 log2ram
python3 -m venv ~/cctv-bot/venv
source ~/cctv-bot/venv/bin/activate
pip install -r requirements.txt
mkdir -p ~/cctv-bot && cp bot.py health.py config.yaml.example ~/cctv-bot/config.yaml
nano ~/cctv-bot/config.yaml  # ใส่ pass/token จริง
sudo cp cctv-bot.service /etc/systemd/system/
sudo systemctl enable --now cctv-bot
journalctl -u cctv-bot -f
```

## ทดสอบจาก PC ก่อน

```bash
pip install pyyaml requests
python health.py  # ต้องมี config.yaml ในโฟลเดอร์เดียวกัน
```

## คำสั่ง Telegram

- `/status` — ดูสถานะ NVR+IPC ล่าสุด (รวม Person backend)
- `/snapshot` — ดึงภาพล่าสุด 1080p จาก IPC 192.168.1.21
- `/clip [วินาที]` — ดึงคลิป 5-30s
- `/person [conf]` — Phase 3: สแกนภาพล่าสุดหา 'คน' ด้วย YOLOv8n (เช่น `/person 0.6`)
- `/person_auto [on/off]` — เปิด/ปิด auto scan ทุก 30วิ (ส่งเฉพาะมีคน, cooldown 5นาที)
- `/reboot` — สั่ง power cycle (ต้องต่อ actions.py กับ Smart Plug ก่อน)

## Phase 3 — Person Filter (YOLOv8n)

> Matebook D2019 RAM พอ — ติดตั้ง `pip install ultralytics opencv-python` แล้วรัน `/person` ได้เลย
> Pi Z2W 512MB ไม่แนะนำรัน YOLO ต่อเนื่อง — ใช้ fallback motion หรือ NVR `SUPPORT_MOTION_RECORDING`

```powershell
# บน Matebook D2019 (Windows)
C:\Users\Nithep\AppData\Local\Programs\Python\Python312\Scripts\pip.exe install ultralytics opencv-python
python cctv/scripts/pi-z2w-bot/person_detect.py --image cctv/output/snapshot_2026-09-08_00-39.jpg
python cctv/scripts/pi-z2w-bot/person_detect.py --rtsp rtsp://admin:123456@192.168.1.21:554/0
# ถ้าไม่มี ultralytics จะ fallback เป็น motion (ไม่ error)
```

`person_detect.py` เก็บภาพที่มีคนไว้ที่ `cctv/output/person/person_*.jpg` (ไม่ commit)

## โครงสร้าง

- `health.py` — check_nvr/check_ipc (tcp/http/rtsp)
- `bot.py` — loop 60s + Telegram + SQLite log + /person handler
- `person_detect.py` — YOLOv8n person detect + RTSP snapshot + annotate (Phase 3)
- `config.yaml.example` — ต้นแบบ (ห้าม commit config.yaml จริง)
