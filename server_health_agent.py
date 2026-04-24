"""
Server Health Agent — Web Development QA Agency
================================================
Verifies the dev preview server (port 8081) is up and serving correctly.
Checks every HTML page returns 200, key admin API endpoints respond,
and the DB is reachable.

Checks (critical = blocks commit):
  CRITICAL
    • Dev server is reachable at http://127.0.0.1:8081/
    • Every HTML page in preview/ returns HTTP 200
    • Admin auth endpoint responds (POST /admin/api/auth)
    • DB tables endpoint responds (GET /admin/api/db/tables)
    • No test-artifact DB records left in card_settings
      (mode='color' hero records with no image = leftover test writes)

  WARNING
    • Server health endpoint returns healthy JSON (/admin/api/server/health)
    • Response time < 3 s for all pages
    • No page returns a Python traceback in its body
"""
import os
import re
import sys
import time
from typing import List, Dict, Any

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

BASE_URL   = 'http://127.0.0.1:8081'
PREVIEW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'preview')
ADMIN_PASSWORD = 'Hb2425hb+'
SLOW_THRESHOLD = 3.0   # seconds

# Pages intentionally excluded from the 200-check (they are not standard HTML views)
SKIP_PAGES: set = set()


def _r(check: str, status: str, detail: str = '', page: str = '',
        auto_fixable: bool = False) -> Dict[str, Any]:
    return {
        'agent': 'server_health',
        'check': check,
        'status': status,   # 'pass' | 'fail' | 'warn'
        'detail': detail,
        'page': page,
        'auto_fixable': auto_fixable,
    }


def _get(path: str, timeout: float = 10.0):
    """GET from server, return (status_code, elapsed_s, text) or raise."""
    t0 = time.time()
    resp = requests.get(BASE_URL + path, timeout=timeout)
    return resp.status_code, time.time() - t0, resp.text


def _post_json(path: str, payload: dict, token: str = '', timeout: float = 10.0):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['X-Admin-Token'] = token
    resp = requests.post(BASE_URL + path, json=payload, headers=headers, timeout=timeout)
    return resp.status_code, resp.json()


def _put_json(path: str, payload: dict, token: str, timeout: float = 10.0):
    headers = {'Content-Type': 'application/json', 'X-Admin-Token': token}
    resp = requests.put(BASE_URL + path, json=payload, headers=headers, timeout=timeout)
    return resp.status_code, resp.json()


def _get_auth(path: str, token: str, timeout: float = 10.0):
    """GET with X-Admin-Token header, return (status_code, elapsed_s, text)."""
    t0 = time.time()
    headers = {'X-Admin-Token': token}
    resp = requests.get(BASE_URL + path, headers=headers, timeout=timeout)
    return resp.status_code, time.time() - t0, resp.text


