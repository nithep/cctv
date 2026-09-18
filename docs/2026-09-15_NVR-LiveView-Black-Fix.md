---
type: cctv_fix_report
title: "NVR Live View จอดำ — ตรวจการเข้าถึง + วิธีแก้"
date: 2026-09-15
nvr: 192.168.1.31:8000 NUUO NVRmini 2 fw 03.11.00
status: diagnosed
---

# [Image 1] ดูภาพไม่ได้ — ผลตรวจ + วิธีแก้ (2026-09-15 19:47 ICT)

> ภาพที่ส่งมา: Edge เปิด `192.168.1.31:80..` (โดนตัด) หน้า `Settings | Live View | Playback | Help | Logout`
> `Firmware 03.11.00 / Free 84.6 GB` จอดำ — ตรวจแล้ว **เครื่องปกติ บันทึกปกติ** ปัญหาอยู่ที่ **URL + Browser Plugin**

## 1) สรุปสั้น (อ่านตรงนี้ก่อน)

| ข้อ | ผล |
|---|---|
| NVR ตายไหม | **ไม่ตาย** — `TCP 8000 True`, `HTTP 200 lighttpd/1.4.48`, login `admin/admin → 302 setting.php` ผ่าน |
| กำลังอัดไหม | **อัดอยู่** — `cgi_main?cmd=status&xml=1` = `CH1 192.168.1.21 Connected 10.6fps 3642kbps Record 12`, `DiskFree 88591MB / Total 721079MB` (≈86GB ตรงกับในภาพ 84.6GB) |
| ทำไมจอดำ | **ปกติของรุ่นนี้บน Edge/Chrome ใหม่** — `liveview.php` เรียก `ActiveX NVSWebAll.cab CLSID:1DC4A509...` / `liveview_java.php` เรียก `Java Applet JNLPAppletLauncher` — โดนเบราว์เซอร์เลิกซัพพอร์ตแล้ว เลยดำถึงแม้ login ผ่าน |
| URL ในภาพ | **ผิด/โดนตัด** — พิมพ์แค่ `192.168.1.31:80..` ต้องเป็น `http://192.168.1.31:8000` เต็ม (`:80` ต่อไม่ติด `000`, `:8000` ได้ `200` ทดสอบแล้ว) |
| กล้องอีกตัว | `CH0 HW-33ROBOT30W 192.168.1.2 = Disconnect 0fps` — **หลุด** ต้องเช็คไฟ/สาย/IP นี้ต่างหาก |

## 2) หลักฐานที่ดึงสด (จาก 192.168.1.44)

```
curl http://192.168.1.31:80/   → 000 (ต่อไม่ติด)
curl http://192.168.1.31:8000/ → 200 lighttpd/1.4.48 PHP/7.4.1 NUUO Login
POST login.php user=admin pass=admin → 302 Location: setting.php + PHPSESSID+lang (ผ่าน)
GET ipcam_status.php / setting.php → 200 MaxIPCam 2
GET cgi_main?cmd=status&xml=1 →
  CH0 HW-33ROBOT30W 192.168.1.2  Disconnect 0.0fps 0kbps
  CH1 NK-IP960SP    192.168.1.21 Connected 10.6fps 3642kbps (3307+334) Record 12
  DiskFree 88591 DiskTotal 721079
GET liveview.php → <object CLASSID="CLSID:1DC4... " codebase="NVSWebAll.cab#version=6,1,705,18">
GET liveview_java.php → <applet code="JNLPAppletLauncher" archive="applet-launcher.jar,NpJavaSDK.jar">
```

ไฟล์ดิบที่เซฟไว้: `output/liveview.html`, `output/liveview_java.html`, `output/playback.html` (ดูบรรทัด object/applet ได้)

## 3) วิธีแก้ — ทำตามลำดับ

### A. เปิดให้ถูก URL (1 นาที)
1. ใช้ `http://192.168.1.31:8000` — **ต้องมี `:8000` ครบ** อย่าใช้ `:80` หรือปล่อยให้ Edge ตัด
2. ถ้าขึ้น `ไม่ปลอดภัย / Not secure` — กด `Advanced → Proceed` ได้เลย (NVR รุ่นนี้ไม่มี HTTPS)
3. Login `admin / admin` ต้องเด้งไป `setting.php` ถ้าเด้งกลับ `?cmd=loginfail` = พิมพ์รหัสผิด

### B. ดูภาพให้ถูกวิธี (เลือก 1)
- **วิธีที่ 1 — ดีสุด ไม่พึ่ง browser:** เปิด VLC → `Media → Open Network Stream` → ใส่ `rtsp://admin:123456@192.168.1.21:554/0` (main 1080p) หรือ `/1` (sub 360p ลื่นกว่า) → Play จะเห็นภาพเดียวกับที่ NVR อัด
- **วิธีที่ 2 — ใช้ IE Mode ใน Edge (เฉพาะดูผ่าน NVR):** `Edge Settings → Default browser → Allow IE Mode → Restart` → เปิด `http://192.168.1.31:8000/liveview.php` → `... → Reload in IE Mode` → Allow `NVSWebAll.cab` ครั้งแรก → ดับเบิลคลิกชื่อกล้องในลิสต์ซ้าย
- **วิธีที่ 3 — ใช้บอทที่มีอยู่:** สั่ง Telegram `@hm2569bot` → `/status` (ต้องบอก NVR ok) → `/snapshot` ดูภาพนิ่ง → `/clip 10` ดูย้อนหลัง 10 วิ (ไม่ต้องเปิด browser เลย)
- **อย่าทำ:** ลง Java/ActiveX บน Edge/Chrome ปกติ — ไม่กลับมาแล้ว, อย่าเปิด `:8000` ออกเน็ตตรง (เสี่ยง CVE-2018-1149) ให้ดูนอกบ้านผ่าน WireGuard เท่านั้น

### C. ซ่อมกล้อง CH0 ที่หลุด
- `192.168.1.2 HW-33ROBOT30W Disconnect` → ping `192.168.1.2`, เช็คไฟ/PoE, เช็คสาย, ถ้าเปลี่ยน IP ไปแล้วให้ `Setting → Camera Search` หาใหม่แล้ว Add กลับช่อง 0
- ถ้าไม่ใช้แล้ว → ลบช่อง 0 ออก จะได้ไม่ค้าง Disconnect

## 4) ทำไม Playback ก็อาจดำเหมือนกัน
- `playback.php` ใช้ ActiveX ตัวเดียวกัน, `playback_java.php` ใช้ Java Applet — ดำด้วยเหตุผลเดียวกัน ไม่ใช่ดิสก์เสีย (ดิสก์เหลือ 84-88GB อัดต่อได้)
- วิธีย้อนหลังชัวร์: VLC เปิด RTSP สด + บอท `/clip`, หรือถอด HDD ดูผ่าน NVR โดยตรงเมื่อจำเป็น

## 5) อ้างอิง
- `docs/ip-map.md` — `.31 NVR :8000 / .21 IPC :554`
- `docs/2026-09-08_Config-Test-Report.md` — `admin/admin + admin/123456 /0 /1`
- `output/handover-2026-09-08.md` — ห้ามเปิด 8000 ออก WAN, ดูผ่าน WG
- `output/liveview.html:673` — `CLASSID NVSWebAll.cab`, `output/liveview_java.html:677` — `JNLPAppletLauncher`
