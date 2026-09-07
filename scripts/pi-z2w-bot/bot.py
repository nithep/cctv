#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pi Zero 2 W — CCTV Supervisor Bot
Monitors NVRmini2 (192.168.1.31) + IPC (192.168.1.21), notifies via Telegram, can power-cycle via smart plug.
Designed for 512MB RAM: polling, no video storage.
"""
import time
import yaml
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes
    HAS_TG = True
except ImportError:
    HAS_TG = False

from health import check_nvr, check_ipc

# Phase 3: Person detection (optional deps: ultralytics, opencv)
try:
    from person_detect import scan_snapshot, detect_person, annotate_image, _check_deps as _person_check_deps
    HAS_PERSON = True
except ImportError:
    HAS_PERSON = False

CONFIG_PATH = Path(__file__).with_name("config.yaml")
DB_PATH = Path(__file__).with_name("status.db")
FAIL_THRESHOLD = 3
COOLDOWN_SEC = 900  # 15 min between alerts for same target
CHECK_INTERVAL = 60
PERSON_AUTO_INTERVAL = 30  # sec between person scans when auto enabled
PERSON_COOLDOWN = 300  # 5 min between person alerts

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("cctv-bot")

fail_count = {}
last_alert = {}
person_auto_enabled = False
last_person_alert = 0

def load_cfg():
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS checks (ts TEXT, target TEXT, ok INTEGER, detail TEXT)")
    con.commit()
    con.close()

def save_check(target, ok, detail):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO checks VALUES (?,?,?,?)", (datetime.now().isoformat(), target, int(ok), detail[:500]))
    con.commit()
    con.close()

def should_alert(target):
    now = time.time()
    if target not in last_alert or now - last_alert[target] > COOLDOWN_SEC:
        last_alert[target] = now
        return True
    return False

# --- Telegram handlers (optional) ---
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = load_cfg()
    ok_nvr, res_nvr = check_nvr(cfg)
    lines = [f"NVR 192.168.1.31: {'✅' if ok_nvr else '❌'} {res_nvr}"]
    for ipc in cfg.get("ipc", []):
        ok_ipc, res_ipc = check_ipc(ipc)
        lines.append(f"IPC {ipc['ip']}: {'✅' if ok_ipc else '❌'} {res_ipc}")
    # Person backend status
    if HAS_PERSON:
        has_cv2, has_yolo = _person_check_deps()
        backend = "YOLOv8n ✅" if has_yolo else ("motion fallback" if has_cv2 else "ไม่มี AI — ใช้ NVR Motion")
        lines.append(f"Person: {backend} auto={'ON' if person_auto_enabled else 'OFF'}")
    lines.append(f"\nคำสั่ง: /snapshot /clip [วินาที] /person [/person_auto] /status /reboot")
    await update.message.reply_text("\n".join(lines)[:4000])

def _ffmpeg_bin():
    import shutil, pathlib
    f = shutil.which("ffmpeg")
    if f:
        return f
    for p in pathlib.Path.home().glob("AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg*/ffmpeg-*/bin/ffmpeg.exe"):
        if p.exists():
            return str(p)
    return "ffmpeg"

async def cmd_snapshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ดึงภาพล่าสุดจาก IPC 192.168.1.21 ผ่าน ffmpeg RTSP ส่งกลับเป็นรูป"""
    cfg = load_cfg()
    ipc = cfg.get("ipc", [{}])[0]
    rtsp = ipc.get("rtsp") or ipc.get("rtsp_main") or "rtsp://admin:123456@192.168.1.21:554/0"
    tmp = Path("/tmp/cctv_snapshot.jpg")
    # Windows fallback: C:\Temp
    if not Path("/tmp").exists():
        tmp = Path(os.environ.get("TEMP", ".")) / "cctv_snapshot.jpg"
    await update.message.reply_text(f"กำลังดึงภาพจาก {ipc.get('ip','192.168.1.21')} ...")
    try:
        import subprocess, os
        ff = _ffmpeg_bin()
        cmd = [ff, "-y", "-rtsp_transport", "tcp", "-i", rtsp, "-vframes", "1", "-q:v", "2", str(tmp)]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, check=False)
        if tmp.exists() and tmp.stat().st_size > 1000:
            await update.message.reply_photo(photo=open(tmp, "rb"), caption=f"ภาพล่าสุด {ipc.get('ip')} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 1080p")
            log.info(f"snapshot sent to {update.effective_chat.id}")
        else:
            await update.message.reply_text("ดึงภาพไม่สำเร็จ — RTSP ไม่ตอบ ลองใหม่")
    except Exception as e:
        log.exception("snapshot err")
        await update.message.reply_text(f"snapshot error: {e}")

