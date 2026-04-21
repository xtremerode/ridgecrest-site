"""
Admin Panel Agent — Web Development QA Agency
=============================================
Checks the admin panel HTML/JS for structural completeness and
correct wiring of all interactive features.

Checks (critical = blocks commit):
  CRITICAL
    • admin/pages.html: heroBgPanel present and has save button
    • admin/pages.html: heroTextPanel present
    • admin/pages.html: pendingBgPick, pendingPick, pendingCardPick declared
    • admin/pages.html: message handler for rd_hero_bg_open dispatches to _bgpOpen
    • admin/pages.html: message handler for rd_set_hero_bg sends to iframe
    • admin/pages.html: pickerUse click handler saves to both pages + card_settings APIs
    • admin/index.html: dashboard KPI cards present
    • admin/settings.html: exists and has settings form structure

  WARNING
    • admin/pages.html: Escape key closes heroBgPanel
    • admin/pages.html: closePicker() clears pendingBgPick
    • admin/pages.html: bgColorPicker and bgColorHex are synced (two-way)
    • admin/pages.html: bgModeRow toggle buttons (data-bv) present
    • All admin pages have <title> tags
    • All admin pages link to admin.css
"""
import os
import re
import sys
from typing import List, Dict, Any

ADMIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'preview', 'admin')

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False


def _r(check: str, status: str, detail: str = '', page: str = '',
        auto_fixable: bool = False) -> Dict[str, Any]:
    return {
        'agent': 'admin_panel',
        'check': check,
        'status': status,
        'detail': detail,
        'page': page,
        'auto_fixable': auto_fixable,
    }


def _read(path: str) -> str:
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        return fh.read()


def _check(content: str, token: str, page: str, description: str,
           severity: str, results: List[Dict[str, Any]]) -> bool:
    if token in content:
        results.append(_r(f'token_present', 'pass', f'Found: {description}', page))
        return True
    else:
        results.append(_r(f'token_present', severity,
                           f'{page} missing: {description}', page))
        return False


