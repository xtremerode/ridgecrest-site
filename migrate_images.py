#!/usr/bin/env python3
"""
Ridgecrest Designs — Wix Image Migration Script
Run this from your Mac/laptop (NOT from the server — the server IP is blocked by Wix CDN).

Usage:
    python3 migrate_images.py

Requirements: Python 3.8+ (no extra packages needed)
"""
import urllib.request
import urllib.parse
import urllib.error
import json
import base64
import re
import sys
import getpass

# ── Config ──────────────────────────────────────────────────────────────────
SERVER = "http://147.182.242.54:8081"
WIX_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer": "https://www.ridgecrestdesigns.com/",
}

# ── Auth ─────────────────────────────────────────────────────────────────────
def login(password):
    req = urllib.request.Request(
        f"{SERVER}/admin/api/auth",
        data=json.dumps({"password": password}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    if "token" not in data:
        raise ValueError(f"Login failed: {data}")
    return data["token"]

# ── Fetch all unmigrated Wix URLs ─────────────────────────────────────────────
def get_wix_urls(token):
    req = urllib.request.Request(
        f"{SERVER}/admin/api/media/wix-urls",
        headers={"X-Admin-Token": token}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())["urls"]

# ── Deduplicate to unique base images ─────────────────────────────────────────
def deduplicate(urls):
    seen = {}
    tasks = []
    for url in urls:
        parts = url.split("/media/")
        if len(parts) < 2:
            continue
        filename = parts[1].split("?")[0].split("/")[0]
        if not filename or filename in seen:
            continue
        seen[filename] = True
        safe = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
        tasks.append({
            "original_url": url,
            "base_url": f"https://static.wixstatic.com/media/{filename}",
            "filename": filename,
            "safe_name": safe,
            "local_path": f"/assets/images/{safe}",
        })
    return tasks

# ── Download one image from Wix CDN ──────────────────────────────────────────
def download_image(url):
    req = urllib.request.Request(url, headers=WIX_HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

# ── Upload image to server ────────────────────────────────────────────────────
def upload_image(token, filename, data_bytes, password):
    b64 = base64.b64encode(data_bytes).decode()
    req = urllib.request.Request(
        f"{SERVER}/media/receive",
        data=json.dumps({"token": password, "filename": filename, "data": b64}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        result = json.loads(r.read())
    if not result.get("ok"):
        raise ValueError(result.get("error", "Upload failed"))

# ── Update references in DB + HTML ───────────────────────────────────────────
def update_refs(token, wix_url, local_path):
    req = urllib.request.Request(
        f"{SERVER}/admin/api/media/update-references",
        data=json.dumps({"wix_url": wix_url, "local_path": local_path}).encode(),
        headers={"Content-Type": "application/json", "X-Admin-Token": token},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=== Ridgecrest Designs — Wix Image Migration ===\n")
    print(f"Server: {SERVER}")
    print("Note: this must run from your laptop, not the server.\n")

    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        password = getpass.getpass("Admin password: ")

    print("Logging in…")
    try:
        token = login(password)
        print("Logged in.\n")
    except Exception as e:
        print(f"Login failed: {e}")
        sys.exit(1)

    print("Fetching unmigrated image list from server…")
    try:
        urls = get_wix_urls(token)
    except Exception as e:
        print(f"Failed to load image list: {e}")
        sys.exit(1)

    tasks = deduplicate(urls)
    print(f"Found {len(urls)} URL references → {len(tasks)} unique images to download.\n")

    if not tasks:
        print("Nothing to migrate — all images are already on your server.")
        return

    succeeded = 0
    failed = 0
    skipped = 0

    for i, task in enumerate(tasks, 1):
        label = f"[{i}/{len(tasks)}]"
        try:
            raw = download_image(task["base_url"])
            if len(raw) < 100:
                raise ValueError(f"Response only {len(raw)} bytes — likely an error")

            upload_image(token, task["safe_name"], raw, password)
            update_refs(token, task["original_url"], task["local_path"])

            kb = len(raw) // 1024
            print(f"{label} ✓  {task['safe_name']} ({kb} KB)")
            succeeded += 1

        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"{label} —  {task['filename']} (not found on Wix CDN, skipping)")
                skipped += 1
            else:
                print(f"{label} ✗  {task['filename']} — HTTP {e.code}: {e.reason}")
                failed += 1
        except Exception as e:
            print(f"{label} ✗  {task['filename']} — {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Done. {succeeded} saved · {skipped} skipped · {failed} failed")
    if succeeded > 0:
        print(f"Images saved to {SERVER}/assets/images/")
        print("All blog post images and HTML references updated automatically.")

if __name__ == "__main__":
    main()
