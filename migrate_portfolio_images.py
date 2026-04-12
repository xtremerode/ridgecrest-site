#!/usr/bin/env python3
"""
Portfolio Image Migration — downloads missing project images from Wix CDN.
Run from Henry's laptop (not the server — Wix blocks DigitalOcean IPs).
Usage: python migrate_portfolio_images.py
"""
import sys, json, base64, time, getpass
import urllib.request, urllib.error

PASSWORD = getpass.getpass("Admin password: ")
SERVER = "http://147.182.242.54:8081"
WIX_BASE = "https://static.wixstatic.com/media"
TOTAL = 25

# Wix hotlink protection — Referer must be ridgecrestdesigns.com or you get 403
WIX_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer": "https://www.ridgecrestdesigns.com/",
}

IMAGES = [
    ('ff5b18_4161051f37ba482fafc49baddabc8a96', 'jpg', 'ff5b18_4161051f37ba482fafc49baddabc8a96~mv2.jpg'),
    ('ff5b18_4025b406261e47e8993a0ad777ca3ebe', 'jpg', 'ff5b18_4025b406261e47e8993a0ad777ca3ebe~mv2.jpg'),
    ('ff5b18_938143f6f9374aa88d8ed87d5de5bb73', 'jpg', 'ff5b18_938143f6f9374aa88d8ed87d5de5bb73~mv2.jpg'),
    ('ff5b18_e25234795a7a4ed08b1bea59751199a9', 'jpg', 'ff5b18_e25234795a7a4ed08b1bea59751199a9~mv2.jpg'),
    ('ff5b18_bb1013e8034740828826f718ad2216d9', 'png', 'ff5b18_bb1013e8034740828826f718ad2216d9~mv2.png'),
    ('ff5b18_c1637bae333840e4a71cbdaac8405213', 'png', 'ff5b18_c1637bae333840e4a71cbdaac8405213~mv2.png'),
    ('ff5b18_de2ed75da1a541abb0861b82d04e1135', 'png', 'ff5b18_de2ed75da1a541abb0861b82d04e1135~mv2.png'),
    ('ff5b18_a69a1fba43ec4dd98ec66e582d5ec86f', 'png', 'ff5b18_a69a1fba43ec4dd98ec66e582d5ec86f~mv2.png'),
    ('ff5b18_dab676506e77455e942b02a857f21cc3', 'jpg', 'ff5b18_dab676506e77455e942b02a857f21cc3~mv2.jpg'),
    ('ff5b18_f8bf8933487f45db825a713b4ea4c540', 'jpg', 'ff5b18_f8bf8933487f45db825a713b4ea4c540~mv2.jpg'),
    ('ff5b18_5f016abc7ce04830a7f65e61c2b4a3fa', 'jpg', 'ff5b18_5f016abc7ce04830a7f65e61c2b4a3fa~mv2.jpg'),
    ('ff5b18_e1ef86fee44b4c14b077ecbdb2ca10f5', 'png', 'ff5b18_e1ef86fee44b4c14b077ecbdb2ca10f5~mv2.png'),
    ('ff5b18_73ddf9ebf03a4477926cbf2283271380', 'png', 'ff5b18_73ddf9ebf03a4477926cbf2283271380~mv2.png'),
    ('ff5b18_f575a25ba7f14e1389d0ae63bb2d356f', 'png', 'ff5b18_f575a25ba7f14e1389d0ae63bb2d356f~mv2.png'),
    ('ff5b18_9a3cb5be52fb466ebd047a075c89ee74', 'png', 'ff5b18_9a3cb5be52fb466ebd047a075c89ee74~mv2.png'),
    ('ff5b18_7bb937306ca1481894944e9f7b7b64c4', 'png', 'ff5b18_7bb937306ca1481894944e9f7b7b64c4~mv2.png'),
    ('ff5b18_8fec027febcb4fdb9a1f34db0e462fac', 'png', 'ff5b18_8fec027febcb4fdb9a1f34db0e462fac~mv2.png'),
    ('ff5b18_fa64df3266cb4f5687726c7ab5ac76f7', 'jpg', 'ff5b18_fa64df3266cb4f5687726c7ab5ac76f7~mv2.jpg'),
    ('ff5b18_8534e71718a54408b57038ba0fc8c02f', 'jpg', 'ff5b18_8534e71718a54408b57038ba0fc8c02f~mv2.jpg'),
    ('ff5b18_349218a966f148919fc38da254ca4619', 'jpg', 'ff5b18_349218a966f148919fc38da254ca4619~mv2.jpg'),
    ('ff5b18_29f3aa1ef62549ecbc7c5dd6b4aac717', 'jpg', 'ff5b18_29f3aa1ef62549ecbc7c5dd6b4aac717~mv2.jpg'),
    ('ff5b18_c1bace39ccc64636b710dc307c31bb77', 'jpg', 'ff5b18_c1bace39ccc64636b710dc307c31bb77~mv2.jpg'),
    ('ff5b18_0ab4862750bf42ac8c38304bf1a054ed', 'jpg', 'ff5b18_0ab4862750bf42ac8c38304bf1a054ed~mv2.jpg'),
    ('ff5b18_f81286bb193b4eceade91c476d030da2', 'png', 'ff5b18_f81286bb193b4eceade91c476d030da2~mv2.png'),
    ('ff5b18_f2d002a1b71342199e013a4389c24d40', 'jpg', 'ff5b18_f2d002a1b71342199e013a4389c24d40~mv2.jpg'),
]

def post_json(url, payload, timeout=30):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

# Login
print("Logging in...")
try:
    result = post_json(f"{SERVER}/admin/api/auth", {"password": PASSWORD})
    token = result.get("token", "")
    if not token:
        print(f"Auth failed: {result}")
        sys.exit(1)
    print(f"Authenticated. Downloading {TOTAL} images...\n")
except Exception as e:
    print(f"Auth error: {e}")
    sys.exit(1)

ok = fail = 0
for i, (hash_id, ext, wix_file) in enumerate(IMAGES, 1):
    wix_url = f"{WIX_BASE}/{wix_file}/v1/fill/w_1920,h_1280,q_90"
    local_name = f"{hash_id}_mv2.{ext}"
    print(f"[{i}/{TOTAL}] {local_name} ... ", end="", flush=True)
    try:
        # Download from Wix (works from laptop, not server)
        req = urllib.request.Request(wix_url, headers=WIX_HEADERS)
        with urllib.request.urlopen(req, timeout=30) as r:
            img_bytes = r.read()

        # Upload to server via /media/receive (base64 JSON — same as migrate.bat)
        b64 = base64.b64encode(img_bytes).decode()
        result = post_json(f"{SERVER}/media/receive", {
            "token": token,
            "filename": local_name,
            "data": b64
        })
        if result.get("ok"):
            print(f"OK ({len(img_bytes)//1024}KB)")
            ok += 1
        else:
            print(f"UPLOAD ERROR: {result.get('error', result)}")
            fail += 1
    except Exception as e:
        print(f"ERROR: {e}")
        fail += 1
    time.sleep(0.2)

print(f"\nDone: {ok} downloaded, {fail} failed.")
if ok > 0:
    print("\nImages saved to server. The server will auto-optimize them to WebP on next access.")
