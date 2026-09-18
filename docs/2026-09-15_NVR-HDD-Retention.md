---
type: cctv_disk_report
title: "NVR HDD 2 ลูก + ย้อนหลังได้กี่วัน"
date: 2026-09-15 20:30 ICT
nvr: 192.168.1.31:8000 NUUO NVRmini2 fw 03.11.00
status: verified-live
---

# HDD 2 ลูก + ดูย้อนหลังได้กี่วัน (ตรวจสด 2026-09-15 20:27)

## 1) ตอบสั้น

- **ย้อนหลังมี ~14-16 วัน** (อัด `Always` กล้องเดียว `CH1 .21` ~3.7 Mbps กิน ~40GB/วัน ของเก่าค้างอยู่ ~604GB)
- **เหลือที่ว่าง ~83-85GB ใช้ได้อีก ~2 วันแล้ววนทับ** (AutoRecycle 10% วนลบของเก่าสุดอัตโนมัติ ไม่ต้องลบเอง)
- ถ้าซ่อม `CH0 .2` กลับมาอัด 2 กล้อง = กิน ~80GB/วัน → **เหลือย้อนหลังแค่ ~8-9 วัน** และที่ว่างจะหมดใน ~1 วัน
- **ดิสก์ 2 ลูกยัง Functional ทั้งคู่ แต่แก่ + ไม่ปลอดภัย (RAID0 ลูกละ volume ไม่มีสำรอง):**
  - Disk1 250GB SAMSUNG อ่าน SMART ไม่ได้ (UNKNOWN) — เสี่ยงสุด
  - Disk2 500GB Seagate SMART = PASSED แต่มี `End-to-End Error = Abnormal` + `Command Timeout = Warning` — ควรเปลี่ยน

## 2) สถานะดิสก์สดจาก `cgi_system?cmd=raid_setup&act=getvdinfo/getsysinfo`

| Volume | RAID | ดิสก์ | รุ่น / FW / SN | ความจุ (bytes) | Free / Used (MB) | สถานะ |
|---|---|---|---|---|---|---|
| VOLUME1 `/dev/md0` | RAID0 (ดิสก์เดียว!) | Disk1 `/dev/nuuo_sata0` | ATA SAMSUNG HD253GJ / 1AJ1 / S24JJ9DZ601932 (250GB รุ่นปี 2009) | 250058113024 (~232GiB) | Free 38660 / Used 196068 (~37/191GB) | Functional, Failed 0, Activity none |
| VOLUME2 `/dev/md1` | RAID0 (ดิสก์เดียว!) | Disk2 `/dev/nuuo_sata1` | ATA ST500DM002-1BD14 / KC44 / W2A2W5R5 (500GB รุ่นปี 2012) | 500106788864 (~465GiB) | Free 46812 / Used 422640 (~45/412GB) | Functional, Failed 0, Activity none |
| รวม NVR | — | 2 bays เต็ม (HwRaid 0) | — | ~750GB raw / 715413MB usable | Free ~85476MB (~83.5GB ตรงกับหน้าเวป 84.6GB) / Used ~88% | `checkvolume ok` |

> หมายเหตุ: `RAID0 DiskCount 1` = ไม่ได้ทำ mirror/striping จริง แค่แยก volume ละลูก **ลูกไหนพัง ข้อมูล volume นั้นหายหมด** + `DisksInfo` ว่าง = ไม่มี spare

### SMART (`act=getsmartinfo`)

- **Disk1 SAMSUNG:** `DiskHealth UNKNOWN`, `Test -1`, ไม่มี Attribute ส่งกลับ — แปลว่า controller อ่าน SMART ลูกนี้ไม่ได้ (ดิสก์เก่า/ไม่รองรับ passthrough/ใกล้เสีย) **ห้ามไว้ใจลูกนี้**
- **Disk2 Seagate:** `DiskHealth PASSED`, Temp 35C Good (Airflow 65/45) แต่:
  - `184 End to End Error = Abnormal raw 8 value 92 < threshold 99` — เคยมี error ปลายทาง 8 ครั้ง
  - `188 Command Timeout = Warning raw 2` — คำสั่งค้าง 2 ครั้ง
  - `187 Reported Uncorrectable raw 0x19f (415)` — เยอะ ควรเฝ้า
  - `199 UDMA CRC raw 0xd26cc (861140)` — สาย SATA/ขั้วมี error สะสม (ลองเปลี่ยนสาย SATA)
  - `9 Power-On 0x22dc (8924 ชม.) / 12 PowerCycle 854 / 4 StartStop 849 / 5 Reallocated 0 / 197-198 Pending/Offline 0` — ยังไม่มี sector ตาย แต่เปิดมาเยอะ

