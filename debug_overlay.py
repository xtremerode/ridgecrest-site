"""Quick debug: check overlay bottom and exact coordinate mapping."""
from playwright.sync_api import sync_playwright
import time

ADMIN_PW = 'Hb2425hb+'
BASE = 'http://localhost:8081'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
    page = ctx.new_page()

    page.goto(f'{BASE}/view/admin/', wait_until='networkidle')
    page.fill('#password', ADMIN_PW)
    page.click('#loginBtn')
    page.wait_for_url('**/dashboard.html', timeout=10000)
    page.goto(f'{BASE}/view/admin/pages.html', wait_until='networkidle')
    time.sleep(2)

    # Click Home
    page.click('.pg-node--home', timeout=5000)
    time.sleep(4)

    # Enable edit mode
    page.click('button:has-text("Edit Mode")', timeout=5000)
    time.sleep(5)

    # Get the site frame
    site_frame = None
    for f in page.frames:
        if '/view/' in f.url and 'admin' not in f.url:
            site_frame = f
            break

    if not site_frame:
        print("NO SITE FRAME FOUND")
        browser.close()
        exit()

    print(f"Frame URL: {site_frame.url}")

    # Check overlay computed styles and actual position
    info = site_frame.evaluate("""() => {
        const ov = document.querySelector('[data-rd-overlay="hero"]');
        const hero = document.querySelector('section.hero');
        const handle = document.querySelector('[data-rd-section-handle="hero"]');

        if (!ov) return { error: 'no overlay found' };

        const ovCS = window.getComputedStyle(ov);
        const heroCS = hero ? window.getComputedStyle(hero) : null;
        const heroRect = hero ? hero.getBoundingClientRect() : null;
        const ovRect = ov.getBoundingClientRect();
        const handleRect = handle ? handle.getBoundingClientRect() : null;

        // elementFromPoint at handle bottom center
        let epHandle = null;
        if (handleRect) {
            const cx = handleRect.left + handleRect.width/2;
            const cy = handleRect.top + handleRect.height/2;
            const el = document.elementFromPoint(cx, cy);
            epHandle = el ? {
                tag: el.tagName,
                overlay: el.getAttribute('data-rd-overlay'),
                sectionHandle: el.getAttribute('data-rd-section-handle'),
                zIndex: window.getComputedStyle(el).zIndex,
                pointerEvents: window.getComputedStyle(el).pointerEvents,
            } : null;
        }

        return {
            ovStyleBottom: ov.style.bottom,
            ovComputedBottom: ovCS.bottom,
            ovPointerEvents: ovCS.pointerEvents,
            ovRect: { top: Math.round(ovRect.top), bottom: Math.round(ovRect.bottom), height: Math.round(ovRect.height) },
            heroRect: heroRect ? { top: Math.round(heroRect.top), bottom: Math.round(heroRect.bottom), height: Math.round(heroRect.height) } : null,
            handleRect: handleRect ? { top: Math.round(handleRect.top), bottom: Math.round(handleRect.bottom), height: Math.round(handleRect.height) } : null,
            elementAtHandleCenter: epHandle,
            heroOffsetHeight: hero ? hero.offsetHeight : null,
            heroInlineStyle: hero ? hero.style.cssText : null,
        };
    }""")

    import json
    print(json.dumps(info, indent=2))

    browser.close()
