#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Get Telegram chat_id for @hm2569bot
1. ให้ user เปิด Telegram -> @hm2569bot -> /start
2. รัน: python get_chat_id.py
"""
import time, requests, yaml
from pathlib import Path

cfg_path = Path(__file__).with_name("config.yaml")
cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
token = cfg["telegram"]["token"]
print(f"Bot @hm2569bot token {token[:10]}... polling getUpdates (10s)...")
print(">>> กรุณาเปิด Telegram แล้วพิมพ์ /start ไปที่ @hm2569bot ตอนนี้ <<<")
for i in range(12):
    try:
        r = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=10).json()
        if r.get("result"):
            for upd in r["result"]:
                msg = upd.get("message", {})
                chat = msg.get("chat", {})
                print(f"Found chat_id={chat.get('id')} username={chat.get('username')} text={msg.get('text')}")
                # Send test back
                chat_id = chat.get("id")
                if chat_id:
                    test = f"CCTV Bot online — NVR 192.168.1.31 (admin/admin) OK, IPC 192.168.1.21 rtsp://admin:123456@192.168.1.21:554/0 OK (ffmpeg probe passed) — จาก Matebook D2019"
                    try:
                        resp = requests.get(f"https://api.telegram.org/bot{token}/sendMessage", params={"chat_id": chat_id, "text": test}, timeout=10).json()
                        print(f"Send test to {chat_id}: {resp}")
                    except Exception as e:
                        print(f"Send err: {e}")
                    # optionally clear updates
                    # requests.get(f"https://api.telegram.org/bot{token}/getUpdates?offset={upd['update_id']+1}")
            if r["result"]:
                break
        else:
            print(f"[{i}] no updates yet...")
    except Exception as e:
        print(f"poll err: {e}")
    time.sleep(5)
else:
    print("Timeout — ยังไม่พบ /start กรุณาส่ง /start แล้วรันใหม่")
