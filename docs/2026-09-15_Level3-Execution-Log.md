---
type: cctv_ops_log
title: "Level 3 Execution Log — 2026-09-15 20:47-20:55"
nvr: 192.168.1.31:8000 NVRmini2 03.11.0000.0005
status: partial-done
---

# Level 3 — ผลดำเนินการ (20:47-20:55 ICT)

## ✅ ที่ทำสำเร็จแล้ว (remote ปลอดภัย)

1. **Export log ย้อนหลัง:**
   - `output/log_20260915_disk.csv` — filter Disk ว่าง (ไม่มี disk event = ดี)
   - `output/log_20260916_all.csv` — มีแต่ User Login จาก 192.168.1.44 (คือเราตรวจเอง)
   - ดึงตรง: `2026-09-15 Recycle started/over x3 (08:44,10:58,14:07)` + `20:37 Start LAN DHCP` + `20:41 Camera2 lost/restored 51วิ`
   - `filter=5 Connection Lost 2026-09-15` = Camera2 หลุด 20:41:00 กลับมา 20:41:51
2. **ย้อนหลังจริง:** `datelog nvs+event` = `20260831-20260916 = 17 วัน` (มากกว่าที่ประเมิน 14-16)
3. **SMART short test Disk2:** สั่ง `smarttest sata1 short` → `ExecuteResult 1 smart test ok` → progress 40% → จบ `previous_test_time 1789505400, progress -1, PASSED` — ค่าเสียเท่าเดิม (184 Abnormal raw8, 188 Warning raw2, 199 CRC 861140, Reallocated/Pending 0) = **ไม่มี sector ตายใหม่**
4. **System health:** `NVR 03.11.0000.0005 / IPCPack 19.10 / CPU Feroceon 17.65% / CPU 39C / Fan 3333rpm Enable / UPS Disable / checkvolume ok`

## ⏸️ ที่ยังไม่ทำ (ต้องหน้างาน — ไม่เสี่ยง remote)

5. **ลบ CH0 (192.168.1.2 Disconnect):** เจอแล้วว่า event config ปัจจุบัน `system event = {} contact = []` = **ไม่มีแจ้งเตือนดิสก์/กล้องหลุดเลย** แต่การลบกล้องต้อง POST `status_update/ipcam setup` ผ่าน form — ถ้าพลาด NVR อาจรีบูต/อัดหยุด → **ให้ทำผ่าน IE Mode หน้างาน: Setting → Camera → เลือก CH0 → Delete**
6. **เปิด E-mail/Push แจ้งดิสก์:** ตอนนี้ `contact list ว่าง` — ต้องใส่ SMTP/เมล์จริง + กด Save (restart service) → **ขอเมล์ผู้รับก่อน แล้วทำหน้างานพร้อมกัน**
7. **Reboot + เช็คสาย SATA:** `handle_reboot_shutdown.php act=reboot&checkdisk=1` ทำ remote ได้แต่ NVR ดับ 2-3 นาที + ถ้าสายหลวมอาจไม่บูต → **ต้องมีคนหน้างานพร้อมเปิดเครื่อง/เสียบสาย แล้วค่อยสั่ง**

## คำสั่งที่รัน (หลักฐาน)
```
login admin/admin → 302 setting.php (หลาย session, session เก่าหมดอายุ ret=3 ต้อง login ใหม่แบบ 3-step: login→setting→api)
event?rand → system {} contact [] push [admin]
exportlog nvs 0915 all → Recycle x3 + DHCP + Cam2 lost/restored
exportlog nvs 0916 → login only
smarttest sata1 short → ok → 40% → PASSED (prev 1789505400)
system_info → 03.11/CPU17%/39C/3333rpm/UPS Disable
raid getvdinfo → VOL1 250GB SAMSUNG + VOL2 500GB Seagate Functional (Free 38008+46812)
status → CH1 3646-3828kbps Connected / CH0 Disconnect / Free 86863
```
