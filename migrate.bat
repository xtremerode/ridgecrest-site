@echo off
echo ============================================
echo  Ridgecrest Designs - Image Migration Tool
echo ============================================
echo.
echo Downloading migration script...
curl.exe -s -o "%TEMP%\migrate_images.py" "http://147.182.242.54:8081/migrate_images.py"
if %errorlevel% neq 0 (
    echo ERROR: Could not download script. Check your internet connection.
    pause
    exit /b 1
)

echo Verifying script integrity...
rem SHA-256 of migrate_images.py — update this when the script changes
set EXPECTED=7B82F847FDE476CA0C32ECE115F82D68DA605221604D0EDF0DC4A87424DA3752
for /f "usebackq tokens=*" %%H in (`powershell -NoProfile -Command "(Get-FileHash '%TEMP%\migrate_images.py' -Algorithm SHA256).Hash"`) do set ACTUAL=%%H
if /i not "%ACTUAL%"=="%EXPECTED%" (
    echo.
    echo ERROR: Hash mismatch - script may have been tampered with. Aborting.
    echo Expected: %EXPECTED%
    echo Actual:   %ACTUAL%
    del "%TEMP%\migrate_images.py" 2>nul
    pause
    exit /b 1
)
echo Hash verified OK.
echo.

echo Running migration...
echo.
python "%TEMP%\migrate_images.py"
del "%TEMP%\migrate_images.py" 2>nul
echo.
echo Done. Press any key to close.
pause >nul
