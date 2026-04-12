@echo off
REM Fetch 2 remaining missing images that the server cannot download (Wix CDN blocks server IP)
REM pleasanton-custom: ff5b18_894d7faa27664f35862b420c27f51f57
REM pleasanton-custom: ff5b18_98f97a76f69c41dca1e0ddb7a927be32

set SERVER=http://147.182.242.54:8081
set TOKEN=ea501a45abb967a5fde5feaa14361a230d0eed48bd76a6284d868ab7737e4365
set SLUG=pleasanton-custom

echo === Fetching missing Pleasanton Custom images ===
echo.

REM --- Image 1: ff5b18_894d7faa27664f35862b420c27f51f57 ---
set HASH1=ff5b18_894d7faa27664f35862b420c27f51f57
set TMP1=%TEMP%\%HASH1%_mv2.jpg
echo Downloading %HASH1% ...
curl -L --silent --show-error -o "%TMP1%" "https://static.wixstatic.com/media/%HASH1%_mv2.jpg/v1/fill/w_2048,h_2048,al_c,q_90,enc_auto/%HASH1%_mv2.jpg"
if not exist "%TMP1%" goto try1png
for %%A in ("%TMP1%") do if %%~zA lss 5000 goto try1png
goto upload1
:try1png
curl -L --silent --show-error -o "%TMP1%" "https://static.wixstatic.com/media/%HASH1%_mv2.png/v1/fill/w_2048,h_2048,al_c,q_90,enc_auto/%HASH1%_mv2.png"
if not exist "%TMP1%" goto fail1
for %%A in ("%TMP1%") do if %%~zA lss 5000 goto fail1
:upload1
curl -X POST "%SERVER%/admin/api/gallery/add-image" ^
  -H "X-Admin-Token: %TOKEN%" ^
  -F "slug=%SLUG%" ^
  -F "file=@%TMP1%;type=image/jpeg"
echo.
echo Uploaded %HASH1%
goto next1
:fail1
echo FAILED to download %HASH1% - image may no longer exist on Wix
:next1
echo.

REM --- Image 2: ff5b18_98f97a76f69c41dca1e0ddb7a927be32 ---
set HASH2=ff5b18_98f97a76f69c41dca1e0ddb7a927be32
set TMP2=%TEMP%\%HASH2%_mv2.jpg
echo Downloading %HASH2% ...
curl -L --silent --show-error -o "%TMP2%" "https://static.wixstatic.com/media/%HASH2%_mv2.jpg/v1/fill/w_2048,h_2048,al_c,q_90,enc_auto/%HASH2%_mv2.jpg"
if not exist "%TMP2%" goto try2png
for %%A in ("%TMP2%") do if %%~zA lss 5000 goto try2png
goto upload2
:try2png
curl -L --silent --show-error -o "%TMP2%" "https://static.wixstatic.com/media/%HASH2%_mv2.png/v1/fill/w_2048,h_2048,al_c,q_90,enc_auto/%HASH2%_mv2.png"
if not exist "%TMP2%" goto fail2
for %%A in ("%TMP2%") do if %%~zA lss 5000 goto fail2
:upload2
curl -X POST "%SERVER%/admin/api/gallery/add-image" ^
  -H "X-Admin-Token: %TOKEN%" ^
  -F "slug=%SLUG%" ^
  -F "file=@%TMP2%;type=image/jpeg"
echo.
echo Uploaded %HASH2%
goto done
:fail2
echo FAILED to download %HASH2% - image may no longer exist on Wix
:done
echo.
echo Done. Check: %SERVER%/view/pleasanton-custom.html
pause
