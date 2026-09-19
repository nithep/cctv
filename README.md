# cctv — ระบบคืนชีพ CCTV ตกรุ่นไร้ Support (แจกฟรี Public)

> **Public Free** — แจกฟรีสำหรับช่าง/ร้านที่เจอ NVR/IPC ตกรุ่นเหมือนกัน
> แยกจาก `T.C.Com` vault ที่เป็น private — ไม่มีข้อมูลลูกค้า/บัญชีหลุด
> โครงการเดิม `HMS-2026-001 Hermes Sentinel` ยกเลิกชื่อรีโป `hermes-sentinel` — ใช้ `cctv` แทน

## ทำอะไรได้

- เฝ้า `NUUO NVRmini 2 fw 03.11.00` (EOL 2020, CVE-2018-1149) + `Seetong IPC LIVE555 gSOAP/2.8` (2014) ที่ vendor หายแล้ว
- Health check 60s (`tcp/http/rtsp`), แจ้ง Telegram, ดึงภาพ/คลิป On-Demand (`/snapshot` `/clip`)
- Person Filter YOLOv8n (On-Demand `/person` + Auto `/person_auto` ทุก 30s)
- กันภัย: ไม่เปิด 8000 ออก WAN — บังคับผ่าน `WireGuard` + `Cloudflare WARP`
- Edge Deploy: Z2W watchdog / Pi4 4GB / MiniPC

## โครงสร้าง

```
docs/       — ip-map, Config-Test-Report, Seetong-Config
plans/      — Master-Execution-Plan, Project, Phase0-5 reports, handover, Repo-Split-Plan
scripts/pi-z2w-bot/ — bot.py, health.py, person_detect.py, config.yaml.example, cctv-bot.service
output/     — snapshot, demo_nvr, person, handover (ไม่ commit *.mp4/*.jpg)
raw/        — ข้อมูลดิบ
```

## เริ่มใช้ (3 นาที)

```bash
git clone https://github.com/nithep/cctv.git
cd cctv/scripts/pi-z2w-bot
cp config.yaml.example config.yaml   # ใส่ pass/token จริง — ห้าม commit
pip install -r requirements.txt       # + ultralytics opencv-python ถ้าจะใช้ YOLO
python health.py                      # ต้องได้ NVR True IPC True rtsp ok
python bot.py                         # รันบอท poll 60s + Telegram
```

ดู `scripts/pi-z2w-bot/README.md` สำหรับคำสั่ง Telegram ทั้ง 6 คำสั่ง

## ความปลอดภัย

- `config.yaml` (token/pass) และ `status.db` อยู่ใน `.gitignore` — ไม่เคย push
- `output/**/*.mp4/*.jpg` ไม่ push
- ห้ามเปิด `192.168.1.31:8000` ออกเน็ต — ใช้ WireGuard `10.0.0.3/24 → 192.168.1.94:51820` เท่านั้น

## License

MIT — แจกฟรี ใช้ได้ แก้ได้ ขายได้ แต่ไม่มีประกัน — ดู `LICENSE`

## ที่มา

- สร้างจากงานจริง Matebook D2019 + NUUO NE-2020 + Seetong IPC `192.168.1.21:554/0`
- เอกสารส่งมอบ `output/handover-2026-09-08.md`
- Skill เฉพาะทาง `.agents/skills/cctv/SKILL.md` ใน T.C.Com vault (private)

## ติดต่อ / Issue

เปิด Issue ที่ GitHub — ยินดีรับ PR สำหรับ Pi4/MiniPC benchmark, YOLO on Pi, WireGuard auto-fix
