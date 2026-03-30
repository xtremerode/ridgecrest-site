# Ridgecrest Designs — Portfolio Image Migration
# Downloads 143 missing project images from Wix CDN and uploads them to the server.
# Run from your laptop (Wix blocks DigitalOcean IPs).
# Usage: powershell -ExecutionPolicy Bypass -File migrate_portfolio.ps1 -Password <admin_pw>
param(
    [Parameter(Mandatory=$true)][string]$Password
)

$SERVER   = "http://147.182.242.54:8081"
$WIX_BASE = "https://static.wixstatic.com/media"
$TOTAL    = 143

$IMAGES = @(
    @{hash="ff5b18_02bdae21cf9549b38aecd09306a4842c_mv2"; ext="png"},
    @{hash="ff5b18_037bd402192d4bd19879917e9f9dc7b1_mv2"; ext="jpg"},
    @{hash="ff5b18_068672b4c90e4610b467c3569fda0658_mv2"; ext="jpg"},
    @{hash="ff5b18_09e7d253bf96411a9fe30835cc9ee34b_mv2"; ext="png"},
    @{hash="ff5b18_0b701547bc92489cbf3985cef0ed0275_mv2"; ext="png"},
    @{hash="ff5b18_105d9435292548ff9f61e8cae0711f9f_mv2"; ext="png"},
    @{hash="ff5b18_166b3d9326fb475aa78e1c30e2f70208_mv2"; ext="jpg"},
    @{hash="ff5b18_17b3952b932d497d8734d0ee1254a6b7_mv2"; ext="jpg"},
    @{hash="ff5b18_180583f962c742faaa90d6b0adda3528_mv2"; ext="png"},
    @{hash="ff5b18_1a145219498d4e75a79bbe13d3ab23ae_mv2"; ext="png"},
    @{hash="ff5b18_1b7372e889bd4b6793da6f9a0c159dfb_mv2"; ext="png"},
    @{hash="ff5b18_1d319e46d16c42edb618f929d78be1ce_mv2"; ext="jpg"},
    @{hash="ff5b18_1eda3d15c3f849579ab21c436e0ceb0d_mv2"; ext="jpg"},
    @{hash="ff5b18_1f525ab949e548f39a3a614b47579b62_mv2"; ext="jpg"},
    @{hash="ff5b18_25b92e31b44346549995acfa378ad325_mv2"; ext="jpg"},
    @{hash="ff5b18_265b8cd6595d4ba9a608381a18222fde_mv2"; ext="png"},
    @{hash="ff5b18_2780ac2b8ec84080a5eca2658e4a8f27_mv2"; ext="jpg"},
    @{hash="ff5b18_282f835436004b0d9b5de972e29a5d5f_mv2"; ext="jpg"},
    @{hash="ff5b18_287252fbc1f0474c8c5448c350dcfad2_mv2"; ext="jpg"},
    @{hash="ff5b18_290d185c4a514099b505fa1baa0adcc7_mv2"; ext="jpg"},
    @{hash="ff5b18_29d906c1527b408a99118280841bbd42_mv2"; ext="png"},
    @{hash="ff5b18_2a98f5aa4f384219b7c48068558b230a_mv2"; ext="jpg"},
    @{hash="ff5b18_2b1800ac28b247f98060b77e9034f227_mv2"; ext="png"},
    @{hash="ff5b18_2bff65721a084bfb839c2c52bf19c666_mv2"; ext="png"},
    @{hash="ff5b18_2e1838a06bff4e77960eaba2a20242a5_mv2"; ext="png"},
    @{hash="ff5b18_33d2068cd10941fbad0293bdc73d63d5_mv2"; ext="jpg"},
    @{hash="ff5b18_374f5820e34b4e66992972e7c6124b55_mv2"; ext="jpg"},
    @{hash="ff5b18_3ea2da7dae7046758adcc27e54b5b865_mv2"; ext="jpg"},
    @{hash="ff5b18_3f1b7aa631894aa8b3345db56bc8fdc2_mv2"; ext="png"},
    @{hash="ff5b18_3f272f8928964dc8a4ef4c4100ebcbb9_mv2"; ext="png"},
    @{hash="ff5b18_4115fae529ce4974a6b6ead3ded507a9_mv2"; ext="jpg"},
    @{hash="ff5b18_41d97144818e40e09ddddd7357704009_mv2"; ext="png"},
    @{hash="ff5b18_47b90fee8ee54b1281403a55b433a3d1_mv2"; ext="jpg"},
    @{hash="ff5b18_4b1779cf3392422587cb7f1388175437_mv2"; ext="jpg"},
    @{hash="ff5b18_4d5fdc218b3548c0a2ad0b47802d0ca3_mv2"; ext="png"},
    @{hash="ff5b18_4dbbff9e350e432980cccfc598f0dc7f_mv2"; ext="png"},
    @{hash="ff5b18_4e56d06b0c6e4c80aabe636642bf8346_mv2"; ext="jpg"},
    @{hash="ff5b18_50c83d3193bf45818fc0ba11ae615bed_mv2"; ext="png"},
    @{hash="ff5b18_52079e7283d74abf8837e9acd2730309_mv2"; ext="jpg"},
    @{hash="ff5b18_54560c45e21d46688e1c6ed98ed51d37_mv2"; ext="png"},
    @{hash="ff5b18_55920f3db2594268a5fd35adf593a130_mv2"; ext="jpg"},
    @{hash="ff5b18_56709ef3ab734ab79dac77379f00eb78_mv2"; ext="jpg"},
    @{hash="ff5b18_56b178a8e1854af29fed0a75961a5a6f_mv2"; ext="png"},
    @{hash="ff5b18_56d7f44285954670840a9274a0dcc8dc_mv2"; ext="jpg"},
    @{hash="ff5b18_573d3c0f5dad490897ba75af9370d696_mv2"; ext="jpg"},
    @{hash="ff5b18_5790c7262fb04a25a5f08dc6b385e4c9_mv2"; ext="jpg"},
    @{hash="ff5b18_5843843f2d0141e987c0e96a1e68b6b1_mv2"; ext="jpg"},
    @{hash="ff5b18_5a87c321b5db4ad99b66177a8685ee53_mv2"; ext="png"},
    @{hash="ff5b18_5ab5e51647d5480687a20189d68a382e_mv2"; ext="jpg"},
    @{hash="ff5b18_5ac00492e13c47a9b02bad9e8a10bdae_mv2"; ext="jpg"},
    @{hash="ff5b18_5b2a034ec6cc483baa376f49e147dc08_mv2"; ext="jpg"},
    @{hash="ff5b18_5b8b0ffc05f041c1bac1baa89ee201e3_mv2"; ext="jpg"},
    @{hash="ff5b18_5e380d36f3d64940a665de8a281fe23f_mv2"; ext="jpg"},
    @{hash="ff5b18_5ef00a1c27fa49929b6841b112dedb12_mv2"; ext="png"},
    @{hash="ff5b18_5f782d175d304c39bd1a5a68ecd17837_mv2"; ext="jpg"},
    @{hash="ff5b18_60cc1d030a0345f9842e564e4f3dbeae_mv2"; ext="jpg"},
    @{hash="ff5b18_60dcea6c584443c786986468f367b604_mv2"; ext="jpg"},
    @{hash="ff5b18_65d7e65ebe3942c38054df7a5eba4302_mv2"; ext="jpg"},
    @{hash="ff5b18_66c5153a1ec44adab9d8603f0eceec8f_mv2"; ext="jpg"},
    @{hash="ff5b18_672125820d5a46069583b4cc0f2a6335_mv2"; ext="jpg"},
    @{hash="ff5b18_6851d4154ba84f9d9fecc60cf88f9ad5_mv2"; ext="jpg"},
    @{hash="ff5b18_689c82335590480bab8687093b788f39_mv2"; ext="png"},
    @{hash="ff5b18_6a5a8b093a7d4ec1bfb1eddf7fe753b4_mv2"; ext="jpg"},
    @{hash="ff5b18_6b774e563986424c88cb4a867ddbcfa3_mv2"; ext="jpg"},
    @{hash="ff5b18_6c49c91ca5d1455f9d9035d0a4cc3a4a_mv2"; ext="jpg"},
    @{hash="ff5b18_6ce3779e8542406db45d54ee9e8a9d33_mv2"; ext="jpg"},
    @{hash="ff5b18_6e14ea0a4cdd4f5c88885680df88f8af_mv2"; ext="png"},
    @{hash="ff5b18_727f447718cc420c89065988a2d0f818_mv2"; ext="png"},
    @{hash="ff5b18_76ec6d9dbc3b4d29ab02bc08c56cf7e5_mv2"; ext="png"},
    @{hash="ff5b18_789d474d6d0149eea64b9629dc7a9d7b_mv2"; ext="jpg"},
    @{hash="ff5b18_7afabe08804f4547850b618be2d91ae6_mv2"; ext="png"},
    @{hash="ff5b18_7c54ccfe90ad4065ae0f0aa063a629e4_mv2"; ext="jpg"},
    @{hash="ff5b18_7d9860cd5e234283aebffeff9b4bfbc9_mv2"; ext="png"},
    @{hash="ff5b18_7e7176ba86d043e7a79be3fcd53aa7c0_mv2"; ext="png"},
    @{hash="ff5b18_7f1d04c690b0453fbb22aaf1d443dc76_mv2"; ext="jpg"},
    @{hash="ff5b18_8263a2cdc43a4f9d9f5b0b6945039c77_mv2"; ext="png"},
    @{hash="ff5b18_831537efc37e4610adff9f8e982c8039_mv2"; ext="jpg"},
    @{hash="ff5b18_8439227c1cde4a3f8687607a2b2d7282_mv2"; ext="jpg"},
    @{hash="ff5b18_88c5c1ca33004b5bb5be4c9d6cdfa968_mv2"; ext="jpg"},
    @{hash="ff5b18_8987814f88814d3aaf441bd83b524f9d_mv2"; ext="jpg"},
    @{hash="ff5b18_8ae6f73e058844489a19f7cb714ddf51_mv2"; ext="jpg"},
    @{hash="ff5b18_8d194ec65ece42e1a9a046dacdd67157_mv2"; ext="jpg"},
    @{hash="ff5b18_8d75523812e941f2a37fafd4d1f65557_mv2"; ext="jpg"},
    @{hash="ff5b18_8f94e57d36c84799bacb3aec32cd1418_mv2"; ext="png"},
    @{hash="ff5b18_92fd4a14ebbe454eadd6715a9ccf6053_mv2"; ext="jpg"},
    @{hash="ff5b18_933c6fe0073f459dba6c4f077fd9704a_mv2"; ext="png"},
    @{hash="ff5b18_9549cbaddd59469e8c0e7335fb83fcd3_mv2"; ext="jpg"},
    @{hash="ff5b18_972295aeee794eb793ab8d1c9f066f0c_mv2"; ext="jpg"},
    @{hash="ff5b18_9722b896c36d42cf8a61833d4caa389f_mv2"; ext="jpg"},
    @{hash="ff5b18_9ad5ceb2247b4dbfb5382b6cd47974e8_mv2"; ext="jpg"},
    @{hash="ff5b18_9cd0d8a66b364c1ea15c032acb7da0cc_mv2"; ext="png"},
    @{hash="ff5b18_a0ebb85eb6174c0eb286208f5bf564ca_mv2"; ext="png"},
    @{hash="ff5b18_a466dbb965e94f008c62bfb48a04ab21_mv2"; ext="png"},
    @{hash="ff5b18_a6a474bf0bef4095af1c07f5505da43f_mv2"; ext="png"},
    @{hash="ff5b18_a74c7ef598444446bb8d03653c3328e8_mv2"; ext="png"},
    @{hash="ff5b18_a7c7f26a79b44b539bd15ec69632c520_mv2"; ext="jpg"},
    @{hash="ff5b18_a99b2d9dbfe04a39a3aee368c065c00c_mv2"; ext="jpg"},
    @{hash="ff5b18_a9a4054d937b4d2f87b68ae86f8e6505_mv2"; ext="jpg"},
    @{hash="ff5b18_ada0f19a57c548ea93ead7ed89a8b568_mv2"; ext="jpg"},
    @{hash="ff5b18_af3d4948b1c349bcaf72ebff882f4ad6_mv2"; ext="png"},
    @{hash="ff5b18_b15ebdc0b69a4cdb902a74bf1a0e1c72_mv2"; ext="jpg"},
    @{hash="ff5b18_b651e8713e0749368367a9e5e840fa55_mv2"; ext="jpg"},
    @{hash="ff5b18_b81ad19e857d4e99b57edf295d8732b7_mv2"; ext="jpg"},
    @{hash="ff5b18_b8e188bd228f4ea990fd6c1c7120140f_mv2"; ext="png"},
    @{hash="ff5b18_bcd726fa503f41e8ae32288d50273c8e_mv2"; ext="jpg"},
    @{hash="ff5b18_bd546d2e47244fdcbda2e0bf2e07c43d_mv2"; ext="png"},
    @{hash="ff5b18_bee090a1db814d60844aed6337fc984d_mv2"; ext="png"},
    @{hash="ff5b18_bff1a21d68894b1485619571dec937c1_mv2"; ext="jpg"},
    @{hash="ff5b18_c1c8fff952dd4e6d878c60e6d6117d56_mv2"; ext="png"},
    @{hash="ff5b18_c520c9ca384d4c3ebe02707d0c8f45ab_mv2"; ext="jpg"},
    @{hash="ff5b18_cac57df9732942439511bdf23455bae9_mv2"; ext="png"},
    @{hash="ff5b18_cbf6c17a98f949e19d6969e9e377f278_mv2"; ext="png"},
    @{hash="ff5b18_cd0bbd1ca0924ba38e0578501a1958ec_mv2"; ext="jpg"},
    @{hash="ff5b18_cd5a5fdbf7ed4b23b03a9a3e7533e051_mv2"; ext="png"},
    @{hash="ff5b18_d0f8c15054d7404ab39b2e48dd2c4610_mv2"; ext="jpg"},
    @{hash="ff5b18_d21a6cfecad9421bb43dbd6d1a63828f_mv2"; ext="jpg"},
    @{hash="ff5b18_d4a890f899554194b71163ed3228ad40_mv2"; ext="jpg"},
    @{hash="ff5b18_d61183070b3b4e2f856f0c271ae55b5a_mv2"; ext="png"},
    @{hash="ff5b18_d6990ae171234dd1bbd4ca896c45c0c0_mv2"; ext="jpg"},
    @{hash="ff5b18_da172978dd76485a9d179ca34d1c936b_mv2"; ext="jpg"},
    @{hash="ff5b18_dd853c2703794d2b930b3be2a8fc483f_mv2"; ext="jpg"},
    @{hash="ff5b18_de323270e3574f2582de93c63a85e584_mv2"; ext="png"},
    @{hash="ff5b18_deb303a4cdf1412291032c4e55be8128_mv2"; ext="png"},
    @{hash="ff5b18_e5a7d0e7216249bfbb6fbebba64021a8_mv2"; ext="png"},
    @{hash="ff5b18_e611e808bcca468690b28ccea00566f3_mv2"; ext="jpg"},
    @{hash="ff5b18_e73241a2a89840e8b828d1a604830f17_mv2"; ext="jpg"},
    @{hash="ff5b18_e770197d24e4436aae7c1c05d9d07a62_mv2"; ext="jpg"},
    @{hash="ff5b18_e9017ba51d1544b789d5add8c4ecc484_mv2"; ext="jpg"},
    @{hash="ff5b18_ec34ac50f5ed421b8914a9ed0c9d168e_mv2"; ext="jpg"},
    @{hash="ff5b18_ecc34a03656549caa7e8d6ee648480dc_mv2"; ext="jpg"},
    @{hash="ff5b18_ef18abb4037848e3b75100bef53ef666_mv2"; ext="png"},
    @{hash="ff5b18_ef43f9ef1b89406a8ed43208ece970c8_mv2"; ext="jpg"},
    @{hash="ff5b18_ef630f1a109d4f1aa6e918307c0e02a6_mv2"; ext="png"},
    @{hash="ff5b18_ef9b9e4c9e8048c0b21b0d5ad19143b3_mv2"; ext="jpg"},
    @{hash="ff5b18_f2d3db3381af451ebbb7ce65d407c99b_mv2"; ext="jpg"},
    @{hash="ff5b18_f38f6e2f56dc45948213c61e22ae354a_mv2"; ext="jpg"},
    @{hash="ff5b18_f399ea12bfd842d48f6f1a70f5c199bc_mv2"; ext="jpg"},
    @{hash="ff5b18_f406990c34ad4a039524b10579cc5295_mv2"; ext="png"},
    @{hash="ff5b18_f9b4f2ba1f81409a86985fabcbbea3be_mv2"; ext="png"},
    @{hash="ff5b18_fa07e12f600447eb9ef4801fa17bf8bc_mv2"; ext="png"},
    @{hash="ff5b18_fa6237e022fb42d5812a4e932b054bee_mv2"; ext="jpg"},
    @{hash="ff5b18_fc8284a96978430ba265e928d858b15d_mv2"; ext="png"},
    @{hash="ff5b18_ff725c980f7a43dcb69904fdbc47bd24_mv2"; ext="png"}
)

