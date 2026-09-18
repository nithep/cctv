---
type: cctv_report
title: "NVR เป็น File Server ได้ไหม — ตรวจจริง + ทางเลือก"
date: 2026-09-15 21:05 ICT
nvr: 192.168.1.31 NVRmini2 fw 03.11.00
status: verified-live
---

# NVR เป็นที่เก็บ+แชร์ไฟล์ได้ไหม — ตอบ: ได้บางส่วน แต่ไม่แนะนำ

## 1) ผลตรวจสด (21:00)

| บริการ | สถานะ | หลักฐาน |
|---|---|---|
| **FTP Server (port 21)** | ✅ เปิดอยู่ `Enable` `port 21 pasv 1024-65535` | `ftp_setup query → Enable`; login `admin/admin` เห็น `VOLUME1 VOLUME2` |
| ไฟล์วิดีโอ | ✅ เข้าถึงได้ | `VOLUME1/VIDEODATA/20260915/C00001/12/C00001A...dat` (ไฟล์ `.dat` ราย ~5 นาที/ชั่วโมงละ ~12 ไฟล์) + `C00001.rcd/record.log/RecordSequence_2.ini`; `VOLUME2` มี `20260903-20260914` |
| **Windows Share (SMB/CIFS port 445/139)** | ✅ เครื่องมี แต่ ❌ ปิดอยู่ | `samba_setup query → Disable ComName NVR Workgroup WORKGROUP`; `Test 445/139 False` — เปิดได้แต่ไม่ควร (ดูข้อ 3) |
| พื้นที่ว่างรวม | ~84GB (VOL1 free 37916 + VOL2 free 46812 MB) | `getsysinfo` — เก็บไฟล์ทั่วไปได้นิดหน่อย แต่จะเบียดที่อัดวิดีโอ (Recycle จะลบของเก่าเร็วขึ้น) |
| Auto-Archive | มี (`ftp_settings.php` = ส่งออกไป FTP นอก ไม่ใช่รับไฟล์เข้า) | ใช้สำรองวิดีโอออกไป NAS/PC ได้ ไม่ใช่เอาไฟล์ทั่วไปมาฝาก |

## 2) ถ้าจะใช้ชั่วคราว (ไม่แก้ config — ใช้ของที่มีเลย)

- **ดึงคลิปย้อนหลังผ่าน FTP (แนะนำ):** `FileZilla → Host 192.168.1.31 Port 21 User admin Pass admin → /VOLUME1/VIDEODATA/<yyyymmdd>/C00001/<hh>/xxx.dat` โหลด `.dat` มาเปิดด้วย **VLC** (ลากไฟล์ใส่ได้เลย) หรือให้บอท `/clip` แปลงให้
- **โครงไฟล์:** `VIDEODATA/<วัน>/C00001/<ชั่วโมง 00-23>/*.dat` = กล้อง CH1; `Record2/` = กล้องอีกช่อง/record สำรอง; `RecordSequence_2.ini + *.rcd + record.log` = ดัชนี (อย่าลบ/แก้)
- **ห้าม:** อัปโหลด/สร้างโฟลเดอร์/ลบไฟล์ผ่าน FTP — จะทำให้ดัชนีพัง + Recycle คำนวณพลาด + เสี่ยงบูตไม่ขึ้น; FTP ไม่มีเข้ารหัส ส่งรหัสเป็น plain text ใน LAN พอรับได้ ห้ามเปิดออกเน็ต

## 3) ทำไมไม่ควรเปิด SMB / ฝากไฟล์ทั่วไปบน NVR

1. **CPU อ่อน (Feroceon 800MHz-class, load 17% ตอนอัดกล้องเดียว)** — เปิด Samba + มีคน copy ไฟล์ใหญ่จะกระตุก/เฟรมหาย/Recycle ถี่
2. **ดิสก์แก่ไม่มีสำรอง:** Disk1 250GB SMART UNKNOWN, Disk2 500GB มีแผล 184/188 + RAID0 ลูกละ volume พังลูกไหนหายลูกนั้น — เอาไฟล์งานมาฝาก = เสี่ยงหายคู่กับวิดีโอ
3. **SMBv1 เก่า:** fw 2020 แชร์ด้วย SMB1 ที่ Windows 10/11 ปิดโดย default + มีช่องโหว่ (WannaCry-class) — ต้องลด security client ลงมาต่อ
4. **พื้นที่เบียด:** ไฟล์ฝากทุก GB ไปแย่งที่อัด → ประวัติ 17 วันหดทันที

## 4) ทางที่ถูก (แนะนำ)

- **ใช้ NVR เก็บวิดีโออย่างเดียวต่อไป** + ดึงออกผ่าน **FTP (อ่านอย่างเดียว)** หรือบอท `/clip /snapshot`
- **ไฟล์งานทั่วไป → แยกเครื่อง:** Matebook `.44` แชร์โฟลเดอร์ / NAS / USB เสียบเราเตอร์ `.1` — ถูกกว่าและไม่เสี่ยงวิดีโอหาย
- ถ้าจำเป็นต้องแชร์วิดีโอให้หลายคนดู: เปิด **Samba แบบ Read-Only ชั่วคราว** หน้างาน (`Protocol → Windows → Enable → Workgroup เดียวกับ PC → \\192.168.1.31\VOLUME1`) ดูเสร็จ **ปิดกลับ Disable** ทันที — อย่าเปิดค้าง + อย่าเปิดออก WAN (CVE-2018-1149 + SMB)
- สำรองยาว: ตั้ง **Auto-Archive (FTP Settings)** ส่ง `.dat` ไป NAS/PC อัตโนมัติ แล้วค่อยแชร์จากตรงนั้น

## คำสั่งที่รัน
```
samba_setup query → Disable NVR/WORKGROUP; ftp_setup query → Enable 21/1024-65535
Test 445/139 False; Test 21 True
ftp / → VOLUME1 VOLUME2; /VOLUME1 → VIDEODATA; /VOLUME1/VIDEODATA → 20260831-20260916
/20260915/C00001/ → 00-23; /12/ → C00001A*.dat ~12 ไฟล์/ชม
getsysinfo → VOL1 free 37916 + VOL2 free 46812
```