async def cmd_clip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ดึงคลิปสั้น 5-30 วินาที จาก IPC ส่งเป็นวิดีโอ"""
    cfg = load_cfg()
    ipc = cfg.get("ipc", [{}])[0]
    rtsp = ipc.get("rtsp") or "rtsp://admin:123456@192.168.1.21:554/0"
    # ดูพารามิเตอร์วินาที เช่น /clip 10
    secs = 5
    if context.args:
        try:
            secs = max(2, min(30, int(context.args[0])))
        except:
            pass
    tmp = Path("/tmp/cctv_clip.mp4")
    if not Path("/tmp").exists():
        import os
        tmp = Path(os.environ.get("TEMP", ".")) / "cctv_clip.mp4"
    await update.message.reply_text(f"กำลังดึงคลิป {secs} วินาทีจาก {ipc.get('ip')} ...")
    try:
        import subprocess, os
        ff = _ffmpeg_bin()
        cmd = [ff, "-y", "-rtsp_transport", "tcp", "-i", rtsp, "-t", str(secs), "-c", "copy", str(tmp)]
        # ถ้า copy ไม่ได้ ให้ re-encode
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=secs+15)
        if not tmp.exists() or tmp.stat().st_size < 5000:
            cmd2 = [ff, "-y", "-rtsp_transport", "tcp", "-i", rtsp, "-t", str(secs), "-c:v", "libx264", "-preset", "ultrafast", str(tmp)]
            subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=secs+20)
        if tmp.exists() and tmp.stat().st_size > 5000:
            await update.message.reply_video(video=open(tmp, "rb"), caption=f"คลิป {secs}วิ {ipc.get('ip')} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", supports_streaming=True)
            log.info(f"clip {secs}s sent to {update.effective_chat.id}")
        else:
            await update.message.reply_text("ดึงคลิปไม่สำเร็จ — ลอง /snapshot ก่อน")
    except Exception as e:
        log.exception("clip err")
        await update.message.reply_text(f"clip error: {e}")

async def cmd_person(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Phase 3: /person — สแกนภาพล่าสุดหา 'คน' ด้วย YOLOv8n"""
    if not HAS_PERSON:
        await update.message.reply_text("Person detect ยังไม่พร้อม — ติดตั้ง: pip install ultralytics opencv-python")
        return
    cfg = load_cfg()
    ipc = cfg.get("ipc", [{}])[0]
    rtsp = ipc.get("rtsp") or "rtsp://admin:123456@192.168.1.21:554/0"
    # conf threshold param เช่น /person 0.6
    conf = 0.5
    if context.args:
        try:
            conf = max(0.2, min(0.9, float(context.args[0])))
        except:
            pass
    await update.message.reply_text(f"กำลังสแกนหาคน (conf>{conf}) จาก {ipc.get('ip')} ...")
    try:
        res = scan_snapshot(rtsp, conf=conf, save=True)
        if not res.get("ok"):
            await update.message.reply_text(f"สแกนไม่สำเร็จ: {res.get('error')}")
            return
        persons = res.get("persons", [])
        backend = res.get("backend", "?")
        if persons:
            caption = f"พบคน {len(persons)} คน (backend={backend} conf>{conf}) {datetime.now().strftime('%H:%M:%S')} 1080p"
            # annotated image if saved, else tmp
            img_path = res.get("saved") or res.get("image")
            if img_path and Path(img_path).exists():
                await update.message.reply_photo(photo=open(img_path, "rb"), caption=caption)
            else:
                await update.message.reply_text(caption + " (ไม่มีไฟล์ภาพ)")
            log.info(f"person found {len(persons)} sent to {update.effective_chat.id}")
        else:
            hint = " (YOLO)" if backend == "yolo" else " (fallback — ไม่มี YOLO, เช็ค NVR Motion ที่ ipcam_event.php)"
            await update.message.reply_text(f"ไม่พบคน{hint} — backend={backend} conf>{conf} {datetime.now().strftime('%H:%M:%S')}")
    except Exception as e:
        log.exception("person err")
        await update.message.reply_text(f"person error: {e}")


