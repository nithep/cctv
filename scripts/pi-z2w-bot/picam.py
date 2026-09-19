#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pi Z2W local camera (CSI ov5647) — snapshot via rpicam-still.

ใช้กับ Pi Zero 2 W + OV5647 ที่เสียบ CSI ตรง (ไม่ผ่าน RTSP).
bot.py เรียก capture() สำหรับคำสั่ง /picam
"""
import shutil
import subprocess
from pathlib import Path


def _rpicam_bin():
    for c in ("rpicam-still", "libcamera-still"):
        p = shutil.which(c)
        if p:
            return p
    return None


def capture(out_path=None, width=1296, height=972, timeout_ms=1500):
    """ถ่าย 1 ภาพจากกล้อง local — คืน dict {ok, file/error}

    หมายเหตุ: อย่าใส่ -n/--nopreview — บน Z2W+ov5647 ทำให้ค้างหลัง
    configure streams แล้วโดน kill (EXIT 143) ไม่ได้ไฟล์
    ใช้ --immediate (ถ่ายเฟรมแรกทันที ไม่รอ preview ครบ timeout) เพราะ
    pipeline บน Z2W ตอนบอทรันอยู่ช้ากว่าปกติ (เฟรมกระดึ๊บ อาจเกิน 17 วิ
    จนโดน subprocess timeout kill เอง = exit -15) — เผื่อ subprocess 60 วิ
    """
    # กล้องติดกลับหัว (ภาพ 01:39 ตัวหนังสือตีลังกา) — หมุน 180 ที่ซอฟต์แวร์
    # ถ้าจัดท่ากล้องใหม่แล้วภาพกลับหัวอีก ให้เปลี่ยนเป็น 0
    ROTATION = 180
    out = Path(out_path) if out_path else Path("/tmp/picam_snapshot.jpg")
    exe = _rpicam_bin()
    if not exe:
        return {"ok": False, "error": "ไม่เจอ rpicam-still (apt install rpicam-apps?)"}
    cmd = [exe, "-o", str(out), "--timeout", str(timeout_ms), "--immediate",
           "--rotation", str(ROTATION)]
    try:
        r = subprocess.run(cmd, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=60)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "rpicam timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}
    try:
        if out.exists() and out.stat().st_size > 1000:
            with open(out, "rb") as f:
                head = f.read(2)
                f.seek(-2, 2)
                tail = f.read(2)
            if head == b"\xff\xd8" and tail == b"\xff\xd9":
                return {"ok": True, "file": str(out), "size": out.stat().st_size}
        err = (r.stderr or b"").decode(errors="ignore").strip()
        # ตัดเฉพาะ 500 ตัวท้าย + returncode ไว้ debug (rpicam พ่น INFO เยอะแม้ตอนพัง)
        tail_err = "\n".join(err.splitlines()[-8:]) if err else ""
        return {"ok": False,
                "error": f"exit={r.returncode} no file. stderr tail: {tail_err}"[:500]}
    except OSError as e:
        return {"ok": False, "error": str(e)[:200]}


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/picam_snapshot.jpg"
    print(capture(out))
