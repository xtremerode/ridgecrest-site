@echo off
setlocal enabledelayedexpansion
echo Recovering 17 missing images for pleasanton-custom...
echo.
set SERVER=http://147.182.242.54:8081
set TOKEN=35e8bdf6f9cddb3a140a3ac34a9dcb3963c7bff434ef8bd6fedfda70299b13f1
set SLUG=pleasanton-custom
set UPLOAD_URL=%SERVER%/admin/api/gallery/%SLUG%/add-image
set TMPDIR=%TEMP%\recover_pleasanton_custom
set OK=0
set FAIL=0

if not exist "%TMPDIR%" mkdir "%TMPDIR%"

call :upload ff5b18_0fa3c6aad5a541438897a84ad6db194d
call :upload ff5b18_385f591edbba4d0ebb97596060f9db25
call :upload ff5b18_43fe86f6054e4fb6b2776bd8276c2da6
call :upload ff5b18_4e102e22b38c4e669a675d6c5ba2828c
call :upload ff5b18_50869659ed3c4e3f8f4c36b7b4beb77b
call :upload ff5b18_570afd436ed440f293e0d8cdbf233680
call :upload ff5b18_5c95484e71be40fcb6fa3488ab329d7e
call :upload ff5b18_636b098f75d949199a33b243fdc28b37
call :upload ff5b18_6cbfed746e2a4b65b782d2bec6fe7e66
call :upload ff5b18_78697f715ddf4082be8e19b6c881328d
call :upload ff5b18_78a43da623c14ffdb482c0c764d51435
call :upload ff5b18_98f97a76f69c41dca1e0ddb7a927be32
call :upload ff5b18_a10f5754a19f4231ae59ea1e426f6aed
call :upload ff5b18_aefe29f6fca140c69d7bdc67db5d3ef5
call :upload ff5b18_c1ce2107fbf04733b33347af25cfaddf
call :upload ff5b18_c5cb0ea7b12844efb50e924af0d95a33
call :upload ff5b18_fdf3242178144df0a5a83686e9cdf70b

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
