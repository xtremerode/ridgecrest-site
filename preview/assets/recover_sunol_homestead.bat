@echo off
setlocal enabledelayedexpansion
echo Recovering 3 missing images for sunol-homestead...
echo.
set SERVER=http://147.182.242.54:8081
set TOKEN=35e8bdf6f9cddb3a140a3ac34a9dcb3963c7bff434ef8bd6fedfda70299b13f1
set SLUG=sunol-homestead
set UPLOAD_URL=%SERVER%/admin/api/gallery/%SLUG%/add-image
set TMPDIR=%TEMP%\recover_sunol_homestead
set OK=0
set FAIL=0

if not exist "%TMPDIR%" mkdir "%TMPDIR%"

call :upload ff5b18_76b40b966a2b42968a9901d32b968372
call :upload ff5b18_8f4c22f892d84eaf871e7d7097008ee2
call :upload ff5b18_c196bc18f07846b2965eb7753ce1a32e

echo.
echo Done. %OK% uploaded, %FAIL% failed.
rmdir /s /q "%TMPDIR%" 2>nul
pause
goto :eof

:upload
set HASH=%1
set LOCALFILE=%TMPDIR%\%HASH%_mv2.jpg
echo Downloading %HASH%...
curl.exe -s -L -o "%LOCALFILE%" "https://static.wixstatic.com/media/%HASH%~mv2.jpg"
if not exist "%LOCALFILE%" ( echo   FAILED: download empty & set /a FAIL+=1 & goto :eof )
curl.exe -s -X POST "%UPLOAD_URL%" -H "X-Admin-Token: %TOKEN%" -F "file=@%LOCALFILE%;filename=%HASH%_mv2.jpg;type=image/jpeg"
echo   OK
set /a OK+=1
del "%LOCALFILE%" 2>nul
goto :eof
