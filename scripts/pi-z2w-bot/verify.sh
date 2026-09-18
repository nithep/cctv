#!/usr/bin/env bash
# verify.sh — ตรวจทั้งหมดบน Pi4 / Pi Zero 2W / ecs-agent (Linux)
# ใช้:  bash verify.sh
#       bash verify.sh --full   (+ เช็ค network จริง: health.py — ต้องอยู่วง LAN/WG เดียวกับกล้อง)
set -u
cd "$(dirname "$0")"
PASS=0; FAIL=0

step() { # step "ชื่อ" 0|1 "รายละเอียด"
  if [ "$2" -eq 1 ]; then echo "[PASS] $1 — $3"; PASS=$((PASS+1))
  else echo "[FAIL] $1 — $3"; FAIL=$((FAIL+1)); fi
}

echo "=== CCTV Bot Verify (Linux/Pi) ==="

# --- 1) ffmpeg ---
if command -v ffmpeg >/dev/null 2>&1; then
  step "ffmpeg" 1 "$(ffmpeg -hide_banner -version 2>/dev/null | head -n 1)"
else
  step "ffmpeg" 0 "not found — รัน: sudo apt install -y ffmpeg"
fi

# --- 2) python3 + venv + deps ---
PY=""
if [ -x "$HOME/cctv-bot/venv/bin/python" ]; then
  PY="$HOME/cctv-bot/venv/bin/python"
  step "venv" 1 "$HOME/cctv-bot/venv"
elif command -v python3 >/dev/null 2>&1; then
  PY="$(command -v python3)"
  step "venv" 0 "ไม่มี ~/cctv-bot/venv — ใช้ system python3 (บน Pi แนะนำ venv ตาม README)"
fi
if [ -z "$PY" ]; then
  step "python3" 0 "python3 not found — รัน: sudo apt install -y python3-venv python3-pip"
else
  step "python3" 1 "$($PY --version 2>&1)"
  MISSING=""
  for m in yaml requests telegram; do
    "$PY" -c "import $m" >/dev/null 2>&1 || MISSING="$MISSING $m"
  done
  if [ -z "$MISSING" ]; then
    step "python deps" 1 "yaml, requests, telegram OK"
  else
    step "python deps" 0 "missing:$MISSING — รัน: $PY -m pip install -r requirements.txt"
  fi
  # pytest: ไม่มีก็ติดตั้งให้เลย (venv เท่านั้น ไม่แตะ system)
  if ! "$PY" -c "import pytest" >/dev/null 2>&1; then
    echo "       pytest ไม่มี — ติดตั้งให้อัตโนมัติ..."
    "$PY" -m pip install -q pytest >/dev/null 2>&1 || true
  fi
  "$PY" -c "import pytest" >/dev/null 2>&1
  step "pytest" $? "pytest ready"

  # --- 3) syntax ---
  "$PY" -m py_compile bot.py health.py check-config.py >/dev/null 2>&1
  step "syntax (py_compile)" $? "bot.py, health.py, check-config.py"

  # --- 4) config.yaml เทียบ example ---
  "$PY" -X utf8 check-config.py
  step "config.yaml vs example" $? "รายละเอียดด้านบน (❌ = คีย์ขาด, ⚠️ = ควรเพิ่ม)"

  # --- 5) pytest health alert ---
  "$PY" -X utf8 -m pytest test_health_alerts.py -v --tb=short
  step "pytest health alerts" $? "ดูผลด้านบน"
fi

# --- 6) systemd service (ถ้ามี) ---
if systemctl list-unit-files 2>/dev/null | grep -q cctv-bot; then
  systemctl is-active --quiet cctv-bot
  step "systemd cctv-bot" $? "$(systemctl is-active cctv-bot 2>/dev/null) — journal: journalctl -u cctv-bot -f"
else
  echo "[skip] systemd cctv-bot — ยังไม่ติดตั้ง service (ดู README หัวติดตั้งบน Pi)"
fi

# --- 7) --full: network จริง ---
if [ "${1:-}" = "--full" ] && [ -n "$PY" ]; then
  echo ""
  echo "=== [--full] network check: health.py ==="
  "$PY" health.py
  step "network (health.py)" $? "ผลจริงด้านบน"
fi

# --- สรุป ---
echo ""
echo "=== SUMMARY: $PASS pass, $FAIL fail ==="
if [ "$FAIL" -eq 0 ]; then
  echo "ผ่านทั้งหมด 🎉 — เริ่มบอท: systemctl restart cctv-bot หรือ ./venv/bin/python bot.py"
  exit 0
else
  echo "มี $FAIL รายการไม่ผ่าน — แก้ตาม detail ด้านบน หรือก๊อป output ทั้งหมดให้ Buffy แก้ให้"
  exit 1
fi
