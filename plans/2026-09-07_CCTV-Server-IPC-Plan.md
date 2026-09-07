---
type: cctv_plan
title: "แผนสร้าง Server จัดเก็บข้อมูล CCTV + เชื่อมต่อ IPC — NUUO NVRmini 2 (192.168.1.31:8000)"
date: 2026-09-07
status: draft
nvr_ip: 192.168.1.31
nvr_port: 8000
nvr_model: NUUO NVRmini 2 (firmware 03.11.0000.0005)
verified_by: Muse Spark
---

# แผนสร้าง Server จัดเก็บข้อมูล CCTV — เตรียมเชื่อม IPC

> ต้นทางคำสั่ง: `http://192.168.1.31:8000/?cmd=invalid&ret=1` — ตรวจสอบแล้ว

## 1) สรุปผลตรวจสอบระบบ ณ 2026-09-07 20:56 / 21:06 ICT

### NUUO NVRmini 2 — 192.168.1.31:8000
| รายการ | ผล | หมายเหตุ |
|---|---|---|
| **Ping / TCP 192.168.1.31:8000** | ✅ `TcpTestSucceeded: True` `Src 192.168.1.44 → 192.168.1.31` | Wi-Fi, latency ปกติ |
| **HTTP GET /** | ✅ `200 OK` `lighttpd/1.4.48` `PHP/7.4.1` `PHPSESSID` | หน้า `Network Video Recorder Login` |
| **HTTP GET /?cmd=invalid&ret=1** | ✅ `200 OK` แต่ `alert(v_index_noauthen)` → `top.location.replace("index.php")` | คือพฤติกรรมปกติเมื่อยังไม่ login — ไม่ใช่ error ของเครื่อง |
| **MAC Address (ARP)** | `94:de:80:9d:53:f1` dynamic | บันทึกไว้ทำ IP reservation |
| **Vendor / Model** | `VENDOR_NAME=NUUO` `PROJECT_NAME=NVRmini 2` `Yahoo YUI 03.11.0000.0005` | อ้างอิง `wiki/products/NUUO-Resources.md` |
| **ความสามารถจาก HTML header** | `LIVE_STREAM_MAX_CONN=64`, `SUPPORT_RAID_SETTING=true`, `SUPPORT_MOTION_RECORDING=true`, `SUPPORT_WEB_SERVICE=true`, `ALLOW_DUPLICATE_CAMERA=1`, `SUPPORT_AUTO_REBOOT=1` | รองรับงานขยายกล้องได้ |
| **API Probe `/cgi-bin/api.cgi?cmd=GetDeviceInfo`** | `404 Not Found` | NUUO รุ่นนี้ใช้ `login.php` + Web Service แบบเก่า ไม่ใช่ Reolink API — ต้องใช้ ONVIF/RTSP |

### Seetong IPC — 192.168.1.21 (เพิ่มใหม่จากภาพ UC2 4.7)
| รายการ | ผล | หมายเหตุ |
|---|---|---|
| **Source** | ภาพ `cctv/raw/UC2_4.7_setup [Image 1]` → `Config Management → Remote Config → Network Status` | กลั่นแล้ว → `cctv/docs/2026-09-07_Seetong-IPC-192.168.1.21-Config.md` + `wiki/products/Seetong-UC2.md` |
| **Wire Net** | `MAC 00:4A:7B:3E:00:61` `Static IP 192.168.1.21` `GW 192.168.1.1` `Mask 255.255.255.0` `DNS1 203.113.111.162` `DNS2 192.168.1.1` | ตรงกับ `arp -a` |
| **Cloud** | `Login Status 1` `Device Cloud ID 1666840.seetong.com` | ออนไลน์ผ่าน seetong.com |
| **Port Scan** | `80 ✅ (gSOAP/2.8 200 OK)` `554 ✅ (RTSP)` `8000 ❌` | ต่างจาก NUUO ที่ใช้ 8000 |
| **Web UI** | `http://192.168.1.21/` → `IPCConfig v2.0.0.31` ต้อง ActiveX `IPCConfigCtrl` | มีลิงก์ `IPCConfig.exe?version=2.0.0.31.exe` |
| **Tool** | `UC2_4.7_setup.exe` 17.8 MB 2014-01-06 `SHA256 C77BCE7E...` | ย้ายแบบ copy-verify-delete → `cctv/docs/tools/UC2_4.7_setup.exe` |

**สรุป:** พบอุปกรณ์ 2 ระบบใน LAN เดียวกัน — NVR พร้อมใช้งาน + Seetong IPC พร้อม RTSP ต้องให้ Storage Server ดึงทั้งคู่ (ดู `cctv/docs/ip-map.md`)

---

## 2) เป้าหมายโครงการ (Scope)

1.  สร้าง **Server จัดเก็บข้อมูล** แยกจาก NVRmini 2 เพื่อเก็บไฟล์วิดีโอระยะยาว (Retention 14–30 วัน) และเป็นศูนย์กลางดึงสตรีมจาก IPC
2.  เตรียมเชื่อม **IPC (IP Camera)** ผ่าน NVR หรือตรงเข้า Server (ONVIF + RTSP)
3.  ทำให้ดู Live / Playback ย้อนหลัง / Export ได้จาก LAN และ (ถ้าต้องการ) Remote ผ่าน VPN
4.  มีระบบสำรองไฟ, แจ้งเตือน disk failure, และบันทึกการเข้าถึง

**ไม่อยู่ในเฟสนี้:** เปลี่ยนสาย, ติดตั้งกล้องใหม่ — ใช้กล้องเดิมที่ต่อ NVR อยู่ก่อน

---

## 3) สถาปัตยกรรมที่เสนอ (3 ทางเลือก)

```
[IPC 1..N] --(PoE/RTSP/ONVIF)--> [NUUO NVRmini 2 : 192.168.1.31] --+
                                                                |
[IPC ใหม่] --(RTSP)--> [Storage Server : 192.168.1.32*] <--------+
                           |--> NAS/RAID --> SMB/NFS --> Backup USB
                           |--> NVR Software (เลือก 1): Shinobi / Frigate / ZoneMinder / Milestone / Synology Surveillance
                           `--> Viewer: Browser / NUUO Client / VLC
* IP ใหม่ที่ต้องจอง DHCP Reservation ไม่ชน  .31
```

| ทางเลือก | เหมาะเมื่อ | ข้อดี | ข้อเสีย |
|---|---|---|---|
| **A: ใช้ NVRmini 2 เป็นหลัก + เพิ่ม Disk/RAID** | กล้อง ≤16 ตัว, retention สั้น | เร็ว, ไม่ต้องตั้ง server ใหม่ | ขยายยาก, lock-in NUUO |
| **B: สร้าง Storage Server แยก (แนะนำ)** | กล้อง ≥8 ตัว, ต้องการ 30 วัน+, ทำ AI/วิเคราะห์ | ยืดหยุ่น, ใช้ซ้ำได้, แยกภาระ | ต้องลงทุน server + ตั้งค่า |
| **C: Hybrid — NVR บันทึกหลัก, Server ดึงสตรีมสำรอง (Dual Recording)** | ต้องการความมั่นคงสูงสุด | มีสำเนา 2 ชุด | ใช้พื้นที่ x2 |

> **แนะนำทางเลือก B หรือ C** — ตรงกับคำขอ “สร้าง server จัดเก็บข้อมูล”

---

## 4) สเปก Server จัดเก็บ (คำนวณ Storage)

### สูตรคำนวณ
`GB/วัน = (Bitrate Mbps × 3600 × 24 / 8 / 1024) × จำนวนกล้อง × ปัจจัย Motion (0.5–1.0)`

| สมมติฐาน (ปรับได้หน้างาน) | 1080p 4Mbps | 4MP 6Mbps |
|---|---|---|
| 8 กล้อง, H.264, บันทึก 24ชม. | ~337 GB/วัน | ~506 GB/วัน |
| 16 กล้อง, H.264, บันทึก 24ชม. | ~675 GB/วัน | ~1012 GB/วัน |
| ด้วย H.265 ประหยัด ~40% | ~202 GB/วัน (8ch) | ~304 GB/วัน (8ch) |

**ตัวอย่างโจทย์ 16 กล้อง 1080p H.265 เก็บ 30 วัน:**
`~405 GB/วัน × 30 = ~12.1 TB usable` → ต้องดิสก์ **16–20 TB** (เผื่อ RAID + 20% overhead)

### สเปกขั้นต่ำที่เสนอ (B/C)

- **CPU:** Intel i5-12400 / Ryzen 5 5600 ขึ้นไป (รองรับ QuickSync ถ้าจะทำ Transcode)
- **RAM:** 16 GB (32 GB ถ้ารัน Frigate + AI)
- **OS Disk:** 512 GB NVMe (OS + DB)
- **Data Disk:** 4× 6TB NAS HDD (WD Red Plus / Seagate IronWolf) ทำ **RAID5** หรือ **RAID10** (ถ้าเน้นทน)
- **RAID Controller / Software:** mdadm (Linux) หรือ TrueNAS Scale
- **LAN:** 1 Gbps (2.5Gbps ถ้ากล้องเยอะ), PoE Switch แยก VLAN CCTV
- **UPS:** 1000–1500VA Online (ให้รันได้อย่างน้อย 15 นาทีเพื่อ shutdown สะอาด)
- **OS:** Ubuntu Server 22.04 LTS / TrueNAS Scale / Windows Server (เลือกตามถนัด) + Docker
- **Software:** แนะนำ `Shinobi` (ฟรี, ONVIF auto) หรือ `Frigate` (ถ้าต้องการ AI detect) — ดู `cctv/docs/` สำหรับคู่มือ

> ถ้า retention แค่ 14 วัน ใช้ 8TB usable ก็พอ — ลดเหลือ 3×4TB RAID5 ได้

---

## 5) เครือข่ายและการเตรียม IP

```
Router (192.168.1.1) ── PoE Switch (VLAN 10 CCTV) ─┬─ 192.168.1.31 NUUO NVRmini2 (จอง DHCP: 94:de:80:9d:53:f1) :8000
                                                  ├─ 192.168.1.21 Seetong IPC (จอง DHCP: 00:4a:7b:3e:00:61) :80/554 Cloud 1666840.seetong.com
                                                  ├─ 192.168.1.32 Storage Server (จองใหม่) ← ดึง RTSP จากทั้ง .31 และ .21
                                                  └─ 192.168.1.101-150 IPC Pool (เผื่อขยาย)
```

- จอง IP แบบ **Static DHCP Reservation** ทุกตัว (อย่าใช้ Static ที่ตัวกล้องอย่างเดียว กันชน)
- เปิดพอร์ตภายใน: `8000 (NVR web)`, `554 (RTSP)`, `80/443`, `9000 (Shinobi)` — ปิดจาก WAN, ให้เข้า Remote ผ่าน **WireGuard VPN** เท่านั้น
- NTP: ตั้ง NVR + Server + IPC ให้ sync `time.google.com` หรือ `192.168.1.1` เพื่อ timestamp ตรงกัน (สำคัญต่อ Playback)

---

## 6) ขั้นตอนเตรียมเชื่อม IPC (Checklist เชื่อมต่อ)

### 6.1 เตรียมข้อมูลก่อนเชื่อม

- [ ] ขอ **User/Pass ของ NVR** (default `admin/admin` จาก HTML แต่ต้องเปลี่ยนแล้ว) — ถ้าไม่มีให้ reset ผ่าน NUUO tool
- [ ] สำรวจ IPC ทั้งหมด: ยี่ห้อ/รุ่น/IP/RTSP path/ONVIF port (ปกติ `554` และ `80`)
- [ ] บันทึก `MAC → IP → ตำแหน่งกล้อง` ลง `cctv/docs/ip-map.md`
- [ ] เทส `ping` และ `rtsp://user:pass@IP:554/stream1` ด้วย VLC ก่อน

### 6.2 เชื่อมผ่าน NUUO NVRmini 2 (วิธีหลัก)

1. Login `http://192.168.1.31:8000/` → **System → Camera → Add Camera**
2. เลือก `ONVIF` หรือ `Generic RTSP` ใส่ `IP / Port / User / Pass / RTSP URL`
3. ตั้ง **Recording Schedule** = Continuous + Motion, ความละเอียดตามกล้อง
4. ทดสอบ Live View ครบทุกช่อง, เช็ค `SUPPORT_MOTION_RECORDING=true` ทำงาน

### 6.3 เชื่อมตรงเข้า Storage Server (สำรอง/แยกเก็บ)

- ติดตั้ง Shinobi: `docker compose up -d` → Add Monitor → `Input Type: H264 RTSP` → ใส่ URL เดียวกัน
- หรือ Frigate: แก้ `frigate.yml` ใส่ `rtmp/cameras: { camera1: { ffmpeg: { inputs: [{ path: rtsp://... }] } } }`
- เปิด **ONVIF Discovery** (`onvifscan` หรือ `ws-discovery`) เพื่อหา IPC อัตโนมัติ — ดูสคริปต์ `cctv/scripts/onvif_scan.py` (จะสร้างในขั้นตอนถัดไป)

### 6.4 ทดสอบ Playback & Export

- [ ] Live View 64 conn พร้อมกัน (`LIVE_STREAM_MAX_CONN=64` รองรับ)
- [ ] Playback ย้อนหลัง 24 ชม. แต่ละกล้อง
- [ ] Export MP4/AVI แล้วเปิดด้วย VLC ได้
- [ ] ทดสอบดึงไฟล์ผ่าน Server (`/recordings/yyyy-mm-dd/`) และผ่าน NVR web

---

## 7) ความปลอดภัย

- เปลี่ยนรหัส `admin` ทันที, สร้าง user `viewer` สิทธิ์อ่านอย่างเดียวสำหรับ Server ดึงสตรีม
- ปิด `SUPPORT_TRIAL` และ `SUPPORT_LICENSE_TRANSFER` ถ้าไม่ใช้
- เปิด `SUPPORT_HW_LOG` + `SUPPORT_ABNORMAL_DISK_EVENT` ให้ส่งเมล/แจ้งเตือน
- Backup config NVR สม่ำเสมอ → เก็บใน `cctv/output/` และ `business/archive/`
- ไม่เปิดพอร์ต NVR ออกอินเทอร์เน็ตตรง — ใช้ VPN เท่านั้น (ตาม `AGENTS.md` ห้ามนำ secrets เข้า Git)

---

## 8) แผนงาน 5 เฟส (2–3 สัปดาห์)

| เฟส | งาน | ผู้รับผิดชอบ | เวลา | Deliverable |
|---|---|---|---|---|
| **0 — ตรวจสอบซ้ำ** | เทส login NVR, นับกล้องจริง, วัด bitrate, ถ่ายรูปตู้ Rack | ช่างหน้างาน | 1 วัน | `cctv/raw/site-survey-2026-09-07.md` + รูป |
| **1 — จัดซื้อ & เตรียม Server** | สั่ง HDD/NAS, ประกอบ server, ติดตั้ง OS/Docker/UPS, จอง IP .32 | IT | 3–5 วัน | Server พร้อม `ping .32` ได้ |
| **2 — ติดตั้ง Software & Storage** | ตั้ง RAID, สร้าง share, ติดตั้ง Shinobi/Frigate, ตั้ง NTP/Auto-Reboot | IT | 2 วัน | `http://192.168.1.32:8080` ใช้งานได้ |
| **3 — เชื่อม IPC** | Add กล้องเข้า NVR + Server, ตั้ง Schedule/Motion, ทดสอบ VLC/ONVIF | ช่าง + IT | 2–3 วัน | กล้องครบ, Live/Playback ผ่าน |
| **4 — ทดสอบ & ส่งมอบ** | ทดสอบ 48 ชม., วัดพื้นที่/วันจริง, ปรับ retention, อบรมผู้ใช้, ส่งมอบรหัส | ทั้งทีม | 2 วัน | `cctv/output/handover-2026-09-xx.md` + วิดีโอทดสอบ |

**Critical Path:** ต้องได้รหัส NVR ก่อนเริ่มเฟส 3 — ถ้าไม่มีให้เผื่อเวลา reset 1 วัน

---

## 9) สคริปต์ตรวจสอบ (จะวางใน `cctv/scripts/`)

- `check_nvr.ps1` — `Test-NetConnection 192.168.1.31 -Port 8000` + `Invoke-WebRequest` ตรวจ login page (รันไปแล้ว ผลตามข้อ 1)
- `onvif_scan.py` — สแกน `192.168.1.0/24` หา ONVIF device (พอร์ต 80,8000,554)
- `rtsp_test.py` — ลองเปิด RTSP ด้วย `ffmpeg -rtsp_transport tcp -i rtsp://... -t 5 -f null -`
- `storage_calc.py` — คำนวณ GB/วัน ตาม bitrate/กล้อง/retention

> รัน `python verify_system.py` หลังเพิ่มไฟล์ — ต้องคง `ALL PASS`

---

## 10) สิ่งที่ต้องขอจากลูกค้า/หน้างาน ก่อนเริ่มเฟส 1

1.  User/Pass ของ `192.168.1.31:8000` (และของ IPC แต่ละตัวถ้ามี)
2.  จำนวนกล้องจริง + รุ่น + ความละเอียดที่ต้องการ (1080p/4MP) + ระยะเก็บย้อนหลังที่ต้องการ (14/30 วัน?)
3.  มี PoE Switch กี่พอร์ต, ตู้ Rack มีพื้นที่ใส่ Server 2U ไหม, มี UPS แล้วหรือยัง
4.  ต้องการดูผ่านมือถือ/นอกสถานที่ไหม (ถ้าใช่ เตรียม VPN)
5.  งบประมาณคร่าวๆ (Server + HDD 4 ลูก + UPS ประมาณ 35k–60k บาท ขึ้นกับความจุ)

---

## 11) ความเสี่ยงและวิธีลด

| ความเสี่ยง | วิธีลด |
|---|---|
| ลืมรหัส NVR | ใช้ NUUO `NVRmini2 reset tool` หรือขอจากผู้ติดตั้งเดิม |
| IPC คนละยี่ห้อ RTSP ไม่ตรง | เทสด้วย VLC ก่อน, ใช้ ONVIF Device Manager |
| ดิสก์เต็มก่อนกำหนด | ตั้ง Quota + Auto-overwrite + แจ้งเตือน 80% |
| ไฟดับแล้วไฟล์เสีย | UPS + ตั้ง `SUPPORT_AUTO_REBOOT=1` + journaling filesystem (ext4/ZFS) |

---

## 12) ขั้นถัดไป (Action Next 48 ชม.)

- [ ] ยืนยัน User/Pass NVR และจำนวนกล้อง — ใส่ใน `cctv/docs/credentials.md` (ไม่ commit ขึ้น Git ตาม `.gitignore`)
- [ ] รัน `cctv/scripts/onvif_scan.py` สแกนหา IPC ทั้งหมดแล้วเติม `cctv/docs/ip-map.md`
- [ ] ตัดสินใจ Retention (14 vs 30 วัน) เพื่อล็อกสเปก HDD
- [ ] สั่งของเฟส 1 แล้วจอง IP `192.168.1.32` ในเราท์เตอร์

---

**อ้างอิง:** `cctv/checklist.md:1` | `wiki/products/NUUO-Resources.md` | `wiki/products/Seetong-UC2.md` | `cctv/docs/2026-09-07_Seetong-IPC-192.168.1.21-Config.md` | `cctv/docs/ip-map.md` | `NUMBERING-STANDARD.md` | ผลทดสอบ `lighttpd/1.4.48` + `NUUO NVRmini 2 03.11.0000.0005` @ `192.168.1.31:8000` และ `gSOAP/2.8` + Seetong `192.168.1.21` `1666840.seetong.com`
