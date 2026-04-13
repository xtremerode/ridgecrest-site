"""Check for multiple handles and identify which one has the IIFE listener."""
from playwright.sync_api import sync_playwright
import time, json

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
    if not site_frame: print("No site frame"); browser.close(); exit()

    result = site_frame.evaluate("""() => {
        const handles = document.querySelectorAll('[data-rd-section-handle="hero"]');
        const info = {
            handleCount: handles.length,
            handles: []
        };

        handles.forEach(function(h, i) {
            const rect = h.getBoundingClientRect();
            const parentTag = h.parentElement ? h.parentElement.tagName + '.' + h.parentElement.className.trim().split(' ')[0] : 'none';

            // Try to fire a synthetic mousedown and see if height changes
            const hero = document.querySelector('section.hero');
            const h0 = hero.offsetHeight;

            h.dispatchEvent(new MouseEvent('mousedown', {
                bubbles: true, cancelable: true,
                clientX: rect.left + rect.width/2,
                clientY: rect.top + rect.height/2,
                button: 0, buttons: 1,
                isTrusted: false
            }));

            // immediate check — did height change?
            const h1 = hero.offsetHeight;

            // dispatch mousemove on document
            document.dispatchEvent(new MouseEvent('mousemove', {
                bubbles: true, cancelable: true,
                clientX: rect.left + rect.width/2,
                clientY: rect.top + rect.height/2 - 200,
                button: 0, buttons: 1
            }));

            const h2 = hero.offsetHeight;

            document.dispatchEvent(new MouseEvent('mouseup', {
                bubbles: true, cancelable: true,
                clientX: rect.left + rect.width/2,
                clientY: rect.top + rect.height/2 - 200,
                button: 0, buttons: 0
            }));

            info.handles.push({
                index: i,
                parent: parentTag,
                rect: { top: Math.round(rect.top), bottom: Math.round(rect.bottom) },
                dragWorked: h2 !== h0,
                h0, h1, h2
            });
        });

        // Also check the script element
        const scripts = document.querySelectorAll('script');
        const hasResizeScript = Array.from(scripts).some(s =>
            s.textContent && s.textContent.includes('rd-section-resize')
        );
        const resizeScriptEl = document.getElementById('rd-section-resize');

        info.scriptByIdFound = !!resizeScriptEl;
        info.scriptByContentFound = hasResizeScript;
        info.totalScripts = scripts.length;

        return info;
    }""")

    print(json.dumps(result, indent=2))

    print(f"\n=== DIAGNOSIS ===")
    print(f"Handle count: {result['handleCount']}")
    for h in result['handles']:
        if h['dragWorked']:
            print(f"  Handle {h['index']}: DRAG WORKED via synthetic events! (parent: {h['parent']})")
        else:
            print(f"  Handle {h['index']}: drag failed (parent: {h['parent']}) h0={h['h0']} h2={h['h2']}")

    browser.close()
