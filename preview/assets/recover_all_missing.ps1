# recover_all_missing.ps1
# Recovers 37 missing gallery images from Wix CDN using Referer header bypass.
# Must run from Henry's laptop — Wix CDN blocks DigitalOcean server IPs.
# Usage: right-click > Run with PowerShell  (or: powershell -ExecutionPolicy Bypass -File recover_all_missing.ps1)

$SERVER   = "http://147.182.242.54:8081"
$TOKEN    = "35e8bdf6f9cddb3a140a3ac34a9dcb3963c7bff434ef8bd6fedfda70299b13f1"
$WIX_BASE = "https://static.wixstatic.com/media"

$images = @(
    # ── Sierra Mountain Ranch (31) ── all jpg
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_027f176ef5824dfd9dd2ec10927937d8_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_03276ddc259940a5903b66a52e469ebf_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_0a0b79090200416bbdcaf4f290e5a438_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_0c7ab3ca9f05426bbf482f451894c984_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_0e18906f10654dc0ba18452b1f3058a0_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_0f70516a7a444134986fd175ae6fe9d8_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_0fbbdc6672dc4670a1085ab8efa49c53_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_18f52b35197745c9bc2549a9b11df0c7_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_1f6e8bfc396d4a37be3073e6ea40fb49_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_33c98f3466814e4a976ed33652eee8f4_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_4a07f0b2c2c2446ca526166302209b4b_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_4bdf972f19904b6986507296acd5f8ef_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_518e99797c404c72ad516ec2ce442c35_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_51f670ffcb7145f095e187361dec4807_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_53dcd2cb483742e6939bfb9d7af0b7be_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_5c95663a38ef4d699337edda083651e3_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_64336d36bde0454fa4c961fd447fd810_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_6df8f21e414b4271923bcb20df8f5b0e_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_72bc4b3302d848c99e406f8ae3a2058f_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_938820bd34644e438f3535c5143e00e3_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_a547a47c31044674a1e78f28c174315f_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_b1978e1190874e24b3e7d2aaac8aa6f6_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_b75aa49a6f724236b558d3aa99e4c585_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_bf69bc0c11e14d64a4042cd0a34336bb_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_c50ed7dd65684c7a813bf8f84ab67c0a_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_cfe52d2b2a934112b5f0b39edc31796e_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_d2d0371f15a14ebca5f05a4e1844ac8e_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_d4e6f6aca0ff4cf89a509ef8e0060e28_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_d9158f0dd5f44a28a8d99f3c27776bcd_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_ed642f6448b1465fbe185c12d4495fa7_mv2"; ext="jpg" },
    @{ slug="sierra-mountain-ranch"; hash="ff5b18_f8807243cc7c495e92d111a63a2ec9f6_mv2"; ext="jpg" },
    # ── Pleasanton Custom (2) ── jpg
    @{ slug="pleasanton-custom"; hash="ff5b18_98f97a76f69c41dca1e0ddb7a927be32_mv2"; ext="jpg" },
    @{ slug="pleasanton-custom"; hash="ff5b18_c5cb0ea7b12844efb50e924af0d95a33_mv2"; ext="jpg" },
    # ── Orinda Kitchen (3) ── png
    @{ slug="orinda-kitchen"; hash="ff5b18_4b19847e3cf14ecfb78313bac274f651_mv2"; ext="png" },
    @{ slug="orinda-kitchen"; hash="ff5b18_ad29115ec24b4bbaa33893ed164199cf_mv2"; ext="png" },
    @{ slug="orinda-kitchen"; hash="ff5b18_b2c6186a71644039b5e9854f48df0d7f_mv2"; ext="png" },
    # ── Pleasanton Cottage Kitchen (1) ── png
    @{ slug="pleasanton-cottage-kitchen"; hash="ff5b18_56956b7fa72d450998718343281c35e4_mv2"; ext="png" }
)

$TempDir = Join-Path $env:TEMP "rdrecover_$([System.Guid]::NewGuid().ToString('N').Substring(0,8))"
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

Write-Host ""
Write-Host "=== Ridgecrest Image Recovery ===" -ForegroundColor Cyan
Write-Host "Recovering $($images.Count) missing images from Wix CDN..."
Write-Host ""