## 3) ย้อนหลังได้กี่วัน (คำนวณจาก bitrate จริง)

โหมดอัด (`cgi_main?cmd=recordingmode_xml`): `Mode Always Camera1=1 Camera2=1 AutoRecycle=1 @10% KeepDays=0 (ปิด = วนทับไม่จำกัดวัน)`

บิตเรตสด (`cgi_main?cmd=status`): `CH1 Connected 10.8fps 3723kbps (3387+336) / CH0 Disconnect 0kbps`

```
1 กล้อง (ตอนนี้): 3723 kbps /8*86400 = ~40.2 GB/วัน (~37.4 GiB/วัน)
ของที่เก็บอยู่ ~618708MB (~604GB) /40.2 = ~15 วัน ← นี่คือที่ Playback ย้อนไปได้ตอนนี้
ที่ว่าง 85476MB (~83.5GB) /40.2 = ~2.1 วัน แล้วเริ่มทับของเก่าสุด
ความจุรวม 704180MB /40.2 = ~17.5 วัน คือเพดานสูงสุดถ้าอัดกล้องเดียวตลอด

ถ้า 2 กล้อง (ซ่อม CH0 กลับมา ~7.4Mbps): กิน ~80GB/วัน
→ ประวัติเหลือ ~7-8 วัน, ที่ว่างหมดใน ~1 วัน
```

### วิธีดูว่าเก่าสุดถึงวันไหน (ชัวร์สุด)
NVR รุ่นนี้ไม่มี API ถามวันเก่าสุด ต้องดูปฏิทินใน Playback:
`IE Mode → http://192.168.1.31:8000/playback_java.php → Open Record (ไอคอนกล่อง) → ปฏิทินวันที่มีสี/กดได้ = มีไฟล์` — ควรเห็นย้อนไป ~ต้นเดือน ก.ย. ถ้าเห็นน้อยกว่านี้แปลว่าบางวันกล้องหลุด/ไฟดับ

## 4) ต้องทำอะไร

1. **ด่วน: Backup + เตรียมเปลี่ยนดิสก์** — ลูกไหนก็พังได้โดยไม่มี mirror; อย่า Create/Delete/Format RAID เอง (ข้อมูลหาย) — ถอด/โคลนเมื่อมีลูกใหม่เท่านั้น
2. **เช็คสาย SATA Disk2** (CRC 8แสน) — ปิดเครื่อง ถอดเสียบสายใหม่/เปลี่ยนเส้น
3. **เปิด SMART Test แบบ Short ตอนไม่บันทึก:** `RAID Management → เลือก Disk2 → SMART Short (~60นาที)` อย่ากดตอนกำลังอัด (โค้ด `raid.js` เตือน recording อยู่)
4. **ถ้าอยากเก็บนานขึ้น:** ลดบิตเรตกล้อง `.21` ลง (เช่น 1080p 12fps → 720p / CBR 2048kbps จะได้ ~22GB/วัน → เก็บได้ ~30 วัน) ที่ `Setting → Camera → Mainstream`
5. **อย่าเปิด KeepDays** ถ้าไม่จำเป็น — ตอนนี้ `KeepDays 0 + AutoRecycle 10%` ถูกต้องแล้ว (เก็บนานสุดเท่าที่ดิสก์มี)

## อ้างอิงคำสั่งที่รัน
```
cgi_main?cmd=status&xml=1 → CH1 Connected 3723kbps / DiskFree 87494 DiskTotal 721079
cgi_main?cmd=recordingmode_xml → Always / AutoRecycle 1/10% / KeepDays 0
cgi_system?cmd=raid_setup&act=getsysinfo/getvdinfo → VOLUME1 250GB + VOLUME2 500GB Functional
cgi_system?cmd=raid_setup&act=getsmartinfo sata0 → UNKNOWN / sata1 → PASSED+Abnormal184
cgi_system?cmd=raid_setup&act=getfreecapacity → total 715413 free 85476
cgi_system?cmd=system_machine → HwRaid 0 Bay 2
```
