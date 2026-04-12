@echo off
echo ============================================
echo  Ridgecrest Designs - Portfolio Image Fetch
echo ============================================
echo.
echo Downloading migration script...
curl.exe -s -o "%TEMP%\rdmigrate.ps1" "http://147.182.242.54:8081/migrate_portfolio.ps1"
if %errorlevel% neq 0 (
    echo ERROR: Could not download script. Is the server running?
    pause
    exit /b 1
)

echo Verifying script integrity...
rem SHA-256 of migrate_portfolio.ps1 — update this when the script changes
set EXPECTED=1AB1B8AEF06C5D47DC6B1C983D995A1E91C1C517907C25A4DFAF1BC6126CBC7B
for /f "usebackq tokens=*" %%H in (`powershell -NoProfile -Command "(Get-FileHash '%TEMP%\rdmigrate.ps1' -Algorithm SHA256).Hash"`) do set ACTUAL=%%H
if /i not "%ACTUAL%"=="%EXPECTED%" (
    echo.
    echo ERROR: Hash mismatch - script may have been tampered with. Aborting.
    echo Expected: %EXPECTED%
    echo Actual:   %ACTUAL%
    del "%TEMP%\rdmigrate.ps1" 2>nul
    pause
    exit /b 1
)
echo Hash verified OK.
echo.

powershell -ExecutionPolicy Bypass -File "%TEMP%\rdmigrate.ps1"
del "%TEMP%\rdmigrate.ps1" 2>nul
echo.
echo Done. Press any key to close.
pause >nul