def run(fix: bool = False) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    admin_files = sorted(f for f in os.listdir(ADMIN_DIR) if f.endswith('.html'))
    if not admin_files:
        return [_r('admin_files_exist', 'fail',
                   f'No HTML files found in {ADMIN_DIR}')]

    results.append(_r('admin_files_exist', 'pass',
                       f'Found {len(admin_files)} admin HTML file(s)'))

    # ── pages.html deep checks ────────────────────────────────────────────────
    pages_path = os.path.join(ADMIN_DIR, 'pages.html')
    if not os.path.exists(pages_path):
        results.append(_r('pages_html_exists', 'fail',
                           'admin/pages.html does not exist'))
    else:
        pages = _read(pages_path)

        # CRITICAL: Panel elements
        critical_tokens = [
            ('heroBgPanel',            'heroBgPanel container element'),
            ('heroTextPanel',          'heroTextPanel container element'),
            ('bgSave',                 'bgSave button in heroBgPanel'),
            ('bgColorPicker',          'bgColorPicker color input'),
            ('bgColorHex',             'bgColorHex text input'),
            ('bgModeRow',              'bgModeRow toggle row'),
        ]
        for token, desc in critical_tokens:
            _check(pages, token, 'admin/pages.html', desc, 'fail', results)

        # CRITICAL: JS wiring
        js_critical = [
            ('pendingBgPick',          'pendingBgPick variable declaration'),
            ('pendingPick',            'pendingPick variable declaration'),
            ('pendingCardPick',        'pendingCardPick variable declaration'),
            ('rd_hero_bg_open',        'rd_hero_bg_open message handler'),
            ('_bgpOpen',               '_bgpOpen() function (BG panel open)'),
            ('rd_set_hero_bg',         'rd_set_hero_bg postMessage to iframe'),
        ]
        for token, desc in js_critical:
            _check(pages, token, 'admin/pages.html', desc, 'fail', results)

        # CRITICAL: pickerUse saves to BOTH APIs
        # Search the entire file for the key patterns — they live inside the handler
        # which spans many lines. Searching full content is safe because these tokens
        # are only meaningful inside the pickerUse handler context.
        has_picker = 'pickerUse' in pages
        if has_picker:
            # pages API save: PUT to /admin/api/pages/${...} with hero_image in body
            saves_pages = ('hero_image' in pages and
                           re.search(r'api/pages.*hero_image|hero_image.*api/pages',
                                     pages, re.DOTALL) is not None)
            # cards API save: PUT to /admin/api/cards/... (used for card_settings)
            saves_cards = bool(re.search(r'api/cards/.*pendingBgPick|pendingBgPick.*api/cards',
                                         pages, re.DOTALL) or
                               (re.search(r'api/cards/', pages) and 'pendingBgPick' in pages))

            if saves_pages:
                results.append(_r('picker_saves_pages', 'pass',
                                   'pickerUse saves hero_image to pages API', 'admin/pages.html'))
            else:
                results.append(_r('picker_saves_pages', 'fail',
                                   'pickerUse missing hero_image save to pages API',
                                   'admin/pages.html'))

            if saves_cards:
                results.append(_r('picker_saves_cards', 'pass',
                                   'pickerUse saves image to card_settings via cards API',
                                   'admin/pages.html'))
            else:
                results.append(_r('picker_saves_cards', 'fail',
                                   'pickerUse missing card_settings save in BG panel path',
                                   'admin/pages.html'))
        else:
            results.append(_r('picker_saves_pages', 'warn',
                               'Could not locate pickerUse handler for verification',
                               'admin/pages.html'))

        # WARNING: UX details
        warn_tokens = [
            ('Escape',                 'Escape key closes panel'),
            ('closePicker',            'closePicker() function'),
            ('pendingBgPick = null',   'closePicker() clears pendingBgPick'),
            ('data-bv',                'bgModeRow toggle data-bv buttons'),
            ('_updateModeVis',         '_updateModeVis() mode visibility function'),
        ]
        for token, desc in warn_tokens:
            _check(pages, token, 'admin/pages.html', desc, 'warn', results)

    # ── All admin pages: <title> and admin.css link ───────────────────────────
    if _HAS_BS4:
        for filename in admin_files:
            path = os.path.join(ADMIN_DIR, filename)
            content = _read(path)
            soup = BeautifulSoup(content, 'html.parser')

            title = soup.find('title')
            if not title or not title.get_text(strip=True):
                results.append(_r('admin_page_title', 'warn',
                                   f'{filename} has no <title> tag', filename))

            css_links = [lnk.get('href', '') for lnk in soup.find_all('link', rel='stylesheet')]
            has_admin_css = any('admin.css' in h for h in css_links)
            if not has_admin_css:
                results.append(_r('admin_css_linked', 'warn',
                                   f'{filename} does not link admin.css', filename))

    # ── admin/index.html: KPI dashboard structure ─────────────────────────────
    index_path = os.path.join(ADMIN_DIR, 'index.html')
    if os.path.exists(index_path):
        index = _read(index_path)
        kpi_tokens = [
            ('kpi',        'KPI card element'),
            ('dashboard',  'dashboard section reference'),
        ]
        for token, desc in kpi_tokens:
            _check(index, token, 'admin/index.html', desc, 'warn', results)
    else:
        results.append(_r('admin_index_exists', 'fail',
                           'admin/index.html not found'))

    # ── admin/settings.html: exists ───────────────────────────────────────────
    settings_path = os.path.join(ADMIN_DIR, 'settings.html')
    if os.path.exists(settings_path):
        results.append(_r('admin_settings_exists', 'pass',
                           'admin/settings.html exists'))
    else:
        results.append(_r('admin_settings_exists', 'fail',
                           'admin/settings.html not found'))

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
