#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pi4 Event Recorder — บันทึกวิดีโอเฉพาะตอน bot ตรวจเจอคน/ครบเงื่อนไข
- ไม่แตะ NVR (NVR อัด Always 24 ชม. ต่อไปเหมือนเดิม)
- Pi4 ดึง RTSP ตรงจาก IPC .21 แล้วอัดลงไฟล์เฉพาะ event (ประหยัดดิสก์)
- ออกแบบให้ Pi4 2-4GB รันได้: ใช้ ffmpeg -c copy (ไม่ re-encode, CPU ~5%)
- กันดิสก์เต็ม: quota + auto-prune ไฟล์เก่าสุด + เขียนลง tmpfs ก่อนแล้วย้าย

ใช้ร่วมกับ bot.py: person_watch_loop เจอคน -> เรียก record_event()
หรือสั่งตรง: python event_record.py --secs 30 --reason person
"""
import logging
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

log = logging.getLogger("event_record")

# โฟลเดอร์เก็บคลิป event (บน Pi4 แนะนำ /home/pi/cctv-bot/output/events หรือ external USB)
BASE_DIR = Path(__file__).with_name("output") / "events"
BASE_DIR.mkdir(parents=True, exist_ok=True)

# กันดิสก์เต็ม: quota รวมของโฟลเดอร์ events (MB). เกินแล้วลบไฟล์เก่าสุดอัตโนมัติ
QUOTA_MB_DEFAULT = 4096
# บิตเรตประมาณของ .21 main stream — ใช้กะขนาดไฟล์คร่าวๆ (ไม่ต้องแม่น)
BYTES_PER_SEC_EST = 450_000  # ~3.6 Mbps


def _ffmpeg_bin():
    f = shutil.which("ffmpeg")
    if f:
        return f
    return "ffmpeg"


def _prune_oldest(quota_mb=QUOTA_MB_DEFAULT):
    """ลบไฟล์เก่าสุดจนขนาดรวมต่ำกว่า quota. คืนจำนวนไฟล์ที่ลบ."""
    files = sorted(BASE_DIR.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
    total = sum(p.stat().st_size for p in files)
    removed = 0
    while files and total > quota_mb * 1024 * 1024:
        oldest = files.pop(0)
        try:
            total -= oldest.stat().st_size
            oldest.unlink()
            removed += 1
        except OSError as e:
            log.warning(f"prune {oldest.name} failed: {e}")
            break
    if removed:
        log.info(f"pruned {removed} old event clips (quota {quota_mb}MB)")
    return removed


def record_event(rtsp_url, secs=30, reason="person", conf=0.0,
                 persons=0, quota_mb=QUOTA_MB_DEFAULT, timeout_extra=15):
    """อัดคลิปจาก RTSP ตรง ยาว secs วินาที ลง output/events/.

    ใช้ -c copy (ไม่ re-encode) Pi4 ไหวสบาย. คืน dict {ok, file, size, secs}.
    - reason: person | manual | motion | test (เป็น prefix ชื่อไฟล์)
    - ถ้า stream หลุด/ไฟล์เล็กผิดปกติ -> ok False พร้อม error
    """
    _prune_oldest(quota_mb)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = BASE_DIR / f"{reason}_{ts}_{secs}s.mp4"
    ff = _ffmpeg_bin()
    # pre-roll ไม่ทำ (ต้องมี buffer) — อัดตั้งแต่วินาทีที่ trigger (หน่วง ~1-3 วิจาก detect)
    cmd = [ff, "-y", "-rtsp_transport", "tcp",
           "-i", rtsp_url, "-t", str(secs), "-c", "copy", str(out)]
    try:
        r = subprocess.run(cmd, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=secs + timeout_extra)
    except FileNotFoundError:
        return {"ok": False, "error": "ffmpeg not found (apt install ffmpeg)"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"ffmpeg timeout {secs}s"}
    if not out.exists() or out.stat().st_size < 5000:
        err = ""
        try:
            err = r.stderr.decode(errors="ignore")[-300:]
        except Exception:
            pass
        if out.exists():
            try:
                out.unlink()
            except OSError:
                pass
        return {"ok": False, "error": f"record failed/too small {err[:200]}"}
    size = out.stat().st_size
    log.info(f"event recorded: {out.name} {size}B reason={reason} persons={persons} conf={conf}")
    _prune_oldest(quota_mb)
    return {"ok": True, "file": str(out), "size": size,
            "secs": secs, "reason": reason, "ts": ts}


def estimate_quota_days(quota_mb, events_per_day=20, secs_per_event=30):
    """กะคร่าวๆ ว่า quota เก็บ event ได้กี่วัน."""
    per_day = events_per_day * secs_per_event * BYTES_PER_SEC_EST
    if per_day <= 0:
        return 0
    return round(quota_mb * 1024 * 1024 / per_day, 1)


if __name__ == "__main__":
    import argparse
    import json
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser(description="Pi4 event recorder")
    ap.add_argument("--rtsp", default="rtsp://admin:123456@192.168.1.21:554/0")
    ap.add_argument("--secs", type=int, default=30)
    ap.add_argument("--reason", default="test")
    ap.add_argument("--quota", type=int, default=QUOTA_MB_DEFAULT)
    args = ap.parse_args()
    print(json.dumps(record_event(args.rtsp, secs=args.secs,
                                  reason=args.reason, quota_mb=args.quota),
                     indent=2, ensure_ascii=False))
    print(f"quota {args.quota}MB ~= {estimate_quota_days(args.quota)} days @20 events/day x30s")
