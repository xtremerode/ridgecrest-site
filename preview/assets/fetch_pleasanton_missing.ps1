# fetch_pleasanton_missing.ps1
# Downloads 66 missing Pleasanton Custom images from Wix and uploads to our server
# Run on Henry's laptop: powershell -ExecutionPolicy Bypass -File fetch_pleasanton_missing.ps1

$SERVER = "http://147.182.242.54:8081"
$TOKEN  = "35e8bdf6f9cddb3a140a3ac34a9dcb3963c7bff434ef8bd6fedfda70299b13f1"
$SLUG   = "pleasanton-custom"
$UPLOAD_URL = "$SERVER/admin/api/gallery/$SLUG/add-image"

$HASHES = @(
  "ff5b18_fb13d3b2359f78413ad107f355e430f9",
  "ff5b18_f5e2d1244a02ad4b45bfd23a704d13b1",
  "ff5b18_08d8dac4e3a27c47df39abce050ac573",
  "ff5b18_bd1d0cb4625ee1b00b7b426e3e976cc7",
  "ff5b18_8885f7ff92419bcdbff73bf3f37891a7",
  "ff5b18_58423d1c7470fe24b55a2930c1e06363",
  "ff5b18_5e781097d465071dffb668c0932bd04c",
  "ff5b18_61ed1991484acd5e2d24ab8a17b41e38",
  "ff5b18_0b068dee485acd56a83b820cb6a5d347",
  "ff5b18_693605de9e9e855daff2e291091436b9",
  "ff5b18_b69750b7a5656f396a626c37446ef852",
  "ff5b18_5fff38fdf4152a62fd19e5a590fece6d",
  "ff5b18_772a97f4c6eee15290bbebce936d500a",
  "ff5b18_f52258a7eee8ad639d64d1d791019e0e",
  "ff5b18_efc6822c7e7d2c009ad3e6a286b493f2",
  "ff5b18_4938cae3572722d89b25bba372fd3117",
  "ff5b18_7e0b347d55f68742f4dff90c64ce2959",
  "ff5b18_5e3c1469607d174bc87db6fa41ccc6ed",
  "ff5b18_39bf510f37eee923698067796469b9aa",
  "ff5b18_ff33e00800168bfe4d94ca4a8ae15e88",
  "ff5b18_96c341602f7e57faad737ff0523f98be",
  "ff5b18_6ec165395655f6597c08621eb9142702",
  "ff5b18_f18c74e8b9a782a3cd5453a12d2174f8",
  "ff5b18_6f6932b21d975b0f87e3a6a6f78f055d",
  "ff5b18_5727bc1abe8e393f6be4db8be695bbdd",
  "ff5b18_95dc5787f236acb1fdc762bc6963e53d",
  "ff5b18_d51f851b312a561107cdddda2b2d20f0",
  "ff5b18_02cc34d6974b2f66e9e6c06d1bc66f4e",
  "ff5b18_d57ecd40640ccf15e5581e4b71e7b383",
  "ff5b18_e7669e01d1a18a9e0b35b4c23a179412",
  "ff5b18_cedd6f07b9b796f7e2c0be46be5621f9",
  "ff5b18_e038d4fe950b3e7968bb154c134d7521",
  "ff5b18_02ec1a01433cf7ae0b117c8ac649fb26",
  "ff5b18_310b18bcf37b98d909bbb440258d60d1",
  "ff5b18_99e750b81be6a6c4565ce1bc2d89fcef",
  "ff5b18_ec6f2d49d7083f3ed43f4fdd76904a8a",
  "ff5b18_f8e20fd87498b99d6769688c1c3422b0",
  "ff5b18_a86b72f67a16a526b05787a493aa53b4",
  "ff5b18_e700a83513d9f58ed050c719702bc661",
  "ff5b18_6ca95f02fa49ab6316e9560de4333aac",
  "ff5b18_3574a2d1d31f2c5396d9a95ce661c0cf",
  "ff5b18_f99126ba9dd29ecfc95b3b52b3942885",
  "ff5b18_beb1c1e39c354dc958a6a5c25587e09f",
  "ff5b18_3838ef51caaa71ec287d555db1e167b8",
  "ff5b18_389c2314b4e8678722c6d8eac8a62e0c",
  "ff5b18_3c34d4072ce363457f88f86e2bee5338",
  "ff5b18_0d032d07e3c5dda7f1cdeb864c1ada6c",
  "ff5b18_e421e99013aa794a231c8774881f9afb",
  "ff5b18_d3adf5e64eeadf0816739ca2c5f634f2",
  "ff5b18_98f97a76f69c41dca1e0ddb7a927be32",
  "ff5b18_4161051f37ba482fafc49baddabc8a96",
  "ff5b18_50869659ed3c4e3f8f4c36b7b4beb77b",
  "ff5b18_570afd436ed440f293e0d8cdbf233680",
  "ff5b18_6cbfed746e2a4b65b782d2bec6fe7e66",
  "ff5b18_0fa3c6aad5a541438897a84ad6db194d",
  "ff5b18_78a43da623c14ffdb482c0c764d51435",
  "ff5b18_c1ce2107fbf04733b33347af25cfaddf",
  "ff5b18_5c95484e71be40fcb6fa3488ab329d7e",
  "ff5b18_aefe29f6fca140c69d7bdc67db5d3ef5",
  "ff5b18_fdf3242178144df0a5a83686e9cdf70b",
  "ff5b18_a10f5754a19f4231ae59ea1e426f6aed",
  "ff5b18_385f591edbba4d0ebb97596060f9db25",
  "ff5b18_78697f715ddf4082be8e19b6c881328d",
  "ff5b18_636b098f75d949199a33b243fdc28b37",
  "ff5b18_4e102e22b38c4e669a675d6c5ba2828c",
  "ff5b18_43fe86f6054e4fb6b2776bd8276c2da6"
)

