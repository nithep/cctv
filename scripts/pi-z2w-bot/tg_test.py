#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ทดสอบ Telegram getMe/sendMessage — รันบน ecs-agent (ไม่โชว์ token เต็ม)"""
import sys
import yaml
import requests
from pathlib import Path

cfg = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
token = cfg["telegram"]["token"]
mode = sys.argv[1] if len(sys.argv) > 1 else "getme"

if mode == "getme":
    r = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10).json()
    print(r)
elif mode == "send":
    chat_id = cfg["telegram"]["allow_chat_ids"][0]
    text = " ".join(sys.argv[2:]) or "ecs-agent ffmpeg OK"
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      data={"chat_id": chat_id, "text": text}, timeout=10).json()
    print(r)
elif mode == "photo":
    chat_id = cfg["telegram"]["allow_chat_ids"][0]
    path = sys.argv[2]
    cap = " ".join(sys.argv[3:]) or path
    with open(path, "rb") as f:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendPhoto",
                          data={"chat_id": chat_id, "caption": cap},
                          files={"photo": f}, timeout=20).json()
    print(r)
