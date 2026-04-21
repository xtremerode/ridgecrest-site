"""
JS Compliance Agent — Web Development QA Agency
================================================
Parses all JS files in preview/js/ and the admin panel JS in
preview/admin/ and checks them against architectural rules.

Checks (critical = blocks commit):
  CRITICAL
    • main.js: applyHeroTransform defined
    • main.js: __RD_HERO used for service hero image injection
    • main.js: __RD_DIFF_MODE IIFE present (diff split panel)
    • main.js: __RD_ABOUT_VISUAL_MODE IIFE present (about split panel)
    • main.js: HERO_FALLBACK must never be /undefined or /null
    • preview_server.py: rd_set_hero_bg postMessage handler present
    • preview_server.py: rd_hero_bg_open postMessage handler present

  WARNING
    • main.js: responsive image swap IIFE present (_pickVariant)
    • main.js: fade-in IntersectionObserver present
    • main.js: nav scroll handler present
    • admin/pages.html: pendingBgPick variable declared
    • admin/pages.html: heroBgPanel element referenced
    • No console.log left in production JS (main.js, lightbox.js)
    • No alert() calls in production JS
"""
import os
import re
import sys
from typing import List, Dict, Any

PREVIEW_DIR = os.path.dirname(os.path.abspath(__file__))
JS_DIR      = os.path.join(PREVIEW_DIR, 'preview', 'js')
ADMIN_DIR   = os.path.join(PREVIEW_DIR, 'preview', 'admin')
SERVER_FILE = os.path.join(PREVIEW_DIR, 'preview_server.py')

CONSOLE_LOG_RE = re.compile(r'\bconsole\.log\s*\(')
ALERT_RE        = re.compile(r'\balert\s*\(')


def _r(check: str, status: str, detail: str = '', file: str = '',
        auto_fixable: bool = False) -> Dict[str, Any]:
    return {
        'agent': 'js_compliance',
        'check': check,
        'status': status,
        'detail': detail,
        'page': file,
        'auto_fixable': auto_fixable,
    }


def _read(path: str) -> str:
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        return fh.read()


def _check_token(content: str, token: str, filename: str,
                 description: str, severity: str,
                 results: List[Dict[str, Any]]) -> bool:
    if token in content:
        results.append(_r(f'token_{token[:40]}', 'pass',
                           f'Found: {description}', filename))
        return True
    else:
        results.append(_r(f'token_{token[:40]}', severity,
                           f'{filename} missing required token: {description}', filename))
        return False


