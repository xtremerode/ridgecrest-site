@echo off
echo ============================================
echo  Ridgecrest Designs - Install Browser Deps
echo ============================================
echo.
echo This will SSH into the server and install
echo the system libraries needed for the visual
echo browser (Playwright/Chromium).
echo.
echo Make sure your SSH key is set up for root@147.182.242.54
echo.
pause

echo.
echo Connecting to server and installing dependencies...
echo.
ssh -o StrictHostKeyChecking=accept-new root@147.182.242.54 "apt-get install -y libatk1.0-0 libatk-bridge2.0-0 libcups2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2 2>&1"

if %errorlevel% neq 0 (
    echo.
    echo ERROR: SSH connection failed or install failed.
    echo Check that your SSH key works: ssh root@147.182.242.54
    pause
    exit /b 1
)

echo.
echo Done! Browser dependencies installed.
echo Claude can now use the visual browser to scrape Wix pages.
echo.
pause
