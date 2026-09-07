# Hermes Sentinel WG Auto-Fix - runs at startup, fixes peer key if boot looses handshake
# Gateway pub qmay... is correct, Matebook should peer to it
$peerCorrect='qmayuuUMsQ/Vc8qddbHdtg3JuyG/fBSUT/5KRmrqa18='
$peerOld='cseC7LbFmGMwX2GtwWGX1YPrVwutdH/RZnj0eGpqdHw='
$endpoint='192.168.1.94:51820'
$allowed='10.0.0.0/24'
$wg='C:\Program Files\WireGuard\wg.exe'
$maxWait=60
for ($i=0; $i -lt $maxWait; $i++) {
  Start-Sleep 2
  $adapters = Get-NetAdapter -ErrorAction SilentlyContinue | Where-Object { $_.Name -like '*hotel*' }
  if ($adapters -and ($adapters.Status -contains 'Up')) {
    # tunnel up - try to fix peer
    try {
      & $wg show 2>&1 | Out-Null
      $show = & $wg show 2>&1 | Out-String
      if ($show -match 'qmay') { Write-Host " 00:50:02 WG already correct\; exit 0 }
 # remove old, add correct
 if ($show -match 'cseC') { & $wg set hotel-admin peer $peerOld remove 2>&1 | Out-Null }
 & $wg set hotel-admin peer $peerCorrect allowed-ips $allowed endpoint $endpoint persistent-keepalive 25 2>&1 | Out-Null
 Start-Sleep 1
 $ping = Test-Connection 10.0.0.1 -Count 2 -ErrorAction SilentlyContinue | Measure-Object
 if ($ping.Count -gt 0) { Write-Host \00:50:02 WG fixed handshake ok\; exit 0 }
 } catch {}
 } else {
 # try to activate tunnel via WireGuard UI command if not up - user must have tunnel visible in manager
 # we cannot auto-activate without admin, so just wait
 if ($i % 10 -eq 0) { Write-Host \00:50:02 waiting for hotel-admin adapter...\ }
 }
}
Write-Host \WG auto-fix timeout\
