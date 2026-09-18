#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_health_alerts.py — pytest สำหรับฟังก์ชัน health alert ใน bot.py

รัน:
    pip install pytest
    pytest scripts/pi-z2w-bot/test_health_alerts.py -v

ไม่ต้องมี network / Telegram token — ทุก test patch การส่งข้อความและเวลา
"""
import sys
import time as _time_mod
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import bot  # noqa: E402


@pytest.fixture(autouse=True)
def reset_state():
    """คืน global state ของ health alert ให้สะอาดก่อน/หลังทุก test"""
    bot.ffmpeg_alert_sent = False
    bot.rtsp_alert_sent = {}
    bot.rtsp_down_since = {}
    yield
    bot.ffmpeg_alert_sent = False
    bot.rtsp_alert_sent = {}
    bot.rtsp_down_since = {}


@pytest.fixture
def sent():
    """จับข้อความที่ _tg_send_text ได้รับ แทนการยิง Telegram จริง"""
    msgs = []
    bot._tg_send_text = lambda cfg, text: msgs.append(text) or True
    return msgs


@pytest.fixture
def cfg():
    return {
        "ipc": [{"ip": "192.168.1.21"}],
        "telegram": {"token": "x", "allow_chat_ids": [1]},
    }


def set_ffmpeg(monkeypatch, found):
    monkeypatch.setattr(bot, "_ffmpeg_found", (lambda: found) if found else (lambda: None))


# ---------------- ffmpeg ----------------

def test_ffmpeg_missing_alerts_once(cfg, sent, monkeypatch):
    set_ffmpeg(monkeypatch, False)
    bot._alert_ffmpeg_rtsp(cfg, {"ipc_192.168.1.21": True})
    assert len([m for m in sent if "ffmpeg" in m]) == 1
    # รอบถัดไป (ยังหาย) ต้องไม่สแปม
    bot._alert_ffmpeg_rtsp(cfg, {"ipc_192.168.1.21": True})
    assert len([m for m in sent if "ffmpeg" in m]) == 1
    assert "install-deps" in sent[0]  # ข้อความบอกวิธีแก้


def test_ffmpeg_recovery_alerts_once(cfg, sent, monkeypatch):
    set_ffmpeg(monkeypatch, False)
    bot._alert_ffmpeg_rtsp(cfg, {})
    assert bot.ffmpeg_alert_sent is True
    set_ffmpeg(monkeypatch, True)
    bot._alert_ffmpeg_rtsp(cfg, {})
    bot._alert_ffmpeg_rtsp(cfg, {})
    rec = [m for m in sent if "กลับมาแล้ว" in m]
    assert len(rec) == 1  # แจ้งหายครั้งเดียว
    assert bot.ffmpeg_alert_sent is False


# ---------------- RTSP ----------------

def test_rtsp_down_alerts_after_5min(cfg, sent, monkeypatch):
    set_ffmpeg(monkeypatch, True)
    now = _time_mod.time()
    monkeypatch.setattr(bot.time, "time", lambda: now)

    bot._alert_ffmpeg_rtsp(cfg, {"ipc_192.168.1.21": False})
    assert sent == []  # เพิ่งล่ม — ยังไม่เตือน

    monkeypatch.setattr(bot.time, "time", lambda: now + 299)
    bot._alert_ffmpeg_rtsp(cfg, {"ipc_192.168.1.21": False})
    assert sent == []  # ยังไม่ถึง 300 วิ

    monkeypatch.setattr(bot.time, "time", lambda: now + 301)
    bot._alert_ffmpeg_rtsp(cfg, {"ipc_192.168.1.21": False})
    assert len(sent) == 1 and "192.168.1.21" in sent[0]

    # ยังล่มต่อ — ไม่เตือนซ้ำ
    monkeypatch.setattr(bot.time, "time", lambda: now + 900)
    bot._alert_ffmpeg_rtsp(cfg, {"ipc_192.168.1.21": False})
    assert len(sent) == 1


def test_rtsp_recovery_alerts_once(cfg, sent, monkeypatch):
    set_ffmpeg(monkeypatch, True)
    now = _time_mod.time()
    monkeypatch.setattr(bot.time, "time", lambda: now)
    bot._alert_ffmpeg_rtsp(cfg, {"ipc_192.168.1.21": False})
    monkeypatch.setattr(bot.time, "time", lambda: now + 400)
    bot._alert_ffmpeg_rtsp(cfg, {"ipc_192.168.1.21": False})
    assert len(sent) == 1

    # กลับมา — แจ้งครั้งเดียว
    bot._alert_ffmpeg_rtsp(cfg, {"ipc_192.168.1.21": True})
    bot._alert_ffmpeg_rtsp(cfg, {"ipc_192.168.1.21": True})
    rec = [m for m in sent if "กลับมาแล้ว" in m]
    assert len(rec) == 1
    assert bot.rtsp_down_since == {}  # reset ตัวนับเมื่อ up


def test_rtsp_threshold_from_config(cfg, sent, monkeypatch):
    cfg["alerts"] = {"rtsp_down_secs": 60}
    set_ffmpeg(monkeypatch, True)
    now = _time_mod.time()
    monkeypatch.setattr(bot.time, "time", lambda: now)
    bot._alert_ffmpeg_rtsp(cfg, {"ipc_192.168.1.21": False})
    monkeypatch.setattr(bot.time, "time", lambda: now + 61)
    bot._alert_ffmpeg_rtsp(cfg, {"ipc_192.168.1.21": False})
    assert len(sent) == 1  # ตาม config ไม่ใช่ default 300


def test_two_ips_alert_independently(cfg, sent, monkeypatch):
    cfg["ipc"] = [{"ip": "192.168.1.21"}, {"ip": "192.168.1.22"}]
    set_ffmpeg(monkeypatch, True)
    now = _time_mod.time()
    monkeypatch.setattr(bot.time, "time", lambda: now)
    res = {"ipc_192.168.1.21": False, "ipc_192.168.1.22": True}
    bot._alert_ffmpeg_rtsp(cfg, res)
    monkeypatch.setattr(bot.time, "time", lambda: now + 400)
    bot._alert_ffmpeg_rtsp(cfg, res)
    assert len(sent) == 1 and "192.168.1.21" in sent[0]  # .22 ปกติ ไม่เตือน


# ---------------- helpers ----------------

def test_valid_jpeg(tmp_path):
    ok = tmp_path / "ok.jpg"
    ok.write_bytes(b"\xff\xd8" + b"x" * 2000 + b"\xff\xd9")
    assert bot._valid_jpeg(ok) is True

    truncated = tmp_path / "bad.jpg"
    truncated.write_bytes(b"\xff\xd8" + b"x" * 2000)  # ไม่มี tail
    assert bot._valid_jpeg(truncated) is False

    tiny = tmp_path / "tiny.jpg"
    tiny.write_bytes(b"\xff\xd8\xff\xd9")
    assert bot._valid_jpeg(tiny) is False  # <1000 bytes


def test_dig_reads_nested_and_list():
    # check-config.py มีขีดกลาง จึงต้องโหลดด้วย importlib
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "check_config", Path(__file__).with_name("check-config.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cfg = {"nvr": {"ip": "1.2.3.4"}, "ipc": [{"ip": "5.6.7.8", "rtsp": "rtsp://x/0"}]}
    assert mod.dig(cfg, "nvr.ip") == ("1.2.3.4", True)
    assert mod.dig(cfg, "ipc[0].rtsp") == ("rtsp://x/0", True)
    assert mod.dig(cfg, "ipc[5].rtsp") == (None, False)
    assert mod.dig(cfg, "nvr.nope") == (None, False)