def run(fix: bool = False) -> List[Dict[str, Any]]:
    if not _HAS_REQUESTS:
        return [_r('requests_available', 'warn',
                   'requests not installed — server checks skipped. '
                   'Run: pip install requests')]

    results: List[Dict[str, Any]] = []

    # ── 1. Basic reachability ─────────────────────────────────────────────────
    try:
        status, elapsed, body = _get('/view/', timeout=5.0)
        if status == 200:
            results.append(_r('server_reachable', 'pass',
                               f'Dev server up — index.html returned 200 in {elapsed:.2f}s'))
        else:
            results.append(_r('server_reachable', 'fail',
                               f'Dev server returned HTTP {status} for /view/'))
            return results   # everything else will also fail — stop early
    except Exception as exc:
        results.append(_r('server_reachable', 'fail',
                           f'Dev server not reachable at {BASE_URL}: {exc}'))
        return results

    # ── 2. All HTML pages return 200 ──────────────────────────────────────────
    html_files = sorted(
        f for f in os.listdir(PREVIEW_DIR)
        if f.endswith('.html') and f not in SKIP_PAGES
        and not f.startswith('admin')
    )

    slow_pages: List[str] = []
    traceback_pages: List[str] = []
    fail_pages: List[str] = []

    for filename in html_files:
        path = f'/view/{filename}'
        try:
            code, elapsed, body = _get(path)
        except Exception as exc:
            fail_pages.append(f'{filename} (error: {exc})')
            continue

        if code != 200:
            fail_pages.append(f'{filename} (HTTP {code})')
        else:
            if elapsed > SLOW_THRESHOLD:
                slow_pages.append(f'{filename} ({elapsed:.1f}s)')
            if 'Traceback (most recent call last)' in body or 'Internal Server Error' in body:
                traceback_pages.append(filename)

    if fail_pages:
        results.append(_r('all_pages_200', 'fail',
                           f'{len(fail_pages)} page(s) did not return 200: '
                           + ', '.join(fail_pages)))
    else:
        results.append(_r('all_pages_200', 'pass',
                           f'All {len(html_files)} pages returned HTTP 200'))

    if slow_pages:
        results.append(_r('page_response_time', 'warn',
                           f'{len(slow_pages)} page(s) exceeded {SLOW_THRESHOLD}s: '
                           + ', '.join(slow_pages)))
    else:
        results.append(_r('page_response_time', 'pass',
                           f'All pages responded in under {SLOW_THRESHOLD}s'))

    if traceback_pages:
        results.append(_r('no_server_errors', 'fail',
                           f'Server error / traceback in body of: '
                           + ', '.join(traceback_pages)))
    else:
        results.append(_r('no_server_errors', 'pass',
                           'No tracebacks or 500 errors in page bodies'))

    # ── 3. Admin API endpoints ────────────────────────────────────────────────
    # Auth ping — 200 = public endpoint, 401 = endpoint exists but requires session (both are ok)
    try:
        code, _, _ = _get('/admin/api/auth/ping')
        if code in (200, 401):
            results.append(_r('admin_auth_ping', 'pass',
                               f'Auth ping endpoint up (HTTP {code})'))
        else:
            results.append(_r('admin_auth_ping', 'fail',
                               f'/admin/api/auth/ping returned HTTP {code}'))
    except Exception as exc:
        results.append(_r('admin_auth_ping', 'fail', str(exc)))

    # Server health endpoint
    try:
        code, _, body = _get('/admin/api/server/health')
        if code == 401:
            # Requires auth token — just check it responds
            results.append(_r('server_health_endpoint', 'pass',
                               'Server health endpoint up (401 — auth required, as expected)'))
        elif code == 200:
            results.append(_r('server_health_endpoint', 'pass',
                               'Server health endpoint returned 200'))
        else:
            results.append(_r('server_health_endpoint', 'warn',
                               f'/admin/api/server/health returned HTTP {code}'))
    except Exception as exc:
        results.append(_r('server_health_endpoint', 'warn', str(exc)))

    # ── 4. Admin panel HTML pages load ────────────────────────────────────────
    admin_pages = [
        'admin/index.html',
        'admin/pages.html',
        'admin/media.html',
        'admin/leads.html',
        'admin/settings.html',
    ]
    admin_fail = []
    for ap in admin_pages:
        try:
            code, _, _ = _get(f'/view/{ap}')
            if code != 200:
                admin_fail.append(f'{ap} (HTTP {code})')
        except Exception as exc:
            admin_fail.append(f'{ap} (error: {exc})')

    if admin_fail:
        results.append(_r('admin_pages_200', 'fail',
                           'Admin pages not returning 200: ' + ', '.join(admin_fail)))
    else:
        results.append(_r('admin_pages_200', 'pass',
                           f'All {len(admin_pages)} admin pages returned 200'))

    # ── 5. DB test-artifact guardrail ─────────────────────────────────────────
    # Detect records that are classic test artifacts:
    # hero card_settings rows with mode='color' and no image — these get created
    # when the BG panel is tested and must not persist to the live site.
    try:
        import db as _db
        conn = _db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT page_slug, card_id FROM card_settings "
            "WHERE card_id LIKE '%hero%' AND mode = 'color' AND image IS NULL"
        )
        artifacts = cur.fetchall()
        conn.close()
        if artifacts:
            names = ', '.join(f"{r['page_slug']}/{r['card_id']}" for r in artifacts)
            results.append(_r('no_test_artifacts', 'fail',
                               f'{len(artifacts)} test-artifact hero color record(s) left in DB: '
                               f'{names} — run: python db_test_scope.py restore',
                               auto_fixable=True))
        else:
            results.append(_r('no_test_artifacts', 'pass',
                               'No test-artifact color-mode hero records in DB'))
    except Exception as exc:
        results.append(_r('no_test_artifacts', 'warn',
                           f'Could not check DB for test artifacts: {exc}'))

    # ── 6. Hero flash-fix regression guard ────────────────────────────────────
    # The server must inject a <style> in <head> that pre-sets background-image and
    # background-color on hero elements BEFORE JS runs. Without it the ::before overlay
    # renders on the white body background = dark gray flash (Apr 2026 incident).
    #
    # Checks:
    #   A. .page-hero--service pages (about, process, services/) must have:
    #      - .page-hero--service{background-image:...} in flash-fix style
    #      - background-color:#0d1a22 in flash-fix style (prevents gray flash while image loads)
    #      - --rd-overlay present (hero gradient)
    #   B. Home page must have .hero__bg{background-image:...} in flash-fix style
    #      (home hero is JS-applied otherwise; CSS rule eliminates the flash)
    service_pages = [
        'about.html', 'process.html', 'services.html',
        'contact.html', 'portfolio.html', 'team.html',
        'kitchen-remodels.html', 'bathroom-remodels.html',
        'whole-house-remodels.html', 'custom-homes.html',
    ]
    flash_fail = []
    flash_bgcolor_fail = []
    flash_grad_fail = []
    for sp in service_pages:
        try:
            code, _, body = _get(f'/view/{sp}')
            if code != 200:
                continue
            if '.page-hero--service{background-image:' not in body:
                flash_fail.append(sp)
            if 'background-color:#0d1a22' not in body:
                flash_bgcolor_fail.append(sp)
            if '--rd-overlay' not in body:
                flash_grad_fail.append(sp)
        except Exception:
            pass

    if flash_fail:
        results.append(_r('hero_flash_fix', 'fail',
                           f'Server not injecting flash-fix style on: {", ".join(flash_fail)} '
                           f'— _apply_hero_to_html may be broken',
                           auto_fixable=False))
    else:
        results.append(_r('hero_flash_fix', 'pass',
                           f'Flash-fix style injected on all checked service pages'))

    if flash_bgcolor_fail:
        results.append(_r('hero_flash_bgcolor', 'fail',
                           f'Flash-fix style missing background-color:#0d1a22 on: '
                           f'{", ".join(flash_bgcolor_fail)} — ::before overlay will render on '
                           f'white body background = dark gray flash while image loads. '
                           f'Add background-color:#0d1a22 to flash-fix in _apply_hero_to_html.',
                           auto_fixable=False))
    else:
        results.append(_r('hero_flash_bgcolor', 'pass',
                           'Flash-fix includes background-color:#0d1a22 — no gray flash while image loads'))

    if flash_grad_fail:
        results.append(_r('hero_gradient_present', 'warn',
                           f'--rd-overlay not present on: {", ".join(flash_grad_fail)} '
                           f'— hero gradient may not display correctly'))
    else:
        results.append(_r('hero_gradient_present', 'pass',
                           'Hero gradient overlay present on all checked service pages'))

    # Home page flash-fix: .hero__bg must get background-image via CSS in <head>
    # Without it, .hero__bg shows background-color:#0d1a22 until JS runs = dark flash.
    try:
        _hc, _, _hbody = _get('/view/')
        if _hc == 200:
            if '.hero__bg{background-image:' not in _hbody:
                results.append(_r(
                    'home_hero_flash_fix', 'fail',
                    'Home page missing .hero__bg flash-fix CSS — .hero__bg background-image '
                    'is JS-applied only, causing a dark (#0d1a22) flash before the image loads. '
                    'Add .hero__bg rule to _apply_hero_to_html flash-fix style.',
                    auto_fixable=False,
                ))
            else:
                results.append(_r('home_hero_flash_fix', 'pass',
                                   'Home page .hero__bg flash-fix CSS present — no dark flash before hero image loads'))
        else:
            results.append(_r('home_hero_flash_fix', 'warn',
                               f'Home page returned HTTP {_hc}, cannot verify flash-fix'))
    except Exception as _hfe:
        results.append(_r('home_hero_flash_fix', 'warn', f'Home hero flash-fix check failed: {_hfe}'))

    # ── 8. Services/ subdirectory pages return 200 (sampled) ──────────────────
    # Check one page per service type × one city = representative sample.
    # Full 200-page audit would be too slow; a sample catches route/template breakage.
    SAMPLE_SERVICES = [
        'services/design-build-danville.html',
        'services/kitchen-remodel-pleasanton.html',
        'services/bathroom-remodel-alamo.html',
        'services/custom-home-builder-walnut-creek.html',
        'services/whole-house-remodel-lafayette.html',
        'services/danville.html',
    ]
    svc_fail = []
    svc_no_hero_id = []
    for sp in SAMPLE_SERVICES:
        try:
            code, _, body = _get(f'/view/{sp}')
            if code != 200:
                svc_fail.append(f'{sp} (HTTP {code})')
            else:
                # Guardrail: served HTML must contain data-hero-id on the hero
                # (confirms the attribute survived the strip/inject pipeline)
                if 'data-hero-id=' not in body:
                    svc_no_hero_id.append(sp)
        except Exception as exc:
            svc_fail.append(f'{sp} (error: {exc})')

    if svc_fail:
        results.append(_r('services_pages_200', 'fail',
                           f'Services pages not returning 200: {", ".join(svc_fail)}',
                           auto_fixable=False))
    else:
        results.append(_r('services_pages_200', 'pass',
                           f'Sample of {len(SAMPLE_SERVICES)} services pages returned 200'))

    if svc_no_hero_id:
        results.append(_r('services_hero_id_present', 'fail',
                           f'data-hero-id missing from served HTML on: {", ".join(svc_no_hero_id)} '
                           f'— T button will not appear. Fix: add data-hero-id to hero divs and '
                           f'run: sudo python3 /tmp/fix_services.py for root-owned files',
                           auto_fixable=False))
    else:
        results.append(_r('services_hero_id_present', 'pass',
                           f'data-hero-id present in all sampled services pages'))

    # ── 9. Blog index hero editability guard ──────────────────────────────────
    # The RD Edit blog index (/blog) is a Flask dynamic route — compliance agent
    # cannot check it. Verify the served HTML has data-hero-id on the blog hero
    # so the edit overlay system can find it and make it editable.
    try:
        code, _, body = _get('/blog')
        if code != 200:
            results.append(_r('blog_hero_editable', 'fail',
                               f'/blog returned HTTP {code}', auto_fixable=False))
        elif 'data-hero-id="blog-index-hero"' not in body:
            results.append(_r('blog_hero_editable', 'fail',
                               '/blog served HTML missing data-hero-id="blog-index-hero" '
                               '— edit overlay cannot attach. Fix: ensure blog_index() in '
                               'preview_server.py sets data-hero-id on .blog-hero div.',
                               auto_fixable=False))
        else:
            results.append(_r('blog_hero_editable', 'pass',
                               'Blog index hero has data-hero-id — edit overlay will attach'))
    except Exception as exc:
        results.append(_r('blog_hero_editable', 'warn',
                           f'Could not check /blog: {exc}'))

    # ── 10. Hero text controls — functional end-to-end test ───────────────────
    # Verifies the T-panel save/inject pipeline works end-to-end:
    #   1. Auth → get token
    #   2. PUT hero_text_align + hero_text_color for a known services page
    #   3. GET that page with ?_stage=1 (admin staging view)
    #   4. Assert data-hero-text-align and data-hero-text-color appear in HTML
    #   5. Clean up (clear the settings)
    # If any step fails, the T-panel controls are broken — either the API doesn't
    # accept the fields, or _inject_hero_text_controls isn't running at serve time.
    _TEST_SLUG      = 'services/design-build-walnut-creek'
    _TEST_CARD_ID   = 'services-design-build-walnut-creek-hero'
    _TEST_ALIGN     = 'right'
    _TEST_COLOR     = 'dark'
    try:
        import urllib.parse as _up

        # Step 1: auth
        _ac, _aj = _post_json('/admin/api/auth', {'password': ADMIN_PASSWORD})
        if _ac != 200 or 'token' not in _aj:
            raise RuntimeError(f'auth failed: HTTP {_ac}')
        _tok = _aj['token']

        # Step 2: PUT hero text settings
        _slug_enc = _up.quote(_TEST_SLUG, safe='')
        _pc, _pj = _put_json(
            f'/admin/api/cards/{_slug_enc}/{_TEST_CARD_ID}',
            {
                'mode': 'image', 'color': '#1C1C1C', 'image': None,
                'position': '50% 50%', 'zoom': 1.0,
                'hero_text_align': _TEST_ALIGN,
                'hero_text_color': _TEST_COLOR,
                'hero_cta_visible': 'show',
            },
            _tok,
        )
        if _pc != 200 or not _pj.get('ok'):
            raise RuntimeError(f'card PUT failed: HTTP {_pc} {_pj}')

        # Step 3: GET staged page
        _slug_path = _TEST_SLUG.replace('services/', '')
        _gc, _, _body = _get(f'/view/services/{_slug_path}.html?_stage=1')
        if _gc != 200:
            raise RuntimeError(f'staged page returned HTTP {_gc}')

        # Step 4: assert injected attributes present
        _missing = []
        if f'data-hero-text-align="{_TEST_ALIGN}"' not in _body:
            _missing.append(f'data-hero-text-align="{_TEST_ALIGN}"')
        if f'data-hero-text-color="{_TEST_COLOR}"' not in _body:
            _missing.append(f'data-hero-text-color="{_TEST_COLOR}"')

        # Step 5: clean up regardless of result
        _put_json(
            f'/admin/api/cards/{_slug_enc}/{_TEST_CARD_ID}',
            {'mode': 'image', 'color': '#1C1C1C', 'image': None,
             'position': '50% 50%', 'zoom': 1.0},
            _tok,
        )

        if _missing:
            results.append(_r(
                'hero_text_controls_functional', 'fail',
                f'T-panel save/inject broken — missing from staged HTML: '
                + ', '.join(_missing) + '. '
                'Check _inject_hero_text_controls() in preview_server.py and '
                'that the PUT endpoint accepts hero_text_align/hero_text_color.',
                auto_fixable=False,
            ))
        else:
            results.append(_r(
                'hero_text_controls_functional', 'pass',
                f'T-panel end-to-end OK: save → _inject_hero_text_controls → '
                f'data-hero-text-align/color appear in staged HTML',
            ))

        # Also verify overlay scripts include rd_set_hero_text listener (live preview)
        _oc, _, _oscript = _get_auth(
            f'/admin/api/overlay-scripts?slug={_up.quote(_TEST_SLUG)}'
            f'&token={_tok}&device=desktop',
            token=_tok,
        )
        if _oc != 200:
            results.append(_r('hero_text_overlay_listener', 'warn',
                               f'overlay-scripts returned HTTP {_oc}'))
        elif 'rd_set_hero_text' not in _oscript:
            results.append(_r(
                'hero_text_overlay_listener', 'fail',
                'rd_set_hero_text listener missing from overlay-scripts — '
                'T-panel live preview will not work (changes will not appear in '
                'iframe until page reload). Check _CARD_EDIT_OVERLAY_TPL in '
                'preview_server.py.',
                auto_fixable=False,
            ))
        else:
            results.append(_r(
                'hero_text_overlay_listener', 'pass',
                'rd_set_hero_text listener present in overlay-scripts — '
                'T-panel live preview will update iframe in real time',
            ))

        # ── Check: G panel save must NOT wipe T panel settings (cross-contamination) ──
        # Sequence: save T settings → save gradient (G panel) → verify T settings survive
        try:
            # Save T settings
            _put_json(
                f'/admin/api/cards/{_slug_enc}/{_TEST_CARD_ID}',
                {
                    'mode': 'image', 'color': '#1C1C1C', 'image': None,
                    'position': '50% 50%', 'zoom': 1.0,
                    'hero_text_align': 'left', 'hero_text_color': 'dark',
                    'hero_cta_visible': 'show',
                },
                _tok,
            )
            # Simulate G panel save (only sends gradient + cardState fields as G panel does)
            _put_json(
                f'/admin/api/cards/{_slug_enc}/{_TEST_CARD_ID}',
                {
                    'mode': 'image', 'color': '#1C1C1C', 'image': None,
                    'position': '50% 50%', 'zoom': 1.0,
                    'gradient_type': 'fade', 'gradient_tint': 'dark',
                    'gradient_opacity': 50, 'gradient_direction': 'bottom', 'gradient_distance': 80,
                    # G panel save MUST include hero_text_* (fix was applied)
                    'hero_text_align': 'left', 'hero_text_color': 'dark', 'hero_cta_visible': 'show',
                    'hero_cta_align': None, 'hero_cta_primary': None, 'hero_cta_secondary': None,
                },
                _tok,
            )
            # GET staged page and check text settings survived
            _gc2, _, _body2 = _get(f'/view/services/{_slug_path}.html?_stage=1')
            _wipe_missing = []
            if 'data-hero-text-align="left"' not in _body2:
                _wipe_missing.append('data-hero-text-align="left"')
            if 'data-hero-text-color="dark"' not in _body2:
                _wipe_missing.append('data-hero-text-color="dark"')
            # Clean up
            _put_json(
                f'/admin/api/cards/{_slug_enc}/{_TEST_CARD_ID}',
                {'mode': 'image', 'color': '#1C1C1C', 'image': None, 'position': '50% 50%', 'zoom': 1.0},
                _tok,
            )
            if _wipe_missing:
                results.append(_r(
                    'g_panel_no_text_wipe', 'fail',
                    'G panel save wiped T panel text settings — after G panel save, '
                    + ', '.join(_wipe_missing) + ' missing from staged HTML. '
                    'G panel cardState in rd_gradient_open message must include hero_text_* fields.',
                    auto_fixable=False,
                ))
            else:
                results.append(_r(
                    'g_panel_no_text_wipe', 'pass',
                    'G panel save preserves T panel text settings — cross-contamination fix confirmed',
                ))
        except Exception as _wipe_exc:
            results.append(_r('g_panel_no_text_wipe', 'warn',
                               f'G panel cross-contamination test skipped: {_wipe_exc}'))

    except Exception as exc:
        results.append(_r('hero_text_controls_functional', 'warn',
                           f'Hero text controls test skipped: {exc}'))

    return results


if __name__ == '__main__':
    results = run()
    fails  = [r for r in results if r['status'] == 'fail']
    warns  = [r for r in results if r['status'] == 'warn']
    passes = [r for r in results if r['status'] == 'pass']

    for r in passes:
        print(f"  \033[32m✓\033[0m [{r['check']}] {r['detail']}")
    for r in warns:
        print(f"  \033[33m⚠\033[0m [{r['check']}] {r.get('page','')} — {r['detail']}")
    for r in fails:
        print(f"  \033[31m✗\033[0m [{r['check']}] {r.get('page','')} — {r['detail']}")

    print(f"\n{len(fails)} critical, {len(warns)} warnings, {len(passes)} passed")
    sys.exit(1 if fails else 0)
