# fetch_98f97a76_only.ps1
# Fetches Pleasanton Custom construction photo using PowerShell WebClient (same method as recover_all_missing.ps1)
# Usage: right-click > Run with PowerShell  (or: powershell -ExecutionPolicy Bypass -File fetch_98f97a76_only.ps1)

$SERVER  = "http://147.182.242.54:8081"
$TOKEN   = "35e8bdf6f9cddb3a140a3ac34a9dcb3963c7bff434ef8bd6fedfda70299b13f1"
$SLUG    = "pleasanton-custom"
$HASH    = "ff5b18_98f97a76f69c41dca1e0ddb7a927be32_mv2"
$WIX_HASH = "ff5b18_98f97a76f69c41dca1e0ddb7a927be32"

$TempDir = Join-Path $env:TEMP "fetch_98f97a76"
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

Write-Host ""
Write-Host "=== Pleasanton Custom — construction photo (photo 77) ===" -ForegroundColor Cyan
Write-Host ""

$downloaded = $false
$outFile    = $null
$ext        = $null

foreach ($tryExt in @("jpg", "webp", "png")) {
    $wixUrl  = "https://static.wixstatic.com/media/$($WIX_HASH)~mv2.$tryExt"
    $outFile = Join-Path $TempDir "$HASH.$tryExt"

    Write-Host "  Trying .$tryExt ... " -NoNewline

    try {
        $wc = New-Object System.Net.WebClient
        $wc.Headers.Add("Referer",    "https://www.ridgecrestdesigns.com/")
        $wc.Headers.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        $wc.DownloadFile($wixUrl, $outFile)
        $size = (Get-Item $outFile).Length
        if ($size -lt 1000) {
            Write-Host "BLOCKED ($size bytes)" -ForegroundColor Red
            Remove-Item $outFile -Force -ErrorAction SilentlyContinue
        } else {
            Write-Host "OK ($([math]::Round($size/1024))KB)" -ForegroundColor Green
            $downloaded = $true
            $ext = $tryExt
            break
        }
    } catch {
        Write-Host "ERROR - $($_.Exception.Message)" -ForegroundColor Red
    }
}

if (-not $downloaded) {
    Write-Host ""
    Write-Host "FAILED: All extensions blocked by Wix CDN." -ForegroundColor Red
    Write-Host "This image may have been deleted from the Wix media library." -ForegroundColor Yellow
    Write-Host "Please check your Wix Media Manager at wix.com/my-account/media" -ForegroundColor Yellow
    Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue
    Read-Host "Press Enter to exit"
    exit
}

# Upload to server
$LF       = "`r`n"
$mimeType = if ($ext -eq "png") { "image/png" } elseif ($ext -eq "webp") { "image/webp" } else { "image/jpeg" }
$boundary = "boundary" + [System.Guid]::NewGuid().ToString("N")
$filename = "$HASH.$ext"

Write-Host ""
Write-Host "  Uploading to server ($SLUG)... " -NoNewline

$fileBytes = [System.IO.File]::ReadAllBytes($outFile)
$hdrStr    = "--$boundary$LF" +
             "Content-Disposition: form-data; name=`"file`"; filename=`"$filename`"$LF" +
             "Content-Type: $mimeType$LF$LF"
$hdrBytes  = [System.Text.Encoding]::UTF8.GetBytes($hdrStr)
$tailBytes = [System.Text.Encoding]::UTF8.GetBytes("$LF--$boundary--$LF")
$body      = New-Object byte[] ($hdrBytes.Length + $fileBytes.Length + $tailBytes.Length)
[System.Buffer]::BlockCopy($hdrBytes,  0, $body, 0,                                    $hdrBytes.Length)
[System.Buffer]::BlockCopy($fileBytes, 0, $body, $hdrBytes.Length,                     $fileBytes.Length)
[System.Buffer]::BlockCopy($tailBytes, 0, $body, $hdrBytes.Length + $fileBytes.Length, $tailBytes.Length)

try {
    $req = [System.Net.WebRequest]::Create("$SERVER/admin/api/gallery/$SLUG/add-image")
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
        Write-Host ""
        Write-Host "SUCCESS. Image uploaded. Page will re-render automatically." -ForegroundColor Green
    } else {
        Write-Host "FAILED - $($obj.error)" -ForegroundColor Red
    }
} catch {
    Write-Host "FAILED - $($_.Exception.Message)" -ForegroundColor Red
}

Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue
Write-Host ""
Read-Host "Press Enter to exit"
