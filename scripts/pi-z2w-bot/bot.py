#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pi Z2W — CCTV Supervisor Bot
Monitors NVRmini2 (192.168.1.31) + IPC (192.168.1.21), notifies via Telegram, can power-cycle via smart plug.
Designed for 512MB RAM: polling, no video storage.
Pi4: + Event Recorder (event_record.py) — อัดคลิปเฉพาะตอนเจอคน/สั่ง /rec (NVR ยังอัด Always ต่อ)
"""
import time
import os
import shutil
import asyncio
import subprocess
import yaml
import sqlite3
import json
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
    from person_detect import scan_snapshot, detect_person, annotate_image, OUTPUT_DIR, _check_deps as _person_check_deps
    HAS_PERSON = True
except ImportError:
    HAS_PERSON = False

# Pi4 Event Recorder (optional — บันทึกเฉพาะ event ลงเครื่อง Pi4)
try:
    from event_record import record_event
    HAS_REC = True
except ImportError:
    HAS_REC = False

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

# Person "visit" dedup — คนเดิมที่ยังยืนหน้ากล้อง = เหตุการณ์เดียว ไม่เซฟ/ไม่แจ้งซ้ำ
# ปิดเหตุการณ์เมื่อไม่เจอคนต่อเนื่องเกิน NEW_VISIT_GAP_SEC → กลับมาเจอใหม่ = เริ่ม event ใหม่
NEW_VISIT_GAP_SEC = 600  # 10 นาที (ตั้งทับได้ที่ person.new_visit_gap ใน config.yaml)
person_visit_active = False
person_visit_since = None
person_event_seq = 0
last_seen_ts = 0.0

# Health alert state (ffmpeg หาย / RTSP ล่มเกิน 5 นาที)
ffmpeg_alert_sent = False
rtsp_down_since = {}
rtsp_alert_sent = {}

def load_cfg():
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def _person_scan_delegated(cfg, conf):
    """มอบงานสแกน YOLO ให้เครื่องอื่นทำผ่าน SSH (Z2W → Gateway/Pi4 ที่มี torch)

    ตั้งค่าใน config.yaml:
      person:
        delegate_ssh: "ecs-agent@192.168.1.94"   # ว่าง = สแกนบนเครื่องนี้
        delegate_ssh_key: ""                      # (ทางเลือก) path key เช่น ~/.ssh/id_ed25519

    เครื่องปลายทางต้องมี ~/cctv-bot/{person_detect.py, venv, config ไม่จำเป็น}
    คืน dict รูปแบบเดียวกับ person_detect.scan_snapshot() — None ถ้าไม่ได้ตั้ง delegate
    """
    p_cfg = cfg.get("person") or {}
    target = p_cfg.get("delegate_ssh") or ""
    if not target:
        return None
    ipc = cfg.get("ipc", [{}])[0]
    # ใช้ main stream 1080p สำหรับ YOLO เสมอ (delegate ทำแทน ไม่ต้องกลัวหนัก)
    rtsp = ipc.get("rtsp_main") or ipc.get("rtsp") or "rtsp://admin:123456@192.168.1.21:554/0"
    key = p_cfg.get("delegate_ssh_key") or ""
    ssh_base = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
                "-o", "StrictHostKeyChecking=accept-new"]
    if key:
        ssh_base += ["-i", key]
    remote_cmd = (f"cd ~/cctv-bot && ./venv/bin/python person_detect.py "
                  f"--rtsp '{rtsp}' --conf {float(conf)}")
    try:
        r = subprocess.run(ssh_base + [target, remote_cmd],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
    except Exception as e:
        return {"ok": False, "error": f"delegate ssh err: {e}"[:200],
                "persons": [], "backend": "delegate", "image": None}
    if r.returncode != 0:
        err = (r.stderr.decode(errors="ignore") or f"delegate exit {r.returncode}")[:200]
        return {"ok": False, "error": err, "persons": [], "backend": "delegate", "image": None}
    try:
        res = json.loads(r.stdout.decode(errors="ignore") or "{}")
    except Exception as e:
        return {"ok": False, "error": f"delegate json err: {e}"[:200],
                "persons": [], "backend": "delegate", "image": None}
    if not res:
        return {"ok": False, "error": "delegate empty result", "persons": [], "backend": "delegate", "image": None}
    # ภาพอยู่ฝั่ง delegate — ดึงกลับเฉพาะเมื่อเจอคน (กัน /tmp บน Z2W โดนกองทุก 30วิ)
    img = res.get("saved") or res.get("image")
    if res.get("ok") and res.get("has_person") and img:
        local = Path("/tmp") / Path(img).name
        scp_cmd = ["scp", "-q", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
                   "-o", "StrictHostKeyChecking=accept-new"]
        if key:
            scp_cmd += ["-i", key]
        try:
            sr = subprocess.run(scp_cmd + [f"{target}:{img}", str(local)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            if sr.returncode == 0 and local.exists() and local.stat().st_size > 1000:
                if res.get("saved"):
                    res["saved"] = str(local)
                else:
                    res["image"] = str(local)
            else:
                res["saved"] = None
                res["image"] = None
        except Exception as e:
            log.warning(f"delegate scp img err: {e}")
            res["saved"] = None
            res["image"] = None
    return res

def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS checks (ts TEXT, target TEXT, ok INTEGER, detail TEXT)")
    # เหตุการณ์ "พบคน" — 1 แถวต่อการเยี่ยม (dedup แล้ว) เรียกย้อนหลังด้วย /events /event <id>
    con.execute("""CREATE TABLE IF NOT EXISTS person_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started TEXT, persons INTEGER, conf REAL,
        image_file TEXT, clip_file TEXT)""")
    con.commit()
    con.close()

def save_check(target, ok, detail):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO checks VALUES (?,?,?,?)", (datetime.now().isoformat(), target, int(ok), detail[:500]))
    con.commit()
    con.close()

def save_person_event(n_persons, persons, image_file, clip_file=None, visit_start=None):
    """บันทึกเหตุการณ์ "พบคน" 1 ครั้งต่อการเยี่ยม (dedup ทำที่ loop) — คืน id ที่เพิ่ม"""
    try:
        conf = max((p.get("conf", 0.0) for p in persons), default=0.0) if persons else 0.0
        con = sqlite3.connect(DB_PATH)
        cur = con.execute(
            "INSERT INTO person_events (started, persons, conf, image_file, clip_file) VALUES (?,?,?,?,?)",
            ((visit_start or datetime.now()).isoformat(timespec="seconds"),
             int(n_persons), float(conf),
             str(image_file) if image_file else None,
             str(clip_file) if clip_file else None))
        con.commit()
        new_id = cur.lastrowid
        con.close()
        return new_id
    except Exception as e:
        log.warning(f"save_person_event err: {e}")
        return None


def update_person_event_clip(eid, clip_file):
    try:
        con = sqlite3.connect(DB_PATH)
        con.execute("UPDATE person_events SET clip_file = ? WHERE id = ?", (str(clip_file), int(eid)))
        con.commit()
        con.close()
    except Exception as e:
        log.warning(f"update_person_event_clip err: {e}")


def list_person_events(limit=10):
    try:
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT * FROM person_events ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
        con.close()
        return rows
    except Exception as e:
        log.warning(f"list_person_events err: {e}")
        return []


def get_person_event(eid):
    try:
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        row = con.execute("SELECT * FROM person_events WHERE id = ?", (int(eid),)).fetchone()
        con.close()
        return row
    except Exception as e:
        log.warning(f"get_person_event err: {e}")
        return None


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
    # ffmpeg status (จำเป็นสำหรับ /snapshot /clip)
    ff = _ffmpeg_found()
    lines.append(f"FFmpeg: {'✅ ' + str(ff) if ff else '❌ หาย — รัน install-deps.ps1'}")
    # Person backend status
    if HAS_PERSON:
        has_cv2, has_yolo = _person_check_deps()
        backend = "YOLOv8n ✅" if has_yolo else ("motion fallback" if has_cv2 else "ไม่มี AI — ใช้ NVR Motion")
        lines.append(f"Person: {backend} auto={'ON' if person_auto_enabled else 'OFF'}")
    if HAS_REC:
        rec_cfg = cfg.get("event_rec", {})
        lines.append(f"EventRec: ✅ พร้อม (เฉพาะ event {rec_cfg.get('secs', 30)}วิ quota {rec_cfg.get('quota_mb', 4096)}MB)")
    else:
        lines.append("EventRec: ❌ (ไม่มี event_record.py — ใช้ /clip แทน)")
    lines.append(f"\nคำสั่ง: /snapshot /clip [วินาที] /person [/person_auto] /rec [วินาที] /events [/event #] /status /reboot")
    await update.message.reply_text("\n".join(lines)[:4000])

def _ffmpeg_found():
    """หา ffmpeg: PATH ก่อน แล้วไล่หา Gyan.FFmpeg* ทุกเวอร์ชันใน WinGet — คืน path หรือ None"""
    f = shutil.which("ffmpeg")
    if f:
        return f
    for p in Path.home().glob("AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg*/ffmpeg-*/bin/ffmpeg.exe"):
        if p.exists():
            return str(p)
    return None

def _ffmpeg_bin():
    return _ffmpeg_found() or "ffmpeg"

def _tmp_file(name):
    """ไฟล์ชั่วคราว: /tmp บน Pi/POSIX, %TEMP% บน Windows"""
    if os.name == "posix" and Path("/tmp").exists():
        return Path("/tmp") / name
    return Path(os.environ.get("TEMP", ".")) / name

def _valid_jpeg(p: Path) -> bool:
    """เช็คไฟล์ภาพจบสมบูรณ์ (magic FFD8 ... FFD9) — กันส่งไฟล์เสียหาย"""
    try:
        if not p.exists() or p.stat().st_size < 1000:
            return False
        with open(p, "rb") as f:
            head = f.read(2)
            f.seek(-2, 2)
            tail = f.read(2)
        return head == b"\xff\xd8" and tail == b"\xff\xd9"
    except OSError:
        return False

def _ffmpeg_err_tail(res) -> str:
    """บรรทัดสุดท้ายของ ffmpeg stderr ไว้แปะในข้อความ error"""
    err = (getattr(res, "stderr", None) or b"").decode(errors="ignore").strip()
    return err.splitlines()[-1][:200] if err else f"exit code {getattr(res, 'returncode', '?')}"

def _snapshot_cmd(ff, rtsp, out):
    # หมายเหตุ: เคยใช้ -rw_timeout 10s แต่ ffmpeg >= 8 ตัด option นี้ทิ้ง
    # ("Option not found" ทำให้ snapshot/clip พังทั้งยวง) — ตอนนี้พึ่ง
    # subprocess timeout=15 (snapshot) / secs+15 (clip) ตัด RTSP ค้างแทน
    return [ff, "-y", "-hide_banner", "-loglevel", "error",
            "-rtsp_transport", "tcp", "-i", rtsp, "-vframes", "1", "-q:v", "2", str(out)]

async def cmd_snapshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ดึงภาพล่าสุดจาก IPC 192.168.1.21 ผ่าน ffmpeg RTSP ส่งกลับเป็นรูป

    ลอง main 2 ครั้ง + sub stream 1 ครั้ง — กัน RTSP หลุดแวบเดียว/สตรีมหลักค้าง
    """
    cfg = load_cfg()
    ipc = cfg.get("ipc", [{}])[0]
    rtsp_main = ipc.get("rtsp") or ipc.get("rtsp_main") or "rtsp://admin:123456@192.168.1.21:554/0"
    # sub stream fallback: จาก cfg (rtsp_sub) หรือเปลี่ยน path ท้ายเป็น /1 (Seetong /0=main /1=sub)
    rtsp_sub = ipc.get("rtsp_sub")
    if not rtsp_sub:
        base, _, last = rtsp_main.rpartition("/")
        rtsp_sub = f"{base}/1" if last.isdigit() else rtsp_main
    tmp = _tmp_file("cctv_snapshot.jpg")
    await update.message.reply_text(f"กำลังดึงภาพจาก {ipc.get('ip','192.168.1.21')} ...")
    last_err = ""
    used_label = ""
    try:
        ff = _ffmpeg_bin()
        attempts = [("main 1080p", rtsp_main), ("main 1080p", rtsp_main), ("sub 360p", rtsp_sub)]
        for i, (label, rtsp) in enumerate(attempts, 1):
            try:
                tmp.unlink(missing_ok=True)  # ลบไฟล์เก่า/เสียทิ้งก่อนทุกครั้ง
            except OSError:
                pass
            try:
                res = subprocess.run(_snapshot_cmd(ff, rtsp, tmp), stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, timeout=15)
                last_err = _ffmpeg_err_tail(res)
            except subprocess.TimeoutExpired:
                last_err = "ffmpeg timeout >15s (RTSP ไม่ตอบ)"
            if _valid_jpeg(tmp):
                used_label = label
                break
            log.warning(f"snapshot {i}/{len(attempts)} ล้มเหลว ({label}): {last_err}")
            await asyncio.sleep(2)
        else:
            await update.message.reply_text(
                f"ดึงภาพไม่สำเร็จ {len(attempts)} ครั้ง — RTSP ไม่ตอบ (ลอง /status ดู)\nffmpeg: {last_err}")
            return
        with open(tmp, "rb") as f:
            await update.message.reply_photo(
                photo=f,
                caption=f"ภาพล่าสุด {ipc.get('ip')} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {used_label}")
        log.info(f"snapshot sent to {update.effective_chat.id} ({used_label})")
    except Exception as e:
        log.exception("snapshot err")
        await update.message.reply_text(f"snapshot error: {e}")
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass

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
    tmp = _tmp_file("cctv_clip.mp4")
    await update.message.reply_text(f"กำลังดึงคลิป {secs} วินาทีจาก {ipc.get('ip')} ...")
    try:
        ff = _ffmpeg_bin()
        try:
            tmp.unlink(missing_ok=True)  # ลบคลิปเก่าทิ้ง กันส่งคลิปเก่าซ้ำ
        except OSError:
            pass
        cmd = [ff, "-y", "-hide_banner", "-loglevel", "error",
               "-rtsp_transport", "tcp", "-i", rtsp, "-t", str(secs), "-c", "copy", str(tmp)]
        # ถ้า copy ไม่ได้ ให้ re-encode
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=secs+15)
        if not tmp.exists() or tmp.stat().st_size < 5000:
            cmd2 = [ff, "-y", "-hide_banner", "-loglevel", "error",
                    "-rtsp_transport", "tcp", "-i", rtsp, "-t", str(secs), "-c:v", "libx264", "-preset", "ultrafast", str(tmp)]
            subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=secs+20)
        if tmp.exists() and tmp.stat().st_size > 5000:
            with open(tmp, "rb") as vf:
                await update.message.reply_video(video=vf, caption=f"คลิป {secs}วิ {ipc.get('ip')} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", supports_streaming=True)
            log.info(f"clip {secs}s sent to {update.effective_chat.id}")
        else:
            await update.message.reply_text("ดึงคลิปไม่สำเร็จ — ลอง /snapshot ก่อน")
    except Exception as e:
        log.exception("clip err")
        await update.message.reply_text(f"clip error: {e}")
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass

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
        # ถ้าตั้ง person.delegate_ssh — มอบ YOLO ให้เครื่องอื่นทำ (Z2W ไม่มี torch)
        res = _person_scan_delegated(cfg, conf)
        if res is None:
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


