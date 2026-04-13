"""
Test the hero section resize handle in the admin panel.
Saves screenshots to /home/claudeuser/agent/downloads/
View at: http://147.182.242.54:8081/screenshots/
"""
from playwright.sync_api import sync_playwright
import time, os

OUT      = '/home/claudeuser/agent/downloads'
ADMIN_PW = 'Hb2425hb+'
BASE     = 'http://localhost:8081'
os.makedirs(OUT, exist_ok=True)

def shot(page, name):
    path = f'{OUT}/hero_test_{name}.png'
    page.screenshot(path=path, full_page=False)
    print(f'  📸 {path}')
    print(f'     http://147.182.242.54:8081/screenshots/hero_test_{name}.png')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
    page = ctx.new_page()

    # ── 0. Log in ────────────────────────────────────────────────────────────
    print('\n0. Logging in...')
    page.goto(f'{BASE}/view/admin/', wait_until='networkidle')
    page.fill('#password', ADMIN_PW)
    page.click('#loginBtn')
    page.wait_for_url('**/dashboard.html', timeout=10000)
    print('   ✓ logged in')

    # ── 1. Open pages.html ───────────────────────────────────────────────────
    print('\n1. Opening pages editor...')
    page.goto(f'{BASE}/view/admin/pages.html', wait_until='networkidle')
    time.sleep(3)
    shot(page, '01_pages_loaded')

    # ── 2. Click Home in the page tree ──────────────────────────────────────
    print('\n2. Clicking Home page...')
    clicked = False
    for sel in ['.pg-node--home', '[data-slug="home"]', 'text=Home']:
        try:
            page.click(sel, timeout=3000)
            clicked = True
            print(f'   ✓ clicked: {sel}')
            break
        except:
            pass
    if not clicked:
        # Find any element with "Home" text in the tree
        nodes = page.query_selector_all('.pg-node-name')
        for n in nodes:
            if 'Home' in n.inner_text():
                n.click()
                clicked = True
                print('   ✓ clicked Home node by text')
                break

    # Wait for iframe to load the home page
    time.sleep(4)

    # Check iframe URL
    iframe_el = page.query_selector('#siteFrame')
    if iframe_el:
        frame = page.frame(name='siteFrame')
        print(f'   iframe frames: {[f.url for f in page.frames]}')

    shot(page, '02_home_loaded')

    # ── 3. Enable Edit Mode ──────────────────────────────────────────────────
    print('\n3. Enabling Edit Mode...')
    for sel in ['button:has-text("Edit Mode")', 'button:has-text("Edit")',
                '#editToggle', '#editModeToggle']:
        try:
            page.click(sel, timeout=3000)
            print(f'   ✓ clicked: {sel}')
            break
        except:
            pass

    time.sleep(5)  # wait for overlay scripts to inject
    shot(page, '03_edit_mode_on')

    # ── 4. Inspect the iframe for handles ───────────────────────────────────
    print('\n4. Inspecting iframe for section handles...')
    frames = page.frames
    print(f'   all frames ({len(frames)}):')
    for f in frames:
        print(f'     - {f.url}')

    # Find the site frame (not about:blank, not pages.html itself)
    site_frame = None
    for f in frames:
        if 'index.html' in f.url or 'home' in f.url or (
            f.url != 'about:blank' and 'admin' not in f.url and f != page.main_frame
        ):
            site_frame = f
            break

    if not site_frame and len(frames) > 1:
        site_frame = frames[-1]  # last frame is usually the site iframe

    if site_frame:
        print(f'   using frame: {site_frame.url}')

        handles = site_frame.query_selector_all('[data-rd-section-handle]')
        print(f'   section handles found: {len(handles)}')
        for h in handles:
            sid  = h.get_attribute('data-rd-section-handle')
            vis  = h.is_visible()
            bbox = h.bounding_box()
            print(f'     [{sid}] visible={vis} bbox={bbox}')

        # ── Hero handle deep-dive ────────────────────────────────────────────
        hero_h = site_frame.query_selector('[data-rd-section-handle="hero"]')
        if hero_h:
            bbox = hero_h.bounding_box()
            print(f'\n   HERO HANDLE:')
            print(f'     visible: {hero_h.is_visible()}')
            print(f'     bbox: {bbox}')

            computed = site_frame.evaluate("""() => {
                const h = document.querySelector('[data-rd-section-handle="hero"]');
                if (!h) return null;
                const cs = window.getComputedStyle(h);
                return {
                    zIndex: cs.zIndex,
                    pointerEvents: cs.pointerEvents,
                    position: cs.position,
                    display: cs.display,
                    height: cs.height,
                };
            }""")
            print(f'     computed styles: {computed}')

            # What element is actually ON TOP at the handle's center?
            if bbox:
                cx = bbox['x'] + bbox['width']/2
                cy = bbox['y'] + bbox['height']/2
                top_el = site_frame.evaluate(f"""() => {{
                    const el = document.elementFromPoint({cx}, {cy});
                    if (!el) return null;
                    const cs = window.getComputedStyle(el);
                    return {{
                        tag: el.tagName,
                        id: el.id || '',
                        className: (el.className || '').substring(0, 60),
                        sectionHandle: el.getAttribute('data-rd-section-handle') || '',
                        overlay: el.getAttribute('data-rd-overlay') || '',
                        zIndex: cs.zIndex,
                        pointerEvents: cs.pointerEvents,
                        cursor: cs.cursor,
                    }};
                }}""")
                print(f'\n     elementFromPoint at handle center ({cx:.0f},{cy:.0f}):')
                print(f'     {top_el}')
                if top_el:
                    if top_el.get('sectionHandle') == 'hero':
                        print('     ✅ HANDLE IS ON TOP — pointer events should work')
                    else:
                        print('     ❌ SOMETHING ELSE IS ON TOP — that is the bug')
        else:
            print('   ❌ HERO HANDLE NOT FOUND IN IFRAME')

        # ── Check hero overlay status ────────────────────────────────────────
        overlays = site_frame.query_selector_all('[data-rd-overlay]')
        print(f'\n   image overlays found: {len(overlays)}')
        for ov in overlays:
            cs = site_frame.evaluate(f"""() => {{
                const el = document.querySelector('[data-rd-overlay="' + '{ov.get_attribute("data-rd-overlay")}' + '"]');
                if (!el) return null;
                const s = window.getComputedStyle(el);
                return {{ zIndex: s.zIndex, pointerEvents: s.pointerEvents, cursor: s.cursor }};
            }}""")
            print(f'     overlay[{ov.get_attribute("data-rd-overlay")}] styles={cs}')

    else:
        print('   ❌ No site frame found')

    shot(page, '04_handle_inspection')

    # ── 5. Attempt drag on hero handle ──────────────────────────────────────
    if site_frame:
        hero_h = site_frame.query_selector('[data-rd-section-handle="hero"]')
        if hero_h and hero_h.bounding_box():
            bbox = hero_h.bounding_box()
            print(f'\n5. Drag test on hero handle...')

            h_before = site_frame.evaluate("""() => {
                const s = document.querySelector('section.hero');
                return s ? s.offsetHeight : null;
            }""")
            print(f'   hero height BEFORE: {h_before}px')

            # Get iframe position on the page and scale factor
            iframe_el = page.query_selector('#siteFrame')
            iframe_box = iframe_el.bounding_box() if iframe_el else None
            if iframe_box:
                scale = iframe_box['width'] / 1440
                abs_cx = iframe_box['x'] + bbox['x'] * scale + (bbox['width'] * scale)/2
                abs_cy = iframe_box['y'] + bbox['y'] * scale + (bbox['height'] * scale)/2
                print(f'   iframe scale: {scale:.3f}')
                print(f'   abs drag point: ({abs_cx:.0f}, {abs_cy:.0f})')

                # Move to handle, pause, drag up
                page.mouse.move(abs_cx, abs_cy)
                time.sleep(0.5)
                shot(page, '05_mouse_on_handle')

                cursor = site_frame.evaluate(f"""() => {{
                    const el = document.elementFromPoint({bbox['x'] + bbox['width']/2}, {bbox['y'] + bbox['height']/2});
                    return el ? window.getComputedStyle(el).cursor : 'unknown';
                }}""")
                print(f'   cursor at handle: {cursor}')

                page.mouse.down()
                time.sleep(0.1)
                page.mouse.move(abs_cx, abs_cy - 100, steps=30)
                time.sleep(0.5)
                shot(page, '06_mid_drag')

                h_during = site_frame.evaluate("""() => {
                    const s = document.querySelector('section.hero');
                    return s ? s.offsetHeight : null;
                }""")
                print(f'   hero height DURING drag: {h_during}px')

                page.mouse.up()
                time.sleep(1)
                shot(page, '07_after_drag')

                h_after = site_frame.evaluate("""() => {
                    const s = document.querySelector('section.hero');
                    return s ? s.offsetHeight : null;
                }""")
                print(f'   hero height AFTER: {h_after}px')

                if h_before and h_after and h_after != h_before:
                    print('   ✅ DRAG WORKED — height changed!')
                else:
                    print('   ❌ DRAG FAILED — height unchanged')

    browser.close()
    print('\n\nAll screenshots:')
    for f in sorted(os.listdir(OUT)):
        if f.startswith('hero_test_'):
            print(f'  http://147.182.242.54:8081/screenshots/{f}')
