"""Test hero handle drag — all events in one JS call to share closure state."""
from playwright.sync_api import sync_playwright
import time, os, json

OUT = '/home/claudeuser/agent/downloads'
ADMIN_PW = 'Hb2425hb+'
BASE = 'http://localhost:8081'

def shot(page, name):
    path = f'{OUT}/jsdrag_{name}.png'
    page.screenshot(path=path)
    print(f'  📸 http://147.182.242.54:8081/screenshots/jsdrag_{name}.png')

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

    shot(page, '01_before')

    # Run the complete drag simulation in ONE evaluate call so closure variables are shared
    result = site_frame.evaluate("""() => {
        const handle = document.querySelector('[data-rd-section-handle="hero"]');
        if (!handle) return { error: 'no handle' };

        const hero = document.querySelector('section.hero');
        const rect = handle.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        const h0 = hero.offsetHeight;

        const log = [];
        log.push('handle found at clientY=' + cy.toFixed(0) + ', h0=' + h0);

        // Check what is currently at that position
        const topEl = document.elementFromPoint(cx, cy);
        log.push('elementFromPoint: ' + (topEl ? topEl.tagName + ' handle=' + topEl.getAttribute('data-rd-section-handle') + ' overlay=' + topEl.getAttribute('data-rd-overlay') : 'null (off screen)'));

        // Scroll the hero into view to bring it into the viewport
        handle.scrollIntoView({ block: 'center' });
        const rect2 = handle.getBoundingClientRect();
        const cy2 = rect2.top + rect2.height / 2;
        log.push('after scrollIntoView: cy=' + cy2.toFixed(0));

        const topEl2 = document.elementFromPoint(rect2.left + rect2.width/2, cy2);
        log.push('elementFromPoint after scroll: ' + (topEl2 ? topEl2.tagName + ' handle=' + topEl2.getAttribute('data-rd-section-handle') + ' overlay=' + topEl2.getAttribute('data-rd-overlay') + ' cursor=' + window.getComputedStyle(topEl2).cursor : 'null'));

        // Fire mousedown
        handle.dispatchEvent(new MouseEvent('mousedown', {
            bubbles: true, cancelable: true,
            clientX: rect2.left + rect2.width/2,
            clientY: cy2, button: 0, buttons: 1,
        }));
        log.push('mousedown fired, h after=' + hero.offsetHeight);

        // Fire mousemove events on document
        const heights = [];
        for (let i = 1; i <= 20; i++) {
            document.dispatchEvent(new MouseEvent('mousemove', {
                bubbles: true, cancelable: true,
                clientX: rect2.left + rect2.width/2,
                clientY: cy2 - (i * 10), button: 0, buttons: 1,
            }));
            heights.push(hero.offsetHeight);
        }
        log.push('heights during drag: ' + heights.join(','));

        // Fire mouseup
        document.dispatchEvent(new MouseEvent('mouseup', {
            bubbles: true, cancelable: true,
            clientX: rect2.left + rect2.width/2,
            clientY: cy2 - 200, button: 0, buttons: 0,
        }));

        const hFinal = hero.offsetHeight;
        log.push('final height: ' + hFinal);
        log.push(hFinal !== h0 ? 'DRAG WORKED' : 'DRAG FAILED');

        return { log, h0, hFinal, changed: hFinal !== h0 };
    }""")

    print(f"\n--- Results ---")
    for line in result['log']:
        print(f"  {line}")
    print(f"\nh0={result['h0']} → hFinal={result['hFinal']}")

    time.sleep(1)
    shot(page, '02_after')

    if result['changed']:
        print(f"\n✅ DRAG WORKED")
    else:
        print(f"\n❌ DRAG FAILED")

    browser.close()
