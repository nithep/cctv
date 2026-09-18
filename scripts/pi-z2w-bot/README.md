# Pi Z2W Bot — วิธีใช้

> บอทเบาสำหรับ Pi Zero 2 W (512MB) — มอนิเตอร์ NVRmini 2 + Seetong IPC ไม่เก็บวิดีโอ
> **Pi 4 (2-4GB): + Event Recorder** — ตรวจเจอคนแล้วอัดคลิปเฉพาะ event ลงเครื่อง (`/rec` + auto)

## คำสั่ง Telegram

- `/status` — ดูสถานะ NVR+IPC ล่าสุด (รวม FFmpeg + Person + EventRec backend)
- `/snapshot` — ดึงภาพล่าสุด 1080p จาก IPC 192.168.1.21 (ลอง main 2 ครั้ง + sub stream 1 ครั้ง)
- `/clip [วินาที]` — ดึงคลิป 5-30s มาดูอย่างเดียว (ไม่เก็บ)
- `/rec [วินาที]` — **Pi4 เท่านั้น:** บันทึก event ลงเครื่องทันที (default 30วิ, สูงสุด 120วิ) + ส่งคลิปให้
- `/person [conf]` — Phase 3: สแกนภาพล่าสุดหา 'คน' ด้วย YOLOv8n (เช่น `/person 0.6`)
- `/person_auto [on/off]` — เปิด/ปิด auto scan ทุก 30วิ — **dedup แบบ "การเยี่ยม"**: คนที่ยังยืนหน้ากล้อง = 1 เหตุการณ์ (ไม่เซฟไฟล์ซ้ำ/ไม่แจ้งซ้ำ) หายไปเกิน `person.new_visit_gap` (default 600วิ) แล้วกลับมา = เหตุการณ์ใหม่; Pi4 + `record_on_person:true` จะแนบคลิป event มาด้วย
- `/events [จำนวน]` — รายการเหตุการณ์ "พบคน" ย้อนหลัง (เก็บใน status.db → `person_events` 1 แถวต่อการเยี่ยม)
- `/event <หมายเลข>` — เรียกภาพ/คลิปของเหตุการณ์ย้อนหลังส่งเข้าแชท (ถ้าไฟล์ยังไม่โดน quota prune)
- `/reboot` — สั่ง power cycle (ต้องต่อ actions.py กับ Smart Plug ก่อน)

## Pi4 Event Recorder (ใหม่)

> NVR ยังอัด `Always` 24 ชม. ต่อไปเหมือนเดิม — Pi4 อัด **สำเนาเฉพาะ event** ลง `output/events/` หยิบง่าย ไม่ต้องขุด `.dat` ใน NVR

- ตั้งใน `config.yaml`: `event_rec: {record_on_person: true, secs: 30, quota_mb: 4096, max_secs: 120}`
- `record_on_person: true` → `/person_auto on` เจอคนปุ๊บอัด `person_<timestamp>_30s.mp4` ทันที (ffmpeg `-c copy` CPU ~5%)
- quota เต็มลบไฟล์เก่าสุดอัตโนมัติ (`4GB ≈ 20 event/วัน x30วิ เก็บได้ ~7 วัน`)
- **Z2W/SD card:** ตั้ง `record_on_person: false` — SD เขียนบ่อยพังไว ใช้แค่ `/clip`
- ทดสอบ: `python event_record.py --secs 10 --reason test` (ไม่ต้องมี YOLO)## ตรวจทั้งหมดในคำสั่งเดียว (verify.ps1 / verify.sh)

```powershell
# Windows (Matebook):
powershell -ExecutionPolicy Bypass -File scripts\pi-z2w-bot\verify.ps1        # ffmpeg + deps + syntax + config + pytest
powershell -ExecutionPolicy Bypass -File scripts\pi-z2w-bot\verify.ps1 -full   # + เช็ค network จริง (health.py)
```

