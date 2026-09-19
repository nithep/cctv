#!/usr/bin/env python3
"""ตรวจ policy ของ repo cctv (public repo) ก่อน merge/push — ใช้ stdlib + git เท่านั้น

Usage: python3 scripts/check_repo_policy.py [--quiet]

ตรวจ 5 ด้าน:
  1. Python ทุกไฟล์ใต้ scripts/ ต้อง compile ผ่าน (py_compile — ไม่ต้องลง dependency)
  2. ไฟล์ที่ "ห้าม track" ต้องไม่ถูก track: config.yaml, status.db, *.log, .env*, output artifact, *.pt,
     ไฟล์ credential/password
  3. ไฟล์เหล่านั้นต้องถูก .gitignore จริง (git check-ignore) — กัน secret หลุดขึ้น public
  4. สแกน secret pattern ในไฟล์ที่ track (ghp_…, github_pat_…, AKIA…, PRIVATE KEY, Telegram bot token)
  5. ไฟล์คู่มือบังคับต้องอยู่ครบ และ config.yaml.example ต้องเป็น placeholder (มี CHANGE_ME)

Exit: 0 = ผ่านทุกข้อ, 1 = พบปัญหา (แสดงทุกรายการ)
"""

from __future__ import annotations

import py_compile
import re
import subprocess
import sys
from pathlib import Path

# ให้ log ไทย/emoji ทำงานได้ทั้งบน CI (UTF-8) และคอนโซล Windows ที่ codepage เก่า (เช่น cp874)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # pragma: no cover - บาง stream ไม่รองรับ
        pass

REPO = Path(__file__).resolve().parent.parent
REQUIRED_FILES = (
    "README.md",
    "LICENSE",
    ".gitignore",
    "checklist.md",
    "scripts/pi-z2w-bot/README.md",
    "scripts/pi-z2w-bot/bot.py",
    "scripts/pi-z2w-bot/health.py",
    "scripts/pi-z2w-bot/person_detect.py",
    "scripts/pi-z2w-bot/cctv-bot.service",
    "scripts/pi-z2w-bot/config.yaml.example",
)
# ไฟล์/ไดเรกทอรีที่ต้องไม่ถูก track และต้องถูก gitignore
FORBIDDEN_TRACKED = (
    re.compile(r"scripts/pi-z2w-bot/config\.yaml$"),
    re.compile(r"scripts/pi-z2w-bot/status\.db$"),
    re.compile(r"\.log$"),
    re.compile(r"(^|/)\.env($|\.)"),
    re.compile(r"^output/.*\.(mp4|jpg|jpeg|png|avi|mov)$"),
    re.compile(r"\.pt$"),
    re.compile(r"credential", re.IGNORECASE),
    re.compile(r"(password|passwd)", re.IGNORECASE),
)
MUST_BE_IGNORED = (
    "scripts/pi-z2w-bot/config.yaml",
    "scripts/pi-z2w-bot/status.db",
    "scripts/pi-z2w-bot/bot.log",
    ".env",
    "output/demo_nvr/clip.mp4",
    "output/person/person.jpg",
    "yolov8n.pt",
)
SECRET_PATTERNS = (
    ("github-personal-token", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    ("github-fine-grained-token", re.compile(r"github_pat_[A-Za-z0-9_]{20,}")),
    ("aws-access-key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private-key-block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("telegram-bot-token", re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b")),
)

problems: list[str] = []


def fail(message: str) -> None:
    problems.append(message)


def git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)


def tracked_files() -> list[str]:
    result = git(["ls-files"])
    if result.returncode != 0:
        fail(f"เรียก git ls-files ไม่ได้: {result.stderr.strip()}")
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def check_required_files() -> None:
    for name in REQUIRED_FILES:
        if not (REPO / name).is_file():
            fail(f"ขาดไฟล์ที่ต้องมีใน repo: {name}")


def check_python_syntax() -> None:
    seen = 0
    for path in sorted((REPO / "scripts").rglob("*.py")):
        if any(part in {"venv", ".venv", "__pycache__"} for part in path.parts):
            continue
        seen += 1
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            first_line = (exc.msg or str(exc)).splitlines()[0]
            fail(f"{path.relative_to(REPO)} compile ไม่ผ่าน: {first_line}")
    if seen == 0:
        fail("ไม่พบไฟล์ .py ใต้ scripts/ ให้ตรวจเลย")


def check_tracked_policy(files: list[str]) -> None:
    for name in files:
        for pattern in FORBIDDEN_TRACKED:
            if pattern.search(name):
                fail(f"ไฟล์ต้องห้ามถูก track: {name} (ตรงกับ pattern '{pattern.pattern}')")
                break


def check_ignored() -> None:
    for path in MUST_BE_IGNORED:
        if git(["check-ignore", "-q", path]).returncode != 0:
            fail(f".gitignore ยังไม่ได้กัน {path} — เสี่ยงหลุดขึ้น public repo")


def check_secrets(files: list[str]) -> None:
    for name in files:
        path = REPO / name
        if not path.is_file() or path.stat().st_size > 1_000_000:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(text):
                fail(f"พบ secret pattern '{label}' ในไฟล์ที่ track: {name} (ให้ใช้ placeholder + rotate ค่าเดิม)")


def check_example_placeholders() -> None:
    path = REPO / "scripts/pi-z2w-bot/config.yaml.example"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8", errors="ignore")
    if "CHANGE_ME" not in text:
        fail("config.yaml.example ต้องใช้ค่า placeholder (CHANGE_ME) ไม่ใช่ค่าจริง")
    for label, _pattern in SECRET_PATTERNS:
        if _pattern.search(text):
            fail(f"config.yaml.example ต้องไม่มีค่าจริง (พบ '{label}')")


def main() -> int:
    quiet = "--quiet" in sys.argv[1:]
    check_required_files()
    check_python_syntax()
    files = tracked_files()
    check_tracked_policy(files)
    check_ignored()
    check_secrets(files)
    check_example_placeholders()

    if problems:
        print("❌ ตรวจ policy ไม่ผ่าน:", file=sys.stderr)
        for item in problems:
            print(f"   - {item}", file=sys.stderr)
        return 1
    if not quiet:
        print(f"🔍 ตรวจ {len(files)} tracked files + python ใต้ scripts/ ใน {REPO}")
    print("✅ ผ่านทุกข้อ — python compile ได้ · ไม่มี secret ขึ้น public · gitignore กันไฟล์อ่อนไหวครบ")
    return 0


if __name__ == "__main__":
    sys.exit(main())