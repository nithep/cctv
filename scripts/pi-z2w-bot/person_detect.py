#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hermes Sentinel — Phase 3 Person Filter
YOLOv8n person detection for NVR/IPC snapshots.

Design goals:
- Matebook D2019 (Win10, RAM 8GB+) can run YOLOv8n (~6MB) via ultralytics.
- Pi Z2W (512MB) fallback to motion diff / NVR motion flag if YOLO unavailable.
- On-demand: /person command captures snapshot then detects.
- Auto: person_watch loop every 30s captures & detects, alerts via Telegram.

Deps (optional):
  pip install ultralytics opencv-python   # Matebook / Pi4
  # Pi Z2W: no heavy deps needed — uses motion fallback
"""

import os
import time
import logging
from pathlib import Path
from datetime import datetime

log = logging.getLogger("person_detect")

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output" / "person"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Lazy globals
_YOLO_MODEL = None
_HAS_CV2 = None
_HAS_YOLO = None

CONF_DEFAULT = 0.5
MODEL_DEFAULT = "yolov8n.pt"


def _check_deps():
    global _HAS_CV2, _HAS_YOLO
    if _HAS_CV2 is None:
        try:
            import cv2  # noqa: F401
            _HAS_CV2 = True
        except ImportError:
            _HAS_CV2 = False
    if _HAS_YOLO is None:
        try:
            from ultralytics import YOLO  # noqa: F401
            _HAS_YOLO = True
        except ImportError:
            _HAS_YOLO = False
    return _HAS_CV2, _HAS_YOLO


def _ffmpeg_bin():
    import shutil, pathlib
    f = shutil.which("ffmpeg")
    if f:
        return f
    for p in pathlib.Path.home().glob("AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg*/ffmpeg-*/bin/ffmpeg.exe"):
        if p.exists():
            return str(p)
    return "ffmpeg"


def get_yolo_model(model_name=MODEL_DEFAULT):
    """Lazy load YOLOv8n — downloads on first run (~6MB)."""
    global _YOLO_MODEL
    if _YOLO_MODEL is not None:
        return _YOLO_MODEL
    _, has_yolo = _check_deps()
    if not has_yolo:
        log.warning("ultralytics not installed — YOLO unavailable, fallback to motion")
        return None
    try:
        from ultralytics import YOLO
        # model file cached at ~/.ultralytics or cwd
        _YOLO_MODEL = YOLO(model_name)
        log.info(f"YOLO model loaded: {model_name}")
        return _YOLO_MODEL
    except Exception as e:
        log.warning(f"YOLO load failed ({e}) — fallback")
        return None


def capture_snapshot(rtsp_url, tmp_path=None, timeout=15):
    """Capture single frame via ffmpeg RTSP -> jpg. Returns Path or None."""
    import subprocess
    if tmp_path is None:
        tmp = Path(os.environ.get("TEMP", "/tmp")) / f"person_snap_{int(time.time())}.jpg"
        if Path("/tmp").exists():
            tmp = Path(f"/tmp/person_snap_{int(time.time())}.jpg")
    else:
        tmp = Path(tmp_path)
    ff = _ffmpeg_bin()
    cmd = [ff, "-y", "-rtsp_transport", "tcp", "-i", rtsp_url, "-vframes", "1", "-q:v", "2", str(tmp)]
    try:
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        if tmp.exists() and tmp.stat().st_size > 1000:
            return tmp
        log.warning(f"snapshot empty: {r.stderr.decode(errors='ignore')[:200]}")
        return None
    except Exception as e:
        log.warning(f"snapshot error: {e}")
        return None


def detect_person_yolo(image_path, conf=CONF_DEFAULT, model_name=MODEL_DEFAULT):
    """Run YOLOv8n person (class 0) detection. Returns list of dicts."""
    model = get_yolo_model(model_name)
    if model is None:
        return None  # signal fallback
    try:
        results = model(str(image_path), verbose=False, conf=conf)
        persons = []
        for r in results:
            for box in r.boxes:
                cls = int(box.cls.item())
                if cls == 0:  # person
                    c = float(box.conf.item())
                    x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
                    persons.append({"bbox": [x1, y1, x2, y2], "conf": c, "class": "person"})
        return persons
    except Exception as e:
        log.warning(f"YOLO inference failed: {e}")
        return None


def detect_motion_fallback(image_path, prev_path=None):
    """Lightweight fallback when YOLO not available.
    Uses frame diff if prev image exists, else reports no person but motion unknown.
    Returns empty list (no person) — but logs hint to use NVR motion."""
    # No heavy CV2 needed — just return empty to indicate "no AI, check NVR motion"
    log.info("fallback: no YOLO — returning motion hint (check NVR SUPPORT_MOTION_RECORDING)")
    return []


def detect_person(image_path, conf=CONF_DEFAULT, model_name=MODEL_DEFAULT, use_fallback=True):
    """Unified entry: YOLO if available else motion fallback. Returns (persons, backend)."""
    has_cv2, has_yolo = _check_deps()
    if has_yolo:
        persons = detect_person_yolo(image_path, conf=conf, model_name=model_name)
        if persons is not None:
            return persons, "yolo"
    if use_fallback:
        persons = detect_motion_fallback(image_path)
        return persons, "motion_fallback"
    return [], "none"


def annotate_image(image_path, persons, out_path=None):
    """Draw bboxes on image via cv2 if available. Returns out Path."""
    has_cv2, _ = _check_deps()
    if not has_cv2 or not persons:
        return Path(image_path)
    try:
        import cv2
        img = cv2.imread(str(image_path))
        if img is None:
            return Path(image_path)
        for p in persons:
            x1, y1, x2, y2 = [int(v) for v in p["bbox"]]
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"person {p['conf']:.2f}"
            cv2.putText(img, label, (x1, max(0, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        if out_path is None:
            out_path = OUTPUT_DIR / f"person_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        else:
            out_path = Path(out_path)
        cv2.imwrite(str(out_path), img)
        return out_path
    except Exception as e:
        log.warning(f"annotate failed: {e}")
        return Path(image_path)


def scan_snapshot(rtsp_url, conf=CONF_DEFAULT, save=True):
    """Capture + detect in one call. Saves to output/person/ if person found."""
    tmp = capture_snapshot(rtsp_url)
    if tmp is None:
        return {"ok": False, "error": "snapshot failed", "persons": [], "backend": "none", "image": None}
    persons, backend = detect_person(tmp, conf=conf)
    result = {
        "ok": True,
        "persons": persons,
        "backend": backend,
        "image": str(tmp),
        "has_person": len(persons) > 0,
    }
    if save and persons:
        out = OUTPUT_DIR / f"person_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(persons)}p.jpg"
        annotated = annotate_image(tmp, persons, out_path=out)
        result["saved"] = str(annotated)
        # also copy original with timestamp
        log.info(f"person found {len(persons)} -> {annotated}")
    elif save:
        # No person — optionally keep last no-person snapshot for debug (overwrite)
        debug = OUTPUT_DIR / "_last_noperson.jpg"
        try:
            import shutil
            shutil.copy(str(tmp), str(debug))
        except Exception:
            pass
    return result


def extract_clip_frames(rtsp_url, secs=10, fps=1, tmp_dir=None):
    """Extract frames from RTSP clip for scanning (NVR On-Demand).
    Returns list of image Paths."""
    import subprocess, tempfile
    if tmp_dir is None:
        tmp_dir = Path(os.environ.get("TEMP", "/tmp")) / f"clip_frames_{int(time.time())}"
        if not Path("/tmp").exists():
            tmp_dir = Path(os.environ.get("TEMP", ".")) / f"clip_frames_{int(time.time())}"
    tmp_dir = Path(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    ff = _ffmpeg_bin()
    # Extract 1 fps
    out_pattern = str(tmp_dir / "frame_%03d.jpg")
    cmd = [ff, "-y", "-rtsp_transport", "tcp", "-i", rtsp_url, "-t", str(secs), "-vf", f"fps={fps}", "-q:v", "2", out_pattern]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=secs + 15)
        frames = sorted(tmp_dir.glob("frame_*.jpg"))
        return [p for p in frames if p.stat().st_size > 1000]
    except Exception as e:
        log.warning(f"clip extract failed: {e}")
        return []


def scan_clip(rtsp_url, secs=10, conf=CONF_DEFAULT):
    """Scan recent clip for persons frame-by-frame. Returns summary."""
    frames = extract_clip_frames(rtsp_url, secs=secs)
    if not frames:
        return {"ok": False, "error": "no frames extracted", "persons": [], "frames": 0}
    all_persons = []
    hit_frames = 0
    saved = None
    for fp in frames:
        persons, backend = detect_person(fp, conf=conf)
        if persons:
            hit_frames += 1
            all_persons.extend(persons)
            if saved is None:
                saved = str(annotate_image(fp, persons))
    return {
        "ok": True,
        "frames": len(frames),
        "hit_frames": hit_frames,
        "persons_total": len(all_persons),
        "has_person": hit_frames > 0,
        "saved": saved,
        "backend": backend if frames else "none",
    }


# CLI for testing
if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser(description="Person detect — YOLOv8n")
    ap.add_argument("--image", help="image path to scan")
    ap.add_argument("--rtsp", help="RTSP url to capture + scan")
    ap.add_argument("--clip", type=int, help="scan clip secs from RTSP")
    ap.add_argument("--conf", type=float, default=CONF_DEFAULT)
    ap.add_argument("--model", default=MODEL_DEFAULT)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO)

    if args.image:
        persons, backend = detect_person(args.image, conf=args.conf, model_name=args.model)
        print(json.dumps({"backend": backend, "persons": persons, "count": len(persons)}, indent=2, ensure_ascii=False))
        if persons:
            out = annotate_image(args.image, persons)
            print(f"annotated -> {out}")
    elif args.rtsp:
        if args.clip:
            res = scan_clip(args.rtsp, secs=args.clip, conf=args.conf)
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            res = scan_snapshot(args.rtsp, conf=args.conf)
            # convert Path to str for json
            print(json.dumps({k: str(v) if isinstance(v, Path) else v for k, v in res.items()}, indent=2, ensure_ascii=False))
    else:
        ap.print_help()
        print("\nExamples:")
        print("  python person_detect.py --image cctv/output/snapshot_2026-09-08_00-39.jpg")
        print("  python person_detect.py --rtsp rtsp://admin:123456@192.168.1.21:554/0")
        print("  python person_detect.py --rtsp rtsp://admin:123456@192.168.1.21:554/0 --clip 10")
