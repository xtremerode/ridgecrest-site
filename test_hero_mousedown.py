"""Diagnose hero handle: check if mousedown fires and sets _drag state."""
from playwright.sync_api import sync_playwright
import time, json

OUT = '/home/claudeuser/agent/downloads'
ADMIN_PW = 'Hb2425hb+'
BASE = 'http://localhost:8081'

def shot(page, name):
    path = f'{OUT}/hmd_{name}.png'
    page.screenshot(path=path)
    print(f'  📸 http://147.182.242.54:8081/screenshots/hmd_{name}.png')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
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

    # ── Step 1: Inject debug hooks BEFORE testing ──────────────────────────────
    debug = site_frame.evaluate("""() => {
        // Expose internal _drag state via window for inspection
        // We need to PATCH the IIFE's _drag — can't directly, but we can
        // inject a mousedown listener on the handle and track it separately

        const handle = document.querySelector('[data-rd-section-handle="hero"]');
        if (!handle) return { error: 'no handle' };

        window._dbgMousedownFired = false;
        window._dbgMousedownClientY = null;
        window._dbgMousemoveFired = false;
        window._dbgMouseupFired = false;

        // Capture-phase listener — fires BEFORE any bubble-phase listener
        handle.addEventListener('mousedown', function(e) {
            window._dbgMousedownFired = true;
            window._dbgMousedownClientY = e.clientY;
            console.log('[DBG] handle mousedown fired at clientY=' + e.clientY + ' button=' + e.button);
        }, true); // capture=true

        // Document-level listener to track mousemove
        document.addEventListener('mousemove', function(e) {
            if (window._dbgMousedownFired && !window._dbgMouseupFired) {
                window._dbgMousemoveFired = true;
                console.log('[DBG] document mousemove clientY=' + e.clientY);
            }
        });

        document.addEventListener('mouseup', function(e) {
            window._dbgMouseupFired = true;
            console.log('[DBG] document mouseup fired');
        });

        const rect = handle.getBoundingClientRect();
        return {
            handleFound: true,
            rect: { top: Math.round(rect.top), bottom: Math.round(rect.bottom),
                    left: Math.round(rect.left), right: Math.round(rect.right) },
            heroHeight: document.querySelector('section.hero').offsetHeight
        };
    }""")
    print(f"\n--- Setup ---")
    print(f"  {debug}")

    # ── Step 2: Get handle's page-level coordinates via Playwright ─────────────
    handle_el = site_frame.query_selector('[data-rd-section-handle="hero"]')
    if not handle_el:
        print("Handle not found via Playwright"); browser.close(); exit()

    bbox = handle_el.bounding_box()
    print(f"\n  Playwright bbox (page coords): {bbox}")

    cx = bbox['x'] + bbox['width'] / 2
    cy = bbox['y'] + bbox['height'] / 2
    print(f"  Page-level drag coords: ({cx:.0f}, {cy:.0f})")

    shot(page, '01_before')

    # ── Step 3: Attempt drag via Playwright page.mouse ─────────────────────────
    print(f"\n--- Drag Test ---")

    h_before = site_frame.evaluate("() => document.querySelector('section.hero').offsetHeight")
    print(f"  Height before: {h_before}px")

    # Move to handle center
    page.mouse.move(cx, cy)
    time.sleep(0.3)

    # Check if hover landed on handle
    hover_check = site_frame.evaluate("""() => {
        const h = document.querySelector('[data-rd-section-handle="hero"]');
        const r = h.getBoundingClientRect();
        const el = document.elementFromPoint(r.left + r.width/2, r.top + r.height/2);
        return el ? {
            tag: el.tagName,
            sectionHandle: el.getAttribute('data-rd-section-handle'),
            cursor: window.getComputedStyle(el).cursor
        } : null;
    }""")
    print(f"  Element at handle (iframe coords): {hover_check}")

    shot(page, '02_hover')

    # Press mouse down
    page.mouse.down()
    time.sleep(0.3)

    # Check if mousedown fired
    state1 = site_frame.evaluate("""() => ({
        mousedownFired: window._dbgMousedownFired,
        mousedownClientY: window._dbgMousedownClientY,
        heroHeight: document.querySelector('section.hero').offsetHeight
    })""")
    print(f"\n  After mousedown: {state1}")

    # Move mouse up 200px
    page.mouse.move(cx, cy - 200, steps=20)
    time.sleep(0.3)

    # Check state after mousemove
    state2 = site_frame.evaluate("""() => ({
        mousemoveFired: window._dbgMousemoveFired,
        heroHeight: document.querySelector('section.hero').offsetHeight
    })""")
    print(f"  After mousemove: {state2}")

    shot(page, '03_during_drag')

    page.mouse.up()
    time.sleep(0.5)

    state3 = site_frame.evaluate("""() => ({
        mouseupFired: window._dbgMouseupFired,
        heroHeight: document.querySelector('section.hero').offsetHeight
    })""")
    print(f"  After mouseup: {state3}")

    shot(page, '04_after')

    # ── Step 4: Conclusion ─────────────────────────────────────────────────────
    print(f"\n=== DIAGNOSIS ===")
    if not state1['mousedownFired']:
        print("❌ MOUSEDOWN DID NOT FIRE — something is blocking it before it reaches the handle")
        print("   → Check overlay z-index or position blocking the handle's hit area")
    elif not state2['mousemoveFired']:
        print("✅ Mousedown fired")
        print("❌ MOUSEMOVE DID NOT FIRE on document — pointer events lost after mousedown")
        print("   → The drag listener may not be receiving events (iframe boundary issue?)")
    elif state3['heroHeight'] == h_before:
        print("✅ Mousedown fired")
        print("✅ Mousemove fired")
        print("❌ HEIGHT DID NOT CHANGE — the IIFE _drag state not being set, or height update failing")
    else:
        print("✅ Mousedown fired")
        print("✅ Mousemove fired")
        print(f"✅ HEIGHT CHANGED: {h_before}px → {state3['heroHeight']}px")

    browser.close()
