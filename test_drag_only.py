"""Focused drag test with correct coordinate handling."""
from playwright.sync_api import sync_playwright
import time, os

OUT = '/home/claudeuser/agent/downloads'
ADMIN_PW = 'Hb2425hb+'
BASE = 'http://localhost:8081'

def shot(page, name):
    path = f'{OUT}/drag_{name}.png'
    page.screenshot(path=path)
    print(f'  📸 http://147.182.242.54:8081/screenshots/drag_{name}.png')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    # Taller viewport so the hero bottom is visible
    ctx = browser.new_context(viewport={'width': 1440, 'height': 1100})
    page = ctx.new_page()

    page.goto(f'{BASE}/view/admin/', wait_until='networkidle')
    page.fill('#password', ADMIN_PW)
    page.click('#loginBtn')
    page.wait_for_url('**/dashboard.html', timeout=10000)
    page.goto(f'{BASE}/view/admin/pages.html', wait_until='networkidle')
    time.sleep(2)

    page.click('.pg-node--home', timeout=5000)
    time.sleep(4)
    page.click('button:has-text("Edit Mode")', timeout=5000)
    time.sleep(5)

    site_frame = next((f for f in page.frames if '/view/' in f.url and 'admin' not in f.url), None)
    if not site_frame:
        print("No site frame"); browser.close(); exit()

    print(f"Frame: {site_frame.url}")

    # Get hero section handle — bbox is in PAGE coordinates (Playwright handles scaling)
    handle = site_frame.query_selector('[data-rd-section-handle="hero"]')
    if not handle:
        print("No hero handle found"); browser.close(); exit()

    bbox = handle.bounding_box()
    print(f"Handle page bbox: {bbox}")

    # These ARE page coordinates — use them directly
    cx = bbox['x'] + bbox['width'] / 2
    cy = bbox['y'] + bbox['height'] / 2
    print(f"Click target: ({cx:.0f}, {cy:.0f})")

    h_before = site_frame.evaluate("() => document.querySelector('section.hero').offsetHeight")
    print(f"Hero height BEFORE: {h_before}px")

    shot(page, '01_before_drag')

    # Scroll the frame-wrap so the handle is visible
    frame_wrap = page.query_selector('#frameWrap, .editor-frame-wrap, [id*="frame"]')
    print(f"Frame wrap: {frame_wrap}")

    # Hover, then drag up 150px
    page.mouse.move(cx, cy)
    time.sleep(0.5)

    # Check cursor
    cursor = site_frame.evaluate("""() => {
        const h = document.querySelector('[data-rd-section-handle="hero"]');
        const r = h.getBoundingClientRect();
        const el = document.elementFromPoint(r.left + r.width/2, r.top + r.height/2);
        return el ? {
            tag: el.tagName,
            handle: el.getAttribute('data-rd-section-handle'),
            overlay: el.getAttribute('data-rd-overlay'),
            cursor: window.getComputedStyle(el).cursor,
        } : null;
    }""")
    print(f"Element at handle center: {cursor}")

    shot(page, '02_hovering')

    page.mouse.down()
    time.sleep(0.1)
    page.mouse.move(cx, cy - 150, steps=40)
    time.sleep(0.5)

    h_during = site_frame.evaluate("() => document.querySelector('section.hero').offsetHeight")
    print(f"Hero height DURING drag: {h_during}px")

    shot(page, '03_mid_drag')

    page.mouse.up()
    time.sleep(1.5)

    h_after = site_frame.evaluate("() => document.querySelector('section.hero').offsetHeight")
    print(f"Hero height AFTER: {h_after}px")

    shot(page, '04_after_drag')

    if h_before and h_after and h_after != h_before:
        print(f"\n✅ DRAG WORKED — {h_before}px → {h_after}px")
    else:
        print(f"\n❌ DRAG FAILED — height unchanged at {h_after}px")

    browser.close()