$tmpDir = "$env:TEMP\pleasanton_missing"
New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null

# Verify curl.exe is available
if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) {
  Write-Host "ERROR: curl.exe not found. Please update Windows 10 or install curl." -ForegroundColor Red
  exit 1
}

$ok = 0; $fail = 0; $skip = 0; $i = 0
foreach ($hash in $HASHES) {
  $i++
  $wixUrl    = "https://static.wixstatic.com/media/${hash}~mv2.jpg"
  $localName = "${hash}_mv2.jpg"
  $localFile = "$tmpDir\$localName"

  Write-Host "[$i/$($HASHES.Count)] $hash" -NoNewline

  # Download from Wix using curl.exe
  $dlResult = curl.exe -s -L -o $localFile $wixUrl -w "%{http_code}" 2>$null
  if ($dlResult -ne "200") {
    Write-Host " DOWNLOAD FAILED (HTTP $dlResult)" -ForegroundColor Red
    $fail++
    continue
  }

  $fileSize = (Get-Item $localFile -ErrorAction SilentlyContinue).Length
  if (-not $fileSize -or $fileSize -lt 5000) {
    Write-Host " EMPTY ($fileSize bytes)" -ForegroundColor Yellow
    $fail++
    continue
  }

  # Upload to server using curl.exe -F (reliable multipart)
  $response = curl.exe -s `
    -X POST $UPLOAD_URL `
    -H "X-Admin-Token: $TOKEN" `
    -F "file=@$localFile;filename=$localName;type=image/jpeg" `
    2>$null

  if ($response -match '"ok"\s*:\s*true') {
    $countMatch = [regex]::Match($response, '"gallery_count"\s*:\s*(\d+)')
    $count = if ($countMatch.Success) { $countMatch.Groups[1].Value } else { "?" }
    Write-Host " OK (gallery: $count)" -ForegroundColor Green
    $ok++
  } elseif ($response -match 'already in gallery') {
    Write-Host " SKIPPED (already exists)" -ForegroundColor Gray
    $skip++
  } else {
    Write-Host " UPLOAD FAILED: $response" -ForegroundColor Red
    $fail++
  }

  Remove-Item $localFile -Force -ErrorAction SilentlyContinue
  Start-Sleep -Milliseconds 300
}

Write-Host ""
Write-Host "Done. $ok uploaded, $skip skipped (already existed), $fail failed." -ForegroundColor Cyan
Remove-Item -Recurse -Force $tmpDir -ErrorAction SilentlyContinue
