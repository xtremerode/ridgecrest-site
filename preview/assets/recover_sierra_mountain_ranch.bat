@echo off
setlocal enabledelayedexpansion
echo Recovering 31 missing images for sierra-mountain-ranch...
echo.
set SERVER=http://147.182.242.54:8081
set TOKEN=35e8bdf6f9cddb3a140a3ac34a9dcb3963c7bff434ef8bd6fedfda70299b13f1
set SLUG=sierra-mountain-ranch
set UPLOAD_URL=%SERVER%/admin/api/gallery/%SLUG%/add-image
set TMPDIR=%TEMP%\recover_sierra_mountain_ranch
set OK=0
set FAIL=0

if not exist "%TMPDIR%" mkdir "%TMPDIR%"

call :upload ff5b18_027f176ef5824dfd9dd2ec10927937d8
call :upload ff5b18_03276ddc259940a5903b66a52e469ebf
call :upload ff5b18_0a0b79090200416bbdcaf4f290e5a438
call :upload ff5b18_0c7ab3ca9f05426bbf482f451894c984
call :upload ff5b18_0e18906f10654dc0ba18452b1f3058a0
call :upload ff5b18_0f70516a7a444134986fd175ae6fe9d8
call :upload ff5b18_0fbbdc6672dc4670a1085ab8efa49c53
call :upload ff5b18_18f52b35197745c9bc2549a9b11df0c7
call :upload ff5b18_1f6e8bfc396d4a37be3073e6ea40fb49
call :upload ff5b18_33c98f3466814e4a976ed33652eee8f4
call :upload ff5b18_4a07f0b2c2c2446ca526166302209b4b
call :upload ff5b18_4bdf972f19904b6986507296acd5f8ef
call :upload ff5b18_518e99797c404c72ad516ec2ce442c35
call :upload ff5b18_51f670ffcb7145f095e187361dec4807
call :upload ff5b18_53dcd2cb483742e6939bfb9d7af0b7be
call :upload ff5b18_5c95663a38ef4d699337edda083651e3
call :upload ff5b18_64336d36bde0454fa4c961fd447fd810
call :upload ff5b18_6df8f21e414b4271923bcb20df8f5b0e
call :upload ff5b18_72bc4b3302d848c99e406f8ae3a2058f
call :upload ff5b18_938820bd34644e438f3535c5143e00e3
call :upload ff5b18_a547a47c31044674a1e78f28c174315f
call :upload ff5b18_b1978e1190874e24b3e7d2aaac8aa6f6
call :upload ff5b18_b75aa49a6f724236b558d3aa99e4c585
call :upload ff5b18_bf69bc0c11e14d64a4042cd0a34336bb
call :upload ff5b18_c50ed7dd65684c7a813bf8f84ab67c0a
call :upload ff5b18_cfe52d2b2a934112b5f0b39edc31796e
call :upload ff5b18_d2d0371f15a14ebca5f05a4e1844ac8e
call :upload ff5b18_d4e6f6aca0ff4cf89a509ef8e0060e28
call :upload ff5b18_d9158f0dd5f44a28a8d99f3c27776bcd
call :upload ff5b18_ed642f6448b1465fbe185c12d4495fa7
call :upload ff5b18_f8807243cc7c495e92d111a63a2ec9f6

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
