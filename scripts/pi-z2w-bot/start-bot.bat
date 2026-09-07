@echo off
set FFMPEG=C:\Users\Nithep\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin
set PATH=%PATH%;%FFMPEG%
python -X utf8 cctv\scripts\pi-z2w-bot\bot.py >> cctv\output\logs\bot.log 2>&1
