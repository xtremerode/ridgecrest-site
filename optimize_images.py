#!/usr/bin/env python3
"""
Memory-efficient image optimization for Ridgecrest Designs.

Key technique: JPEG draft mode — asks the JPEG decoder to produce ~1/4 scale
output (9500px → 2375px) so peak RAM is ~11 MB instead of ~180 MB per image.
PNG files are generally much smaller; processed normally.
"""

import gc
import os
import re
from pathlib import Path
from PIL import Image

ASSETS_DIR  = Path("/home/claudeuser/agent/preview/assets/images")
OPT_DIR     = Path("/home/claudeuser/agent/preview/assets/images-opt")
PREVIEW_DIR = Path("/home/claudeuser/agent/preview")
CSS_DIR     = PREVIEW_DIR / "css"

QUALITY = 85

OPT_DIR.mkdir(parents=True, exist_ok=True)

# ── helpers ──────────────────────────────────────────────────────────────────

def open_normalised(path):
    """Open image, apply draft mode for JPEGs, normalise to RGB. Returns PIL Image."""
    ext = path.suffix.lower()
    img = Image.open(path)

    # JPEG draft mode: request ~1/4 scale decode to save RAM
    if ext in (".jpg", ".jpeg"):
        img.draft("RGB", (1920, 1920))

    img.load()  # force decode at (possibly draft-reduced) resolution

    if img.mode in ("RGBA", "P"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        mask = img.split()[3] if img.mode == "RGBA" else None
        bg.paste(img, mask=mask)
        img.close()
        img = bg
    elif img.mode != "RGB":
        tmp = img.convert("RGB")
        img.close()
        img = tmp

    return img

def resize_to_width(img, target_w):
    """Resize to target_w, maintaining aspect ratio. Never upscale."""
    w, h = img.size
    if target_w >= w:
        return img.copy()
    return img.resize((target_w, int(h * target_w / w)), Image.LANCZOS)


# ── 1. Convert images ────────────────────────────────────────────────────────

print("=== Converting images to WebP ===")

source_files = sorted([
    f for f in ASSETS_DIR.iterdir()
    if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
])

total_before = sum(f.stat().st_size for f in source_files)
total_after  = 0
converted    = 0
skipped      = 0

for i, src in enumerate(source_files, 1):
    stem = src.stem
    try:
        # Open with draft mode for JPEGs
        img = open_normalised(src)

        # Cascade: 1920 → 960 → 480
        img1920 = resize_to_width(img, 1920)
        img.close(); del img; gc.collect()

        out = OPT_DIR / f"{stem}.webp"
        img1920.save(out, "WEBP", quality=QUALITY, method=4)
        total_after += out.stat().st_size

        img960 = resize_to_width(img1920, 960)
        out = OPT_DIR / f"{stem}_960w.webp"
        img960.save(out, "WEBP", quality=QUALITY, method=4)
        total_after += out.stat().st_size
        img960.close(); del img960

        img480 = resize_to_width(img1920, 480)
        out = OPT_DIR / f"{stem}_480w.webp"
        img480.save(out, "WEBP", quality=QUALITY, method=4)
        total_after += out.stat().st_size
        img480.close(); del img480

        img1920.close(); del img1920
        gc.collect()

        converted += 1
        if i % 10 == 0 or i == len(source_files):
            pct = (1 - total_after / max(total_before, 1)) * 100
            print(f"  [{i}/{len(source_files)}]  WebP so far: {total_after/1024/1024:.1f} MB  ({pct:.0f}% smaller)")

    except MemoryError as e:
        print(f"  OOM {src.name} — skipping")
        skipped += 1
        gc.collect()
    except Exception as e:
        print(f"  ERROR {src.name}: {e}")
        skipped += 1
        gc.collect()

print(f"\n  Converted: {converted}  Skipped: {skipped}")
print(f"  Before: {total_before/1024/1024:.1f} MB  |  After: {total_after/1024/1024:.1f} MB  |  Reduction: {(1 - total_after/max(total_before,1))*100:.1f}%")


# ── 2. Build lookup ──────────────────────────────────────────────────────────

img_map = {f.name: f.stem for f in source_files}

def webp_path(filename, width=None):
    stem = img_map.get(filename, Path(filename).stem)
    suffix = f"_{width}w" if width and width != 1920 else ""
    return f"/assets/images-opt/{stem}{suffix}.webp"

def build_srcset(filename):
    return (
        f"{webp_path(filename, 480)} 480w, "
        f"{webp_path(filename, 960)} 960w, "
        f"{webp_path(filename)} 1920w"
    )


# ── 3. Update HTML ───────────────────────────────────────────────────────────

print("\n=== Updating HTML files ===")

IMG_TAG_RE = re.compile(
    r'<img\b([^>]*?)\bsrc=["\']([^"\']*?/assets/images/([^"\']+))["\']([^>]*?)(/?)>',
    re.IGNORECASE | re.DOTALL
)

HERO_CLASSES = {"hero", "hero-img", "hero-image", "hero-section", "hero-bg"}

def replace_img_tag(m):
    before = m.group(1)
    orig   = m.group(2)
    fname  = m.group(3)
    after  = m.group(4)
    all_attrs = (before + " " + after).strip()

    is_hero = any(c in all_attrs for c in HERO_CLASSES)
    lazy    = "" if is_hero else ' loading="lazy"'

    if fname not in img_map:
        if not is_hero and 'loading=' not in all_attrs:
            return f'<img{before}src="{orig}"{after} loading="lazy">'
        return m.group(0)

    clean = re.sub(r'\s*loading=["\'][^"\']*["\']', '', all_attrs).strip()
    srcs  = build_srcset(fname)

    return (
        f'<picture>\n'
        f'  <source type="image/webp" srcset="{srcs}"\n'
        f'          sizes="(max-width: 480px) 480px, (max-width: 960px) 960px, 1920px">\n'
        f'  <img src="{orig}" {clean}{lazy}>\n'
        f'</picture>'
    )

html_files = [f for f in PREVIEW_DIR.rglob("*.html") if "/admin/" not in str(f)]
html_upd = img_repl = 0

for hf in html_files:
    text = hf.read_text(encoding="utf-8")
    new_text, n = IMG_TAG_RE.subn(replace_img_tag, text)
    if n:
        hf.write_text(new_text, encoding="utf-8")
        html_upd += 1
        img_repl += n

print(f"  HTML files updated: {html_upd}")
print(f"  <img> → <picture> replacements: {img_repl}")


# ── 4. Update CSS ────────────────────────────────────────────────────────────

print("\n=== Updating CSS ===")

CSS_BG_RE = re.compile(
    r'url\(["\']?(/assets/images/([^"\')\s]+))["\']?\)',
    re.IGNORECASE
)

def replace_css_bg(m):
    fname = m.group(2)
    return f"url('{webp_path(fname)}')" if fname in img_map else m.group(0)

css_upd = css_repl = 0
for cf in CSS_DIR.glob("*.css"):
    text = cf.read_text(encoding="utf-8")
    new_text, n = CSS_BG_RE.subn(replace_css_bg, text)
    if n:
        cf.write_text(new_text, encoding="utf-8")
        css_upd += 1
        css_repl += n

print(f"  CSS files updated: {css_upd}")
print(f"  background-image URLs replaced: {css_repl}")


# ── 5. Register /assets/images-opt route in server (if not present) ─────────

print("\n=== Checking Flask route for /assets/images-opt ===")
server_path = Path("/home/claudeuser/agent/preview_server.py")
server_text = server_path.read_text()
if "images-opt" not in server_text:
    # Find existing /assets/images route and add a sibling
    patch = """
@app.route('/assets/images-opt/<path:filename>')
def serve_images_opt(filename):
    return send_from_directory('/home/claudeuser/agent/preview/assets/images-opt', filename)
"""
    # Insert after the /assets/images route definition
    marker = "@app.route('/assets/images/"
    if marker in server_text:
        pos = server_text.find(marker)
        # Find end of that route function
        next_route = server_text.find("\n@app.route", pos + 1)
        if next_route == -1:
            next_route = len(server_text)
        server_text = server_text[:next_route] + "\n" + patch + server_text[next_route:]
        server_path.write_text(server_text)
        print("  Added /assets/images-opt route to preview_server.py")
    else:
        print("  WARNING: Could not find /assets/images route — add manually")
else:
    print("  Route already present — OK")


# ── 6. Summary ───────────────────────────────────────────────────────────────

print("\n=== COMPLETE ===")
print(f"  Original: {total_before/1024/1024:.1f} MB  |  WebP: {total_after/1024/1024:.1f} MB  |  Saved: {(1 - total_after/max(total_before,1))*100:.1f}%")
print(f"  HTML: {html_upd} files, {img_repl} tags wrapped in <picture>")
print(f"  CSS:  {css_upd} files, {css_repl} background-images updated")
print(f"\n  NEXT: sudo systemctl restart preview_server  (to pick up new Flask route)")