```bash
# Pi4 / Pi Zero 2W / ecs-agent:
bash scripts/pi-z2w-bot/verify.sh          # ffmpeg + venv + deps + syntax + config + pytest
bash scripts/pi-z2w-bot/verify.sh --full   # + เช็ค network จริง (health.py)
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts\pi-z2w-bot\verify.ps1        # ffmpeg + deps + syntax + config + pytest
powershell -ExecutionPolicy Bypass -File scripts\pi-z2w-bot\verify.ps1 -full   # + เช็ค network จริง (health.py)
```

## Tests (pytest)
```powershell
pip install pytest
pytest scripts/pi-z2w-bot/test_health_alerts.py -v
```

ครอบคลุม health alert (ffmpeg หาย/RTSP ล่มเกิน 5 นาที): เตือนครั้งเดียวตอนพัง, แจ้งครั้งเดียวตอนหาย, เกณฑ์ 300 วิ + ตั้งตาม `alerts.rtsp_down_secs` ได้, หลายกล้องแจ้งแยกกัน, `_valid_jpeg` ตรวจไฟล์เสีย
## Health Alerts (ใหม่)

- บอทเตือนเข้า Telegram เองเมื่อ **ffmpeg หาย** (โดนลบ/uninstall) หรือ **RTSP ล่มต่อเนื่องเกิน 5 นาที** (ตั้งได้ `alerts.rtsp_down_secs` ใน config.yaml)
- พังส่งเตือนครั้งเดียว หายก็แจ้งกลับครั้งเดียว — ไม่สแปม
- เช็คว่า config.yaml จริงบนเครื่องตรงกับ example ไหม (ไม่แสดง secret):

```bash
python scripts/pi-z2w-bot/check-config.py   # ไม่ใส่ path = หาเอง (โฟลเดอร์นี้ → สำเนา Google Drive)
```

## ติดตั้งใหม่ทั้งหมดบน Windows (เมื่อ ffmpeg/python โดนลบ)
```powershell
powershell -ExecutionPolicy Bypass -File scripts\pi-z2w-bot\install-deps.ps1
```
- ติดตั้ง ffmpeg (winget Gyan.FFmpeg) + python packages ตาม requirements.txt + เสนอติดตั้ง YOLO
- `start-bot.ps1` / `snapshot-hourly.ps1` **หา ffmpeg เอง** (PATH ก่อน แล้วไล่หา Gyan.FFmpeg* ทุกเวอร์ชัน) — winget อัปเดตเวอร์ชัน path เปลี่ยนก็ไม่พัง
- ทดสอบเร็ว: `powershell -File scripts\pi-z2w-bot\start-bot.ps1` แล้วสั่ง `/snapshot` ใน Telegram

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

## Troubleshooting — Pi4 SIGILL (torch wheel เกิน CPU)

อาการ: bot crash วนด้วย `Main process exited, code=killed, status=4/ILL` ประมาณ 10 วิหลัง log `YOLO model loaded`
สาเหตุ: torch wheel ใหม่ (เช่น 2.14.0 บน Python 3.13) compile ด้วย instruction ที่ Cortex-A72 ไม่รองรับ — try/except กันไม่ได้ (process ตายทันที)
แก้:

```bash
~/cctv-bot/venv/bin/pip install --force-reinstall torch==2.6.0 torchvision==0.21.0
```

กันไว้แล้วในโค้ด: `person_detect._torch_ok()` ทดสอบ YOLO inference จริงใน subprocess ลูกก่อนใช้ทุกครั้ง (cache ผล) — ถ้า torch พังจะปิด YOLO แล้ว fallback อย่างสง่างาม ไม่ลาก bot ตาย

## โครงสร้าง

- `health.py` — check_nvr/check_ipc (tcp/http/rtsp)
- `bot.py` — loop 60s + Telegram + SQLite log + /person handler
- `person_detect.py` — YOLOv8n person detect + RTSP snapshot + annotate (Phase 3)
- `config.yaml.example` — ต้นแบบ (ห้าม commit config.yaml จริง)
