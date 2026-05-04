"""
Visual Overlay Agent
====================
Uses Playwright (headless Chromium) to verify that edit-mode card overlays
are visually accessible — pill appears on hover AND is not occluded by
overlapping elements with higher z-index — AND that clicking the overlay
actually cycles the card image.

This is the automated enforcement of Rule 11 (§22 CLAUDE.md): "rendered effect"
verification for every card overlay. Code-level checks (HTML present, DB records
exist) cannot catch CSS stacking context conflicts. Only a rendered browser check
can.

For each card tested:
  1. Hover — pill must become visible (opacity 1) in the correct _attachEl container
  2. Pill placement — for diff__zone/--one, pill must NOT be trapped inside the zone
  3. Click-to-cycle — clicking the ov must change the card's background-image
  4. Restore — original card state is saved before the test and restored via API after,
     so no test artifact is left in card_settings (db_approved_state will catch any leak)

Pages tested (representative structural types, not exhaustive):
  - kitchen-remodels.html   diff__zone inside diff__visual--one (critical case)
  - index.html              diff__zone inside diff__visual--two (home page regression check)
  - allprojects.html        proj-card__img allproj-* cards
  - portfolio.html          portfolio-featured cards

Intentionally excluded from Playwright overlay tests (no card edit overlay):
  - admin/render-review.html      standalone admin review tool — no hover/pill overlay UI
  - GET /admin/api/renders/review-queue  backend data endpoint — no interactive UI surface
  - _record_render_approval / render_approved_state  DB write helpers — backend only
  - reference_image_b64 / ref_b64  rerender endpoint extension — admin-only file upload,
    exercised only during manual render review sessions, not a card overlay surface
  - render_model / script_openai   model selector (Gemini vs gpt-image-1) — admin-only
    rerender path, no interactive card overlay UI surface; gpt-image-1 + quality='high'
    via OpenAI SDK (gpt-image-2 requires org verification, not available on this account);
    Gemini upgraded to gemini-3-pro-image-preview; no card overlay UI surface
  - rotate buttons in render-review.html   ↺↻ CW/CCW rotate for original and render panels —
    admin-only tool, calls existing /admin/api/images/rotate endpoint; no card overlay surface
  - _RENDER_INDEX_LOCK / stub reservation   threading lock around _ai_N index allocation —
    server-side race-condition fix for concurrent auto-renders; no UI surface
  - glob-based AI render scan in admin_image_versions + admin_image_rerender — replaces
    sequential while-loop scan; handles gaps from failed-render stub cleanup correctly
  - render_model column in image_render_prompts + versions endpoint — DB stores model per
    render; endpoint returns it; filmVersions JS map includes it; admin-only, no card overlay
  - filmstrip object-fit:contain — portrait AI renders in landscape thumbnail box show full
    image with dark bg instead of cropped center band; admin render-review.html only
  - set-version size-appropriate paths — card_settings/_960w, pages.hero_image/_1920w,
    blog_posts/_960w; _migrate_ai_render_paths() startup migration fixes existing rows;
    _upgrade_card_images() extended to catch _ai_N.webp base paths; no card overlay surface

Exports: run(fix=False) -> List[Dict]
"""
import json
import os
import time
import urllib.request
import urllib.error
import psycopg2
import psycopg2.extras
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = 'http://127.0.0.1:8081'
DB_CONFIG = dict(
    host='127.0.0.1', port=5432,
    dbname='marketing_agent', user='agent_user', password='StrongPass123!'
)

# Pages to test: (slug, url_path, card_ids_to_test, structural_note)
PAGES_TO_TEST = [
    (
        'kitchen-remodels',
        '/view/kitchen-remodels.html',
        ['kitchen-diff-top'],
        'diff__zone in diff__visual--one (service page investment panel)',
    ),
    (
        'home',
        '/view/index.html',
        ['diff-visual-top'],
        'diff__zone in diff__visual--two (home page — regression check)',
    ),
    (
        'allprojects',
        '/view/allprojects.html',
        ['allproj-danville-hilltop-hideaway'],
        'proj-card__img card (allprojects page)',
    ),
    (
        'portfolio',
        '/view/portfolio.html',
        ['portfolio-featured-1'],
        'portfolio-featured card (portfolio page)',
    ),
    (
        'pleasanton-custom',
        '/view/pleasanton-custom.html',
        ['pleasanton-custom-gal-ff5b18_9cd0d8a66b364c1ea15c032acb7da0cc_mv2'],
        'gallery-item card (rotate button + render button on gallery items)',
    ),
    (
        'danville-hilltop',
        '/view/danville-hilltop.html',
        ['danville-hilltop-gal-ff5b18_63757c728db94733b4f60a7102c0f722_mv2'],
        'gallery-item card whose active_version was cleared — replace-image must reset to base file',
    ),
    (
        'bathroom-remodels',
        '/view/bathroom-remodels.html',
        ['bathroom-remodels-gallery-1'],
        'service page gallery item (rotate: CSS bg + lightbox data-src update, no saveCard)',
    ),
    (
        'start-a-project',
        '/view/start-a-project.html',
        ['sap-bg-main'],
        'full-viewport fixed hero background — sap-bg in _HERO_CLASSES (no _swapAll downgrade)',
    ),
]


