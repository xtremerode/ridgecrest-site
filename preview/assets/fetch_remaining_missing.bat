@echo off
setlocal enabledelayedexpansion
echo Fetching 4 remaining missing images (Sunol Homestead + Pleasanton Cottage Kitchen)...
echo.

set SERVER=http://147.182.242.54:8081
set TOKEN=35e8bdf6f9cddb3a140a3ac34a9dcb3963c7bff434ef8bd6fedfda70299b13f1
set TMPDIR=%TEMP%\remaining_missing
set OK=0
set FAIL=0

if not exist "%TMPDIR%" mkdir "%TMPDIR%"

call :upload sunol-homestead ff5b18_8f4c22f892d84eaf871e7d7097008ee2
call :upload sunol-homestead ff5b18_76b40b966a2b42968a9901d32b968372
call :upload sunol-homestead ff5b18_c196bc18f07846b2965eb7753ce1a32e
call :upload pleasanton-cottage-kitchen ff5b18_c5cb0ea7b12844efb50e924af0d95a33

echo.
echo Done. %OK% uploaded, %FAIL% failed.
rmdir /s /q "%TMPDIR%" 2>/dev/null
pause
goto :eof

:upload
set SLUG=%1
set HASH=%2
set LOCALFILE=%TMPDIR%\%HASH%_mv2.jpg
echo [%SLUG%] Downloading %HASH%...
curl.exe -s -L -o "%LOCALFILE%" "https://static.wixstatic.com/media/%HASH%~mv2.jpg"
if not exist "%LOCALFILE%" (
  echo   FAILED: download empty
  set /a FAIL+=1
  goto :eof
)
curl.exe -s -X POST "%SERVER%/admin/api/gallery/%SLUG%/add-image" -H "X-Admin-Token: %TOKEN%" -F "file=@%LOCALFILE%;filename=%HASH%_mv2.jpg;type=image/jpeg"
echo   OK
set /a OK+=1
del "%LOCALFILE%" 2>/dev/null
goto :eof
