#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pi Z2W — Health checks for NVRmini2 (192.168.1.31:8000) + Seetong IPC (192.168.1.21)
Lightweight: no heavy deps, suitable for 512MB RAM.
"""
import socket
import subprocess
import requests

TIMEOUT = 5

def tcp_check(ip, port):
    try:
        with socket.create_connection((ip, port), timeout=TIMEOUT):
            return True, "open"
    except Exception as e:
        return False, str(e)

def http_check(url):
    try:
        r = requests.get(url, timeout=TIMEOUT)
        ok = r.status_code in (200, 302)
        # NUUO returns 200 even when not auth (login page), so check for NVR marker
        hint = "NUUO" if "NUUO" in r.text else "gSOAP" if "gSOAP" in r.text else f"HTTP {r.status_code}"
        return ok, f"{hint} ({r.status_code})"
    except Exception as e:
        return False, str(e)

def rtsp_probe(rtsp_url, timeout=4):
    """Use ffmpeg probe (lightweight) to verify RTSP reachable. Requires ffmpeg on Pi."""
    try:
        import shutil, os, pathlib
        ffmpeg = shutil.which("ffmpeg")
        # winget GyanFFmpeg fallback on Windows Matebook
        if not ffmpeg:
            for p in pathlib.Path.home().glob("AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg*/ffmpeg-*/bin/ffmpeg.exe"):
                if p.exists():
                    ffmpeg = str(p)
                    break
        if not ffmpeg:
            ffmpeg = "ffmpeg"
        # ใช้ vframes 1 เร็วกว่า -t 4 สำหรับ 512MB Pi / Matebook — จบใน ~0.3s แทน 4s
        cmd = [ffmpeg, "-rtsp_transport", "tcp", "-i", rtsp_url, "-vframes", "1", "-f", "null", "-"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout+5)
        # ffmpeg returns 0 even if stream ok but we check stderr for "Stream #0"
        stderr = result.stderr.decode(errors="ignore")
        if "Stream" in stderr or result.returncode == 0:
            return True, "rtsp ok"
        return False, stderr[:200]
    except FileNotFoundError:
        return False, "ffmpeg not found (apt install ffmpeg)"
    except Exception as e:
        return False, str(e)[:200]

def check_nvr(cfg):
    ip = cfg["nvr"]["ip"]
    port = int(cfg["nvr"].get("port", 8000))
    results = {}
    ok_tcp, msg_tcp = tcp_check(ip, port)
    results["tcp"] = (ok_tcp, msg_tcp)
    ok_http, msg_http = http_check(f"http://{ip}:{port}/")
    results["http"] = (ok_http, msg_http)
    overall = ok_tcp and ok_http
    return overall, results

def check_ipc(ipc_cfg):
    ip = ipc_cfg["ip"]
    results = {}
    ok_tcp80, msg80 = tcp_check(ip, 80)
    results["tcp80"] = (ok_tcp80, msg80)
    ok_tcp554, msg554 = tcp_check(ip, 554)
    results["tcp554"] = (ok_tcp554, msg554)
    ok_http, msg_http = http_check(f"http://{ip}/")
    results["http"] = (ok_http, msg_http)
    if ipc_cfg.get("rtsp"):
        ok_rtsp, msg_rtsp = rtsp_probe(ipc_cfg["rtsp"])
        results["rtsp"] = (ok_rtsp, msg_rtsp)
    overall = ok_tcp80 and ok_tcp554
    return overall, results

if __name__ == "__main__":
    import yaml
    from pathlib import Path
    cfg_path = Path(__file__).with_name("config.yaml")
    if not cfg_path.exists():
        cfg_path = Path("config.yaml")
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    print("=== NVR ===")
    ok, res = check_nvr(cfg)
    print(ok, res)
    for ipc in cfg.get("ipc", []):
        print(f"=== IPC {ipc['ip']} ===")
        ok2, res2 = check_ipc(ipc)
        print(ok2, res2)