async def cmd_rec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/rec [วินาที] — สั่งบันทึก event ลง Pi4 ทันที (ไม่ต้องรอเจอคน).

    ต่างจาก /clip: /clip ดึงแล้วส่งให้ดูอย่างเดียว ไม่เก็บ;
    /rec อัดเก็บลง output/events/ บน Pi4 + ส่งไฟล์ให้ด้วย.
    """
    if not HAS_REC:
        await update.message.reply_text("EventRec ยังไม่พร้อมบนเครื่องนี้ — ใช้ /clip แทน (ดึงมาดูไม่เก็บ)")
        return
    cfg = load_cfg()
    ipc = cfg.get("ipc", [{}])[0]
    rtsp = ipc.get("rtsp") or "rtsp://admin:123456@192.168.1.21:554/0"
    rec_cfg = cfg.get("event_rec", {})
    default_secs = int(rec_cfg.get("secs", 30))
    quota_mb = int(rec_cfg.get("quota_mb", 4096))
    max_secs = int(rec_cfg.get("max_secs", 120))
    secs = default_secs
    if context.args:
        try:
            secs = max(5, min(max_secs, int(context.args[0])))
        except:
            pass
    await update.message.reply_text(f"⏺ กำลังบันทึก {secs} วิ ลง Pi4 ...")
    try:
        import asyncio
        loop = asyncio.get_running_loop()
        # ffmpeg เป็น blocking call ยาว — โยนไป thread ไม่ให้ bot ค้าง
        res = await loop.run_in_executor(
            None, lambda: record_event(rtsp, secs=secs, reason="manual", quota_mb=quota_mb))
        if not res.get("ok"):
            await update.message.reply_text(f"บันทึกไม่สำเร็จ: {res.get('error')}")
            return
        fpath = Path(res["file"])
        caption = f"⏺ บันทึกแล้ว {secs}วิ {fpath.name} {res['size']//1024}KB (NVR ยังอัด Always ต่อ)"
        if fpath.exists() and fpath.stat().st_size < 45 * 1024 * 1024:
            await update.message.reply_video(
                video=open(fpath, "rb"), caption=caption, supports_streaming=True)
        else:
            await update.message.reply_text(caption + " — ไฟล์ใหญ่เกินส่ง Telegram เปิดดูบน Pi4 ที่ output/events/")
        log.info(f"/rec saved {fpath} sent to {update.effective_chat.id}")
    except Exception as e:
        log.exception("rec err")
        await update.message.reply_text(f"rec error: {e}")


async def cmd_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/events [จำนวน] — รายการเหตุการณ์พบคนย้อนหลัง (ล่าสุดก่อน)"""
    limit = 10
    if context.args:
        try:
            limit = max(1, min(50, int(context.args[0])))
        except Exception:
            pass
    rows = list_person_events(limit)
    if not rows:
        await update.message.reply_text("ยังไม่มีเหตุการณ์พบคน — เปิด auto ด้วย /person_auto on")
        return
    lines = ["เหตุการณ์พบคน (ล่าสุด → เก่า):"]
    for r in rows:
        img = Path(r["image_file"]) if r["image_file"] else None
        clip = Path(r["clip_file"]) if r["clip_file"] else None
        mark = ("📷" if img and img.exists() else "·") + ("⏺" if clip and clip.exists() else "")
        lines.append(f"#{r['id']} {mark} {r['started'][:19]} — {r['persons']} คน (conf {r['conf']:.2f})")
    lines.append("\nเรียกดู: /event <หมายเลข> เช่น /event 3")
    await update.message.reply_text("\n".join(lines)[:4000])


