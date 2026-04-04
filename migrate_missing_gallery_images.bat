@echo off
echo ============================================
echo  Ridgecrest Designs - Missing Gallery Images
echo ============================================
echo.
echo Downloading migration script...
curl.exe -s -o "%TEMP%\rdmig_gallery.ps1" "http://147.182.242.54:8081/migrate_missing_gallery_images.ps1"
if %errorlevel% neq 0 (
    echo ERROR: Could not download script. Is the server running?
    pause
    exit /b 1
)

echo Verifying script integrity...
rem SHA-256 of migrate_missing_gallery_images.ps1 — update this when the script changes
set EXPECTED=55526BCB2D6B69FB11EB30EF3C498DD5AFC6B1912B2D6CF00321B4497662401A
for /f "usebackq tokens=*" %%H in (`powershell -NoProfile -Command "(Get-FileHash '%TEMP%\rdmig_gallery.ps1' -Algorithm SHA256).Hash"`) do set ACTUAL=%%H
if /i not "%ACTUAL%"=="%EXPECTED%" (
    echo.
    echo ERROR: Hash mismatch - script may have been tampered with. Aborting.
    echo Expected: %EXPECTED%
    echo Actual:   %ACTUAL%
    del "%TEMP%\rdmig_gallery.ps1" 2>nul
    pause
    exit /b 1
)
echo Hash verified OK.
echo.

powershell -ExecutionPolicy Bypass -File "%TEMP%\rdmig_gallery.ps1"
del "%TEMP%\rdmig_gallery.ps1" 2>nul
echo.
echo Done. Press any key to close.
pause >nul
