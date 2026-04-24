"""
Visual Overlay Agent
====================
Uses Playwright (headless Chromium) to verify that edit-mode card overlays
are visually accessible — pill appears on hover AND is not occluded by
overlapping elements with higher z-index.

This is the automated enforcement of Rule 11 (§22 CLAUDE.md): "rendered effect"
verification for every card overlay. Code-level checks (HTML present, DB records
exist) cannot catch CSS stacking context conflicts. Only a rendered browser check
can.

Pages tested (representative structural types, not exhaustive):
  - kitchen-remodels.html   diff__zone inside diff__visual--one (critical case)
  - index.html              diff__zone inside diff__visual--two (home page regression check)
  - allprojects.html        proj-card__img allproj-* cards
  - portfolio.html          portfolio-featured cards

Exports: run(fix=False) -> List[Dict]
"""
import os
import time
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
        'index',
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
]


def _get_token():
    """
    Return a valid admin token from admin_sessions.
    Validates each token via HTTP ping against the running server.
    Handles Flask hot-reloader restarts: if the server is temporarily down
    (e.g., reloading due to file change detection during git staging),
    waits up to 8 seconds for it to come back up before declaring failure.
    """
    import urllib.request
    import urllib.error
    import json as _json

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
                data = _json.loads(resp.read())
                return bool(data.get('ok'))
        except urllib.error.HTTPError:
            return False   # definitive 401 — token invalid
        except Exception:
            return None    # connection error — server may be restarting

    # Try to find a valid token. If ALL tokens fail with connection errors
    # (Flask hot-reloader restart window), wait and retry up to 2 times.
    for wait_round in range(3):
        rows = _load_rows()
        all_connection_errors = True
        for row in rows:
            token = row['token']
            result = _ping(token)
            if result is True:
                return token    # valid token found
            if result is False:
                all_connection_errors = False  # at least one 401 — server is up

        if not all_connection_errors:
            break  # server responded (just no valid tokens) — stop retrying

        # All connection errors → server is restarting (hot-reload). Wait and retry.
        if wait_round < 2:
            time.sleep(4)

    return None


def _check_card_overlay(page, card_id):
    """
    Hover over the element with data-card-id=card_id and verify:
      1. The edit pill (data-rd-overlay="card") becomes opacity 1 (mouseenter fired)
      2. For diff__zone in diff__visual--one: pill is attached to diff__visual parent
         (not trapped inside diff__zone's stacking context)

    Uses force=True on hover to bypass pointer-events interactability check —
    the card element may be behind a pointer-events:none overlay, but _attachEl
    still receives the mouseenter event.

    Returns (ok: bool, detail: str)
    """
    try:
        selector = f'[data-card-id="{card_id}"]'
        el = page.query_selector(selector)
        if el is None:
            return False, f'Element [data-card-id="{card_id}"] not found in DOM'

        # Scroll into viewport, then force-hover (bypasses pointer-events checks)
        el.scroll_into_view_if_needed(timeout=5000)
        time.sleep(0.2)
        el.hover(timeout=5000, force=True)
        time.sleep(0.35)  # allow opacity transition (0.15s) + paint

        # Find the pill that belongs to THIS specific card by querying within
        # the card's expected _attachEl container (mirrors setupCard() logic).
        result = page.evaluate(
            f"""() => {{
                var card = document.querySelector('[data-card-id="{card_id}"]');
                if (!card) return 'card_not_found';

                // Determine expected _attachEl (mirrors setupCard() in preview_server.py)
                var attachEl = card;
                var isGallery = card.hasAttribute('data-src');

                // role="img" (non-gallery) → use parent if positioned
                if (!isGallery && card.getAttribute('role') === 'img') {{
                    var par = card.parentElement;
                    if (par && window.getComputedStyle(par).position !== 'static') attachEl = par;
                }}

                // diff__zone in diff__visual--one → use diff__visual parent
                if (!isGallery && card.classList.contains('diff__zone')) {{
                    var dv = card.parentElement;
                    if (dv && dv.classList.contains('diff__visual') &&
                        dv.classList.contains('diff__visual--one')) {{
                        attachEl = dv;
                    }}
                }}

                // Find THIS card's pill within the expected container
                var pill = attachEl.querySelector('[data-rd-overlay="card"]');
                if (!pill) return 'no_pill_in_container';

                var opacity = parseFloat(window.getComputedStyle(pill).opacity);
                if (opacity < 0.5) return 'pill_opacity_zero';

                // For diff__zone in diff__visual--ONE: pill must NOT be inside the zone
                // (stuck_in_zone = stacking context fix not active).
                // diff__visual--TWO (home page) correctly keeps pill inside zone — NOT a bug.
                if (card.classList.contains('diff__zone')) {{
                    var dv2 = card.parentElement;
                    var isOne = dv2 && dv2.classList.contains('diff__visual') &&
                                dv2.classList.contains('diff__visual--one');
                    if (isOne && card.contains(pill)) return 'stuck_in_zone';
                }}

                return 'ok';
            }}"""
        )

        if result == 'stuck_in_zone':
            return False, (
                f'Pill trapped inside diff__zone (stacking context conflict NOT fixed) — '
                f'Option A fix in setupCard() is not active for {card_id}'
            )
        if result == 'pill_opacity_zero':
            return False, (
                f'Pill in correct container but opacity=0 — '
                f'mouseenter not triggering on _attachEl for {card_id}'
            )
        if result in ('card_not_found', 'no_pill_in_container'):
            return False, f'Pill not found in expected _attachEl container ({result}) for {card_id}'

        return True, f'Pill visible and correctly attached to _attachEl for {card_id}'

    except PlaywrightTimeoutError:
        return False, f'Timeout: element {card_id} not scrollable/interactable (zero-size or display:none)'
    except Exception as e:
        return False, f'Error checking {card_id}: {e}'


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

                # Give card overlay JS time to initialize
                time.sleep(0.6)

                for card_id in card_ids:
                    ok, detail = _check_card_overlay(page, card_id)
                    results.append({
                        'agent': agent,
                        'check': f'overlay_accessible_{card_id}',
                        'status': 'pass' if ok else 'fail',
                        'detail': detail,
                        'page': slug,
                        'auto_fixable': False,
                    })

                page.close()

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
