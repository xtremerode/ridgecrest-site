@echo off
setlocal enabledelayedexpansion
echo ============================================================
echo Fetch 3 missing gallery images (Pleasanton Custom + Sierra)
echo ============================================================
echo.

set SERVER=http://147.182.242.54:8081
set TOKEN=35e8bdf6f9cddb3a140a3ac34a9dcb3963c7bff434ef8bd6fedfda70299b13f1
set TMPDIR=%TEMP%\fetch_3_missing
set OK=0
set FAIL=0

if not exist "%TMPDIR%" mkdir "%TMPDIR%"

REM ff5b18_c5cb0ea7 = farmhouse sink close-up (.webp)
REM  appears in: pleasanton-custom (photo 42) AND pleasanton-cottage-kitchen (photo 4)
call :upload_webp pleasanton-custom ff5b18_c5cb0ea7b12844efb50e924af0d95a33
call :upload_webp pleasanton-cottage-kitchen ff5b18_c5cb0ea7b12844efb50e924af0d95a33

REM ff5b18_98f97a76 = construction photo (.webp)
REM  appears in: pleasanton-custom (photo 77)
call :upload_webp pleasanton-custom ff5b18_98f97a76f69c41dca1e0ddb7a927be32

REM ff5b18_238b56fc = Sierra Mountain Ranch photo 61 (.jpg)
REM  appears in: sierra-mountain-ranch (photo 61)
call :upload_jpg sierra-mountain-ranch ff5b18_238b56fc1f4249de936b8f5175e89dba

echo.
echo ============================================================
echo Done. %OK% uploaded OK, %FAIL% failed.
echo ============================================================
rmdir /s /q "%TMPDIR%" 2>nul
pause
goto :eof

:upload_webp
set SLUG=%1
set HASH=%2
set LOCALFILE=%TMPDIR%\%HASH%_mv2.webp
echo [%SLUG%] Downloading %HASH% (.webp)...
curl.exe -s -L -o "%LOCALFILE%" ^
    -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36" ^
    -H "Referer: https://www.ridgecrestdesigns.com/" ^
    "https://static.wixstatic.com/media/%HASH%~mv2.webp"
for %%A in ("%LOCALFILE%") do set FSIZE=%%~zA
if not exist "%LOCALFILE%" ( echo   FAILED: file not created & set /a FAIL+=1 & goto :eof )
if %FSIZE% LSS 1000 ( echo   FAILED: file too small (%FSIZE% bytes^) & del "%LOCALFILE%" & set /a FAIL+=1 & goto :eof )
echo   Downloaded %FSIZE% bytes. Uploading to server...
curl.exe -s -X POST "%SERVER%/admin/api/gallery/%SLUG%/add-image" ^
    -H "X-Admin-Token: %TOKEN%" ^
    -F "file=@%LOCALFILE%;filename=%HASH%_mv2.webp;type=image/webp"
echo   Uploaded to %SLUG%.
set /a OK+=1
del "%LOCALFILE%" 2>nul
goto :eof

:upload_jpg
set SLUG=%1
set HASH=%2
set LOCALFILE=%TMPDIR%\%HASH%_mv2.jpg
echo [%SLUG%] Downloading %HASH% (.jpg)...
curl.exe -s -L -o "%LOCALFILE%" ^
    -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36" ^
    -H "Referer: https://www.ridgecrestdesigns.com/" ^
    "https://static.wixstatic.com/media/%HASH%~mv2.jpg"
for %%A in ("%LOCALFILE%") do set FSIZE=%%~zA
if not exist "%LOCALFILE%" ( echo   FAILED: file not created & set /a FAIL+=1 & goto :eof )
if %FSIZE% LSS 1000 ( echo   FAILED: file too small (%FSIZE% bytes^) & del "%LOCALFILE%" & set /a FAIL+=1 & goto :eof )
echo   Downloaded %FSIZE% bytes. Uploading to server...
curl.exe -s -X POST "%SERVER%/admin/api/gallery/%SLUG%/add-image" ^
    -H "X-Admin-Token: %TOKEN%" ^
    -F "file=@%LOCALFILE%;filename=%HASH%_mv2.jpg;type=image/jpeg"
echo   Uploaded to %SLUG%.
set /a OK+=1
del "%LOCALFILE%" 2>nul
goto :eof
