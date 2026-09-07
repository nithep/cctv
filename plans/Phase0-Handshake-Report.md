---
type: cctv_report
title: "Phase 0 Handshake — WireGuard hotel-admin สำเร็จ"
date: 2026-09-08 23:45
gateway: 192.168.1.94 hotel-gateway wg0 10.0.0.1/24
client: Matebook D2019 10.0.0.3/24
---

# Phase 0 Handshake สำเร็จ

## ผลตรวจก่อนแก้
- `WireGuardTunnel$hotel-admin Running` `hotel-admin Up 10.0.0.3/24` แต่ `ping 10.0.0.1 100% loss` `transfer 0 B received`
- `hotel-gateway wg0 Up 10.0.0.1/24` `peer 2Ifg...` ไม่ตรงกับ `Matebook pub XGpVc...`
- `Matebook peer cseC7...` ไม่ตรงกับ `Gateway pub qmay...` → Handshake ไม่ติด

## ที่แก้ (แก้คีย์ A)
- **Gateway:** `ssh ecs-agent@192.168.1.94` `sudo sed -i 's|2IfgJ8ORHEr40OEgeKuYkLVS9HeC7SFUCvW6HZXrElo=|XGpVc3pKJnAVNJbsyWQ84tBetWpWNcCxdtH3WwWAfQQ=|' /etc/wireguard/wg0.conf` → `grep Peer` → `XGpVc...` แล้ว `sudo systemctl restart wg-quick@wg0` → `RESTART_OK` `wg show` `peer XGpVc... latest handshake 37s ago`
- **Matebook:** ยกระดับ `wg.exe set hotel-admin peer qmayuuUMsQ/Vc8qddbHdtg3JuyG/fBSUT/5KRmrqa18= allowed-ips 10.0.0.0/24 endpoint 192.168.1.94:51820 keepalive 25` + `remove cseC7...` → `wg show` `peer qmay... latest handshake 12s ago transfer 812 B received`

## ผลหลังแก้
- `ping 10.0.0.1` `Reply 1-3ms TTL64 0% loss` ✅
- `Test-NetConnection 10.0.0.1:3000 TcpTestSucceeded True` ✅ (ผ่าน WG ถึง `hotel-app:3000`)
- `wg show both` `latest handshake 12-37s ago` `transfer 1KiB` ✅
- `Direct LAN 192.168.1.31:8000` ยัง `True` (ไม่กระทบ SNC)
- `Cloudflare WARP Connected` ยังปกติ

## ค้างทำต่อ (ให้ถาวร)
- **Matebook** `hotel-admin.conf.dpapi` ยังเก็บ `cseC7...` แบบเข้ารหัส — `wg set` ที่ทำเป็น **runtime** จะหายเมื่อ `Restart-Service` หรือ reboot — ต้องแก้ถาวร: เปิด `WireGuard → hotel-admin → Edit` → แก้ `Peer Public key` จาก `cseC7LbFmGMwX2GtwWGX1YPrVwutdH/RZnj0eGpqdHw=` → `qmayuuUMsQ/Vc8qddbHdtg3JuyG/fBSUT/5KRmrqa18=` → `Save` → `Activate` ใหม่
- **Gateway** แก้ถาวรแล้ว (`/etc/wireguard/wg0.conf` มี `XGpVc...` แล้ว)

## ขั้นถัดไป Phase 1
- เพิ่ม `/snapshot` `/clip` ใน `bot.py` ให้เรียก `ffmpeg` ผ่าน WG ได้ (ถ้าต้องดูนอกบ้าน)
- ทดสอบยาว 2-3 วันบน Matebook ก่อน Deploy Edge
