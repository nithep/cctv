---
type: cctv_plan
title: "Repo Split Plan — แยกรีโป Legacy CCTV ให้แชร์ได้ ใต้ T.C.Com ที่ไม่แชร์"
date: 2026-09-08
status: แผน — รอตัดสินใจก่อนแยก (Skill Legacy-CCTV พร้อมแล้ว)
parent: T.C.Com (private, https://github.com/nithep/T.C.Com) — ไม่แชร์ business/resources
child: legacy-cctv (แนะนำ public/private แชร์ได้, https://github.com/nithep/legacy-cctv)
---

# Repo Split Plan — Legacy CCTV แชร์ได้ ใต้ T.C.Com ที่ไม่แชร์

> ตอบคำถาม: "แชรรีโปนี้ดีไหมแต่ให้อยู่ใต้ tccom ที่ไม่แชร์"
> คำตอบ: **ดี — แต่ต้องแยก git** ไม่งั้น `business/ resources/` ของ T.C.Com จะหลุดไปกับ CCTV

## 1) สถานะปัจจุบัน (2026-09-08)

- `T.C.Com` = private vault (`.gitignore:22 business/ resources/` ไม่ track business)
- โฟลเดอร์ `cctv/` เดิม ถูก rename เป็น `Legacy CCTV/` (มีเว้นวรรค) — git เห็นเป็น `deleted: cctv/...` + `untracked: Legacy CCTV/`
- ไม่มี `.git` ย่อย — ยังอยู่ใต้ parent เดียว
- ถ้า push แบบนี้ `Legacy CCTV/` จะถูก track ใน parent — **แต่จะติดเว้นวรรค + ปนกับ vault**

## 2) ปัญหาชื่อโฟลเดอร์มีเว้นวรรค

| ชื่อ | ปัญหา |
|---|---|
| `Legacy CCTV` | `git submodule add` ลำบาก, path ต้อง quote ทุกครั้ง, `health.py` ต้อง hardcode เว้นวรรค, GitHub URL มี `%20` |
| `legacy-cctv` หรือ `cctv` | มาตรฐาน, ใช้ submodule/subtree ได้ง่าย, GitHub repo ชื่อตรงกัน |

**แนะนำ:** โฟลเดอร์จริงใช้ `legacy-cctv` (kebab, ไม่มีเว้นวรรค) — display name ใน README ใช้ "Legacy CCTV" ได้

## 3) 3 ทางเลือกแชร์ (ใต้ parent ไม่แชร์)

### A) Submodule (แนะนำ — แยก history ชัดเจน)

- `legacy-cctv` เป็น repo แยก (public แชร์ได้)
- Parent `T.C.Com` เก็บแค่ `gitlink` (commit hash) — ไม่เก็บเนื้อหา business
- ต้อง `git submodule update --init` เมื่อ clone parent

```
T.C.Com/                 ← private, https://github.com/nithep/T.C.Com
├── business/            ← .gitignore ไม่แชร์
├── resources/           ← .gitignore ไม่แชร์
├── wiki/                ← curated
├── legacy-cctv/         ← git submodule → https://github.com/nithep/legacy-cctv.git (แชร์ได้)
│   ├── docs/
│   ├── plans/
│   ├── scripts/pi-z2w-bot/
│   └── output/
└── .gitmodules
```

**ข้อดี:** แชร์ได้เต็มที่, history แยก, parent ไม่รั่ว business  
**ข้อเสีย:** ต้องจำ `submodule update`, commit 2 ที่ (child ก่อน parent)

### B) Subtree

```bash
git subtree push --prefix=legacy-cctv legacy-cctv master
```
- history รวมใน parent แต่ push แยก remote ได้
- เหมาะถ้าต้องการ monorepo แต่แชร์บางส่วน

### C) Ignore + Nested Git (ง่ายสุด — ไม่แนะนำระยะยาว)

- เพิ่ม `legacy-cctv/` ใน parent `.gitignore`
- `legacy-cctv/.git` เป็น repo แยก push เอง
- Parent ไม่เห็น child เลย — แต่ git เตือน `nested repo without submodule`

## 4) ขั้นตอนทำ A) Submodule (เมื่อตัดสินใจ)

```bash
# 0. สำรอง & verify
python -X utf8 verify_system.py   # ALL PASS
# 1. ปรับชื่อ (ถ้ายังเป็น Legacy CCTV)
git mv "Legacy CCTV" legacy-cctv
# หรือถ้าต้องการคง cctv เป็นชื่อเทคนิค: git mv "Legacy CCTV" cctv

# 2. สร้าง .gitignore ใน child (legacy-cctv/.gitignore)
#    scripts/pi-z2w-bot/config.yaml
#    scripts/pi-z2w-bot/status.db
#    output/**/*.mp4
#    output/**/*.jpg

# 3. สร้างรีโปเปล่าบน GitHub: github.com/nithep/legacy-cctv (public หรือ private แชร์เฉพาะ)

# 4. ใน child
cd legacy-cctv
git init
git add docs/ plans/ scripts/ output/*.md checklist.md raw/
git commit -m "feat: Hermes Sentinel initial — NVRmini2 + Seetong + YOLO"
git remote add origin https://github.com/nithep/legacy-cctv.git
git branch -M master
git push -u origin master
cd ..

# 5. ใน parent (T.C.Com) — เพิ่ม submodule
git submodule add https://github.com/nithep/legacy-cctv.git legacy-cctv
git commit -m "feat(cctv): add legacy-cctv as submodule (shareable) — HMS-2026-001"
git push

# 6. ตรวจว่า business ไม่หลุด
git -C legacy-cctv ls-files | grep -E "business|resources"  # ต้องว่าง
git check-ignore -v legacy-cctv/scripts/pi-z2w-bot/config.yaml  # ต้อง ignored
```

> ถ้าเลือกคงชื่อ `cctv` ให้ `git submodule add ... cctv` แทน

## 5) Skill ที่รองรับการแยก

สร้างแล้ว: `.agents/skills/Legacy-CCTV/SKILL.md:1`

- รู้จักทั้ง `cctv/`, `Legacy CCTV/`, `legacy-cctv/`
- กฎแชร์อยู่ในหัวข้อ `📂 กฎแชร์รีโป`
- Checklist ก่อนสรุปงานตรวจ `git ls-files | grep business` ต้องว่าง

## 6) สิ่งที่ต้องตัดสินใจ (รอเจ้าของ)

- [ ] จะใช้ชื่อโฟลเดอร์จริงเป็น `legacy-cctv` (แนะนำ) หรือ `cctv` (คงเดิม) หรือ `Legacy CCTV` (คงเว้นวรรค)?
- [ ] จะสร้างรีโปใหม่ชื่อ `legacy-cctv` หรือ `hermes-sentinel`?
- [ ] รีโปใหม่เป็น `public` (แชร์ทั่วไป) หรือ `private` (แชร์เฉพาะคน)?
- [ ] จะเริ่มแยกทันทีหรือรอให้ Phase 5 นิ่งก่อน?

**ตอนนี้:** Skill พร้อม, `rebuild_index.py` รองรับทุกชื่อ, `.gitignore` รองรับทุก path — ยังไม่แยกจริงจนกว่าจะยืนยัน

## 7) ไฟล์เกี่ยวข้อง

- `.agents/skills/Legacy-CCTV/SKILL.md:1`
- `.gitignore:50` — CCTV secrets (3 path)
- `rebuild_index.py:15` — รองรับ 3 ชื่อ
- `Legacy CCTV/output/handover-2026-09-08.md:1`
- `Legacy CCTV/plans/2026-09-08_Master-Execution-Plan.md:1` `Project-Hermes-Sentinel.md:1`
