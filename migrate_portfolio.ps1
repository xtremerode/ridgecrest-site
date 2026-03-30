# Ridgecrest Designs — Portfolio Image Migration
# Downloads 25 missing project images from Wix CDN and uploads them to the server.
# Run from your laptop (Wix blocks DigitalOcean IPs).
# Usage: powershell -ExecutionPolicy Bypass -File migrate_portfolio.ps1 -Password <admin_pw>
param(
    [Parameter(Mandatory=$true)][string]$Password
)

$SERVER   = "http://147.182.242.54:8081"
$WIX_BASE = "https://static.wixstatic.com/media"
$TOTAL    = 25

$IMAGES = @(
    @{hash="ff5b18_4161051f37ba482fafc49baddabc8a96"; ext="jpg"},
    @{hash="ff5b18_4025b406261e47e8993a0ad777ca3ebe"; ext="jpg"},
    @{hash="ff5b18_938143f6f9374aa88d8ed87d5de5bb73"; ext="jpg"},
    @{hash="ff5b18_e25234795a7a4ed08b1bea59751199a9"; ext="jpg"},
    @{hash="ff5b18_bb1013e8034740828826f718ad2216d9"; ext="png"},
    @{hash="ff5b18_c1637bae333840e4a71cbdaac8405213"; ext="png"},
    @{hash="ff5b18_de2ed75da1a541abb0861b82d04e1135"; ext="png"},
    @{hash="ff5b18_a69a1fba43ec4dd98ec66e582d5ec86f"; ext="png"},
    @{hash="ff5b18_dab676506e77455e942b02a857f21cc3"; ext="jpg"},
    @{hash="ff5b18_f8bf8933487f45db825a713b4ea4c540"; ext="jpg"},
    @{hash="ff5b18_5f016abc7ce04830a7f65e61c2b4a3fa"; ext="jpg"},
    @{hash="ff5b18_e1ef86fee44b4c14b077ecbdb2ca10f5"; ext="png"},
    @{hash="ff5b18_73ddf9ebf03a4477926cbf2283271380"; ext="png"},
    @{hash="ff5b18_f575a25ba7f14e1389d0ae63bb2d356f"; ext="png"},
    @{hash="ff5b18_9a3cb5be52fb466ebd047a075c89ee74"; ext="png"},
    @{hash="ff5b18_7bb937306ca1481894944e9f7b7b64c4"; ext="png"},
    @{hash="ff5b18_8fec027febcb4fdb9a1f34db0e462fac"; ext="png"},
    @{hash="ff5b18_fa64df3266cb4f5687726c7ab5ac76f7"; ext="jpg"},
    @{hash="ff5b18_8534e71718a54408b57038ba0fc8c02f"; ext="jpg"},
    @{hash="ff5b18_349218a966f148919fc38da254ca4619"; ext="jpg"},
    @{hash="ff5b18_29f3aa1ef62549ecbc7c5dd6b4aac717"; ext="jpg"},
    @{hash="ff5b18_c1bace39ccc64636b710dc307c31bb77"; ext="jpg"},
    @{hash="ff5b18_0ab4862750bf42ac8c38304bf1a054ed"; ext="jpg"},
    @{hash="ff5b18_f81286bb193b4eceade91c476d030da2"; ext="png"},
    @{hash="ff5b18_f2d002a1b71342199e013a4389c24d40"; ext="jpg"}
)

Write-Host ""
Write-Host "============================================"
Write-Host " Ridgecrest Designs - Portfolio Migration v5"
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
    # Direct media URL — no transform parameters, more reliable than /v1/fill/
    $wixUrl    = "$WIX_BASE/$wixFile"
    $localName = "$($img.hash)_mv2.$($img.ext)"
    $tempFile  = "$env:TEMP\rdimg_$($img.hash).$($img.ext)"

    Write-Host -NoNewline "[$i/$TOTAL] $localName ... "

    try {
        # curl.exe (real libcurl, not Invoke-WebRequest alias) — reliably sends Referer
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
