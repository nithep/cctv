#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check-config.py — ตรวจ config.yaml จริงบนเครื่องเทียบกับ config.yaml.example

ใช้: python check-config.py [path/to/config.yaml]   (ไม่ใส่ = หาเองในโฟลเดอร์นี้)
หาไม่เจอจะชี้ตำแหน่งที่ start-bot.ps1 เคยใช้ (สำเนาบน Google Drive) ให้ด้วย
ออกแบบไม่พิมพ์ secret (token/pass) — แสดงแค่ว่าตั้งไว้หรือยัง
"""
import sys
from pathlib import Path

HERE = Path(__file__).with_name("config.yaml.example")
REQUIRED = ["nvr.ip", "nvr.port", "telegram.token", "telegram.allow_chat_ids"]
RECOMMENDED = [
    "ipc[0].ip", "ipc[0].rtsp",            # จำเป็นสำหรับ /snapshot /clip /person
    "alerts.rtsp_down_secs",               # ใหม่: เตือน RTSP ล่มเกินกี่วินาที
    "event_rec.record_on_person", "event_rec.secs", "event_rec.quota_mb",
    "person.conf_threshold", "person.imgsz", "person.clip_secs",
    "person.picam_auto_interval", "person.picam_cooldown",
]
SECRET_KEYS = {"token", "pass", "password", "secret"}


def load_yaml(p: Path):
    import yaml
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def dig(cfg, dotted):
    """อ่านค่าแบบ nvr.ip / ipc[0].rtsp"""
    cur = cfg
    for part in dotted.replace("]", "").replace("[", ".").split("."):
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None, False
        elif isinstance(cur, dict):
            if part not in cur:
                return None, False
            cur = cur[part]
        else:
            return None, False
    return cur, True


def show(dotted, val):
    leaf = dotted.split(".")[-1].split("[")[0]
    if leaf in SECRET_KEYS:
        ok = bool(val) and "CHANGE_ME" not in str(val) and "123456:ABC" not in str(val)
        return "ตั้งแล้ว ✅" if ok else "ยังเป็นค่า default ❌ (แก้ใน config.yaml)"
    return repr(val)


def find_config():
    """ลำดับหา: ผู้ใช้ใส่มา > โฟลเดอร์นี้ > ~/cctv-bot/config.yaml (Pi4/ecs-agent) > Google Drive (Windows)"""
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    local = Path(__file__).with_name("config.yaml")
    if local.exists():
        return local
    pi_bot = Path.home() / "cctv-bot" / "config.yaml"
    if pi_bot.exists():
        return pi_bot
    drive = Path.home() / "ไดรฟ์ของฉัน (cnithep@gmail.com)" / "T.C.Com" / "cctv" / "scripts" / "pi-z2w-bot" / "config.yaml"
    return drive  # อาจไม่ exist — ด้านล่างจะรายงานเอง


def main():
    example = load_yaml(HERE)
    real_path = find_config()
    print(f"example : {HERE}")
    print(f"config  : {real_path}")
    if not real_path.exists():
        print("\n❌ ไม่พบ config.yaml ทั้งในโฟลเดอร์นี้และบน Google Drive")
        print("   แก้: copy config.yaml.example เป็น config.yaml แล้วใส่ token/pass จริง")
        return 1
    real = load_yaml(real_path)

    print("\n--- ค่าที่ต่างจาก example (ซ่อน secret) ---")
    diffs = 0
    for dotted in REQUIRED + RECOMMENDED:
        ev, eok = dig(example, dotted)
        rv, rok = dig(real, dotted)
        if not rok:
            print(f"  ❌ {dotted}: ไม่มีใน config จริง (example: {show(dotted, ev) if eok else 'n/a'})")
            diffs += 1
        elif eok and rv != ev:
            print(f"  • {dotted}: {show(dotted, rv)}  (example: {show(dotted, ev)})")
    if diffs == 0:
        print("  (ทุกคีย์จำเป็นมีครบ — รายละเอียดเพิ่มเติมข้างล่าง)")

    print("\n--- ค่าทั้งหมดที่ใช้จริง ---")
    for dotted in REQUIRED + RECOMMENDED:
        rv, rok = dig(real, dotted)
        print(f"  {'✅' if rok else '❌'} {dotted} = {show(dotted, rv) if rok else 'ขาด!'}")

    # RTSP path sanity: บอท fallback sub stream โดยเดา path ท้ายเป็น /1
    rv, rok = dig(real, "ipc[0].rtsp")
    if rok and rv:
        tail = str(rv).rstrip("/").rpartition("/")[2]
        if not tail.isdigit():
            print(f"\n⚠️  ipc[0].rtsp ลงท้าย '/{tail}' ไม่ใช่ตัวเลข — บอทจะเดา sub stream ไม่ได้ ควรใส่ rtsp_sub ชัด ๆ")
    missing_secret = [d for d in REQUIRED if "token" in d or "pass" in d]
    for dotted in missing_secret:
        rv, rok = dig(real, dotted)
        if rok and (not rv or "CHANGE_ME" in str(rv) or "123456:ABC" in str(rv)):
            print(f"⚠️  {dotted} ยังเป็นค่า default — บอทจะ log เข้า Telegram ไม่ได้")
    print()
    return 0 if diffs == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