async def cmd_person_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle auto person watch — /person_auto on/off"""
    global person_auto_enabled
    if context.args and context.args[0].lower() in ("on", "1", "enable", "เปิด"):
        person_auto_enabled = True
    elif context.args and context.args[0].lower() in ("off", "0", "disable", "ปิด"):
        person_auto_enabled = False
    else:
        person_auto_enabled = not person_auto_enabled
    await update.message.reply_text(f"Person auto {'เปิด ✅ (ทุก 30วิ)' if person_auto_enabled else 'ปิด ❌'} — ใช้ /person เพื่อสแกนครั้งเดียว")


async def cmd_reboot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Placeholder: integrate with smart plug API (Tuya local / MQTT)
    # For now just acknowledge — wire up actions.py for real power cycle
    await update.message.reply_text("Reboot requested — (ต่อ Smart Plug ที่ actions.py แล้วจะสั่ง power cycle จริง)")

def start_telegram(cfg):
    if not HAS_TG or not cfg.get("telegram", {}).get("token"):
        log.warning("Telegram disabled (no token or lib)")
        return None
    token = cfg["telegram"]["token"]
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("snapshot", cmd_snapshot))
    app.add_handler(CommandHandler("clip", cmd_clip))
    if HAS_PERSON:
        app.add_handler(CommandHandler("person", cmd_person))
        app.add_handler(CommandHandler("person_auto", cmd_person_auto))
    app.add_handler(CommandHandler("reboot", cmd_reboot))
    return app

# --- Main polling loop ---
def poll_once(cfg):
    ok_nvr, res_nvr = check_nvr(cfg)
    save_check("nvr_192.168.1.31", ok_nvr, str(res_nvr))
    log.info(f"NVR check: {ok_nvr} {res_nvr}")
    if not ok_nvr:
        fail_count["nvr"] = fail_count.get("nvr", 0) + 1
        if fail_count["nvr"] >= FAIL_THRESHOLD and should_alert("nvr"):
            log.warning(f"ALERT NVR down {fail_count['nvr']}x: {res_nvr}")
            # TODO: call actions.power_cycle("nvr") + send telegram
    else:
        fail_count["nvr"] = 0

    for ipc in cfg.get("ipc", []):
        ok_ipc, res_ipc = check_ipc(ipc)
        key = f"ipc_{ipc['ip']}"
        save_check(key, ok_ipc, str(res_ipc))
        log.info(f"IPC {ipc['ip']}: {ok_ipc} {res_ipc}")
        if not ok_ipc:
            fail_count[key] = fail_count.get(key, 0) + 1
            if fail_count[key] >= FAIL_THRESHOLD and should_alert(key):
                log.warning(f"ALERT {key} down {fail_count[key]}x: {res_ipc}")
        else:
            fail_count[key] = 0

def person_watch_loop(cfg, tg_app):
    """Background loop: auto scan person every 30s when enabled (Phase 3)."""
    global last_person_alert
    import asyncio
    while True:
        try:
            if person_auto_enabled and HAS_PERSON:
                ipc = cfg.get("ipc", [{}])[0]
                rtsp = ipc.get("rtsp") or "rtsp://admin:123456@192.168.1.21:554/0"
                conf = cfg.get("person", {}).get("conf_threshold", 0.5)
                res = scan_snapshot(rtsp, conf=conf, save=True)
                if res.get("has_person"):
                    now = time.time()
                    if now - last_person_alert > PERSON_COOLDOWN:
                        last_person_alert = now
                        persons = res.get("persons", [])
                        caption = f"🚶 พบคน {len(persons)} คน auto {datetime.now().strftime('%H:%M:%S')} 1080p"
                        img_path = res.get("saved") or res.get("image")
                        # Send via telegram app if available
                        if tg_app and img_path and Path(img_path).exists():
                            try:
                                # run async send from sync thread
                                chat_ids = cfg.get("telegram", {}).get("allow_chat_ids", [])
                                token = cfg.get("telegram", {}).get("token")
                                if chat_ids and token:
                                    import requests
                                    # fallback sync send via HTTP API (simpler than async)
                                    for cid in chat_ids:
                                        try:
                                            with open(img_path, "rb") as f:
                                                requests.post(
                                                    f"https://api.telegram.org/bot{token}/sendPhoto",
                                                    data={"chat_id": cid, "caption": caption},
                                                    files={"photo": f},
                                                    timeout=20,
                                                )
                                        except Exception as e:
                                            log.warning(f"auto person send to {cid} failed: {e}")
                                    log.info(f"auto person alert sent {len(persons)} persons")
                            except Exception as e:
                                log.warning(f"auto person send err: {e}")
                        else:
                            log.info(f"auto person found {res.get('persons')} but no telegram/img")
        except Exception as e:
            log.warning(f"person_watch err: {e}")
        time.sleep(cfg.get("person", {}).get("auto_interval", PERSON_AUTO_INTERVAL))


def main():
    cfg = load_cfg()
    init_db()
    log.info("Pi Z2W CCTV Bot starting — interval %ss", CHECK_INTERVAL)
    tg_app = start_telegram(cfg)
    # Fix for Python 3.13: run health polling in thread, Telegram polling in main thread
    if tg_app:
        import threading

        def health_loop():
            while True:
                try:
                    poll_once(cfg)
                except Exception as e:
                    log.exception(f"poll error: {e}")
                time.sleep(cfg.get("nvr", {}).get("check_interval", CHECK_INTERVAL))

        threading.Thread(target=health_loop, daemon=True).start()
        # Phase 3: person auto watch thread (if enabled)
        if HAS_PERSON:
            threading.Thread(target=person_watch_loop, args=(cfg, tg_app), daemon=True).start()
            log.info("person_watch thread started (toggle via /person_auto)")
        log.info("Telegram bot polling started (main thread)")
        tg_app.run_polling()
    else:
        log.info("Telegram disabled, running health loop only")
        while True:
            try:
                poll_once(cfg)
            except Exception as e:
                log.exception(f"poll error: {e}")
            time.sleep(cfg.get("nvr", {}).get("check_interval", CHECK_INTERVAL))

if __name__ == "__main__":
    main()