def run(fix: bool = False) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    # ── main.js checks ────────────────────────────────────────────────────────
    main_js_path = os.path.join(JS_DIR, 'main.js')
    if not os.path.exists(main_js_path):
        results.append(_r('main_js_exists', 'fail', 'main.js not found in preview/js/'))
    else:
        main_js = _read(main_js_path)

        critical_tokens = [
            ('applyHeroTransform',      'applyHeroTransform() helper function'),
            ('__RD_HERO',               'server-injected hero image variable'),
            ('HERO_FALLBACK',           'deterministic hero fallback constant'),
            ('__RD_DIFF_MODE',          'diff split panel mode IIFE'),
            ('__RD_ABOUT_VISUAL_MODE',  'about split panel mode IIFE'),
            ('page-hero--service',      'service hero image injection querySelector'),
        ]
        for token, desc in critical_tokens:
            _check_token(main_js, token, 'main.js', desc, 'fail', results)

        warn_tokens = [
            ('_pickVariant',            'responsive image swap (_pickVariant)'),
            ('IntersectionObserver',    'fade-in IntersectionObserver'),
            ('nav--scrolled',           'nav scroll state toggle'),
            ('__RD_NAV_OPACITY',        'admin-controlled nav opacity injection'),
            ('__RD_CARD_OVERLAY',       'admin-controlled card overlay injection'),
        ]
        for token, desc in warn_tokens:
            _check_token(main_js, token, 'main.js', desc, 'warn', results)

        # HERO_FALLBACK must reference HERO_POOL[0], not a literal undefined/null
        if 'HERO_FALLBACK' in main_js:
            if re.search(r'HERO_FALLBACK\s*=\s*[`\'"][^`\'"]*undefined', main_js):
                results.append(_r('hero_fallback_valid', 'fail',
                                   'HERO_FALLBACK contains "undefined" — broken fallback URL',
                                   'main.js'))
            elif re.search(r'HERO_FALLBACK\s*=\s*[`\'"][^`\'"]*null', main_js):
                results.append(_r('hero_fallback_valid', 'fail',
                                   'HERO_FALLBACK contains "null" — broken fallback URL',
                                   'main.js'))
            else:
                results.append(_r('hero_fallback_valid', 'pass',
                                   'HERO_FALLBACK definition looks valid', 'main.js'))

        # No console.log in main.js
        log_count = len(CONSOLE_LOG_RE.findall(main_js))
        if log_count:
            results.append(_r('no_console_log_main', 'warn',
                               f'main.js has {log_count} console.log() call(s) — remove for production',
                               'main.js'))
        else:
            results.append(_r('no_console_log_main', 'pass',
                               'No console.log() in main.js', 'main.js'))

        # No alert() in main.js
        if ALERT_RE.search(main_js):
            results.append(_r('no_alert_main', 'fail',
                               'main.js contains alert() — must not be in production',
                               'main.js'))
        else:
            results.append(_r('no_alert_main', 'pass',
                               'No alert() in main.js', 'main.js'))

    # ── preview_server.py: postMessage handler checks ─────────────────────────
    if not os.path.exists(SERVER_FILE):
        results.append(_r('server_file_exists', 'fail',
                           f'preview_server.py not found at {SERVER_FILE}'))
    else:
        server = _read(SERVER_FILE)

        server_tokens = [
            ('rd_set_hero_bg',       'rd_set_hero_bg postMessage handler (BG panel save)'),
            ('rd_hero_bg_open',      'rd_hero_bg_open postMessage sender (BG button)'),
            ('rd_set_hero_text',     'rd_set_hero_text postMessage handler (text panel)'),
            ('_apply_hero_color_mode', '_apply_hero_color_mode() server-side function'),
            ('_strip_hero_card_ids', '_strip_hero_card_ids() service hero protection'),
            ('data-hero-id',         'data-hero-id attribute injection'),
        ]
        for token, desc in server_tokens:
            _check_token(server, token, 'preview_server.py', desc, 'fail', results)

    # ── admin/pages.html: BG panel wiring ─────────────────────────────────────
    pages_html_path = os.path.join(ADMIN_DIR, 'pages.html')
    if not os.path.exists(pages_html_path):
        results.append(_r('pages_html_exists', 'warn',
                           'admin/pages.html not found — BG panel checks skipped'))
    else:
        pages_html = _read(pages_html_path)

        pages_tokens_warn = [
            ('pendingBgPick',  'pendingBgPick variable (BG panel image browse state)'),
            ('heroBgPanel',    '#heroBgPanel element (BG panel HTML)'),
            ('rd_hero_bg_open', 'rd_hero_bg_open message handler in pages.html'),
            ('bgColorPicker',  'bgColorPicker color input'),
        ]
        for token, desc in pages_tokens_warn:
            _check_token(pages_html, token, 'admin/pages.html', desc, 'warn', results)

    # ── lightbox.js: no alert() ───────────────────────────────────────────────
    lightbox_path = os.path.join(JS_DIR, 'lightbox.js')
    if os.path.exists(lightbox_path):
        lb = _read(lightbox_path)
        if ALERT_RE.search(lb):
            results.append(_r('no_alert_lightbox', 'fail',
                               'lightbox.js contains alert()', 'lightbox.js'))
        else:
            results.append(_r('no_alert_lightbox', 'pass',
                               'No alert() in lightbox.js', 'lightbox.js'))

    return results


if __name__ == '__main__':
    results = run()
    fails  = [r for r in results if r['status'] == 'fail']
    warns  = [r for r in results if r['status'] == 'warn']
    passes = [r for r in results if r['status'] == 'pass']

    for r in passes:
        print(f"  \033[32m✓\033[0m [{r['check']}] {r.get('page','')} — {r['detail']}")
    for r in warns:
        print(f"  \033[33m⚠\033[0m [{r['check']}] {r.get('page','')} — {r['detail']}")
    for r in fails:
        print(f"  \033[31m✗\033[0m [{r['check']}] {r.get('page','')} — {r['detail']}")

    print(f"\n{len(fails)} critical, {len(warns)} warnings, {len(passes)} passed")
    sys.exit(1 if fails else 0)
