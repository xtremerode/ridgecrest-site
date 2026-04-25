@echo off
setlocal enabledelayedexpansion
echo Recovering 6 missing images for lafayette-luxury...
echo.
set SERVER=http://147.182.242.54:8081
set TOKEN=35e8bdf6f9cddb3a140a3ac34a9dcb3963c7bff434ef8bd6fedfda70299b13f1
set SLUG=lafayette-luxury
set UPLOAD_URL=%SERVER%/admin/api/gallery/%SLUG%/add-image
set TMPDIR=%TEMP%\recover_lafayette_luxury
set OK=0
set FAIL=0

if not exist "%TMPDIR%" mkdir "%TMPDIR%"

call :upload ff5b18_22620574256243ca8f197a3e9fe27ca1
call :upload ff5b18_2882dd1cc3314d3a9e205861b9fff3f7
call :upload ff5b18_46e606322d7d4ae3bc4cc744a6f688af
call :upload ff5b18_4c364cc11c9944fc83ece24b9c91498a
call :upload ff5b18_c2a04c214cf44ddeb43c9d7c7b58ce47
call :upload ff5b18_dd972afe8737434c9014dcca1624d988

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
