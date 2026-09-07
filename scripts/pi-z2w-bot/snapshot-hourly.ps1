while ($true) {
  $ts = Get-Date -Format "yyyy-MM-dd_HH-mm"
  $ff = "C:\Users\Nithep\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffmpeg.exe"
  $out = "C:\Users\Nithep\ไดรฟ์ของฉัน (cnithep@gmail.com)\T.C.Com\cctv\output\snapshot_$ts.jpg"
  & $ff -y -rtsp_transport tcp -i rtsp://admin:123456@192.168.1.21:554/0 -vframes 1 -q:v 2 "$out" 2>&1 | Out-Null
  if (Test-Path "$out") { Write-Host "$(Get-Date -Format HH:mm) snapshot $out $( (Get-Item "$out").Length) bytes" }
  Start-Sleep -Seconds 3600
}