$ready  = [System.Collections.ArrayList]@()
$failed = [System.Collections.ArrayList]@()

foreach ($img in $images) {
    $hash    = $img.hash
    $ext     = $img.ext
    $wixHash = $hash -replace "_mv2$", ""
    $wixUrl  = "$WIX_BASE/$($wixHash)~mv2.$ext"
    $outFile = Join-Path $TempDir "$hash.$ext"

    Write-Host "  $($img.slug) / $hash ... " -NoNewline

    try {
        $wc = New-Object System.Net.WebClient
        $wc.Headers.Add("Referer",    "https://www.ridgecrestdesigns.com/")
        $wc.Headers.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        $wc.DownloadFile($wixUrl, $outFile)
        $size = (Get-Item $outFile).Length
        if ($size -lt 1000) {
            Write-Host "BLOCKED ($size bytes - Wix 403)" -ForegroundColor Red
            Remove-Item $outFile -Force -ErrorAction SilentlyContinue
            $null = $failed.Add($hash)
        } else {
            Write-Host "OK ($([math]::Round($size/1024))KB)" -ForegroundColor Green
            $null = $ready.Add(@{ img=$img; path=$outFile })
        }
    } catch {
        Write-Host "ERROR - $($_.Exception.Message)" -ForegroundColor Red
        $null = $failed.Add($hash)
    }
}

Write-Host ""
Write-Host "Downloaded $($ready.Count)/$($images.Count). Uploading to server..." -ForegroundColor Yellow
Write-Host ""

$LF    = "`r`n"
$added = 0

foreach ($entry in $ready) {
    $img      = $entry.img
    $hash     = $img.hash
    $ext      = $img.ext
    $slug     = $img.slug
    $mimeType = if ($ext -eq "png") { "image/png" } else { "image/jpeg" }
    $boundary = "boundary" + [System.Guid]::NewGuid().ToString("N")

    Write-Host "  Uploading $slug / $hash.$ext ... " -NoNewline

    $fileBytes = [System.IO.File]::ReadAllBytes($entry.path)
    $hdrStr    = "--$boundary$LF" +
                 "Content-Disposition: form-data; name=`"file`"; filename=`"$hash.$ext`"$LF" +
                 "Content-Type: $mimeType$LF$LF"
    $hdrBytes  = [System.Text.Encoding]::UTF8.GetBytes($hdrStr)
    $tailBytes = [System.Text.Encoding]::UTF8.GetBytes("$LF--$boundary--$LF")
    $body      = New-Object byte[] ($hdrBytes.Length + $fileBytes.Length + $tailBytes.Length)
    [System.Buffer]::BlockCopy($hdrBytes,  0, $body, 0,                                    $hdrBytes.Length)
    [System.Buffer]::BlockCopy($fileBytes, 0, $body, $hdrBytes.Length,                     $fileBytes.Length)
    [System.Buffer]::BlockCopy($tailBytes, 0, $body, $hdrBytes.Length + $fileBytes.Length, $tailBytes.Length)

    try {
        $req = [System.Net.WebRequest]::Create("$SERVER/admin/api/gallery/$slug/add-image")
        $req.Method        = "POST"
        $req.ContentType   = "multipart/form-data; boundary=$boundary"
        $req.ContentLength = $body.Length
        $req.Headers.Add("X-Admin-Token", $TOKEN)

        $stream = $req.GetRequestStream()
        $stream.Write($body, 0, $body.Length)
        $stream.Close()

        $resp   = $req.GetResponse()
        $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
        $text   = $reader.ReadToEnd()
        $reader.Close(); $resp.Close()
        $obj = $text | ConvertFrom-Json

        if ($obj.ok) {
            Write-Host "OK" -ForegroundColor Green
            $added++
        } else {
            Write-Host "FAILED - $($obj.error)" -ForegroundColor Red
        }
    } catch {
        Write-Host "FAILED - $($_.Exception.Message)" -ForegroundColor Red
    }
}

Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Cyan
Write-Host "Uploaded $added of $($ready.Count) downloaded images."
if ($failed.Count -gt 0) {
    Write-Host "$($failed.Count) images still blocked by Wix CDN (may need manual download from Wix editor)." -ForegroundColor Yellow
}
Write-Host ""
Read-Host "Press Enter to exit"
