#!/usr/bin/env bash
# setup-ecs-agent.sh — รันบน ecs-agent@192.168.1.94 (gateway) เท่านั้น
# หน้าที่: ติดตั้ง ffmpeg + deps, ตรวจ RTSP/NVR, เตรียม venv + ทดสอบ Telegram
# วิธีใช้ (paste ทีละบล็อกผ่าน ssh):
#   ssh ecs-agent@192.168.1.94
#   bash setup-ecs-agent.sh
set -e
echo "=== 1) OS / disk / mem ==="
uname -a
cat /etc/os-release 2>/dev/null | head -n 5 || true
df -h / /tmp | head -n 10
free -h || true

echo "=== 2) install ffmpeg + python deps ==="
sudo apt-get update
sudo apt-get install -y ffmpeg python3-venv python3-pip sqlite3 curl

echo "=== 3) verify ffmpeg ==="
which ffmpeg
ffmpeg -hide_banner -version | head -n 3

echo "=== 4) network check to NVR/IPC ==="
ping -c 2 192.168.1.31 || true
ping -c 2 192.168.1.21 || true
curl -s --max-time 5 http://192.168.1.31:8000/ -o /dev/null -w 'NVR HTTP:%{http_code}\n' || true
curl -s --max-time 5 http://192.168.1.21/ -o /dev/null -w 'IPC HTTP:%{http_code}\n' || true

echo "=== 5) RTSP probe (sub stream เบาๆ ก่อน) ==="
# NOTE: แก้รหัสจริงตรงนี้ถ้าไม่ใช่ 123456
RTSP_SUB="rtsp://admin:123456@192.168.1.21:554/1"
RTSP_MAIN="rtsp://admin:123456@192.168.1.21:554/0"
timeout 15 ffmpeg -hide_banner -rtsp_transport tcp -i "$RTSP_SUB" -vframes 1 -q:v 2 /tmp/ecs_test_sub.jpg -y && ls -lh /tmp/ecs_test_sub.jpg && echo "SUB OK" || echo "SUB FAIL"
timeout 20 ffmpeg -hide_banner -rtsp_transport tcp -i "$RTSP_MAIN" -vframes 1 -q:v 2 /tmp/ecs_test_main.jpg -y && ls -lh /tmp/ecs_test_main.jpg && echo "MAIN OK" || echo "MAIN FAIL"

echo "=== 6) bot venv ==="
BOTDIR="$HOME/cctv-bot"
echo "BOTDIR=$BOTDIR"
if [ ! -d "$BOTDIR" ]; then
  echo "ยังไม่มี $BOTDIR — กลับไปฝั่ง Matebook รัน deploy-to-ecs-agent.ps1 เพื่อ scp ไฟล์มาก่อน แล้วค่อยรันสคริปต์นี้ต่อ"
  exit 1
fi
cd "$BOTDIR"
python3 -m venv venv || true
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
echo "--- pip list ---"
./venv/bin/pip list | grep -i -E "telegram|requests|yaml|ultralytics|opencv" || true

echo "=== 7) config check (ห้ามโชว์ token) ==="
if [ ! -f config.yaml ]; then
  echo "ยังไม่มี config.yaml — รัน: cp config.yaml.example config.yaml แล้ว nano config.yaml ใส่ pass/token/chat_id"
  echo "ตัวอย่างฟิลด์ที่ต้องแก้: nvr.pass, ipc[0].rtsp, telegram.token, telegram.allow_chat_ids"
else
  echo "config.yaml มีแล้ว — ตรวจว่าไม่ใช่ค่า CHANGE_ME:"
  grep -c CHANGE_ME config.yaml && echo "ยังมี CHANGE_ME — ไปแก้ก่อน" || echo "config ดูโอเค (ไม่มี CHANGE_ME)"
fi

echo "=== 8) health check ==="
./venv/bin/python health.py || echo "health FAIL — ดู config.yaml + network"

echo "=== 9) telegram test ==="
echo "9a) getMe (ตรวจ token อย่างเดียว ไม่ส่งข้อความ):"
./venv/bin/python -c "import yaml; c=yaml.safe_load(open('config.yaml')); t=c['telegram']['token']; import requests; print(requests.get(f'https://api.telegram.org/bot{t}/getMe',timeout=10).json())" || echo "getMe FAIL — token ผิด / เน็ตออกไม่ได้"
echo "9b) get_chat_id — ให้เปิด Telegram -> @hm2569bot -> /start ก่อน แล้วค่อยรัน:"
echo "    ./venv/bin/python get_chat_id.py"
echo "9c) ส่งทดสอบด้วยมือ (แก้ CHAT_ID):"
echo '    ./venv/bin/python -c "import yaml,requests; c=yaml.safe_load(open(\"config.yaml\")); t=c[\"telegram\"][\"token\"]; print(requests.post(f\"https://api.telegram.org/bot{t}/sendMessage\", data={\"chat_id\": 123456789, \"text\": \"ecs-agent ffmpeg OK\"}, timeout=10).json())"'

echo "=== DONE — ถ้า 1-9 ผ่านหมด ค่อย: ./venv/bin/python bot.py (foreground) หรือติดตั้ง service ==="
