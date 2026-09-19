#!/usr/bin/env bash
# setup-frigate-pi4.sh — ติดตั้ง Frigate บน Pi 4 (Raspberry Pi OS Lite 64-bit) ครบในรอบเดียว
# ใช้: bash setup-frigate-pi4.sh          (รันเป็น user ปกติที่มี sudo)
# ตรวจสอบ: http://192.168.1.33:5000  (UI Frigate)
# ต้นทางไฟล์: frigate-pi4/ ใน repo nithep/cctv
set -e

echo "=== 0) ตรวจเงื่อนไข ==="
[ "$(uname -m)" = "aarch64" ] || { echo "❌ ต้องเป็น OS 64-bit (aarch64)"; exit 1; }
MEM=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
[ "$MEM" -ge 3500 ] || echo "⚠️ RAM ${MEM}MB < 4GB — ทำต่อได้แต่ระวังแอพอื่น"
sudo vcgencmd get_throttled 2>/dev/null | grep -q "0x0" && echo "✅ ไฟปกติ (ไม่ throttle)" || echo "⚠️ เคย throttle — เช็คแหล่งจ่ายไฟ 5.1V/3A"
[ -d /dev/dri ] || true

echo "=== 1) deps พื้นฐาน ==="
sudo apt-get update -qq
sudo apt-get install -y -qq docker.io docker-compose-v2 avahi-daemon 2>/dev/null || \
sudo apt-get install -y -qq docker.io docker-compose avahi-daemon
sudo usermod -aG docker "$USER" || true
sudo systemctl enable --now docker

echo "=== 2) เตรียม SSD 120GB (ext4) ที่ /mnt/frigate-media ==="
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT
read -r -p "ใส่ device ของ SSD (เช่น sda1 — ดูจากตารางบน): " SSDDEV
[ -n "$SSDDEV" ] || { echo "ไม่ระบุ device — ข้าม (สมมติ mount แล้ว)"; }
if [ -n "$SSDDEV" ]; then
  sudo mkfs.ext4 -F "/dev/$SSDDEV"
  sudo mkdir -p /mnt/frigate-media
  echo "/dev/$SSDDEV /mnt/frigate-media ext4 defaults,noatime 0 2" | sudo tee -a /etc/fstab
  sudo mount -a
fi
df -h /mnt/frigate-media
sudo mkdir -p /mnt/frigate-media/recordings
sudo chown -R 1000:1000 /mnt/frigate-media

echo "=== 3) วางไฟล์ frigate-pi4 (ถ้ายังไม่มี — copy จาก repo) ==="
mkdir -p ~/frigate-pi4/config
if [ -f ~/frigate-pi4/docker-compose.yml ]; then
  echo "มี docker-compose.yml แล้ว — ข้าม"
fi
cp -n docker-compose.yml ~/frigate-pi4/ 2>/dev/null || true
cp -n config/config.yml ~/frigate-pi4/config/ 2>/dev/null || true

echo "=== 4) เปิด Frigate ==="
cd ~/frigate-pi4
sudo docker compose up -d 2>/dev/null || sudo docker-compose up -d

echo "=== 5) สถานะ ==="
sleep 10
sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "✅ เสร็จ — เปิด UI: http://$(hostname -I | awk '{print $1}'):5000"
echo "ดู log: cd ~/frigate-pi4 && sudo docker compose logs -f frigate"
