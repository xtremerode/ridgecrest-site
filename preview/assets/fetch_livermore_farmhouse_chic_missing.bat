@echo off
setlocal enabledelayedexpansion
echo Fetching 49 missing images for livermore-farmhouse-chic...
echo.
set SERVER=http://147.182.242.54:8081
set TOKEN=35e8bdf6f9cddb3a140a3ac34a9dcb3963c7bff434ef8bd6fedfda70299b13f1
set SLUG=livermore-farmhouse-chic
set UPLOAD_URL=%SERVER%/admin/api/gallery/%SLUG%/add-image
set TMPDIR=%TEMP%\livermore-farmhouse-chic_missing
set OK=0
set FAIL=0

if not exist "%TMPDIR%" mkdir "%TMPDIR%"

call :upload ff5b18_fb13d3b2359f78413ad107f355e430f9
call :upload ff5b18_cedd6f07b9b796f7e2c0be46be5621f9
call :upload ff5b18_08d8dac4e3a27c47df39abce050ac573
call :upload ff5b18_bd1d0cb4625ee1b00b7b426e3e976cc7
call :upload ff5b18_8885f7ff92419bcdbff73bf3f37891a7
call :upload ff5b18_58423d1c7470fe24b55a2930c1e06363
call :upload ff5b18_f5e2d1244a02ad4b45bfd23a704d13b1
call :upload ff5b18_5e781097d465071dffb668c0932bd04c
call :upload ff5b18_61ed1991484acd5e2d24ab8a17b41e38
call :upload ff5b18_0b068dee485acd56a83b820cb6a5d347
call :upload ff5b18_693605de9e9e855daff2e291091436b9
call :upload ff5b18_b69750b7a5656f396a626c37446ef852
call :upload ff5b18_5fff38fdf4152a62fd19e5a590fece6d
call :upload ff5b18_772a97f4c6eee15290bbebce936d500a
call :upload ff5b18_f52258a7eee8ad639d64d1d791019e0e
call :upload ff5b18_efc6822c7e7d2c009ad3e6a286b493f2
call :upload ff5b18_4938cae3572722d89b25bba372fd3117
call :upload ff5b18_7e0b347d55f68742f4dff90c64ce2959
call :upload ff5b18_5e3c1469607d174bc87db6fa41ccc6ed
call :upload ff5b18_39bf510f37eee923698067796469b9aa
call :upload ff5b18_ff33e00800168bfe4d94ca4a8ae15e88
call :upload ff5b18_96c341602f7e57faad737ff0523f98be
call :upload ff5b18_6ec165395655f6597c08621eb9142702
call :upload ff5b18_f18c74e8b9a782a3cd5453a12d2174f8
call :upload ff5b18_6f6932b21d975b0f87e3a6a6f78f055d
call :upload ff5b18_5727bc1abe8e393f6be4db8be695bbdd
call :upload ff5b18_95dc5787f236acb1fdc762bc6963e53d
call :upload ff5b18_d51f851b312a561107cdddda2b2d20f0
call :upload ff5b18_02cc34d6974b2f66e9e6c06d1bc66f4e
call :upload ff5b18_d57ecd40640ccf15e5581e4b71e7b383
call :upload ff5b18_e7669e01d1a18a9e0b35b4c23a179412
call :upload ff5b18_e038d4fe950b3e7968bb154c134d7521
call :upload ff5b18_02ec1a01433cf7ae0b117c8ac649fb26
call :upload ff5b18_310b18bcf37b98d909bbb440258d60d1
call :upload ff5b18_99e750b81be6a6c4565ce1bc2d89fcef
call :upload ff5b18_ec6f2d49d7083f3ed43f4fdd76904a8a
call :upload ff5b18_f8e20fd87498b99d6769688c1c3422b0
call :upload ff5b18_a86b72f67a16a526b05787a493aa53b4
call :upload ff5b18_e700a83513d9f58ed050c719702bc661
call :upload ff5b18_6ca95f02fa49ab6316e9560de4333aac
call :upload ff5b18_3574a2d1d31f2c5396d9a95ce661c0cf
call :upload ff5b18_f99126ba9dd29ecfc95b3b52b3942885
call :upload ff5b18_beb1c1e39c354dc958a6a5c25587e09f
call :upload ff5b18_3838ef51caaa71ec287d555db1e167b8
call :upload ff5b18_389c2314b4e8678722c6d8eac8a62e0c
call :upload ff5b18_3c34d4072ce363457f88f86e2bee5338
call :upload ff5b18_0d032d07e3c5dda7f1cdeb864c1ada6c
call :upload ff5b18_e421e99013aa794a231c8774881f9afb
call :upload ff5b18_d3adf5e64eeadf0816739ca2c5f634f2

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