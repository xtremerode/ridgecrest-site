@echo off
setlocal enabledelayedexpansion
echo ============================================================
echo Fetch: Pleasanton Custom construction photo (photo 77)
echo Hash: ff5b18_98f97a76f69c41dca1e0ddb7a927be32
echo ============================================================
echo.

set SERVER=http://147.182.242.54:8081
set TOKEN=35e8bdf6f9cddb3a140a3ac34a9dcb3963c7bff434ef8bd6fedfda70299b13f1
set SLUG=pleasanton-custom
set HASH=ff5b18_98f97a76f69c41dca1e0ddb7a927be32
set TMPDIR=%TEMP%\fetch_98f97a76
set UA=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36
set REFERER=https://www.ridgecrestdesigns.com/

if not exist "%TMPDIR%" mkdir "%TMPDIR%"

REM Try .webp first, then .jpg, then .png
set DOWNLOADED=0

echo Trying .webp...
set LOCALFILE=%TMPDIR%\%HASH%_mv2.webp
curl.exe -s -L -o "%LOCALFILE%" ^
    -H "User-Agent: %UA%" ^
    -H "Referer: %REFERER%" ^
    -H "Accept: image/avif,image/webp,image/apng,image/*,*/*;q=0.8" ^
    "https://static.wixstatic.com/media/%HASH%~mv2.webp"
for %%A in ("%LOCALFILE%") do set FSIZE=%%~zA
if exist "%LOCALFILE%" if %FSIZE% GTR 5000 (
    echo   Downloaded .webp: %FSIZE% bytes
    set DOWNLOADED=1
    set FINALFILE=%LOCALFILE%
    set MIMETYPE=image/webp
    set FINALNAME=%HASH%_mv2.webp
    goto :upload
)
if exist "%LOCALFILE%" del "%LOCALFILE%"
echo   .webp failed (size: %FSIZE%)

echo Trying .jpg...
set LOCALFILE=%TMPDIR%\%HASH%_mv2.jpg
curl.exe -s -L -o "%LOCALFILE%" ^
    -H "User-Agent: %UA%" ^
    -H "Referer: %REFERER%" ^
    -H "Accept: image/avif,image/webp,image/apng,image/*,*/*;q=0.8" ^
    "https://static.wixstatic.com/media/%HASH%~mv2.jpg"
for %%A in ("%LOCALFILE%") do set FSIZE=%%~zA
if exist "%LOCALFILE%" if %FSIZE% GTR 5000 (
    echo   Downloaded .jpg: %FSIZE% bytes
    set DOWNLOADED=1
    set FINALFILE=%LOCALFILE%
    set MIMETYPE=image/jpeg
    set FINALNAME=%HASH%_mv2.jpg
    goto :upload
)
if exist "%LOCALFILE%" del "%LOCALFILE%"
echo   .jpg failed (size: %FSIZE%)

echo Trying .png...
set LOCALFILE=%TMPDIR%\%HASH%_mv2.png
curl.exe -s -L -o "%LOCALFILE%" ^
    -H "User-Agent: %UA%" ^
    -H "Referer: %REFERER%" ^
    "https://static.wixstatic.com/media/%HASH%~mv2.png"
for %%A in ("%LOCALFILE%") do set FSIZE=%%~zA
if exist "%LOCALFILE%" if %FSIZE% GTR 5000 (
    echo   Downloaded .png: %FSIZE% bytes
    set DOWNLOADED=1
    set FINALFILE=%LOCALFILE%
    set MIMETYPE=image/png
    set FINALNAME=%HASH%_mv2.png
    goto :upload
)
if exist "%LOCALFILE%" del "%LOCALFILE%"
echo   .png failed (size: %FSIZE%)

echo.
echo FAILED: Could not download image in any format from Wix CDN.
echo This image may have been deleted from the Wix media library.
echo Please check Wix Media Manager manually.
goto :cleanup

:upload
echo.
echo Uploading to server (%SLUG%)...
curl.exe -s -X POST "%SERVER%/admin/api/gallery/%SLUG%/add-image" ^
    -H "X-Admin-Token: %TOKEN%" ^
    -F "file=@%FINALFILE%;filename=%FINALNAME%;type=%MIMETYPE%"
echo.
echo Upload complete.

:cleanup
rmdir /s /q "%TMPDIR%" 2>nul
echo.
pause