Write-Host ""
Write-Host "============================================"
Write-Host " Ridgecrest Designs - Portfolio Migration v6"
Write-Host "  143 gallery images across 16 projects"
Write-Host "============================================"
Write-Host ""

# Verify curl.exe is available (built into Windows 10 1803+)
$curlPath = (Get-Command curl.exe -ErrorAction SilentlyContinue)?.Source
if (-not $curlPath) {
    Write-Host "ERROR: curl.exe not found. Please run from Windows 10 (1803+) or install curl." -ForegroundColor Red
    exit 1
}
Write-Host "Using curl.exe: $curlPath"
Write-Host "Downloading $TOTAL images from Wix CDN..."
Write-Host ""

$ok   = 0
$fail = 0
$i    = 0

foreach ($img in $IMAGES) {
    $i++
    $wixFile   = "$($img.hash)~mv2.$($img.ext)"
    # Direct media URL — no transform parameters
    $wixUrl    = "$WIX_BASE/$wixFile"
    $localName = "$($img.hash).$($img.ext)"
    $tempFile  = "$env:TEMP\rdimg_$($img.hash).$($img.ext)"

    Write-Host -NoNewline "[$i/$TOTAL] $localName ... "

    try {
        # curl.exe with Referer header — required to bypass Wix hotlink protection
        $curlResult = & curl.exe -s -L -f `
            --referer "https://www.ridgecrestdesigns.com/" `
            -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36" `
            -H "Accept: image/avif,image/webp,image/apng,image/*,*/*;q=0.8" `
            -H "Accept-Language: en-US,en;q=0.9" `
            -o $tempFile `
            $wixUrl
        $exitCode = $LASTEXITCODE

        if ($exitCode -ne 0 -or -not (Test-Path $tempFile) -or (Get-Item $tempFile).Length -lt 1000) {
            # Fallback: try with /v1/fill/ transform URL
            $wixUrlFallback = "$WIX_BASE/$wixFile/v1/fill/w_1920,h_1280,al_c,q_90,enc_avif,quality_auto/$wixFile"
            & curl.exe -s -L -f `
                --referer "https://www.ridgecrestdesigns.com/" `
                -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36" `
                -H "Accept: image/avif,image/webp,image/apng,image/*,*/*;q=0.8" `
                -H "Accept-Language: en-US,en;q=0.9" `
                -o $tempFile `
                $wixUrlFallback | Out-Null
        }

        if (-not (Test-Path $tempFile) -or (Get-Item $tempFile).Length -lt 1000) {
            throw "Download failed or file too small (likely error page)"
        }

        $bytes = [System.IO.File]::ReadAllBytes($tempFile)
        Remove-Item $tempFile -Force

        # Base64 encode and upload to server
        $b64    = [Convert]::ToBase64String($bytes)
        $body   = @{ token = $Password; filename = $localName; data = $b64 } | ConvertTo-Json -Depth 3
        $result = Invoke-RestMethod -Uri "$SERVER/media/receive" -Method Post -Body $body -ContentType "application/json"

        if ($result.ok) {
            $kb = [math]::Round($bytes.Length / 1024)
            Write-Host "OK ($kb KB)" -ForegroundColor Green
            $ok++
        } else {
            Write-Host "UPLOAD ERROR: $($result.error)" -ForegroundColor Red
            $fail++
        }
    } catch {
        if (Test-Path $tempFile) { Remove-Item $tempFile -Force }
        Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
        $fail++
    }

    Start-Sleep -Milliseconds 200
}

Write-Host ""
Write-Host "Done: $ok downloaded, $fail failed." -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Yellow" })
if ($ok -gt 0) {
    Write-Host "Images saved to server. WebP versions will be generated automatically." -ForegroundColor Cyan
}
Write-Host ""
