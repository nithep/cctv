$env:Path += ';C:\Users\Nithep\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin'
Set-Location 'C:\Users\Nithep\ไดรฟ์ของฉัน (cnithep@gmail.com)\T.C.Com'
python -X utf8 cctv/scripts/pi-z2w-bot/bot.py 2>&1 | Tee-Object -Append cctv/output/logs/bot.log
