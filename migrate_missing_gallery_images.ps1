# migrate_missing_gallery_images.ps1
# Downloads 10 missing gallery images from Wix CDN and adds them to the correct galleries.
# Must run from Henry's laptop - Wix CDN blocks DigitalOcean server IPs.

param(
    [string]$ServerUrl = "http://147.182.242.54:8081",
    [string]$Password  = ""
)
if ([string]::IsNullOrEmpty($Password)) {
    $Password = Read-Host "Enter admin password"
}

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== Ridgecrest Missing Gallery Images ===" -ForegroundColor Cyan
Write-Host "10 images missing from 3 galleries - downloading from Wix and uploading to server."
Write-Host ""

# Step 1: Login
Write-Host "[1/3] Logging in..." -ForegroundColor Yellow
$loginBody = '{"password":"' + $Password + '"}'
try {
    $loginResp = Invoke-RestMethod -Uri "$ServerUrl/admin/api/auth" `
        -Method POST -ContentType "application/json" -Body $loginBody
    $Token = $loginResp.token
    Write-Host "  OK - token $($Token.Substring(0,16))..." -ForegroundColor Green
} catch {
    Write-Host "ERROR: Login failed - $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Step 2: Download from Wix CDN
$images = @(
    @{ slug="lafayette-luxury";           hash="ff5b18_2882dd1cc3314d3a9e205861b9fff3f7_mv2"; ext="jpg" },
    @{ slug="lafayette-luxury";           hash="ff5b18_22620574256243ca8f197a3e9fe27ca1_mv2"; ext="jpg" },
    @{ slug="lafayette-luxury";           hash="ff5b18_4c364cc11c9944fc83ece24b9c91498a_mv2"; ext="jpg" },
    @{ slug="lafayette-luxury";           hash="ff5b18_46e606322d7d4ae3bc4cc744a6f688af_mv2"; ext="jpg" },
    @{ slug="lafayette-luxury";           hash="ff5b18_dd972afe8737434c9014dcca1624d988_mv2"; ext="jpg" },
    @{ slug="lafayette-luxury";           hash="ff5b18_c2a04c214cf44ddeb43c9d7c7b58ce47_mv2"; ext="jpg" },
    @{ slug="orinda-kitchen";             hash="ff5b18_4b19847e3cf14ecfb78313bac274f651_mv2"; ext="png" },
    @{ slug="orinda-kitchen";             hash="ff5b18_b2c6186a71644039b5e9854f48df0d7f_mv2"; ext="png" },
    @{ slug="orinda-kitchen";             hash="ff5b18_ad29115ec24b4bbaa33893ed164199cf_mv2"; ext="png" },
    @{ slug="pleasanton-cottage-kitchen"; hash="ff5b18_56956b7fa72d450998718343281c35e4_mv2"; ext="png" }
)

$TempDir = Join-Path $env:TEMP "rdgallery_$([System.Guid]::NewGuid().ToString('N').Substring(0,8))"
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

Write-Host ""
Write-Host "[2/3] Downloading $($images.Count) images from Wix CDN..." -ForegroundColor Yellow

$ready = [System.Collections.ArrayList]@()
foreach ($img in $images) {
    $hash    = $img.hash
    $ext     = $img.ext
    $wixHash = $hash -replace "_mv2$", ""
    $wixUrl  = "https://static.wixstatic.com/media/$($wixHash)~mv2.$ext"
    $outFile = Join-Path $TempDir "$hash.$ext"

    Write-Host "  $hash.$ext ... " -NoNewline
    try {
        $wc = New-Object System.Net.WebClient
        $wc.Headers.Add("Referer",    "https://www.ridgecrestdesigns.com/")
        $wc.Headers.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        $wc.DownloadFile($wixUrl, $outFile)
        $size = (Get-Item $outFile).Length
        if ($size -lt 1000) {
            Write-Host "FAILED (only $size bytes)" -ForegroundColor Red
            Remove-Item $outFile -Force
        } else {
            Write-Host "OK ($([math]::Round($size/1024))KB)" -ForegroundColor Green
            $null = $ready.Add(@{ img=$img; path=$outFile })
        }
    } catch {
        Write-Host "FAILED - $($_.Exception.Message)" -ForegroundColor Red
    }
}

if ($ready.Count -eq 0) {
    Write-Host ""
    Write-Host "No images downloaded. Exiting." -ForegroundColor Red
    Remove-Item $TempDir -Recurse -Force
    Read-Host "Press Enter to exit"
    exit 1
}

# Step 3: Upload to server via add-image endpoint (preserves hash filename, adds to gallery)
Write-Host ""
Write-Host "[3/3] Uploading $($ready.Count) images to server..." -ForegroundColor Yellow

$LF    = "`r`n"
$added = 0

foreach ($entry in $ready) {
    $img      = $entry.img
    $hash     = $img.hash
    $ext      = $img.ext
    $slug     = $img.slug
    $mimeType = if ($ext -eq "png") { "image/png" } else { "image/jpeg" }
    $boundary = "boundary" + [System.Guid]::NewGuid().ToString("N")

    Write-Host "  $slug / $hash.$ext ... " -NoNewline

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
        $req = [System.Net.WebRequest]::Create("$ServerUrl/admin/api/gallery/$slug/add-image")
        $req.Method        = "POST"
        $req.ContentType   = "multipart/form-data; boundary=$boundary"
        $req.ContentLength = $body.Length
        $req.Headers.Add("X-Admin-Token", $Token)

        $stream = $req.GetRequestStream()
        $stream.Write($body, 0, $body.Length)
        $stream.Close()

        $resp   = $req.GetResponse()
        $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
        $text   = $reader.ReadToEnd()
        $reader.Close()
        $resp.Close()
        $obj = $text | ConvertFrom-Json

        if ($obj.ok) {
            Write-Host "OK (gallery now $($obj.gallery_count) images)" -ForegroundColor Green
            $added++
        } else {
            Write-Host "FAILED - $($obj.error)" -ForegroundColor Red
        }
    } catch {
        Write-Host "FAILED - $($_.Exception.Message)" -ForegroundColor Red
    }
}

Remove-Item $TempDir -Recurse -Force

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Cyan
Write-Host "Added $added of $($images.Count) images to galleries." -ForegroundColor White
Write-Host ""
Write-Host "Next: open the admin panel and run Auto-Tag + Auto-Sort on:" -ForegroundColor White
Write-Host "  - Lafayette Laid-Back Luxury (6 images added)" -ForegroundColor Gray
Write-Host "  - Orinda Kitchen (3 images added)" -ForegroundColor Gray
Write-Host "  - Pleasanton Cottage Kitchen (1 image added)" -ForegroundColor Gray
Write-Host ""
Read-Host "Press Enter to exit"
