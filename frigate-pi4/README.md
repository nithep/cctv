# Frigate บน Pi 4 — Quick Start (frigate-pi4/)

> แผนเต็ม: `plans/2026-09-20_Frigate-Trial-Plan.md` — ทดลองขนานกับ NUUO 1-2 สัปดาห์ ไม่แตะระบบเดิม

## ของที่ต้องมี (ตรวจแล้ว)
- Pi 4 RAM 4GB ✅ (มีอยู่มือ)
- SSD 120GB + enclosure ✅ (มีอยู่มือ — เก็บเทป motion 7-10 วัน)
- ไฟแท้ 5.1V/3A USB-C (ถ้าไม่แน่ใจ สั่งเพิ่ม ~400฿)
- SD card ≥16GB (ลง OS อย่างเดียว)
- สาย LAN (แนะนำ — เชื่อกล้องผ่านเครือข่ายเสถียรกว่า WiFi)

## ขั้นตอน (15-20 นาที)

### 1) Flash SD — Raspberry Pi Imager
- เลือก **Raspberry Pi OS Lite (64-bit)** (Debian 12/13 bookworm/trixie)
- ตั้ง hostname `frigate`, เปิด SSH, ตั้ง user `admin` + รหัส, ตั้ง WiFi ได้ (แต่ LAN ดีกว่า)

### 2) บูต + ต่อ LAN ที่ IP `.33`
- ตั้ง DHCP reservation `.33` บน router (ตาม ip-map)
- `ssh admin@192.168.1.33`

### 3) เตรียมไฟล์จาก repo นี้
```bash
# บน Pi — คัดลอกโฟลเดอร์ frigate-pi4/ จากเครื่อง dev (หรือ clone repo)
scp -r frigate-pi4 admin@192.168.1.33:~/
```

### 4) รันสคริปต์ติดตั้ง
```bash
cd ~/frigate-pi4
bash setup-frigate-pi4.sh    # Docker + เตรียม SSD ext4 + เปิด Frigate
```

### 5) ใช้งาน
- UI: `http://192.168.1.33:5000`
- ดู log: `cd ~/frigate-pi4 && sudo docker compose logs -f frigate`
- ทดสอบ: motion event → person detect → playback ย้อนหลัง

## เกณฑ์ทดสอบ 2 สัปดาห์ (ตัดสินย้ายงานบันทึกจาก NUUO)
- [ ] รันนิ่ง ≥7 วัน ไม่ restart เอง
- [ ] 0 ภาพหาย (เทียบเหตุการณ์กับ NUUO)
- [ ] ตรวจคนแม่นกว่า YOLO-CPU ของบอทชัดเจน
- [ ] CPU < 60% เฉลี่ย, อุณหภูมิ < 75°C

## ไฟล์ในโฟลเดอร์นี้
| ไฟล์ | หน้าที่ |
|---|---|
| `docker-compose.yml` | stack Frigate (device `/dev/video11`, เก็บเทปที่ `/mnt/frigate-media`) |
| `config/config.yml` | config กล้อง Seetong — go2rtc restream, detect sub `/1`, record main `/0`, retain 7 วัน |
| `setup-frigate-pi4.sh` | สคริปต์ติดตั้งครบรอบเดียว |

> Coral USB TPU (~1,800฿) เพิ่มภายหลังได้ — แค่เปิดส่วน `detectors:` ใน config.yml (ดู comment ในไฟล์) — ใช้โมเดล default เท่านั้น (YOLOv8n รันบน Coral ไม่ได้)
