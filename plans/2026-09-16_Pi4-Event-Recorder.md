---
type: cctv_plan
title: "Pi4 Event Recorder — ตรวจแล้วอัดเฉพาะ event (ไม่แตะ NVR)"
date: 2026-09-16
status: implemented-local
---

# Pi4 สั่งบันทึกได้ไหม — ได้ ✅ (เขียนโค้ดแล้ว รอ Pi4 ออนไลน์)

> คำถาม: ภาพ UC2 `192.168.1.21 Sub Stream RTSP 554` + ให้บอทบน Pi4 ตรวจสอบแล้วค่อยบันทึกได้ไหม
> ตอบ: **ได้** — NVR อัด `Always` ต่อไปเหมือนเดิม, Pi4 อัด **สำเนาเฉพาะ event** ลงเครื่องตัวเอง

## 1) สถาปัตยกรรม (ไม่ชนกัน)

```
[IPC .21 Sub/Main RTSP] --Always--> [NVR .31 เก็บ 17 วัน]   (ไม่แตะ)
        |
        +--(Pi4 ตรวจ YOLO ทุก 30วิ)--> เจอคน --> ffmpeg -c copy 30วิ --> output/events/person_*.mp4
        |                                            + ส่งภาพ+คลิปเข้า Telegram
        +-- /rec 30 --> อัดทันทีตามสั่ง
```

- Pi4 ดึง RTSP ตรงจาก `.21` (ไม่ผ่าน NVR) ใช้ `-c copy` ไม่ re-encode → CPU ~5%, Pi4 4GB ไหวสบาย
- NVR ไม่ต้องเปลี่ยนโหมด ไม่เสี่ยง config
- Z2W ห้ามเปิด rec (SD พัง) — `record_on_person: false`

## 2) ไฟล์ที่เพิ่ม/แก้ (ใน `scripts/pi-z2w-bot/`)

| ไฟล์ | เปลี่ยน |
|---|---|
| `event_record.py` (ใหม่) | `record_event(rtsp, secs, reason, quota)` + prune quota + CLI `--secs/--reason` |
| `bot.py` | `HAS_REC` import, `/status` โชว์ EventRec, `/rec [วิ]` (5-120วิ), `person_watch_loop` เจอคน→อัด+ส่งภาพ+คลิป (<45MB) |
| `config.yaml.example` | `event_rec: {record_on_person: true, secs: 30, quota_mb: 4096, max_secs: 120}` |
| `README.md` | คำสั่ง `/rec` + อธิบาย Event Recorder |

## 3) ตรวจแล้ว (บน Matebook .44)

- `py_compile bot.py event_record.py` ✅
- `config.yaml.example yaml OK [nvr,ipc,telegram,smart_plug,person,event_rec,pi]` ✅
- `event_record import OK, quota 4GB ≈ 15.9 วัน @10 event/วัน` ✅
- handlers: `status/snapshot/clip/person/person_auto/rec/reboot` ✅
- `.21:554 True / NVR:200` ✅
- Pi4 `.33` ยังไม่เจอใน arp (`Test 22 timeout`) — **รอ Pi4 ออนไลน์ค่อย deploy**

## 4) Deploy บน Pi4 (เมื่อ Pi4 เปิดแล้ว)

```bash
sudo apt install -y ffmpeg python3-venv
scp -r scripts/pi-z2w-bot pi@192.168.1.33:~/cctv-bot/
ssh pi@192.168.1.33
  cd ~/cctv-bot && python3 -m venv venv && venv/bin/pip install -r requirements.txt
  venv/bin/pip install ultralytics opencv-python  # เอา YOLO
  cp config.yaml.example config.yaml  # เติม pass/token + event_rec
  venv/bin/python event_record.py --secs 10 --reason test  # ต้องได้ mp4
  sudo cp cctv-bot.service /etc/systemd/system/ && sudo systemctl enable --now cctv-bot
```

Telegram: `/status` ต้องขึ้น `EventRec ✅` → `/person_auto on` → เดินผ่านกล้อง → ได้ภาพ+คลิป