async def cmd_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/event <หมายเลข> — เรียกภาพ/คลิปของเหตุการณ์ย้อนหลังส่งเข้าแชท"""
    if not context.args or not context.args[0].lstrip("#").isdigit():
        await update.message.reply_text("ระบุหมายเลขด้วย เช่น /event 3 (ดูรายการ: /events)")
        return
    eid = int(context.args[0].lstrip("#"))
    ev = get_person_event(eid)
    if not ev:
        await update.message.reply_text(f"ไม่พบ event #{eid} — ดูรายการ: /events")
        return
    clip = Path(ev["clip_file"]) if ev["clip_file"] else None
    if clip and clip.exists() and clip.stat().st_size < 45 * 1024 * 1024:
        cap = f"⏺ event #{ev['id']} {ev['started'][:19]} — {ev['persons']} คน (conf {ev['conf']:.2f}) + คลิป {clip.name}"
        with open(clip, "rb") as vf:
            await update.message.reply_video(video=vf, caption=cap, supports_streaming=True)
        return
    img = Path(ev["image_file"]) if ev["image_file"] else None
    if img and img.exists():
        cap = f"📷 event #{ev['id']} {ev['started'][:19]} — {ev['persons']} คน (conf {ev['conf']:.2f})"
        with open(img, "rb") as f:
            await update.message.reply_photo(photo=f, caption=cap)
        return
    await update.message.reply_text(
        f"event #{ev['id']} ({ev['started'][:19]}) — ไฟล์ไม่อยู่แล้ว (โดน quota prune หรือเก็บไว้อีกเครื่อง)")


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
        app.add_handler(CommandHandler("events", cmd_events))
        app.add_handler(CommandHandler("event", cmd_event))
    if HAS_REC:
        app.add_handler(CommandHandler("rec", cmd_rec))
    app.add_handler(CommandHandler("reboot", cmd_reboot))
    return app

# --- Main polling loop ---
def _tg_send_text(cfg, text):
    """ส่งข้อความ Telegram แบบ sync (HTTP API) ไปทุก chat ใน allow_chat_ids — ใช้จาก health loop"""
    tg = cfg.get("telegram", {})
    token, chat_ids = tg.get("token"), tg.get("allow_chat_ids", [])
    if not token or not chat_ids:
        return False
    try:
        import requests
        ok = True
        for cid in chat_ids:
            try:
                r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                                  data={"chat_id": cid, "text": text}, timeout=10)
                ok = ok and r.status_code == 200
            except Exception as e:
                log.warning(f"tg send to {cid} failed: {e}")
                ok = False
        return ok
    except Exception as e:
        log.warning(f"tg send err: {e}")
        return False

def _alert_ffmpeg_rtsp(cfg, ipc_results):
    """เตือนเมื่อ (1) ffmpeg หาย (2) RTSP ล่มต่อเนื่องเกิน alerts.rtsp_down_secs (default 300วิ)

    เรียกจาก poll_once ทุกรอบ — ใช้ผล rtsp_probe ที่ check_ipc ทำไว้แล้ว (ไม่ probe ซ้ำ)
    ส่งเตือนครั้งเดียวตอนพัง + ครั้งเดียวตอนหาย (กันสแปม)
    """
    global ffmpeg_alert_sent, rtsp_alert_sent
    down_secs = int(cfg.get("alerts", {}).get("rtsp_down_secs", 300))

    # --- ffmpeg ---
    if _ffmpeg_found():
        if ffmpeg_alert_sent:
            _tg_send_text(cfg, "✅ ffmpeg กลับมาแล้ว — /snapshot /clip ใช้ได้ปกติ")
            ffmpeg_alert_sent = False
    else:
        if not ffmpeg_alert_sent:
            ffmpeg_alert_sent = True
            log.warning("ALERT ffmpeg หาย (โดนลบ/uninstall?)")
            _tg_send_text(cfg, "❌ ffmpeg หายจากเครื่อง — /snapshot /clip จะทำงานไม่ได้\nแก้: powershell -ExecutionPolicy Bypass -File scripts\\pi-z2w-bot\\install-deps.ps1")

    # --- RTSP ต่อ cam ---
    for ipc in cfg.get("ipc", []):
        key = f"ipc_{ipc['ip']}"
        ok_rtsp = ipc_results.get(key, False)
        if ok_rtsp:
            rtsp_down_since.pop(key, None)
            if rtsp_alert_sent.pop(key, None):
                _tg_send_text(cfg, f"✅ RTSP {ipc['ip']} กลับมาแล้ว {datetime.now().strftime('%H:%M:%S')}")
        else:
            since = rtsp_down_since.setdefault(key, time.time())
            down_for = time.time() - since
            if down_for >= down_secs and not rtsp_alert_sent.get(key):
                rtsp_alert_sent[key] = True
                log.warning(f"ALERT RTSP {ipc['ip']} down {int(down_for)}s")
                _tg_send_text(cfg, f"🚨 RTSP {ipc['ip']} ล่มมาแล้ว {int(down_for)//60} นาที — ภาพ/คลิปจะดึงไม่ได้\nเช็ค: ไฟกล้อง/สาย/Ping หรือ /status")

def poll_once(cfg):
    ipc_results = {}  # key ipc_<ip> -> rtsp ok? (ให้ _alert_ffmpeg_rtsp ใช้ ไม่ต้อง probe ซ้ำ)
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
        # เก็บผล rtsp probe ไว้ให้ _alert_ffmpeg_rtsp (กัน probe ซ้ำ)
        ipc_results[key] = bool(res_ipc.get("rtsp", (False, ""))[0]) if isinstance(res_ipc, dict) else False
        if not ok_ipc:
            fail_count[key] = fail_count.get(key, 0) + 1
            if fail_count[key] >= FAIL_THRESHOLD and should_alert(key):
                log.warning(f"ALERT {key} down {fail_count[key]}x: {res_ipc}")
        else:
            fail_count[key] = 0

    # Health alert: ffmpeg หาย / RTSP ล่มเกิน 5 นาที (ตั้งได้ที่ alerts.rtsp_down_secs)
    try:
        _alert_ffmpeg_rtsp(cfg, ipc_results)
    except Exception as e:
        log.warning(f"ffmpeg/rtsp alert err: {e}")

def person_watch_loop(cfg, tg_app):
    """Background loop: auto scan person every 30s when enabled (Phase 3).

    Pi4: ถ้าเจอคน + เปิด event_rec.record_on_person -> อัดคลิป event
    ลงเครื่อง (event_record.record_event) พร้อมส่งภาพนิ่งเตือน.
    NVR ยังอัด Always ต่อ ไม่เกี่ยวกัน.
    """
    global last_person_alert, person_visit_active, person_visit_since, person_event_seq, last_seen_ts
    import asyncio
    new_visit_gap = int(cfg.get("person", {}).get("new_visit_gap", NEW_VISIT_GAP_SEC))
    try:
        from event_record import record_event as _rec_event
        _has_rec = True
    except ImportError:
        _has_rec = False
    while True:
        try:
            res = None
            if person_auto_enabled and HAS_PERSON:
                ipc = cfg.get("ipc", [{}])[0]
                rtsp = ipc.get("rtsp") or "rtsp://admin:123456@192.168.1.21:554/0"
                conf = cfg.get("person", {}).get("conf_threshold", 0.5)
                # delegate: สั่งสแกนผ่านเครื่องอื่นที่มี torch (Z2W → Gateway/Pi4) — None = สแกนบนเครื่องนี้
                res = _person_scan_delegated(cfg, conf)
                if res is None:
                    res = scan_snapshot(rtsp, conf=conf, save=False)
                if res.get("has_person"):
                    now = time.time()
                    last_seen_ts = now
                    persons = res.get("persons", [])
                    img_path = res.get("saved") or res.get("image")
                    if not person_visit_active:
                        # "เยี่ยม" ใหม่: ไม่เจอคนต่อเนื่องเกิน gap แล้วกลับมา — เริ่ม event ใหม่
                        person_visit_active = True
                        person_visit_since = datetime.now()
                        # เซฟเองตอนเริ่ม event เท่านั้น (เดิม save=True ทุก 30 วิ → ไฟล์ซ้ำทับกอง)
                        try:
                            if img_path and Path(img_path).exists():
                                out = OUTPUT_DIR / f"person_{person_visit_since.strftime('%Y%m%d_%H%M%S')}_{len(persons)}p.jpg"
                                saved_p = annotate_image(img_path, persons, out_path=out)
                                if saved_p and Path(saved_p).exists():
                                    img_path = str(saved_p)
                        except Exception as e:
                            log.warning(f"person save err: {e}")
                        person_event_seq = save_person_event(len(persons), persons, img_path, visit_start=person_visit_since) or 0
                        caption = (f"🚶 พบคน {len(persons)} คน auto {datetime.now().strftime('%H:%M:%S')} 1080p"
                                   + (f" — event #{person_event_seq} (ดูย้อนหลัง /events)" if person_event_seq else ""))
                        last_person_alert = now
                        # Pi4: อัดคลิป event ลงเครื่องก่อน แล้วค่อยส่งภาพนิ่งเตือน
                        # (NVR อัด Always อยู่แล้ว อันนี้คือสำเนาเฉพาะ event หยิบง่าย)
                        rec_cfg = cfg.get("event_rec", {})
                        clip_path = None
                        if _has_rec and rec_cfg.get("record_on_person", False):
                            try:
                                rec = _rec_event(
                                    rtsp,
                                    secs=int(rec_cfg.get("secs", 30)),
                                    reason="person",
                                    conf=conf,
                                    persons=len(persons),
                                    quota_mb=int(rec_cfg.get("quota_mb", 4096)),
                                )
                                if rec.get("ok"):
                                    clip_path = rec.get("file")
                                    if person_event_seq:
                                        update_person_event_clip(person_event_seq, clip_path)
                                else:
                                    log.warning(f"auto rec failed: {rec.get('error')}")
                            except Exception as e:
                                log.warning(f"auto rec err: {e}")
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
                                                cap = caption + (f" + ⏺ {Path(clip_path).name}" if clip_path else "")
                                                requests.post(
                                                    f"https://api.telegram.org/bot{token}/sendPhoto",
                                                    data={"chat_id": cid, "caption": cap},
                                                    files={"photo": f},
                                                    timeout=20,
                                                )
                                            # ส่งคลิปตาม ถ้าไม่ใหญ่เกิน 45MB (limit Bot API)
                                            if clip_path and Path(clip_path).exists() \
                                                    and Path(clip_path).stat().st_size < 45 * 1024 * 1024:
                                                with open(clip_path, "rb") as vf:
                                                    requests.post(
                                                        f"https://api.telegram.org/bot{token}/sendVideo",
                                                        data={"chat_id": cid,
                                                              "caption": f"⏺ event {Path(clip_path).name}",
                                                              "supports_streaming": True},
                                                        files={"video": vf},
                                                        timeout=60,
                                                    )
                                        except Exception as e:
                                            log.warning(f"auto person send to {cid} failed: {e}")
                                    log.info(f"auto person alert sent {len(persons)} persons clip={clip_path}")
                            except Exception as e:
                                log.warning(f"auto person send err: {e}")
                        else:
                            log.info(f"auto person found {res.get('persons')} but no telegram/img")
                    else:
                        # คนเดิมยังยืนอยู่หน้ากล้อง (เยี่ยมเดิม) — ไม่เซฟซ้ำ ไม่แจ้งซ้ำ
                        last_seen_ts = time.time()
                        log.info(f"person visit ongoing ({len(persons)} คน) — ข้าม (กัน duplicate)")
            elif isinstance(res, dict):
                # รอบนี้ไม่เจอคน — เงียบต่อเนื่องเกิน gap → ปิดเหตุการณ์ (ครั้งหน้า = event ใหม่)
                if person_visit_active and last_seen_ts and (time.time() - last_seen_ts) > new_visit_gap:
                    person_visit_active = False
                    log.info(f"person visit closed (หายไป {int(time.time() - last_seen_ts)}s)")
        except Exception as e:
            log.warning(f"person_watch err: {e}")
        time.sleep(cfg.get("person", {}).get("auto_interval", PERSON_AUTO_INTERVAL))


def main():
    global person_auto_enabled
    cfg = load_cfg()
    init_db()
    # เปิด auto person watch ตั้งแต่ boot ได้ด้วย person.auto_start: true (ไม่ต้องสั่ง /person_auto ใหม่หลัง restart)
    if cfg.get("person", {}).get("auto_start", False):
        person_auto_enabled = True
        log.info("person_auto ON (auto_start from config)")
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
            log.info("person_watch thread started (auto=%s, toggle via /person_auto)",
                     "ON" if person_auto_enabled else "OFF")
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
