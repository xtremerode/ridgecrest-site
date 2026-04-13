"""Check if the IIFE's mousedown listener is actually setting _drag."""
from playwright.sync_api import sync_playwright
import time, json

OUT = '/home/claudeuser/agent/downloads'
ADMIN_PW = 'Hb2425hb+'
BASE = 'http://localhost:8081'

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

    # ── Inspect ALL mousedown listeners on the handle ──────────────────────────
    # We can't directly inspect closured IIFE functions, but we can:
    # 1. Monkeypatch EventTarget.prototype.addEventListener to log all listeners
    # 2. Fire the mousedown manually and check aftermath

    result = site_frame.evaluate("""() => {
        const handle = document.querySelector('[data-rd-section-handle="hero"]');
        const hero = document.querySelector('section.hero');

        // Count existing document-level mousemove listeners by tracking adds
        window._docMoveCount = 0;
        window._docUpCount = 0;
        const origAdd = EventTarget.prototype.addEventListener;
        EventTarget.prototype.addEventListener = function(type, fn, opts) {
            if (this === document) {
                if (type === 'mousemove') window._docMoveCount++;
                if (type === 'mouseup') window._docUpCount++;
            }
            return origAdd.call(this, type, fn, opts);
        };

        // Dispatch mousedown manually on the handle
        const rect = handle.getBoundingClientRect();
        const cx = rect.left + rect.width/2;
        const cy = rect.top + rect.height/2;

        const h0 = hero.offsetHeight;

        handle.dispatchEvent(new MouseEvent('mousedown', {
            bubbles: true, cancelable: true,
            clientX: cx, clientY: cy,
            button: 0, buttons: 1
        }));

        const h1 = hero.offsetHeight;

        // Now dispatch mousemove 200px up
        document.dispatchEvent(new MouseEvent('mousemove', {
            bubbles: true, cancelable: true,
            clientX: cx, clientY: cy - 200,
            button: 0, buttons: 1
        }));

        const h2 = hero.offsetHeight;

        // Restore
        EventTarget.prototype.addEventListener = origAdd;

        return {
            docMoveListenersAdded: window._docMoveCount,
            docUpListenersAdded: window._docUpCount,
            h0, h1, h2,
            heightChangedAfterMousedown: h1 !== h0,
            heightChangedAfterMousemove: h2 !== h0,
            handlePos: { top: Math.round(rect.top), bottom: Math.round(rect.bottom) }
        };
    }""")

    print(f"\n--- Results ---")
    print(json.dumps(result, indent=2))

    print(f"\n=== DIAGNOSIS ===")
    if result['docMoveListenersAdded'] == 0:
        print("❌ NO document mousemove listener added after mousedown")
        print("   → The IIFE's mousedown handler IS NOT RUNNING or has a guard condition")
    else:
        print(f"✅ {result['docMoveListenersAdded']} document mousemove listener(s) added")

    if not result['heightChangedAfterMousemove']:
        print("❌ Height did not change after synthetic mousemove")
        print("   → _drag may not be set, or the mousemove delta calc is wrong")
    else:
        print(f"✅ Height changed: {result['h0']} → {result['h2']}")

    browser.close()