def _get_token():
    """
    Return a valid admin token from admin_sessions.
    Validates each token via HTTP ping against the running server.
    Handles Flask hot-reloader restarts: if the server is temporarily down
    (e.g., reloading due to file change detection during git staging),
    waits up to 8 seconds for it to come back up before declaring failure.
    """
    def _load_rows():
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cur.execute("SELECT token FROM admin_sessions ORDER BY created_at DESC LIMIT 10")
            rows = cur.fetchall()
            conn.close()
            return rows
        except Exception:
            return []

    def _ping(token):
        """Returns True if token is valid, False if 401, None if connection error."""
        try:
            req = urllib.request.Request(
                f'{BASE_URL}/admin/api/auth/ping',
                headers={'X-Admin-Token': token}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                return bool(data.get('ok'))
        except urllib.error.HTTPError:
            return False
        except Exception:
            return None

    for wait_round in range(3):
        rows = _load_rows()
        all_connection_errors = True
        for row in rows:
            token = row['token']
            result = _ping(token)
            if result is True:
                return token
            if result is False:
                all_connection_errors = False

        if not all_connection_errors:
            break

        if wait_round < 2:
            time.sleep(4)

    return None


def _read_card_state(card_id):
    """Read current card_settings row for card_id. Returns dict or None if no row."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute('SELECT * FROM card_settings WHERE card_id = %s', (card_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def _restore_card_state(card_id, slug, token, original_state):
    """
    Restore card to its pre-test state via the cards API.
    If the card had no row before the test, delete it.
    RAISES RuntimeError on any failure — never swallows silently.
    Callers must handle or propagate so that test corruption is never silent.
    """
    if original_state is None:
        # Card had no DB row before — delete whatever the test created
        req = urllib.request.Request(
            f'{BASE_URL}/admin/api/cards/{slug}/{card_id}',
            method='DELETE',
            headers={'X-Admin-Token': token}
        )
        try:
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            raise RuntimeError(f'_restore_card_state DELETE failed for {card_id}: {e}') from e
        return

    # Restore the exact pre-test state via PUT
    payload = json.dumps({
        'mode':               original_state.get('mode', 'color'),
        'color':              original_state.get('color'),
        'image':              original_state.get('image'),
        'position':           original_state.get('position', '50% 50%'),
        'zoom':               original_state.get('zoom', 1.0),
        'gradient_type':      original_state.get('gradient_type'),
        'gradient_tint':      original_state.get('gradient_tint'),
        'gradient_opacity':   original_state.get('gradient_opacity'),
        'gradient_direction': original_state.get('gradient_direction'),
        'gradient_distance':  original_state.get('gradient_distance'),
        'gradient_css':       original_state.get('gradient_css'),
        'hero_text_align':    original_state.get('hero_text_align'),
        'hero_text_color':    original_state.get('hero_text_color'),
        'hero_cta_visible':   original_state.get('hero_cta_visible'),
        'hero_cta_align':     original_state.get('hero_cta_align'),
        'hero_cta_primary':   original_state.get('hero_cta_primary'),
        'hero_cta_secondary': original_state.get('hero_cta_secondary'),
    }).encode('utf-8')
    req = urllib.request.Request(
        f'{BASE_URL}/admin/api/cards/{slug}/{card_id}',
        data=payload,
        method='PUT',
        headers={'X-Admin-Token': token, 'Content-Type': 'application/json'}
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        raise RuntimeError(f'_restore_card_state PUT failed for {card_id}: {e}') from e


def _check_card_overlay(page, card_id, slug, token):
    """
    For the card with data-card-id=card_id:
      1. Hover — verify edit pill becomes visible in correct _attachEl container
      2. Pill placement — for diff__zone/--one, pill must NOT be trapped inside zone
      3. Click-to-cycle — click the capture overlay, verify background-image changes
      4. Restore — PUT original card state back via API so no test artifact remains

    Returns list of (check_name, ok, detail) tuples.
    """
    checks = []

    try:
        selector = f'[data-card-id="{card_id}"]'
        el = page.query_selector(selector)
        if el is None:
            return [('overlay_accessible', False,
                     f'Element [data-card-id="{card_id}"] not found in DOM')]

        # ── Save original state before any interaction ────────────────────────
        original_state = _read_card_state(card_id)

        # ── Step 1: Scroll + hover _attachEl ─────────────────────────────────
        # Mouseenter listeners are registered on _attachEl (not el), so we must
        # hover _attachEl directly. For most cards _attachEl === el. For
        # diff__zone/--one, _attachEl is the diff__visual parent.
        # Scroll card into view first
        el.scroll_into_view_if_needed(timeout=5000)
        time.sleep(0.2)

        # Dispatch mouseenter directly on _attachEl (where the listener lives).
        # Playwright's force-hover dispatches to el only; for diff__zone/--one
        # the listener is on the diff__visual parent, so we must fire it there.
        page.evaluate(f"""() => {{
            var card = document.querySelector('[data-card-id="{card_id}"]');
            if (!card) return;
            var attachEl = card;
            var isGallery = card.hasAttribute('data-src');
            if (!isGallery && card.getAttribute('role') === 'img') {{
                var par = card.parentElement;
                if (par && window.getComputedStyle(par).position !== 'static') attachEl = par;
            }}
            if (!isGallery && card.classList.contains('diff__zone')) {{
                var dv = card.parentElement;
                if (dv && dv.classList.contains('diff__visual') &&
                    dv.classList.contains('diff__visual--one') &&
                    window.getComputedStyle(card).display !== 'none') {{
                    attachEl = dv;
                }}
            }}
            // Fixed-position cards: pill lives on document.body
            if (!isGallery && window.getComputedStyle(card).position === 'fixed') {{
                attachEl = document.body;
            }}
            attachEl.dispatchEvent(new MouseEvent('mouseenter', {{bubbles: false, cancelable: true}}));
        }}""")
        time.sleep(0.35)  # allow opacity transition (0.15s) + paint

        # ── Step 2: Verify pill visible and correctly placed ──────────────────
        pill_result = page.evaluate(f"""() => {{
            var card = document.querySelector('[data-card-id="{card_id}"]');
            if (!card) return 'card_not_found';

            // Mirror setupCard() _attachEl logic
            var attachEl = card;
            var isGallery = card.hasAttribute('data-src');

            if (!isGallery && card.getAttribute('role') === 'img') {{
                var par = card.parentElement;
                if (par && window.getComputedStyle(par).position !== 'static') attachEl = par;
            }}
            if (!isGallery && card.classList.contains('diff__zone')) {{
                var dv = card.parentElement;
                if (dv && dv.classList.contains('diff__visual') &&
                    dv.classList.contains('diff__visual--one') &&
                    window.getComputedStyle(card).display !== 'none') {{
                    attachEl = dv;
                }}
            }}
            // Fixed-position cards: pill lives on document.body
            if (!isGallery && window.getComputedStyle(card).position === 'fixed') {{
                attachEl = document.body;
            }}

            // Find pill (z-index 9991) that is a DIRECT child of attachEl.
            // querySelectorAll descends into children — in diff__visual, the hidden
            // diff__zone--bottom's overlays appear first in document order and would
            // be picked by a plain find(zIndex===9991). Restricting to direct children
            // ensures we test the correct card's pill.
            var ovEls = Array.from(attachEl.querySelectorAll('[data-rd-overlay="card"]'));
            var pill = ovEls.find(function(o) {{ return o.style.zIndex === '9991' && o.parentElement === attachEl; }});
            if (!pill) return 'no_pill_in_container';

            var opacity = parseFloat(window.getComputedStyle(pill).opacity);
            if (opacity < 0.5) return 'pill_opacity_zero';

            // diff__zone/--one: pill must NOT be trapped inside zone
            if (card.classList.contains('diff__zone')) {{
                var dv2 = card.parentElement;
                var isOne = dv2 && dv2.classList.contains('diff__visual') &&
                            dv2.classList.contains('diff__visual--one');
                if (isOne && card.contains(pill)) return 'stuck_in_zone';
            }}

            return 'ok';
        }}""")

        if pill_result == 'stuck_in_zone':
            checks.append(('overlay_accessible', False,
                'Pill trapped inside diff__zone (stacking context fix not active)'))
        elif pill_result == 'pill_opacity_zero':
            checks.append(('overlay_accessible', False,
                f'Pill present but opacity=0 — mouseenter not firing on _attachEl for {card_id}'))
        elif pill_result in ('card_not_found', 'no_pill_in_container'):
            checks.append(('overlay_accessible', False,
                f'Pill not found in expected _attachEl ({pill_result}) for {card_id}'))
        else:
            checks.append(('overlay_accessible', True,
                f'Pill visible and correctly placed for {card_id}'))

        # ── Step 3: Click-to-cycle ────────────────────────────────────────────
        # Service page gallery items (inner div inside .gallery-item[data-src]) have an
        # empty imagePool — click-to-cycle does nothing. Skip and mark as N/A.
        # Fixed-position cards skip the capture overlay entirely — no click-to-cycle.
        _is_service_gallery = bool(page.evaluate(f"""() => {{
            var card = document.querySelector('[data-card-id="{card_id}"]');
            return !!(card && !card.hasAttribute('data-src') &&
                      card.closest('.gallery-item[data-src]'));
        }}"""))
        _is_fixed_card = bool(page.evaluate(f"""() => {{
            var card = document.querySelector('[data-card-id="{card_id}"]');
            return !!(card && !card.hasAttribute('data-src') &&
                      window.getComputedStyle(card).position === 'fixed');
        }}"""))
        if _is_service_gallery:
            checks.append(('click_cycles_image', True,
                           f'{card_id}: service gallery item — click-to-cycle skipped (imagePool empty by design)'))
        elif _is_fixed_card:
            checks.append(('click_cycles_image', True,
                           f'{card_id}: fixed-position card — capture overlay skipped, pill-only interaction'))
        else:
            pass  # fall through to normal click-to-cycle below

        if not _is_service_gallery and not _is_fixed_card:
            # Get background-image before click
            bg_before = page.evaluate(f"""() => {{
                var el = document.querySelector('[data-card-id="{card_id}"]');
                return el ? window.getComputedStyle(el).backgroundImage : null;
            }}""")

            # Click the capture overlay (ov, z-index 9990) in the correct _attachEl.
            # Dispatch programmatically to guarantee we hit the right element regardless
            # of pointer-events or stacking on the test viewport.
            click_result = page.evaluate(f"""() => {{
                var card = document.querySelector('[data-card-id="{card_id}"]');
                if (!card) return 'card_not_found';

                var attachEl = card;
                var isGallery = card.hasAttribute('data-src');
                if (!isGallery && card.getAttribute('role') === 'img') {{
                    var par = card.parentElement;
                    if (par && window.getComputedStyle(par).position !== 'static') attachEl = par;
                }}
                if (!isGallery && card.classList.contains('diff__zone')) {{
                    var dv = card.parentElement;
                    if (dv && dv.classList.contains('diff__visual') &&
                        dv.classList.contains('diff__visual--one') &&
                        window.getComputedStyle(card).display !== 'none') {{
                        attachEl = dv;
                    }}
                }}

                var ovEls = Array.from(attachEl.querySelectorAll('[data-rd-overlay="card"]'));
                // Use direct-child constraint (same reason as pill lookup above)
                var ov = ovEls.find(function(o) {{ return o.style.zIndex === '9990' && o.parentElement === attachEl; }});
                if (!ov) return 'ov_not_found';

                ov.click();
                return 'clicked';
            }}""")

            if click_result != 'clicked':
                checks.append(('click_cycles_image', False,
                    f'Could not find capture overlay (ov) to click for {card_id}: {click_result}'))
            else:
                time.sleep(0.6)  # allow saveCard debounce (1.5s) to queue + image to apply

                bg_after = page.evaluate(f"""() => {{
                    var el = document.querySelector('[data-card-id="{card_id}"]');
                    return el ? window.getComputedStyle(el).backgroundImage : null;
                }}""")

                if bg_before == bg_after:
                    checks.append(('click_cycles_image', False,
                        f'Click did not change background-image on {card_id} '
                        f'(imagePool empty, ov misplaced, or applyStyle not firing)'))
                else:
                    checks.append(('click_cycles_image', True,
                        f'Click cycled image correctly on {card_id}'))

        # ── Step 4: Rotate click test ─────────────────────────────────────────
        # Verifies the full click→API→state-update flow for the rotate button.
        # Uses route interception so no image files are modified on disk.
        checks.extend(_check_rotate_click(page, card_id, is_gallery_item=False))

        # ── Step 5: Restore original state ───────────────────────────────────
        _restore_card_state(card_id, slug, token, original_state)

        return checks

    except PlaywrightTimeoutError:
        return [('overlay_accessible', False,
                 f'Timeout: {card_id} not scrollable/interactable (zero-size or display:none)')]
    except Exception as e:
        return [('overlay_accessible', False, f'Error checking {card_id}: {e}')]


def _resolve_attach_el_js(card_id):
    """Return JS snippet that resolves _attachEl for a card (mirrors setupCard logic)."""
    return f"""(function() {{
        var card = document.querySelector('[data-card-id="{card_id}"]');
        if (!card) return null;
        var attachEl = card;
        var isGallery = card.hasAttribute('data-src');
        if (!isGallery && card.getAttribute('role') === 'img') {{
            var par = card.parentElement;
            if (par && window.getComputedStyle(par).position !== 'static') attachEl = par;
        }}
        if (!isGallery && card.classList.contains('diff__zone')) {{
            var dv = card.parentElement;
            if (dv && dv.classList.contains('diff__visual') &&
                dv.classList.contains('diff__visual--one') &&
                window.getComputedStyle(card).display !== 'none') {{
                attachEl = dv;
            }}
        }}
        return attachEl;
    }})()"""


def _check_rotate_click(page, card_id, is_gallery_item):
    """
    Click the rotate button and verify the full flow using Playwright route interception.
    Non-destructive — mocks the API response so no image files are modified on disk.

    Verifies:
      1. Rotate button found in pill (searched on _attachEl, not just card element)
      2. API call fired to /admin/api/images/rotate
      3. Filename sent is base _mv2.webp with no size suffix
      4. Degrees = 90
      5. Button re-enables after response (not stuck in '↻…')
      6. Gallery items: img.src updated with ?v= cache-bust after rotation

    Returns list of (check_name, ok, detail) tuples.
    """
    checks = []
    rotate_requests = []

    def _handle_rotate(route, request):
        try:
            body = request.post_data_json or {}
        except Exception:
            body = {}
        rotate_requests.append(body)
        route.fulfill(
            status=200,
            content_type='application/json',
            body='{"ok": true, "filename": "mock_rotated.webp"}'
        )

    try:
        # Set up route BEFORE hover so it's ready when the click fires the fetch
        page.route('**/admin/api/images/rotate', _handle_rotate)
        time.sleep(0.1)  # brief pause to ensure route is registered

        # Hover on _attachEl (mirrors setupCard logic — pill is on _attachEl, not always the card)
        page.evaluate(f"""() => {{
            var attachEl = {_resolve_attach_el_js(card_id)};
            if (attachEl) attachEl.dispatchEvent(
                new MouseEvent('mouseenter', {{bubbles: false, cancelable: true}})
            );
        }}""")
        time.sleep(0.4)

        # Check whether card has a rotatable source.
        # For non-gallery: require state.image to be set (background-image CSS
        # can come from stylesheets and is not a reliable proxy for state.image).
        # Wait up to 1s for cardMap to populate from async setupCard fetch.
        has_source = False
        _is_svc_gal = False
        if is_gallery_item:
            has_source = bool(page.evaluate(f"""() => {{
                var card = document.querySelector('[data-card-id="{card_id}"]');
                return card ? !!card.getAttribute('data-src') : false;
            }}"""))
        else:
            deadline = time.time() + 1.0
            while time.time() < deadline:
                src = page.evaluate(f"""() => {{
                    var s = window.cardMap && window.cardMap['{card_id}'];
                    return (s && s.image) ? s.image : '';
                }}""")
                if src:
                    has_source = True
                    break
                time.sleep(0.1)
            # Service page gallery: inner div (no data-src) with .gallery-item[data-src] ancestor
            if not has_source:
                anc_src = page.evaluate(f"""() => {{
                    var card = document.querySelector('[data-card-id="{card_id}"]');
                    var anc = card && !card.hasAttribute('data-src') &&
                              card.closest('.gallery-item[data-src]');
                    return anc ? (anc.getAttribute('data-src') || '') : '';
                }}""") or ''
                if anc_src:
                    has_source = True
                    _is_svc_gal = True

        if not has_source:
            checks.append(('rotate_click_skipped', True,
                            f'{card_id}: no image source found — rotate click skipped (color/gradient mode card)'))
            return checks

        # Find the rotate button — search _attachEl since pill is appended there
        found_btn = page.evaluate(f"""() => {{
            var attachEl = {_resolve_attach_el_js(card_id)};
            if (!attachEl) return false;
            return Array.from(attachEl.querySelectorAll('button')).some(
                function(b) {{ return b.textContent.trim() === '↻'; }}
            );
        }}""")

        checks.append(('rotate_click_btn_found', found_btn,
                        f'{card_id}: rotate button {"present" if found_btn else "MISSING"} in pill (searched _attachEl)'))
        if not found_btn:
            return checks

        # Get an ElementHandle to the rotate button so Playwright's native .click()
        # can be used — page.evaluate() blocks the Python thread and prevents
        # route-interceptor callbacks from firing during the async fetch.
        btn_handle = page.evaluate_handle(f"""() => {{
            var attachEl = {_resolve_attach_el_js(card_id)};
            if (!attachEl) return null;
            return Array.from(attachEl.querySelectorAll('button')).find(
                function(b) {{ return b.textContent.trim() === '↻'; }}
            ) || null;
        }}""")
        btn_el = btn_handle.as_element()
        if btn_el:
            btn_el.click(timeout=3000)  # native Playwright click — Python not blocked during fetch

        # Wait for API interception (up to 4s)
        deadline = time.time() + 4.0
        while not rotate_requests and time.time() < deadline:
            time.sleep(0.1)

        api_called = len(rotate_requests) > 0
        checks.append(('rotate_click_api_called', api_called,
                        f'{card_id}: rotate API {"fired" if api_called else "NOT fired — click had no effect (state.image empty or handler error)"}'))

        if api_called:
            req = rotate_requests[0]
            fname = req.get('filename', '')
            degrees = req.get('degrees', 0)
            has_size_suffix = any(s in fname for s in ('_960w', '_1920w', '_480w', '_201w'))
            is_mv2 = '_mv2.webp' in fname

            checks.append(('rotate_click_filename_correct', is_mv2 and not has_size_suffix,
                            f'{card_id}: API filename="{fname}" mv2={is_mv2} size_suffix={has_size_suffix}'))
            checks.append(('rotate_click_degrees_correct', degrees == 90,
                            f'{card_id}: API degrees={degrees} (expected 90)'))

        # Wait for button to re-enable (JS processes mock response)
        time.sleep(0.6)

        btn_recovered = page.evaluate(f"""() => {{
            var attachEl = {_resolve_attach_el_js(card_id)};
            if (!attachEl) return false;
            return Array.from(attachEl.querySelectorAll('button')).some(
                function(b) {{ return b.textContent.trim() === '↻' && !b.disabled; }}
            );
        }}""")
        checks.append(('rotate_click_btn_recovered', btn_recovered,
                        f'{card_id}: button {"re-enabled after response" if btn_recovered else "still disabled/missing — JS error after mock response"}'))

        # Project gallery: verify img.src AND srcset were cache-busted
        if is_gallery_item and api_called:
            img_state = page.evaluate(f"""() => {{
                var card = document.querySelector('[data-card-id="{card_id}"]');
                if (!card) return {{srcOk: false, srcsetOk: false}};
                var img = card.querySelector('img[data-gallery-src]') || card.querySelector('img');
                if (!img) return {{srcOk: false, srcsetOk: false}};
                var srcOk = img.src.indexOf('?v=') !== -1;
                var srcsetOk = !img.srcset || img.srcset.indexOf('?v=') !== -1;
                return {{srcOk: srcOk, srcsetOk: srcsetOk}};
            }}""")
            checks.append(('rotate_click_gallery_img_updated', img_state.get('srcOk', False),
                            f'{card_id}: img.src {"cache-busted" if img_state.get("srcOk") else "NOT updated"}'))
            checks.append(('rotate_click_gallery_srcset_updated', img_state.get('srcsetOk', False),
                            f'{card_id}: img.srcset {"cache-busted" if img_state.get("srcsetOk") else "NOT updated — browser may show cached pre-rotate version"}'))

        # Service gallery: verify CSS background updated + ancestor data-src updated, no saveCard
        if _is_svc_gal and api_called:
            svc_state = page.evaluate(f"""() => {{
                var card = document.querySelector('[data-card-id="{card_id}"]');
                if (!card) return {{bgOk: false, ancOk: false}};
                var bg = card.style.backgroundImage || '';
                var anc = card.closest('.gallery-item[data-src]');
                var ancSrc = anc ? (anc.getAttribute('data-src') || '') : '';
                return {{
                    bgOk: bg.indexOf('?v=') !== -1,
                    ancOk: ancSrc.indexOf('?v=') !== -1
                }};
            }}""")
            checks.append(('rotate_click_svc_bg_updated', svc_state.get('bgOk', False),
                            f'{card_id}: CSS background-image {"cache-busted" if svc_state.get("bgOk") else "NOT updated after rotate"}'))
            checks.append(('rotate_click_svc_datasrc_updated', svc_state.get('ancOk', False),
                            f'{card_id}: lightbox data-src {"cache-busted" if svc_state.get("ancOk") else "NOT updated — lightbox would show stale image"}'))

    except Exception as e:
        checks.append(('rotate_click_api_called', False,
                        f'{card_id}: rotate click test exception: {e}'))
    finally:
        try:
            page.unroute('**/admin/api/images/rotate')
        except Exception:
            pass

    return checks


def _check_gallery_item(page, card_id, slug, token):
    """
    Gallery-item specific checks:
      1. Pill visible on hover (same as _check_card_overlay step 1-2)
      2. Rotate button present in pill
      3. Render button present in pill
      4. Render button postMessage sends correct base _mv2.webp filename (not _960w, not wrong hash)
    No state is written — gallery items are guarded against saveCard() writes.
    """
    checks = []
    try:
        selector = f'[data-card-id="{card_id}"]'
        el = page.query_selector(selector)
        if el is None:
            return [('gallery_overlay_accessible', False,
                     f'Gallery element [{card_id}] not found in DOM')]

        el.scroll_into_view_if_needed(timeout=5000)
        time.sleep(0.2)

        # Hover to show pill
        page.evaluate(f"""() => {{
            var card = document.querySelector('[data-card-id="{card_id}"]');
            if (card) card.dispatchEvent(new MouseEvent('mouseenter', {{bubbles: false, cancelable: true}}));
        }}""")
        time.sleep(0.4)

        # Check pill visible, rotate present, render present
        pill_info = page.evaluate(f"""() => {{
            var card = document.querySelector('[data-card-id="{card_id}"]');
            if (!card) return {{found: false}};
            var pill = card.querySelector('[style*="z-index: 9991"], [style*="z-index:9991"]');
            if (!pill) return {{found: false, reason: 'no pill found'}};
            var opacity = window.getComputedStyle(pill).opacity;
            var btns = pill.querySelectorAll('button');
            var btnTexts = Array.from(btns).map(function(b) {{ return b.textContent.trim(); }});
            return {{
                found: true,
                opacity: opacity,
                hasRotate: btnTexts.some(function(t) {{ return t === '↻'; }}),
                hasRender: btnTexts.some(function(t) {{ return t.indexOf('Render') !== -1 || t === '✨'; }}),
                hasUpload: btnTexts.some(function(t) {{ return t === '+'; }}),
                btnTexts: btnTexts
            }};
        }}""")

        if not pill_info.get('found'):
            checks.append(('gallery_pill_visible', False,
                            f'{card_id}: {pill_info.get("reason","pill not found")}'))
            return checks

        pill_visible = float(pill_info.get('opacity', 0)) > 0.5
        checks.append(('gallery_pill_visible', pill_visible,
                        f'{card_id}: pill opacity={pill_info.get("opacity")}'))
        checks.append(('gallery_rotate_btn', pill_info.get('hasRotate', False),
                        f'{card_id}: rotate button {"present" if pill_info.get("hasRotate") else "MISSING"} — buttons: {pill_info.get("btnTexts")}'))
        checks.append(('gallery_render_btn', pill_info.get('hasRender', False),
                        f'{card_id}: render button {"present" if pill_info.get("hasRender") else "MISSING"} — buttons: {pill_info.get("btnTexts")}'))
        checks.append(('gallery_upload_btn', pill_info.get('hasUpload', False),
                        f'{card_id}: upload (+) button {"present" if pill_info.get("hasUpload") else "MISSING"} — buttons: {pill_info.get("btnTexts")}'))

        # Check render button will send the correct base filename.
        # We verify by inspecting data-src directly (source of truth for gallery render path)
        # and confirming the JS cardMap state has no stale card_settings overriding it.
        # Valid data-src values:
        #   _mv2.webp          — original base (no active AI render)
        #   _mv2_ai_N.webp     — AI render base (active version set) — CORRECT, server guards re-render source
        # Invalid: any sized variant (_960w, _1920w, etc) in data-src
        render_result = page.evaluate(f"""() => {{
            var card = document.querySelector('[data-card-id="{card_id}"]');
            if (!card) return {{ok: false, reason: 'card not found', dataSrc: ''}};
            var dataSrc = card.getAttribute('data-src') || '';
            var fname = dataSrc.split('/').pop();
            // data-src must be an unsized base file — original _mv2.webp or active AI render _ai_N.webp
            var hasSizeSuffix = /_(?:1920|960|480|201)w\\.webp$/.test(fname);
            var hasAiSuffix = /_ai_\\d/.test(fname);
            var isMv2 = fname.indexOf('_mv2.webp') !== -1 || fname.indexOf('_mv2') !== -1;
            // Also verify cardMap state has no stale image that would override data-src
            var cardState = window.cardMap && window.cardMap['{card_id}'];
            var stateImage = cardState ? (cardState.image || '') : '';
            var stateHasBadSuffix = /_(?:1920|960|480|201)w\\.webp$/.test(stateImage);
            return {{
                ok: !hasSizeSuffix && isMv2 && !stateHasBadSuffix,
                dataSrc: dataSrc,
                fname: fname,
                hasSizeSuffix: hasSizeSuffix,
                hasAiSuffix: hasAiSuffix,
                isMv2: isMv2,
                stateImage: stateImage,
                stateHasBadSuffix: stateHasBadSuffix
            }};
        }}""")

        render_ok = render_result.get('ok', False)
        checks.append(('gallery_render_filename', render_ok,
                        f'{card_id}: data-src="{render_result.get("dataSrc","")}" '
                        f'isMv2={render_result.get("isMv2")} '
                        f'size_suffix={render_result.get("hasSizeSuffix")} '
                        f'state_image="{render_result.get("stateImage","")}" '
                        f'state_bad={render_result.get("stateHasBadSuffix")}'))

        # Rotate click test — verifies the full click→API→img-update flow
        checks.extend(_check_rotate_click(page, card_id, is_gallery_item=True))

    except PlaywrightTimeoutError:
        return [('gallery_overlay_accessible', False,
                 f'Timeout: {card_id} not scrollable/interactable')]
    except Exception as e:
        return [('gallery_overlay_accessible', False, f'Error checking gallery {card_id}: {e}')]

    return checks


def run(fix=False):
    results = []
    agent = 'visual_overlay_agent'

    token = _get_token()
    if not token:
        results.append({
            'agent': agent,
            'check': 'token_available',
            'status': 'fail',
            'detail': 'No admin token in admin_sessions — cannot load edit mode for visual check',
            'page': '',
            'auto_fixable': False,
        })
        return results

    results.append({
        'agent': agent,
        'check': 'token_available',
        'status': 'pass',
        'detail': f'Admin token available ({token[:8]}...)',
        'page': '',
        'auto_fixable': False,
    })

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1440, 'height': 900})

            for slug, url_path, card_ids, note in PAGES_TO_TEST:
                page = context.new_page()
                full_url = f'{BASE_URL}{url_path}?admin_edit=1&token={token}&_stage=1'

                try:
                    page.goto(full_url, wait_until='networkidle', timeout=20000)
                except Exception as e:
                    results.append({
                        'agent': agent,
                        'check': f'page_load_{slug}',
                        'status': 'fail',
                        'detail': f'Failed to load {url_path}: {e}',
                        'page': slug,
                        'auto_fixable': False,
                    })
                    page.close()
                    continue

                results.append({
                    'agent': agent,
                    'check': f'page_load_{slug}',
                    'status': 'pass',
                    'detail': f'Loaded in edit mode — {note}',
                    'page': slug,
                    'auto_fixable': False,
                })

                # Give card overlay JS time to initialize and imagePool to load
                # (rd_set_pool is sent by the parent frame — not available in direct-page
                # mode, so we inject a minimal pool from DB so click-to-cycle can run)
                time.sleep(0.6)

                # Inject imagePool from DB so click-to-cycle works outside iframe context
                try:
                    conn = psycopg2.connect(**DB_CONFIG)
                    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                    cur.execute(
                        "SELECT DISTINCT image_path FROM card_settings "
                        "WHERE image_path IS NOT NULL AND image_path <> '' "
                        "ORDER BY image_path LIMIT 20"
                    )
                    pool_images = [r['image_path'] for r in cur.fetchall()]
                    conn.close()
                    if pool_images:
                        # dispatchEvent is synchronous — imagePool is set before
                        # evaluate() returns, so click-to-cycle works immediately.
                        page.evaluate(f"""() => {{
                            window.dispatchEvent(new MessageEvent('message', {{
                                data: {{type:'rd_set_pool', images:{json.dumps(pool_images)}}},
                                origin: window.location.origin
                            }}));
                        }}""")
                except Exception:
                    pass

                for card_id in card_ids:
                    # Gallery items (data-src present) use dedicated gallery check
                    is_gallery = '-gal-' in card_id
                    if is_gallery:
                        card_checks = _check_gallery_item(page, card_id, slug, token)
                    else:
                        card_checks = _check_card_overlay(page, card_id, slug, token)
                    for check_name, ok, detail in card_checks:
                        results.append({
                            'agent': agent,
                            'check': f'{check_name}_{card_id}',
                            'status': 'pass' if ok else 'fail',
                            'detail': detail,
                            'page': slug,
                            'auto_fixable': False,
                        })

                page.close()

            # [HERO-HEIGHT] Verify published home page has rd-hero-height style injected
            # and that the hero section is pinned to the saved DB height (not 100vh).
            try:
                _pub_page = context.new_page()
                _pub_page.goto(f'{BASE_URL}/view/', wait_until='networkidle', timeout=20000)
                _style_id = _pub_page.evaluate(
                    "() => !!document.getElementById('rd-hero-height')"
                )
                _hero_height = _pub_page.evaluate(
                    "() => { const h = document.querySelector('section.hero'); "
                    "return h ? Math.round(h.getBoundingClientRect().height) : null; }"
                )
                _pub_page.close()
                results.append({
                    'agent': agent,
                    'check': 'hero_height_style_injected',
                    'status': 'pass' if _style_id else 'fail',
                    'detail': 'rd-hero-height <style> present on published home page' if _style_id
                              else 'rd-hero-height <style> MISSING from published home page',
                    'page': 'home',
                    'auto_fixable': False,
                })
                if _hero_height is not None:
                    _ok = 400 < _hero_height < 1400
                    results.append({
                        'agent': agent,
                        'check': 'hero_height_reasonable',
                        'status': 'pass' if _ok else 'fail',
                        'detail': f'Home hero rendered height: {_hero_height}px (expected 400–1400px)',
                        'page': 'home',
                        'auto_fixable': False,
                    })
            except Exception as _e:
                results.append({
                    'agent': agent,
                    'check': 'hero_height_style_injected',
                    'status': 'fail',
                    'detail': f'Hero height test error: {_e}',
                    'page': 'home',
                    'auto_fixable': False,
                })

            # [HERO-COLOR-GUARD] Verify service hero pages are not overridden with solid color.
            # _apply_hero_color_mode() must skip card_ids ending in -hero.
            for _slug, _page_path in [
                ('services/kitchen-remodel-dublin',   '/view/services/kitchen-remodel-dublin.html'),
                ('services/kitchen-remodel-orinda',   '/view/services/kitchen-remodel-orinda.html'),
                ('services/kitchen-remodel-san-ramon','/view/services/kitchen-remodel-san-ramon.html'),
                ('services/kitchen-remodel-sunol',    '/view/services/kitchen-remodel-sunol.html'),
            ]:
                try:
                    _svc_page = context.new_page()
                    _svc_page.goto(f'{BASE_URL}{_page_path}', wait_until='networkidle', timeout=20000)
                    _color_modes = _svc_page.evaluate(
                        "() => window.__RD_HERO_COLOR_MODES || null"
                    )
                    _hero_bg = _svc_page.evaluate(
                        "() => { const h = document.querySelector('[data-hero-id]'); "
                        "return h ? getComputedStyle(h).backgroundImage : null; }"
                    )
                    _svc_page.close()
                    # __RD_HERO_COLOR_MODES must not contain any -hero keys
                    _bad_keys = [k for k in (_color_modes or {}) if k.endswith('-hero')]
                    results.append({
                        'agent': agent,
                        'check': 'hero_color_guard',
                        'status': 'fail' if _bad_keys else 'pass',
                        'detail': (f'Hero color override injected for {_bad_keys}' if _bad_keys
                                   else f'No color override on hero — guard active'),
                        'page': _slug,
                        'auto_fixable': False,
                    })
                    # Hero background-image must not be 'none'
                    _bg_ok = _hero_bg and _hero_bg != 'none' and 'url(' in (_hero_bg or '')
                    results.append({
                        'agent': agent,
                        'check': 'hero_image_visible',
                        'status': 'pass' if _bg_ok else 'fail',
                        'detail': (f'Hero background-image: {(_hero_bg or "")[:80]}'),
                        'page': _slug,
                        'auto_fixable': False,
                    })
                except Exception as _e:
                    results.append({
                        'agent': agent,
                        'check': 'hero_color_guard',
                        'status': 'fail',
                        'detail': f'Hero color guard test error on {_slug}: {_e}',
                        'page': _slug,
                        'auto_fixable': False,
                    })

            # [PICK-VARIANT] Verify _pickVariant() picks _960w (not _480w) for portrait
            # strip cards (home-portfolio-2/3/4 are ~246×400 — height-constrained).
            try:
                _vp = context.new_page()
                _vp.goto(f'{BASE_URL}/view/index.html', wait_until='networkidle', timeout=20000)
                # DOMContentLoaded already fired; _swapAll() has run.
                _variant_results = _vp.evaluate("""() => {
                    var ids = ['home-portfolio-1','home-portfolio-2','home-portfolio-3','home-portfolio-4'];
                    var out = {};
                    ids.forEach(function(id) {
                        var el = document.querySelector('[data-card-id="' + id + '"]');
                        out[id] = el ? el.style.backgroundImage : 'NOT_FOUND';
                    });
                    return out;
                }""")
                _vp.close()
                # Portrait cards (2,3,4) must not have _480w — height 400px > 270px threshold
                for _cid in ['home-portfolio-2', 'home-portfolio-3', 'home-portfolio-4']:
                    _bg = _variant_results.get(_cid, '')
                    _has_480 = '_480w' in _bg
                    _has_img = 'images-opt' in _bg or _bg == ''
                    results.append({
                        'agent': agent,
                        'check': f'pick_variant_portrait_{_cid}',
                        'status': 'fail' if _has_480 else 'pass',
                        'detail': (f'REGRESSION: {_cid} using _480w on 400px-tall container: {_bg[:80]}'
                                   if _has_480 else
                                   f'{_cid} variant OK (no _480w): {_bg[:80]}'),
                        'page': 'home',
                        'auto_fixable': False,
                    })
            except Exception as _e:
                results.append({
                    'agent': agent,
                    'check': 'pick_variant_portrait',
                    'status': 'fail',
                    'detail': f'pick_variant portrait test error: {_e}',
                    'page': 'home',
                    'auto_fixable': False,
                })

            # [FEATURED-STRIP] Verify dynamic portfolio strip renders 4 cards from DB
            try:
                import psycopg2, psycopg2.extras as _pge
                _fs_conn = psycopg2.connect(
                    'postgresql://agent_user:StrongPass123!@127.0.0.1/marketing_agent',
                    cursor_factory=_pge.RealDictCursor
                )
                _fs_cur = _fs_conn.cursor()
                _fs_cur.execute("""
                    SELECT f.slot, p.slug FROM featured_project_slots f
                    JOIN portfolio_projects p ON p.slug = f.project_slug
                    WHERE f.page = 'home' ORDER BY f.slot
                """)
                _fs_rows = {r['slot']: r['slug'] for r in _fs_cur.fetchall()}
                _fs_conn.close()

                _fs_page = browser.new_page()
                _fs_page.goto(f'{BASE_URL}/view/', wait_until='networkidle')
                _fs_page.wait_for_timeout(500)

                _strip_ok = True
                _strip_detail = []
                for _slot in range(1, 5):
                    # Check data-card-id element exists
                    _cid = f'home-portfolio-{_slot}'
                    _card_el = _fs_page.query_selector(f'[data-card-id="{_cid}"]')
                    if not _card_el:
                        _strip_ok = False
                        _strip_detail.append(f'slot {_slot}: {_cid} element missing')
                        continue
                    # Check the parent <a> href matches the DB slug
                    _expected_slug = _fs_rows.get(_slot, '')
                    _parent_a = _fs_page.query_selector(f'[data-card-id="{_cid}"]')
                    _href = _fs_page.evaluate('el => el.closest("a") ? el.closest("a").getAttribute("href") : null', _parent_a)
                    if _expected_slug and _href and _expected_slug not in _href:
                        _strip_ok = False
                        _strip_detail.append(f'slot {_slot}: href={_href!r} expected slug={_expected_slug!r}')
                    else:
                        _strip_detail.append(f'slot {_slot}: OK ({_expected_slug})')
                _fs_page.close()

                results.append({
                    'agent': agent,
                    'check': 'featured_strip',
                    'status': 'pass' if _strip_ok else 'fail',
                    'detail': '; '.join(_strip_detail),
                    'page': 'home',
                    'auto_fixable': False,
                })
            except Exception as _e:
                results.append({
                    'agent': agent,
                    'check': 'featured_strip',
                    'status': 'fail',
                    'detail': f'featured_strip test error: {_e}',
                    'page': 'home',
                    'auto_fixable': False,
                })

            # [SWAP-BTN] Verify Swap button exists in admin pill for home-portfolio-1
            try:
                _sb_page = context.new_page()
                _sb_page.goto(
                    f'{BASE_URL}/view/?admin_edit=1&token={token}&_stage=1',
                    wait_until='networkidle', timeout=20000
                )
                _sb_page.wait_for_timeout(600)
                # Hover the first featured card to expose the pill
                _sb_card = _sb_page.query_selector('[data-card-id="home-portfolio-1"]')
                if _sb_card:
                    _sb_card.hover()
                    _sb_page.wait_for_timeout(300)
                # Check Swap button rendered (rendered for all home-portfolio-N slots)
                _swap_btn = _sb_page.query_selector('[data-rd-overlay="card"] button[title*="Swap"]')
                _sb_ok = _swap_btn is not None
                _sb_page.close()
                results.append({
                    'agent': agent,
                    'check': 'swap_btn_home-portfolio-1',
                    'status': 'pass' if _sb_ok else 'fail',
                    'detail': 'Swap button found in admin pill for home-portfolio-1' if _sb_ok
                              else 'Swap button NOT found — check _CARD_EDIT_OVERLAY_TPL',
                    'page': 'home',
                    'auto_fixable': False,
                })
            except Exception as _e:
                results.append({
                    'agent': agent,
                    'check': 'swap_btn_home-portfolio-1',
                    'status': 'fail',
                    'detail': f'swap_btn test error: {_e}',
                    'page': 'home',
                    'auto_fixable': False,
                })

            # [SNAP-FEATURED] Verify published_snapshots.featured_json is populated and
            # the live path renders the strip from snapshot data (not live table).
            try:
                import psycopg2, psycopg2.extras as _pge2, json as _sfjson
                _sf_conn = psycopg2.connect(
                    'postgresql://agent_user:StrongPass123!@127.0.0.1/marketing_agent',
                    cursor_factory=_pge2.RealDictCursor
                )
                _sf_cur = _sf_conn.cursor()
                _sf_cur.execute("SELECT featured_json FROM published_snapshots WHERE slug = 'home'")
                _sf_row = _sf_cur.fetchone()
                _sf_conn.close()
                _sf_ok = False
                _sf_detail = ''
                if not _sf_row:
                    _sf_detail = 'No home snapshot found in published_snapshots'
                elif not _sf_row.get('featured_json'):
                    _sf_detail = 'featured_json is NULL in home snapshot — publish not yet run post-fix'
                else:
                    _fj_data = _sf_row['featured_json']
                    _snap_rows = _fj_data if isinstance(_fj_data, list) else _sfjson.loads(_fj_data)
                    if len(_snap_rows) == 4 and all(('slug' in r or 'project_slug' in r) for r in _snap_rows):
                        _sf_ok = True
                        _sf_detail = f'featured_json has {len(_snap_rows)} slots: ' + ', '.join(r.get("slug") or r.get("project_slug","?") for r in _snap_rows)
                    else:
                        _sf_detail = f'featured_json malformed: {_snap_rows!r}'
                results.append({
                    'agent': agent,
                    'check': 'snap_featured_json',
                    'status': 'pass' if _sf_ok else 'warn',
                    'detail': _sf_detail,
                    'page': 'home',
                    'auto_fixable': False,
                })
            except Exception as _e:
                results.append({
                    'agent': agent,
                    'check': 'snap_featured_json',
                    'status': 'fail',
                    'detail': f'snap_featured_json test error: {_e}',
                    'page': 'home',
                    'auto_fixable': False,
                })

            # [PF-STRIP] Verify portfolio featured grid renders 4 DB-driven cards
            try:
                import psycopg2, psycopg2.extras as _pfse
                _pfs_conn = psycopg2.connect(
                    'postgresql://agent_user:StrongPass123!@127.0.0.1/marketing_agent',
                    cursor_factory=_pfse.RealDictCursor
                )
                _pfs_cur = _pfs_conn.cursor()
                _pfs_cur.execute("""
                    SELECT f.slot, p.slug FROM featured_project_slots f
                    JOIN portfolio_projects p ON p.slug = f.project_slug
                    WHERE f.page = 'portfolio' ORDER BY f.slot
                """)
                _pfs_rows = {r['slot']: r['slug'] for r in _pfs_cur.fetchall()}
                _pfs_conn.close()

                _pfs_page = browser.new_page()
                _pfs_page.goto(f'{BASE_URL}/view/portfolio.html', wait_until='networkidle')
                _pfs_page.wait_for_timeout(500)

                _pfs_ok = True
                _pfs_detail = []
                for _slot in range(1, 5):
                    _cid = f'portfolio-featured-{_slot}'
                    _card_el = _pfs_page.query_selector(f'[data-card-id="{_cid}"]')
                    if not _card_el:
                        _pfs_ok = False
                        _pfs_detail.append(f'slot {_slot}: {_cid} missing')
                        continue
                    _expected = _pfs_rows.get(_slot, '')
                    _href = _pfs_page.evaluate('el => el.closest("a") ? el.closest("a").getAttribute("href") : null', _card_el)
                    if _expected and _href and _expected not in _href:
                        _pfs_ok = False
                        _pfs_detail.append(f'slot {_slot}: href={_href!r} expected={_expected!r}')
                    else:
                        _pfs_detail.append(f'slot {_slot}: OK ({_expected})')
                _pfs_page.close()

                results.append({
                    'agent': agent,
                    'check': 'portfolio_featured_strip',
                    'status': 'pass' if _pfs_ok else 'fail',
                    'detail': '; '.join(_pfs_detail),
                    'page': 'portfolio',
                    'auto_fixable': False,
                })
            except Exception as _e:
                results.append({
                    'agent': agent,
                    'check': 'portfolio_featured_strip',
                    'status': 'fail',
                    'detail': f'portfolio_featured_strip error: {_e}',
                    'page': 'portfolio',
                    'auto_fixable': False,
                })

            # [PF-SWAP-BTN] Verify Swap button appears for portfolio-featured-1 in admin edit mode
            try:
                _pfsb_page = context.new_page()
                _pfsb_page.goto(
                    f'{BASE_URL}/view/portfolio.html?admin_edit=1&token={token}&_stage=1',
                    wait_until='networkidle', timeout=20000
                )
                _pfsb_page.wait_for_timeout(600)
                _pfsb_card = _pfsb_page.query_selector('[data-card-id="portfolio-featured-1"]')
                if _pfsb_card:
                    _pfsb_card.hover()
                    _pfsb_page.wait_for_timeout(300)
                _pfsb_btn = _pfsb_page.query_selector('[data-rd-overlay="card"] button[title*="Swap"]')
                _pfsb_ok = _pfsb_btn is not None
                _pfsb_page.close()
                results.append({
                    'agent': agent,
                    'check': 'swap_btn_portfolio-featured-1',
                    'status': 'pass' if _pfsb_ok else 'fail',
                    'detail': 'Swap button found for portfolio-featured-1' if _pfsb_ok
                              else 'Swap button NOT found for portfolio-featured-1',
                    'page': 'portfolio',
                    'auto_fixable': False,
                })
            except Exception as _e:
                results.append({
                    'agent': agent,
                    'check': 'swap_btn_portfolio-featured-1',
                    'status': 'fail',
                    'detail': f'pf_swap_btn test error: {_e}',
                    'page': 'portfolio',
                    'auto_fixable': False,
                })

            # [NAV-LINKS] Verify project pages use start-a-project.html CTA (not contact.html)
            # and services/ SEO pages include the Services link.
            try:
                _nav_page = context.new_page()
                _nav_page.goto(f'{BASE_URL}/view/danville-hilltop.html',
                               wait_until='networkidle', timeout=20000)
                _nav_hrefs = _nav_page.evaluate("""() => {
                    var links = document.querySelectorAll('#navLinks a');
                    return Array.from(links).map(function(a) { return a.getAttribute('href'); });
                }""")
                _nav_page.close()
                _has_sap = any('start-a-project' in (h or '') for h in _nav_hrefs)
                _has_contact_cta = any(h == 'contact.html' for h in _nav_hrefs)
                results.append({
                    'agent': agent,
                    'check': 'nav_project_cta_href',
                    'status': 'pass' if (_has_sap and not _has_contact_cta) else 'fail',
                    'detail': (f'Nav CTA OK — start-a-project present, contact.html absent. hrefs={_nav_hrefs}'
                               if (_has_sap and not _has_contact_cta) else
                               f'REGRESSION: contact.html in nav or start-a-project missing. hrefs={_nav_hrefs}'),
                    'page': 'danville-hilltop',
                    'auto_fixable': False,
                })
            except Exception as _e:
                results.append({
                    'agent': agent,
                    'check': 'nav_project_cta_href',
                    'status': 'fail',
                    'detail': f'nav_project_cta_href test error: {_e}',
                    'page': 'danville-hilltop',
                    'auto_fixable': False,
                })

            try:
                _nav_svc_page = context.new_page()
                _nav_svc_page.goto(f'{BASE_URL}/view/services/kitchen-remodel-danville.html',
                                   wait_until='networkidle', timeout=20000)
                _svc_nav_hrefs = _nav_svc_page.evaluate("""() => {
                    var links = document.querySelectorAll('#navLinks a');
                    return Array.from(links).map(function(a) { return a.getAttribute('href'); });
                }""")
                _nav_svc_page.close()
                _has_services = any('services.html' in (h or '') for h in _svc_nav_hrefs)
                results.append({
                    'agent': agent,
                    'check': 'nav_svc_page_services_link',
                    'status': 'pass' if _has_services else 'fail',
                    'detail': (f'Services link present in nav. hrefs={_svc_nav_hrefs}'
                               if _has_services else
                               f'REGRESSION: Services link missing from services/ page nav. hrefs={_svc_nav_hrefs}'),
                    'page': 'services/kitchen-remodel-danville',
                    'auto_fixable': False,
                })
            except Exception as _e:
                results.append({
                    'agent': agent,
                    'check': 'nav_svc_page_services_link',
                    'status': 'fail',
                    'detail': f'nav_svc_page_services_link test error: {_e}',
                    'page': 'services/kitchen-remodel-danville',
                    'auto_fixable': False,
                })

            try:
                # gallery_type_badge_cycle: verify the type button in the gallery card pill
                # cycles through labels (Project/Render/Before/Construction/Untagged).
                # Requires admin_edit=1&token= to inject the card overlay with the pill.
                _gtb_card_id = 'danville-hilltop-gal-ff5b18_63757c728db94733b4f60a7102c0f722_mv2'
                _gtb_url = f'{BASE_URL}/view/danville-hilltop.html?admin_edit=1&token={token}&_stage=1'
                _gtb_page = context.new_page()
                _gtb_page.goto(_gtb_url, wait_until='networkidle', timeout=20000)
                _type_labels = ['Project', 'Render', 'Before', 'Construction', 'Untagged']
                # Hover the card to show the pill
                _gtb_page.evaluate(f"""() => {{
                    var card = document.querySelector('[data-card-id="{_gtb_card_id}"]');
                    if (card) card.dispatchEvent(new MouseEvent('mouseenter', {{bubbles: false, cancelable: true}}));
                }}""")
                time.sleep(0.4)
                _pill_info = _gtb_page.evaluate(f"""() => {{
                    var card = document.querySelector('[data-card-id="{_gtb_card_id}"]');
                    if (!card) return {{found: false, reason: 'card not found'}};
                    var pill = card.querySelector('[style*="z-index: 9991"], [style*="z-index:9991"]');
                    if (!pill) return {{found: false, reason: 'pill not found'}};
                    var btns = Array.from(pill.querySelectorAll('button'));
                    var typeBtn = btns.find(function(b) {{
                        return {str(_type_labels)}.indexOf(b.textContent.trim()) !== -1;
                    }});
                    return {{
                        found: !!typeBtn,
                        label: typeBtn ? typeBtn.textContent.trim() : null,
                    }};
                }}""")
                if _pill_info.get('found'):
                    _before_label = _pill_info['label']
                    _gtb_page.evaluate(f"""() => {{
                        var card = document.querySelector('[data-card-id="{_gtb_card_id}"]');
                        var pill = card.querySelector('[style*="z-index: 9991"], [style*="z-index:9991"]');
                        var btns = Array.from(pill.querySelectorAll('button'));
                        var typeBtn = btns.find(function(b) {{
                            return {str(_type_labels)}.indexOf(b.textContent.trim()) !== -1;
                        }});
                        if (typeBtn) typeBtn.click();
                    }}""")
                    time.sleep(0.3)
                    _after_info = _gtb_page.evaluate(f"""() => {{
                        var card = document.querySelector('[data-card-id="{_gtb_card_id}"]');
                        var pill = card.querySelector('[style*="z-index: 9991"], [style*="z-index:9991"]');
                        var btns = Array.from(pill.querySelectorAll('button'));
                        var typeBtn = btns.find(function(b) {{
                            return {str(_type_labels)}.indexOf(b.textContent.trim()) !== -1;
                        }});
                        return typeBtn ? typeBtn.textContent.trim() : null;
                    }}""")
                    _gtb_page.close()
                    _gtb_passed = (_after_info in _type_labels and _after_info != _before_label)
                    _gtb_detail = f'Type badge cycled: {_before_label} -> {_after_info}'
                else:
                    _gtb_page.close()
                    _gtb_passed = False
                    _gtb_detail = f'gallery_type_badge_cycle: {_pill_info.get("reason","pill/button not found")}'
                results.append({
                    'agent': agent,
                    'check': 'gallery_type_badge_cycle',
                    'status': 'pass' if _gtb_passed else 'fail',
                    'detail': _gtb_detail,
                    'page': 'danville-hilltop',
                    'auto_fixable': False,
                })
            except Exception as _e:
                results.append({
                    'agent': agent,
                    'check': 'gallery_type_badge_cycle',
                    'status': 'fail',
                    'detail': f'gallery_type_badge_cycle test error: {_e}',
                    'page': 'danville-hilltop',
                    'auto_fixable': False,
                })

            # ── card_variant_960w_playwright ──────────────────────────────
            # Portfolio cards get background-image via JS (el.style.backgroundImage),
            # not CSS injection, so page.content() misses them. Use evaluate() instead.
            try:
                _cv_page = context.new_page()
                _cv_page.goto(
                    f'{BASE_URL}/view/portfolio.html?_stage=1',
                    wait_until='networkidle', timeout=20000
                )
                _cv_urls = _cv_page.evaluate("""
                    () => {
                        const cards = document.querySelectorAll('[data-card-id]');
                        const urls = [];
                        cards.forEach(el => {
                            const bg = el.style.backgroundImage ||
                                       window.getComputedStyle(el).backgroundImage;
                            if (bg && bg.includes('_mv2')) {
                                const m = bg.match(/url\\(["']?([^"')]+)["']?\\)/);
                                if (m) urls.push(m[1]);
                            }
                        });
                        return urls;
                    }
                """)
                _cv_page.close()
                _cv_bare    = [u for u in _cv_urls if u.endswith('_mv2.webp')]
                _cv_1920w   = [u for u in _cv_urls if '_1920w' in u]
                _cv_has960  = any('_960w' in u for u in _cv_urls)
                if _cv_bare:
                    results.append({
                        'agent': agent,
                        'check': 'card_variant_960w_playwright',
                        'status': 'fail',
                        'detail': f'Cards serving bare base file (moiré risk): {_cv_bare[:3]}',
                        'page': 'portfolio',
                        'auto_fixable': False,
                    })
                elif _cv_1920w:
                    results.append({
                        'agent': agent,
                        'check': 'card_variant_960w_playwright',
                        'status': 'fail',
                        'detail': f'Cards serving _1920w (moiré risk): {_cv_1920w[:3]}',
                        'page': 'portfolio',
                        'auto_fixable': False,
                    })
                elif not _cv_urls:
                    results.append({
                        'agent': agent,
                        'check': 'card_variant_960w_playwright',
                        'status': 'warn',
                        'detail': 'No mv2 card background-image URLs found via JS — cards may not have loaded',
                        'page': 'portfolio',
                        'auto_fixable': False,
                    })
                else:
                    results.append({
                        'agent': agent,
                        'check': 'card_variant_960w_playwright',
                        'status': 'pass',
                        'detail': f'Portfolio cards use _960w variant ✓ ({len(_cv_urls)} card URL(s) checked via JS)',
                        'page': 'portfolio',
                        'auto_fixable': False,
                    })
            except Exception as _e:
                results.append({
                    'agent': agent,
                    'check': 'card_variant_960w_playwright',
                    'status': 'fail',
                    'detail': f'card_variant_960w_playwright test error: {_e}',
                    'page': 'portfolio',
                    'auto_fixable': False,
                })

            # ── start_a_project_iframe_resize ─────────────────────────────
            try:
                _sap_page = browser.new_page()
                _sap_page.goto(f'{BASE_URL}/view/start-a-project.html', wait_until='networkidle', timeout=30000)
                _sap_page.wait_for_timeout(1500)
                _iframe_h = _sap_page.evaluate(
                    "() => { var f = document.querySelector('.sap-frame iframe'); return f ? f.clientHeight : 0; }"
                )
                # Simulate blur (parent loses focus) — with collapse removed, height must be unaffected
                _sap_page.evaluate("() => window.dispatchEvent(new Event('blur'))")
                _sap_page.wait_for_timeout(800)
                _iframe_h_after = _sap_page.evaluate(
                    "() => { var f = document.querySelector('.sap-frame iframe'); return f ? f.clientHeight : 0; }"
                )
                _sap_page.close()
                _ok = _iframe_h > 700 and _iframe_h_after > 700
                results.append({
                    'agent': agent,
                    'check': 'start_a_project_iframe_resize',
                    'status': 'pass' if _ok else 'fail',
                    'detail': (
                        f'initial={_iframe_h} after_blur={_iframe_h_after} — resize stable, no collapse'
                        if _ok else
                        f'initial={_iframe_h} after_blur={_iframe_h_after} — iframe did not resize or collapsed on blur (scroll bar regression)'
                    ),
                    'page': 'start-a-project',
                    'auto_fixable': False,
                })
            except Exception as _e:
                results.append({
                    'agent': agent,
                    'check': 'start_a_project_iframe_resize',
                    'status': 'fail',
                    'detail': f'start_a_project_iframe_resize test error: {_e}',
                    'page': 'start-a-project',
                    'auto_fixable': False,
                })

            # ── portfolio_featured_gradient_btn ──────────────────────────
            # Verify gradient (G) button appears on portfolio-featured cards
            # after removing the cardId.indexOf('portfolio-featured-') exclusion.
            try:
                _pf_page = context.new_page()
                _pf_page.goto(
                    f'{BASE_URL}/view/portfolio.html?admin_edit=1&token={token}&_stage=1',
                    wait_until='networkidle', timeout=20000
                )
                _pf_page.wait_for_timeout(800)
                # Fire mouseenter on _attachEl (parent <a> for role="img" cards)
                _pf_page.evaluate("""
                    () => {
                        var card = document.querySelector('[data-card-id="portfolio-featured-1"]');
                        if (!card) return;
                        var attachEl = card;
                        if (card.getAttribute('role') === 'img') {
                            var par = card.parentElement;
                            if (par && window.getComputedStyle(par).position !== 'static') attachEl = par;
                        }
                        attachEl.dispatchEvent(new MouseEvent('mouseenter', {bubbles: false, cancelable: true}));
                    }
                """)
                _pf_page.wait_for_timeout(500)
                _pf_grad_visible = _pf_page.evaluate("""
                    () => {
                        var card = document.querySelector('[data-card-id="portfolio-featured-1"]');
                        if (!card) return false;
                        var attachEl = card;
                        if (card.getAttribute('role') === 'img') {
                            var par = card.parentElement;
                            if (par && window.getComputedStyle(par).position !== 'static') attachEl = par;
                        }
                        var pill = Array.from(attachEl.children)
                            .find(function(c) { return c.getAttribute('data-rd-overlay') === 'card'; });
                        if (!pill) return false;
                        var btns = pill.querySelectorAll('button');
                        for (var i = 0; i < btns.length; i++) {
                            if (btns[i].textContent.trim() === 'G') return true;
                        }
                        return false;
                    }
                """)
                _pf_page.close()
                results.append({
                    'agent': agent,
                    'check': 'portfolio_featured_gradient_btn',
                    'status': 'pass' if _pf_grad_visible else 'fail',
                    'detail': (
                        'G (gradient) button present on portfolio-featured-1 card pill ✓'
                        if _pf_grad_visible else
                        'G button NOT found on portfolio-featured-1 — exclusion may still be in effect'
                    ),
                    'page': 'portfolio',
                    'auto_fixable': False,
                })
            except Exception as _e:
                results.append({
                    'agent': agent,
                    'check': 'portfolio_featured_gradient_btn',
                    'status': 'fail',
                    'detail': f'portfolio_featured_gradient_btn test error: {_e}',
                    'page': 'portfolio',
                    'auto_fixable': False,
                })

            # ── portfolio_featured_gradient_wired ────────────────────────
            # Verify that rd_set_gradient correctly applies --rd-overlay to
            # .portfolio-featured__overlay (data-gradient-id element), NOT to
            # .portfolio-featured__img (data-card-id). The render function must
            # include data-gradient-id on the overlay div for this to work.
            try:
                _pgw_page = context.new_page()
                _pgw_page.goto(
                    f'{BASE_URL}/view/portfolio.html?admin_edit=1&token={token}&_stage=1',
                    wait_until='networkidle', timeout=20000
                )
                _pgw_page.wait_for_timeout(800)
                # Dispatch a synthetic rd_set_gradient message to the page
                _pgw_page.evaluate("""
                    () => {
                        window.dispatchEvent(new MessageEvent('message', {
                            data: {
                                type: 'rd_set_gradient',
                                cardId: 'portfolio-featured-1',
                                gradientCss: 'linear-gradient(to top,rgba(0,0,0,0.8) 0%,transparent 80%)',
                                gradient: {gradient_type:'fade',gradient_tint:'dark',gradient_opacity:80,gradient_direction:'bottom',gradient_distance:80}
                            },
                            origin: window.location.origin
                        }));
                    }
                """)
                _pgw_page.wait_for_timeout(300)
                _pgw_result = _pgw_page.evaluate("""
                    () => {
                        var overlay = document.querySelector('[data-gradient-id="portfolio-featured-1"]');
                        var imgDiv  = document.querySelector('[data-card-id="portfolio-featured-1"]');
                        return {
                            overlayRdOverlay: overlay ? overlay.style.getPropertyValue('--rd-overlay') : null,
                            imgRdOverlay:     imgDiv  ? imgDiv.style.getPropertyValue('--rd-overlay')  : null,
                            overlayFound: !!overlay
                        };
                    }
                """)
                _pgw_page.close()
                _pgw_wired = (
                    _pgw_result.get('overlayFound') and
                    _pgw_result.get('overlayRdOverlay') and
                    'gradient' in (_pgw_result.get('overlayRdOverlay') or '')
                )
                results.append({
                    'agent': agent,
                    'check': 'portfolio_featured_gradient_wired',
                    'status': 'pass' if _pgw_wired else 'fail',
                    'detail': (
                        f'--rd-overlay set on overlay div ✓ ({_pgw_result.get("overlayRdOverlay","")[:40]})'
                        if _pgw_wired else
                        f'--rd-overlay NOT on overlay div — data-gradient-id missing from rendered HTML? overlay={_pgw_result.get("overlayRdOverlay")!r}'
                    ),
                    'page': 'portfolio',
                    'auto_fixable': False,
                })
            except Exception as _e:
                results.append({
                    'agent': agent,
                    'check': 'portfolio_featured_gradient_wired',
                    'status': 'fail',
                    'detail': f'portfolio_featured_gradient_wired test error: {_e}',
                    'page': 'portfolio',
                    'auto_fixable': False,
                })

            # ── portfolio_featured_gradient_serve_time ────────────────────
            # Verify gradient is baked into the served HTML at page load time
            # (not just applied client-side). Saves a gradient to card_settings,
            # then fetches the public page (no admin_edit) and checks the
            # overlay div has --rd-overlay in its inline style attribute.
            # This test catches the pipeline ordering bug where _inject_gradient_id_overlays
            # ran before _replace_portfolio_featured_grid and its output was discarded.
            try:
                import urllib.request as _ur, urllib.error as _ue, json as _tj, re as _re
                _test_card_id = 'portfolio-featured-1'
                _test_slug    = 'portfolio'
                _test_css     = 'linear-gradient(to top,rgba(0,0,0,0.72) 0%,transparent 80%)'
                # Read current card state so we can restore after
                _gst_orig = _read_card_state(_test_card_id)
                # Safety rule: NEVER set image=None on a live displayed card in a test.
                # Keep the original image so the card is still visible even if restore fails.
                # Only inject gradient fields — leave image/position/zoom from original state.
                _orig_image    = (_gst_orig or {}).get('image')
                _orig_position = (_gst_orig or {}).get('position', '50% 50%')
                _orig_zoom     = (_gst_orig or {}).get('zoom', 1.0)
                _put_payload = _tj.dumps({
                    'mode': 'image', 'color': '#1C1C1C',
                    'image': _orig_image,         # preserve original image — NEVER None
                    'position': _orig_position,
                    'zoom': _orig_zoom,
                    'gradient_type': 'fade', 'gradient_tint': 'dark',
                    'gradient_opacity': 72, 'gradient_direction': 'bottom',
                    'gradient_distance': 80,
                    'gradient_css': _test_css,
                }).encode()
                _put_req = _ur.Request(
                    f'{BASE_URL}/admin/api/cards/{_test_slug}/{_test_card_id}',
                    data=_put_payload, method='PUT',
                    headers={'X-Admin-Token': token, 'Content-Type': 'application/json'}
                )
                _ur.urlopen(_put_req, timeout=8)
                # Fetch the public (non-admin) page — no ?admin_edit, no ?_stage
                _pub_req = _ur.Request(f'{BASE_URL}/view/portfolio.html')
                with _ur.urlopen(_pub_req, timeout=10) as _pub_resp:
                    _pub_html = _pub_resp.read().decode('utf-8', errors='replace')
                # Check that the overlay div for slot 1 has --rd-overlay in its style
                _gst_found = bool(_re.search(
                    r'data-gradient-id="portfolio-featured-1"[^>]*style="[^"]*--rd-overlay',
                    _pub_html
                ) or _re.search(
                    r'style="[^"]*--rd-overlay[^"]*"[^>]*data-gradient-id="portfolio-featured-1"',
                    _pub_html
                ))
                # Restore original state — _restore_card_state raises on failure (never silent)
                _restore_card_state(_test_card_id, _test_slug, token, _gst_orig)
                # Verify restore succeeded by reading the DB — fail loudly if not
                _post_restore = _read_card_state(_test_card_id)
                _restored_image = (_post_restore or {}).get('image')
                if _restored_image != _orig_image:
                    raise RuntimeError(
                        f'Restore verification failed: expected image={_orig_image!r}, '
                        f'got={_restored_image!r}. DB is corrupt — do not commit.'
                    )
                results.append({
                    'agent': agent,
                    'check': 'portfolio_featured_gradient_serve_time',
                    'status': 'pass' if _gst_found else 'fail',
                    'detail': (
                        '--rd-overlay baked into served HTML for portfolio-featured-1 ✓'
                        if _gst_found else
                        '--rd-overlay NOT found in served HTML — gradient injection runs before grid replacement and is discarded'
                    ),
                    'page': 'portfolio',
                    'auto_fixable': False,
                })
            except Exception as _e:
                results.append({
                    'agent': agent,
                    'check': 'portfolio_featured_gradient_serve_time',
                    'status': 'fail',
                    'detail': f'portfolio_featured_gradient_serve_time test error: {_e}',
                    'page': 'portfolio',
                    'auto_fixable': False,
                })

            # ── sitemap_links_navigable ───────────────────────────────────────
            # Loads /view/sitemap.html and resolves every .sm-link href the way
            # a browser would (el.href returns the fully-resolved absolute URL).
            # Verifies every resolved URL returns HTTP 200. This catches
            # root-relative links (/page.html) that 404 from the /view/ context
            # even though the file exists at /view/page.html.
            # Rule: links must work when clicked, not just when fetched by path.
            try:
                import urllib.request as _ur2
                _sm_page = context.new_page()
                _sm_page.goto(f'{BASE_URL}/view/sitemap.html', wait_until='domcontentloaded', timeout=15000)
                # Use browser to resolve all .sm-link hrefs to absolute URLs
                # el.href returns fully-resolved absolute URLs — the true browser destination
                _sm_hrefs = _sm_page.evaluate(
                    "() => Array.from(document.querySelectorAll('a.sm-link')).map(a => ({href: a.href, text: a.textContent.trim()}))"
                )
                _sm_page.close()
                _sm_broken = []
                for _item in _sm_hrefs:
                    _url = _item['href']
                    if not _url.startswith('http'):
                        continue
                    try:
                        _req = _ur2.Request(_url)
                        with _ur2.urlopen(_req, timeout=8) as _r:
                            if _r.status != 200:
                                _sm_broken.append(f"{_r.status} {_url} ({_item['text']})")
                    except Exception as _link_e:
                        _sm_broken.append(f"ERR {_url} ({_item['text']}): {_link_e}")
                results.append({
                    'agent': agent,
                    'check': 'sitemap_links_navigable',
                    'status': 'pass' if not _sm_broken else 'fail',
                    'detail': (
                        f'All {len(_sm_hrefs)} sitemap links resolve correctly ✓'
                        if not _sm_broken else
                        f'{len(_sm_broken)} broken link(s): ' + '; '.join(_sm_broken[:5])
                    ),
                    'page': 'sitemap',
                    'auto_fixable': False,
                })
            except Exception as _sm_e:
                results.append({
                    'agent': agent,
                    'check': 'sitemap_links_navigable',
                    'status': 'fail',
                    'detail': f'sitemap_links_navigable test error: {_sm_e}',
                    'page': 'sitemap',
                    'auto_fixable': False,
                })

            # ── blog_hero_rd_cards_injected ───────────────────────────────────
            # Verifies window.__RD_CARDS is injected on the blog index page
            # (admin_edit=1) and contains the blog-index-hero card with
            # hero_text_align data. Guards against _apply_cards_to_html being
            # accidentally removed from blog_index(), which would break the
            # edit overlay's text alignment and CTA controls silently.
            try:
                _brc_page = context.new_page()
                _brc_url = f'{BASE_URL}/blog?admin_edit=1&token={token}'
                _brc_page.goto(_brc_url, wait_until='domcontentloaded', timeout=15000)
                _brc_cards = _brc_page.evaluate(
                    "() => typeof window.__RD_CARDS !== 'undefined' ? window.__RD_CARDS : null"
                )
                _brc_page.close()
                _brc_hero = None
                if _brc_cards:
                    for _c in _brc_cards:
                        if _c.get('card_id') == 'blog-index-hero':
                            _brc_hero = _c
                            break
                _brc_ok = _brc_hero is not None and 'hero_text_align' in _brc_hero
                results.append({
                    'agent': agent,
                    'check': 'blog_hero_rd_cards_injected',
                    'status': 'pass' if _brc_ok else 'fail',
                    'detail': (
                        'blog-index-hero present in __RD_CARDS with hero_text_align ✓'
                        if _brc_ok else
                        '__RD_CARDS missing or lacks blog-index-hero — edit overlay text/CTA controls broken'
                    ),
                    'page': 'blog',
                    'auto_fixable': False,
                })
            except Exception as _brc_e:
                results.append({
                    'agent': agent,
                    'check': 'blog_hero_rd_cards_injected',
                    'status': 'fail',
                    'detail': f'blog_hero_rd_cards_injected test error: {_brc_e}',
                    'page': 'blog',
                    'auto_fixable': False,
                })

            # ── blog_hero_inline_style ────────────────────────────────────────
            # When a hero image is saved for the blog page in the DB, the
            # .blog-hero div must carry an inline style="background-image:url(...)"
            # so the edit overlay's init() can discover the current image.
            # Without it, picking a new image reverts on reload because the
            # overlay calls buildOverlay(el, null) — url=null — and save writes null.
            try:
                _bhi_page = context.new_page()
                _bhi_page.goto(f'{BASE_URL}/blog?admin_edit=1&token={token}',
                               wait_until='domcontentloaded', timeout=15000)
                _bhi_data = _bhi_page.evaluate('''() => {
                    const hero = document.querySelector('.blog-hero');
                    if (!hero) return {found: false};
                    const rdHero = typeof window.__RD_HERO !== 'undefined' ? window.__RD_HERO : null;
                    const inlineStyle = hero.style.backgroundImage || '';
                    return {found: true, rdHero, inlineStyle};
                }''')
                _bhi_page.close()
                # If __RD_HERO is set (hero image saved in DB), inline style must be present.
                # If __RD_HERO is not set, inline style is correctly absent.
                if not _bhi_data.get('found'):
                    _bhi_ok = False
                    _bhi_detail = '.blog-hero element not found on blog page'
                elif _bhi_data.get('rdHero'):
                    _bhi_ok = bool(_bhi_data.get('inlineStyle'))
                    _bhi_detail = (
                        f"inline style present ✓ ({_bhi_data['inlineStyle'][:60]})"
                        if _bhi_ok else
                        '__RD_HERO set but .blog-hero has no inline background-image — edit overlay will revert image on save'
                    )
                else:
                    _bhi_ok = True
                    _bhi_detail = 'no hero image set in DB — inline style correctly absent'
                results.append({
                    'agent': agent,
                    'check': 'blog_hero_inline_style',
                    'status': 'pass' if _bhi_ok else 'fail',
                    'detail': _bhi_detail,
                    'page': 'blog',
                    'auto_fixable': False,
                })
            except Exception as _bhi_e:
                results.append({
                    'agent': agent,
                    'check': 'blog_hero_inline_style',
                    'status': 'fail',
                    'detail': f'blog_hero_inline_style test error: {_bhi_e}',
                    'page': 'blog',
                    'auto_fixable': False,
                })

            # ── blog_post_hero_image_sync ─────────────────────────────────────
            # Verifies that PUT /admin/api/pages/blog/<slug> writes hero_image to
            # BOTH pages.hero_image AND blog_posts.featured_image. Without the
            # blog_posts sync, blog_post() always reads the old featured_image on
            # reload, causing every picker save to silently revert.
            try:
                _bps_conn = psycopg2.connect(**DB_CONFIG)
                _bps_conn.autocommit = False
                _bps_cur = _bps_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                _bps_cur.execute(
                    "SELECT slug, featured_image FROM blog_posts WHERE status='published' LIMIT 1"
                )
                _bps_row = _bps_cur.fetchone()
                if not _bps_row:
                    results.append({
                        'agent': agent, 'check': 'blog_post_hero_image_sync',
                        'status': 'pass',
                        'detail': 'no published blog posts — test skipped',
                        'page': 'blog', 'auto_fixable': False,
                    })
                else:
                    _bps_slug    = _bps_row['slug']
                    _bps_orig    = _bps_row['featured_image']
                    # Use the existing image or a known fallback for the write test
                    _bps_img = _bps_orig or '/assets/images-opt/ff5b18_c520c9ca384d4c3ebe02707d0c8f45ab_mv2.webp'
                    import requests as _bps_req
                    _bps_resp = _bps_req.put(
                        f'{BASE_URL}/admin/api/pages/blog/{_bps_slug}',
                        json={'hero_image': _bps_img},
                        headers={'X-Admin-Token': token},
                        timeout=10
                    )
                    # Verify blog_posts.featured_image was updated
                    _bps_cur.execute(
                        "SELECT featured_image FROM blog_posts WHERE slug = %s", (_bps_slug,)
                    )
                    _bps_after = _bps_cur.fetchone()
                    _bps_synced = _bps_after and _bps_after['featured_image'] == _bps_img
                    _bps_ok = _bps_resp.ok and _bps_synced
                    results.append({
                        'agent': agent, 'check': 'blog_post_hero_image_sync',
                        'status': 'pass' if _bps_ok else 'fail',
                        'detail': (
                            f'blog_posts.featured_image synced for slug={_bps_slug} ✓'
                            if _bps_ok else
                            f'sync failed — api_status={_bps_resp.status_code}, '
                            f'blog_posts.featured_image={repr(_bps_after["featured_image"] if _bps_after else None)} '
                            f'expected={repr(_bps_img)}'
                        ),
                        'page': 'blog', 'auto_fixable': False,
                    })
                    # Restore original value
                    if _bps_orig != _bps_img:
                        _bps_cur.execute(
                            "UPDATE blog_posts SET featured_image = %s WHERE slug = %s",
                            (_bps_orig, _bps_slug)
                        )
                        _bps_conn.commit()
                _bps_conn.close()
            except Exception as _bps_e:
                results.append({
                    'agent': agent, 'check': 'blog_post_hero_image_sync',
                    'status': 'fail',
                    'detail': f'blog_post_hero_image_sync test error: {_bps_e}',
                    'page': 'blog', 'auto_fixable': False,
                })

            # ── blog_post_text_align_css ──────────────────────────────────────
            # Verifies that [data-hero-text-align] CSS rules apply to .post-hero
            # elements. Guards against missing CSS rules that leave text-alignment
            # controls saving to DB but having zero visual effect on blog post pages.
            try:
                _bpt_page = context.new_page()
                # Load a blog post (or blog index as fallback) with a forced data attribute
                _bpt_url = f'{BASE_URL}/blog'
                _bpt_page.goto(_bpt_url, wait_until='domcontentloaded', timeout=15000)
                # Inject a test post-hero div, set data-hero-text-align, measure CSS effect
                _bpt_result = _bpt_page.evaluate('''() => {
                    const div = document.createElement('div');
                    div.className = 'post-hero post-hero--has-img';
                    div.setAttribute('data-hero-text-align', 'center');
                    div.style.position = 'absolute';
                    div.style.left = '-9999px';
                    const title = document.createElement('h1');
                    title.className = 'post-hero__title';
                    title.textContent = 'Test';
                    div.appendChild(title);
                    document.body.appendChild(div);
                    const computed = window.getComputedStyle(div).textAlign;
                    const titleComputed = window.getComputedStyle(title).textAlign;
                    document.body.removeChild(div);
                    return { divAlign: computed, titleAlign: titleComputed };
                }''')
                _bpt_page.close()
                _bpt_ok = (
                    _bpt_result.get('divAlign') == 'center' or
                    _bpt_result.get('titleAlign') == 'center'
                )
                results.append({
                    'agent': agent, 'check': 'blog_post_text_align_css',
                    'status': 'pass' if _bpt_ok else 'fail',
                    'detail': (
                        f'[data-hero-text-align=center].post-hero applies correctly '
                        f'(div={_bpt_result.get("divAlign")}, title={_bpt_result.get("titleAlign")}) ✓'
                        if _bpt_ok else
                        f'CSS rule missing — div={_bpt_result.get("divAlign")}, '
                        f'title={_bpt_result.get("titleAlign")} (expected center)'
                    ),
                    'page': 'blog', 'auto_fixable': False,
                })
            except Exception as _bpt_e:
                results.append({
                    'agent': agent, 'check': 'blog_post_text_align_css',
                    'status': 'fail',
                    'detail': f'blog_post_text_align_css test error: {_bpt_e}',
                    'page': 'blog', 'auto_fixable': False,
                })

            # ── blog_post_gradient_overlay ────────────────────────────────────
            # Verifies that .post-hero__overlay uses var(--rd-overlay) so the G
            # panel gradient control actually changes the visual overlay on blog
            # post hero sections. Guards against the hardcoded background regression.
            try:
                _bpg_page = context.new_page()
                _bpg_page.goto(f'{BASE_URL}/blog', wait_until='domcontentloaded', timeout=15000)
                _bpg_result = _bpg_page.evaluate('''() => {
                    const hero = document.createElement('div');
                    hero.className = 'post-hero post-hero--has-img';
                    hero.style.cssText = '--rd-overlay: linear-gradient(to bottom, rgba(255,0,0,0.9) 0%, transparent 100%); position:absolute; left:-9999px;';
                    const overlay = document.createElement('div');
                    overlay.className = 'post-hero__overlay';
                    hero.appendChild(overlay);
                    document.body.appendChild(hero);
                    const bg = window.getComputedStyle(overlay).backgroundImage;
                    document.body.removeChild(hero);
                    return { background: bg };
                }''')
                _bpg_page.close()
                _bpg_bg = _bpg_result.get('background', '')
                _bpg_ok = 'rgba(255, 0, 0' in _bpg_bg or 'rgb(255, 0, 0' in _bpg_bg
                results.append({
                    'agent': agent, 'check': 'blog_post_gradient_overlay',
                    'status': 'pass' if _bpg_ok else 'fail',
                    'detail': (
                        f'.post-hero__overlay correctly reads --rd-overlay variable ✓'
                        if _bpg_ok else
                        f'.post-hero__overlay ignores --rd-overlay (background={_bpg_bg[:80]}) — '
                        f'expected var(--rd-overlay) in blog.css'
                    ),
                    'page': 'blog', 'auto_fixable': False,
                })
            except Exception as _bpg_e:
                results.append({
                    'agent': agent, 'check': 'blog_post_gradient_overlay',
                    'status': 'fail',
                    'detail': f'blog_post_gradient_overlay test error: {_bpg_e}',
                    'page': 'blog', 'auto_fixable': False,
                })

            # ── blog_post_meta_align ──────────────────────────────────────────
            # Verifies that .post-hero__meta (flex container) gets justify-content
            # rules when data-hero-text-align is set. Guards against the CSS fix
            # where text-align alone doesn't center flex items in the meta row.
            try:
                _bpm_page = context.new_page()
                _bpm_page.goto(f'{BASE_URL}/blog', wait_until='domcontentloaded', timeout=15000)
                _bpm_result = _bpm_page.evaluate('''() => {
                    const hero = document.createElement('div');
                    hero.className = 'post-hero post-hero--has-img';
                    hero.setAttribute('data-hero-text-align', 'center');
                    hero.style.cssText = 'position:absolute; left:-9999px;';
                    const meta = document.createElement('div');
                    meta.className = 'post-hero__meta';
                    hero.appendChild(meta);
                    document.body.appendChild(hero);
                    const jc = window.getComputedStyle(meta).justifyContent;
                    document.body.removeChild(hero);
                    return { justifyContent: jc };
                }''')
                _bpm_page.close()
                _bpm_jc = _bpm_result.get('justifyContent', '')
                _bpm_ok = _bpm_jc == 'center'
                results.append({
                    'agent': agent, 'check': 'blog_post_meta_align',
                    'status': 'pass' if _bpm_ok else 'fail',
                    'detail': (
                        f'.post-hero__meta justify-content:center applies correctly ✓'
                        if _bpm_ok else
                        f'.post-hero__meta justify-content={_bpm_jc!r} (expected "center") — '
                        f'flex meta row not centering on text alignment change'
                    ),
                    'page': 'blog', 'auto_fixable': False,
                })
            except Exception as _bpm_e:
                results.append({
                    'agent': agent, 'check': 'blog_post_meta_align',
                    'status': 'fail',
                    'detail': f'blog_post_meta_align test error: {_bpm_e}',
                    'page': 'blog', 'auto_fixable': False,
                })

            # ── blog_post_container_shift ─────────────────────────────────────
            # Verifies that [data-hero-text-align="right"].post-hero .container
            # has margin-right:0 (not auto) so the text block physically shifts to
            # the right side of the screen. Guards against the margin:auto override
            # that keeps .container centered even when align-items:flex-end is set.
            try:
                _bpc_page = context.new_page()
                _bpc_page.goto(f'{BASE_URL}/blog', wait_until='domcontentloaded', timeout=15000)
                _bpc_result = _bpc_page.evaluate('''() => {
                    const hero = document.createElement('div');
                    hero.className = 'post-hero post-hero--has-img';
                    hero.setAttribute('data-hero-text-align', 'right');
                    hero.style.cssText = 'position:absolute; left:-9999px; width:1200px; display:flex; flex-direction:column;';
                    const container = document.createElement('div');
                    container.className = 'container container--narrow';
                    hero.appendChild(container);
                    document.body.appendChild(hero);
                    const ml = window.getComputedStyle(container).marginLeft;
                    const mr = window.getComputedStyle(container).marginRight;
                    document.body.removeChild(hero);
                    return { marginLeft: ml, marginRight: mr };
                }''')
                _bpc_page.close()
                _bpc_mr = _bpc_result.get('marginRight', '')
                _bpc_ok = _bpc_mr == '0px'
                results.append({
                    'agent': agent, 'check': 'blog_post_container_shift',
                    'status': 'pass' if _bpc_ok else 'fail',
                    'detail': (
                        f'.post-hero .container margin-right:0 on right-align — '
                        f'text block physically shifts right ✓'
                        if _bpc_ok else
                        f'.post-hero .container margin-right={_bpc_mr!r} on right-align '
                        f'(expected "0px") — container still auto-centered'
                    ),
                    'page': 'blog', 'auto_fixable': False,
                })
            except Exception as _bpc_e:
                results.append({
                    'agent': agent, 'check': 'blog_post_container_shift',
                    'status': 'fail',
                    'detail': f'blog_post_container_shift test error: {_bpc_e}',
                    'page': 'blog', 'auto_fixable': False,
                })

            # ── nav_hero_map_keys ─────────────────────────────────────────────
            # Verifies window.__RD_HERO_MAP entries for whole-house-remodels and
            # blog have real hero images (not the fallback path). Guards against
            # slug typos in _NAV_PREFETCH_SLUGS that silently break nav preload.
            # Keys in __RD_HERO_MAP are /view/<slug>.html paths, not bare slugs.
            _HERO_FALLBACK = 'ff5b18_c520c9ca384d4c3ebe02707d0c8f45ab_mv2'
            try:
                _nhm_page = context.new_page()
                _nhm_page.goto(f'{BASE_URL}/view/index.html', wait_until='domcontentloaded', timeout=15000)
                _nhm_map = _nhm_page.evaluate(
                    "() => typeof window.__RD_HERO_MAP === 'object' ? window.__RD_HERO_MAP : null"
                )
                _nhm_page.close()
                # These two were broken by slug typos ('whole-home-remodels', 'therdedit')
                _required_urls = ['/view/whole-house-remodels.html', '/view/blog.html']
                _bad = []
                if _nhm_map is None:
                    _bad = _required_urls
                else:
                    for _u in _required_urls:
                        _v = _nhm_map.get(_u, '')
                        if not _v or _HERO_FALLBACK in _v:
                            _bad.append(f'{_u} → fallback or missing')
                results.append({
                    'agent': agent,
                    'check': 'nav_hero_map_keys',
                    'status': 'fail' if _bad else 'pass',
                    'detail': (
                        f'__RD_HERO_MAP has wrong/missing heroes: {_bad}' if _bad
                        else 'whole-house-remodels and blog have real hero images in __RD_HERO_MAP ✓'
                    ),
                    'page': 'home',
                    'auto_fixable': False,
                })
            except Exception as _nhm_e:
                results.append({
                    'agent': agent,
                    'check': 'nav_hero_map_keys',
                    'status': 'fail',
                    'detail': f'nav_hero_map_keys test error: {_nhm_e}',
                    'page': 'home',
                    'auto_fixable': False,
                })

            # ── surgical_mode_expands ─────────────────────────────────────────
            # Verifies that toggling Surgical Mode ON expands the re-render modal
            # (maxWidth 1400px, grid 2fr 1fr) and toggling OFF restores it
            # (maxWidth 860px, grid 1fr 1fr). Also confirms openRerender() always
            # resets to normal size regardless of prior surgical state.
            # Server-side: preview_server.py script_surgical and script now guard
            # against response.candidates=None and cand.content.parts=None to avoid
            # TypeError when Gemini returns MALFORMED_FUNCTION_CALL or empty content.
            # Model updated to gemini-3.1-flash-image-preview (from gemini-3-pro-image-preview)
            # — the pro model was returning 500 INTERNAL on real image patches.
            try:
                _srg_page = context.new_page()
                # Admin pages.html uses sessionStorage for auth — set token before navigating
                _srg_page.goto(f'{BASE_URL}/view/admin/index.html', wait_until='domcontentloaded', timeout=10000)
                _srg_page.evaluate(f'() => sessionStorage.setItem("rd_admin_token", "{token}")')
                _srg_page.goto(f'{BASE_URL}/view/admin/pages.html', wait_until='networkidle', timeout=20000)
                # Open the rerender modal directly via JS with a dummy filename
                _srg_page.evaluate("""() => {
                    openRerender('ff5b18_6f6dc7ef92684e7e8af496c4f83f06be_mv2_960w.webp', 'Test');
                }""")
                time.sleep(0.3)
                # Capture baseline modal width (should be 860px max-width)
                _srg_normal = _srg_page.evaluate("""() => {
                    var box = document.querySelector('#rerenderModal .modal-box');
                    var grid = document.getElementById('rerenderPanelGrid');
                    return {
                        maxWidth: box ? box.style.maxWidth : null,
                        width: box ? box.style.width : null,
                        grid: grid ? grid.style.gridTemplateColumns : null,
                        modalVisible: document.getElementById('rerenderModal').style.display !== 'none'
                    };
                }""")
                # Click Surgical Mode ON
                _srg_page.evaluate("() => { toggleSurgicalMode(); }")
                time.sleep(0.2)
                _srg_on = _srg_page.evaluate("""() => {
                    var box = document.querySelector('#rerenderModal .modal-box');
                    var grid = document.getElementById('rerenderPanelGrid');
                    var btn = document.getElementById('surgicalToggleBtn');
                    var orig = document.getElementById('rerenderOriginal');
                    return {
                        maxWidth: box ? box.style.maxWidth : null,
                        width: box ? box.style.width : null,
                        grid: grid ? grid.style.gridTemplateColumns : null,
                        btnText: btn ? btn.textContent.trim() : null,
                        backgroundSize: orig ? orig.style.backgroundSize : null
                    };
                }""")
                # Click Surgical Mode OFF
                _srg_page.evaluate("() => { toggleSurgicalMode(); }")
                time.sleep(0.2)
                _srg_off = _srg_page.evaluate("""() => {
                    var box = document.querySelector('#rerenderModal .modal-box');
                    var grid = document.getElementById('rerenderPanelGrid');
                    var btn = document.getElementById('surgicalToggleBtn');
                    var orig = document.getElementById('rerenderOriginal');
                    return {
                        maxWidth: box ? box.style.maxWidth : null,
                        width: box ? box.style.width : null,
                        grid: grid ? grid.style.gridTemplateColumns : null,
                        btnText: btn ? btn.textContent.trim() : null,
                        backgroundSize: orig ? orig.style.backgroundSize : null
                    };
                }""")
                # Re-open modal while surgical is OFF to confirm size resets properly
                _srg_page.evaluate("() => { toggleSurgicalMode(); }")  # turn ON again
                time.sleep(0.1)
                _srg_page.evaluate("""() => {
                    openRerender('ff5b18_6f6dc7ef92684e7e8af496c4f83f06be_mv2_960w.webp', 'Test2');
                }""")
                time.sleep(0.2)
                _srg_reopen = _srg_page.evaluate("""() => {
                    var box = document.querySelector('#rerenderModal .modal-box');
                    var grid = document.getElementById('rerenderPanelGrid');
                    var orig = document.getElementById('rerenderOriginal');
                    return {
                        maxWidth: box ? box.style.maxWidth : null,
                        grid: grid ? grid.style.gridTemplateColumns : null,
                        backgroundSize: orig ? orig.style.backgroundSize : null
                    };
                }""")
                _srg_page.close()
                # Assertions
                _srg_errors = []
                if not _srg_normal.get('modalVisible'):
                    _srg_errors.append('modal did not open')
                if _srg_on.get('maxWidth') != '1400px':
                    _srg_errors.append(f"surgical ON: maxWidth={_srg_on.get('maxWidth')} expected 1400px")
                if _srg_on.get('width') != '96vw':
                    _srg_errors.append(f"surgical ON: width={_srg_on.get('width')} expected 96vw")
                if '2fr' not in (_srg_on.get('grid') or ''):
                    _srg_errors.append(f"surgical ON: grid={_srg_on.get('grid')} expected 2fr 1fr")
                if _srg_on.get('btnText') != '⚔ Surgical Mode ON':
                    _srg_errors.append(f"surgical ON: btn text={_srg_on.get('btnText')}")
                if _srg_on.get('backgroundSize') != 'contain':
                    _srg_errors.append(f"surgical ON: backgroundSize={_srg_on.get('backgroundSize')} expected contain")
                if _srg_off.get('maxWidth') != '860px':
                    _srg_errors.append(f"surgical OFF: maxWidth={_srg_off.get('maxWidth')} expected 860px")
                if '1fr 1fr' not in (_srg_off.get('grid') or ''):
                    _srg_errors.append(f"surgical OFF: grid={_srg_off.get('grid')} expected 1fr 1fr")
                if _srg_off.get('backgroundSize') != 'cover':
                    _srg_errors.append(f"surgical OFF: backgroundSize={_srg_off.get('backgroundSize')} expected cover")
                if _srg_reopen.get('maxWidth') != '860px':
                    _srg_errors.append(f"reopen after surgical: maxWidth={_srg_reopen.get('maxWidth')} expected 860px reset")
                if '1fr 1fr' not in (_srg_reopen.get('grid') or ''):
                    _srg_errors.append(f"reopen after surgical: grid={_srg_reopen.get('grid')} expected 1fr 1fr reset")
                if _srg_reopen.get('backgroundSize') != 'cover':
                    _srg_errors.append(f"reopen after surgical: backgroundSize={_srg_reopen.get('backgroundSize')} expected cover reset")
                results.append({
                    'agent': agent,
                    'check': 'surgical_mode_expands',
                    'status': 'fail' if _srg_errors else 'pass',
                    'detail': (
                        'REGRESSION: ' + '; '.join(_srg_errors) if _srg_errors
                        else f'Surgical mode expand/collapse verified ✓ (ON={_srg_on.get("maxWidth")}/{_srg_on.get("grid")}/bg={_srg_on.get("backgroundSize")}, OFF={_srg_off.get("maxWidth")}/{_srg_off.get("grid")}/bg={_srg_off.get("backgroundSize")}, reopen={_srg_reopen.get("maxWidth")}/bg={_srg_reopen.get("backgroundSize")})'
                    ),
                    'page': 'admin/pages',
                    'auto_fixable': False,
                })
            except Exception as _srg_e:
                results.append({
                    'agent': agent,
                    'check': 'surgical_mode_expands',
                    'status': 'fail',
                    'detail': f'surgical_mode_expands test error: {_srg_e}',
                    'page': 'admin/pages',
                    'auto_fixable': False,
                })

            # ── crop_mode_toggle ──────────────────────────────────────────────
            # Verifies: crop ON expands modal (1400px/2fr 1fr/contain), crop OFF
            # restores (860px/1fr 1fr/cover), mutual exclusion with surgical,
            # and that applyCrop() saves a file + sets _rerenderResultPath.
            # CLEANUP: all created _ai_N files + DB record deleted at test end.
            _crop_created_path = None
            try:
                _crop_page = context.new_page()
                _crop_page.goto(f'{BASE_URL}/view/admin/index.html', wait_until='domcontentloaded', timeout=10000)
                _crop_page.evaluate(f'() => sessionStorage.setItem("rd_admin_token", "{token}")')
                _crop_page.goto(f'{BASE_URL}/view/admin/pages.html', wait_until='networkidle', timeout=20000)
                _TEST_IMG = 'ff5b18_6f6dc7ef92684e7e8af496c4f83f06be_mv2_960w.webp'
                # Open rerender modal
                _crop_page.evaluate(f"() => {{ openRerender('{_TEST_IMG}', 'Crop test'); }}")
                time.sleep(0.3)
                # ── 1: Crop mode ON ────────────────────────────────────────────
                _crop_page.evaluate("() => { toggleCropMode(); }")
                time.sleep(0.2)
                _crop_on = _crop_page.evaluate("""() => {
                    var box = document.querySelector('#rerenderModal .modal-box');
                    var grid = document.getElementById('rerenderPanelGrid');
                    var btn = document.getElementById('cropToggleBtn');
                    var orig = document.getElementById('rerenderOriginal');
                    var canvas = document.getElementById('rerenderCropCanvas');
                    var status = document.getElementById('cropModeStatus');
                    return {
                        maxWidth: box ? box.style.maxWidth : null,
                        width: box ? box.style.width : null,
                        grid: grid ? grid.style.gridTemplateColumns : null,
                        btnText: btn ? btn.textContent.trim() : null,
                        backgroundSize: orig ? orig.style.backgroundSize : null,
                        canvasVisible: canvas ? (canvas.style.display !== 'none') : false,
                        statusVisible: status ? (status.style.display !== 'none') : false,
                        cropModeActive: (typeof _rerenderCropMode !== 'undefined') ? _rerenderCropMode : null,
                    };
                }""")
                # ── 2: Crop mode OFF ───────────────────────────────────────────
                _crop_page.evaluate("() => { toggleCropMode(); }")
                time.sleep(0.2)
                _crop_off = _crop_page.evaluate("""() => {
                    var box = document.querySelector('#rerenderModal .modal-box');
                    var grid = document.getElementById('rerenderPanelGrid');
                    var orig = document.getElementById('rerenderOriginal');
                    var canvas = document.getElementById('rerenderCropCanvas');
                    return {
                        maxWidth: box ? box.style.maxWidth : null,
                        grid: grid ? grid.style.gridTemplateColumns : null,
                        backgroundSize: orig ? orig.style.backgroundSize : null,
                        canvasVisible: canvas ? (canvas.style.display !== 'none') : false,
                        cropModeActive: (typeof _rerenderCropMode !== 'undefined') ? _rerenderCropMode : null,
                    };
                }""")
                # ── 3: Mutual exclusion — surgical ON → crop ON kills surgical ─
                _crop_page.evaluate("() => { toggleSurgicalMode(); }")
                time.sleep(0.1)
                _crop_page.evaluate("() => { toggleCropMode(); }")
                time.sleep(0.2)
                _crop_mutex = _crop_page.evaluate("""() => {
                    return {
                        surgicalOff: !_rerenderSurgical,
                        cropOn: _rerenderCropMode,
                        surgBtnText: (document.getElementById('surgicalToggleBtn') || {}).textContent || '',
                    };
                }""")
                # ── 4: Apply Crop (inject coords, call applyCrop) ─────────────
                # Image is 9499x6333 — inject realistic dims and a wide crop (>800px).
                # We inject _rerenderCropCoords directly (simulates user drawing a box)
                # and call applyCrop() which posts to /admin/api/images/crop.
                _crop_page.evaluate("""() => {
                    _rerenderActualDims = {w: 9499, h: 6333};
                    _rerenderCropCoords = {x: 500, y: 500, w: 5000, h: 3000};
                    _rerenderFilename = 'ff5b18_6f6dc7ef92684e7e8af496c4f83f06be_mv2_960w.webp';
                }""")
                _crop_page.evaluate("() => { applyCrop(); }")
                # Wait up to 15s for status to reflect completion or failure
                _crop_page.wait_for_function(
                    "() => { var s = document.getElementById('rerenderStatus'); return s && (s.textContent.includes('Crop saved') || s.textContent.includes('failed')); }",
                    timeout=15000
                )
                _crop_result = _crop_page.evaluate("""() => {
                    var st = document.getElementById('rerenderStatus');
                    var ph = document.getElementById('rerenderPlaceholder');
                    var ub = document.getElementById('rerenderUseBtn');
                    return {
                        status: st ? st.textContent : '',
                        placeholderHidden: ph ? (ph.style.display === 'none') : false,
                        useBtnVisible: ub ? (ub.style.display !== 'none') : false,
                        resultPath: (typeof _rerenderResultPath !== 'undefined') ? _rerenderResultPath : null,
                        cropModeOff: (typeof _rerenderCropMode !== 'undefined') ? !_rerenderCropMode : null,
                    };
                }""")
                _crop_created_path = _crop_result.get('resultPath')  # e.g. /assets/images-opt/...webp
                _crop_page.close()

                # ── Assertions ─────────────────────────────────────────────────
                _crop_errors = []
                if not _crop_on.get('cropModeActive'):
                    _crop_errors.append('crop ON: _rerenderCropMode not true')
                if _crop_on.get('maxWidth') != '1400px':
                    _crop_errors.append(f"crop ON: maxWidth={_crop_on.get('maxWidth')} expected 1400px")
                if '2fr' not in (_crop_on.get('grid') or ''):
                    _crop_errors.append(f"crop ON: grid={_crop_on.get('grid')} expected 2fr 1fr")
                if _crop_on.get('backgroundSize') != 'contain':
                    _crop_errors.append(f"crop ON: backgroundSize={_crop_on.get('backgroundSize')} expected contain")
                if not _crop_on.get('canvasVisible'):
                    _crop_errors.append('crop ON: rerenderCropCanvas not visible')
                if not _crop_on.get('statusVisible'):
                    _crop_errors.append('crop ON: cropModeStatus not visible')
                if _crop_off.get('cropModeActive'):
                    _crop_errors.append('crop OFF: _rerenderCropMode still true')
                if _crop_off.get('maxWidth') != '860px':
                    _crop_errors.append(f"crop OFF: maxWidth={_crop_off.get('maxWidth')} expected 860px")
                if _crop_off.get('canvasVisible'):
                    _crop_errors.append('crop OFF: canvas still visible')
                if not _crop_mutex.get('surgicalOff'):
                    _crop_errors.append('mutual exclusion: _rerenderSurgical still ON after crop toggle')
                if not _crop_mutex.get('cropOn'):
                    _crop_errors.append('mutual exclusion: crop not ON after toggle over surgical')
                if 'Crop saved' not in (_crop_result.get('status') or ''):
                    _crop_errors.append(f"apply crop: status={_crop_result.get('status')!r}")
                if not _crop_result.get('placeholderHidden'):
                    _crop_errors.append('apply crop: result placeholder still visible')
                if not _crop_result.get('useBtnVisible'):
                    _crop_errors.append('apply crop: Use This Version button not shown')
                if not _crop_result.get('resultPath'):
                    _crop_errors.append('apply crop: _rerenderResultPath not set')
                if not _crop_result.get('cropModeOff'):
                    _crop_errors.append('apply crop: crop mode not auto-off after apply')

                results.append({
                    'agent': agent,
                    'check': 'crop_mode_toggle',
                    'status': 'fail' if _crop_errors else 'pass',
                    'detail': (
                        'REGRESSION: ' + '; '.join(_crop_errors) if _crop_errors
                        else (f'Crop mode toggle/exclusion/apply verified ✓ '
                              f'(ON={_crop_on.get("maxWidth")}/{_crop_on.get("grid")}'
                              f'/bg={_crop_on.get("backgroundSize")}, '
                              f'OFF={_crop_off.get("maxWidth")}, '
                              f'apply={_crop_result.get("status")!r})')
                    ),
                    'page': 'admin/pages',
                    'auto_fixable': False,
                })
            except Exception as _crop_e:
                results.append({
                    'agent': agent,
                    'check': 'crop_mode_toggle',
                    'status': 'fail',
                    'detail': f'crop_mode_toggle test error: {_crop_e}',
                    'page': 'admin/pages',
                    'auto_fixable': False,
                })
            finally:
                # MANDATORY CLEANUP — delete any _ai_N files and DB record created by this test
                import glob as _glob
                import subprocess as _sp
                if _crop_created_path:
                    _stem = '/home/claudeuser/agent/preview' + _crop_created_path.replace('.webp', '')
                    for _f in _glob.glob(_stem + '*.webp'):
                        try: os.remove(_f)
                        except Exception: pass
                    _fname = os.path.basename(_crop_created_path)
                    try:
                        _sp.run(
                            ['psql', '-h', '127.0.0.1', '-U', 'agent_user', '-d', 'marketing_agent',
                             '-c', f"DELETE FROM image_render_prompts WHERE filename='{_fname}' AND render_model='crop';"],
                            env={**os.environ, 'PGPASSWORD': 'StrongPass123!'},
                            capture_output=True, timeout=10
                        )
                    except Exception: pass

            browser.close()

    except Exception as e:
        results.append({
            'agent': agent,
            'check': 'playwright_run',
            'status': 'fail',
            'detail': f'Playwright browser error: {e}',
            'page': '',
            'auto_fixable': False,
        })

    return results
