"""
Page State Guard — Ridgecrest Designs Website
==============================================
Documents the expected state of each main page and validates the live server
matches. Run after any code change that touches preview_server.py, main.js,
or any CSS file to confirm nothing broke.

Usage:
  python page_state_guard.py              # check live server at 8081
  python page_state_guard.py --server http://127.0.0.1:8082  # check dev

Exit codes:
  0 — all checks passed
  1 — one or more CRITICAL failures

GUARDRAIL RULE:
  After every code edit to server/CSS/JS, run this script.
  If any check fails, restore from the DB or fix the code — never ship a broken state.
"""
import sys
import re
import urllib.request
import urllib.error
import argparse
from typing import List, Dict, Any

# ── Expected page state ───────────────────────────────────────────────────────
# These are the known-good hero image patterns for each key page.
# If the served page doesn't inject a background-image containing this pattern,
# the guard fails. Update this list whenever you intentionally change a hero.
#
# Format: (slug, url_path, hero_image_pattern, description)
EXPECTED_HEROES = [
    ('home',              '/view/',                        '1777305909',      'Homepage hero'),
    ('about',             '/view/about.html',              '487bdc0f',        'About page hero'),
    ('portfolio',         '/view/portfolio.html',          '0b10882438704be9','Portfolio page hero'),
    ('process',           '/view/process.html',            'd2d0371f',        'Process page hero'),
    ('contact',           '/view/contact.html',            '75a9ba9c',        'Contact page hero'),
    ('team',              '/view/team.html',               '8f25d193',        'Team page hero'),
    ('custom-homes',        '/view/custom-homes.html',             '71ff636f',  'Custom homes hero'),
    ('kitchen-remodels',    '/view/kitchen-remodels.html',         '53f46b46',  'Kitchen remodels hero'),
    ('bathroom-remodels',   '/view/bathroom-remodels.html',        'cfe52d2b',  'Bathroom remodels hero'),
    ('services',            '/view/services.html',                 '0f8e248f',  'Services page hero'),
    ('whole-house-remodels','/view/whole-house-remodels.html',     '1939fb8d',  'Whole-house remodels hero'),
    ('danville-dream',      '/view/danville-dream.html',           '83cbc49d',  'Project page hero (danville-dream)'),
    ('services/danville',   '/view/services/danville.html',        '9192e5d3',  'Services subpage hero (danville)'),
]

# ── CSS/JS consistency checks ─────────────────────────────────────────────────
# For each page, verify that:
#   1. <link rel="preload" fetchpriority="high"> is present (fast image start)
#   2. <style>.page-hero--service or .hero__bg has background-image (CSS injection)
#   3. window.__RD_HERO matches the CSS injection URL (no double-download flash)
#   4. window.__RD_HERO_MAP is present (hover prefetch map)

SERVER = 'http://147.182.242.54:8081'


def _r(check, status, detail='', page=''):
    return {'check': check, 'status': status, 'detail': detail, 'page': page}


def _fetch(url: str) -> str:
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        return ''


def check_page(slug: str, path: str, hero_pattern: str, description: str, server: str) -> List[Dict]:
    results = []
    url = server + path
    html = _fetch(url)
    if not html:
        results.append(_r(f'page_load', 'fail', f'Could not fetch {url}', slug))
        return results

    # 1. preload tag
    if 'fetchpriority="high"' in html:
        results.append(_r('preload_tag', 'pass', 'fetchpriority=high preload present', slug))
    else:
        results.append(_r('preload_tag', 'fail', f'Missing fetchpriority=high preload on {slug}', slug))

    # 2. CSS injection
    css_bg_m = re.search(r'background-image:url\("(/assets/[^"]+)"', html)
    if css_bg_m:
        results.append(_r('css_injection', 'pass', f'CSS background-image injected: ...{css_bg_m.group(1)[-30:]}', slug))
        css_url = css_bg_m.group(1)
        # Check hero pattern
        if hero_pattern in css_url:
            results.append(_r('hero_image', 'pass', f'{description} uses correct image', slug))
        else:
            results.append(_r('hero_image', 'fail',
                f'{description} — expected pattern "{hero_pattern}" in CSS URL but got: ...{css_url[-40:]}', slug))
    else:
        results.append(_r('css_injection', 'fail', f'No CSS background-image injection found on {slug}', slug))

    # 3. __RD_HERO matches CSS injection
    rd_hero_m = re.search(r'window\.__RD_HERO="([^"]+)"', html)
    if rd_hero_m and css_bg_m:
        if rd_hero_m.group(1) == css_bg_m.group(1):
            results.append(_r('rd_hero_match', 'pass',
                '__RD_HERO matches CSS injection URL (no double-download)', slug))
        else:
            results.append(_r('rd_hero_match', 'fail',
                f'__RD_HERO mismatch — CSS has ...{css_bg_m.group(1)[-30:]} '
                f'but __RD_HERO has ...{rd_hero_m.group(1)[-30:]} → will cause dark flash',
                slug))
    elif rd_hero_m:
        results.append(_r('rd_hero_match', 'warn', '__RD_HERO set but no CSS injection found', slug))

    # 4. hero map
    if '__RD_HERO_MAP' in html:
        results.append(_r('hero_map', 'pass', '__RD_HERO_MAP present (hover prefetch)', slug))
    else:
        results.append(_r('hero_map', 'warn', '__RD_HERO_MAP missing — hover prefetch disabled', slug))

    return results


# ── Approved nav settings ─────────────────────────────────────────────────────
# These were approved/confirmed working. Any value outside these ranges indicates
# a test artifact or accidental change that will make the nav hard to read.
# Source: overrides.css comment (opacity 0.6 approved 2026-04-08), original
# CSS default blur(8px), and Henry's confirmation 2026-04-22.
NAV_APPROVED = {
    '__RD_NAV_OPACITY':         {'min': 0.4, 'approved': 0.6,  'label': 'nav band opacity (pre-scroll)'},
    '__RD_NAV_SCROLLED_OPACITY':{'min': 0.7, 'approved': 0.94, 'label': 'nav scrolled opacity'},
    '__RD_NAV_BLUR':            {'min': 4.0, 'approved': 8.0,  'label': 'nav backdrop blur (px)'},
}


def check_nav_settings(server: str) -> List[Dict]:
    """Verify nav opacity/blur injected by server match approved values."""
    results = []
    html = _fetch(server + '/view/')
    if not html:
        results.append(_r('nav_settings', 'warn', 'Could not fetch home page to verify nav settings'))
        return results
    all_ok = True
    for var, spec in NAV_APPROVED.items():
        m = re.search(rf'window\.{re.escape(var)}=([0-9.]+)', html)
        if not m:
            results.append(_r('nav_settings', 'warn', f'{var} not found in page — nav JS may not apply'))
            continue
        val = float(m.group(1))
        label = spec['label']
        approved = spec['approved']
        if val < spec['min']:
            all_ok = False
            results.append(_r('nav_settings', 'fail',
                f'{label}: value is {val} — below minimum {spec["min"]}. '
                f'Approved value is {approved}. Likely a test artifact in system_settings.'))
        elif val != approved:
            results.append(_r('nav_settings', 'warn',
                f'{label}: value is {val} (approved {approved}) — intentional change or drift?'))
        else:
            results.append(_r('nav_settings', 'pass',
                f'{label}: {val} ✓ (approved value)'))
    return results


def run(fix: bool = False, server: str = SERVER) -> List[Dict]:
    all_results = []
    for slug, path, pattern, desc in EXPECTED_HEROES:
        results = check_page(slug, path, pattern, desc, server)
        all_results.extend(results)
    all_results.extend(check_nav_settings(server))
    return all_results


GREEN = '\033[32m'
YELLOW = '\033[33m'
RED = '\033[31m'
BOLD = '\033[1m'
RESET = '\033[0m'


def main():
    parser = argparse.ArgumentParser(description='Page State Guard')
    parser.add_argument('--server', default=SERVER, help='Server base URL')
    args = parser.parse_args()

    print(f'\n{BOLD}Page State Guard — {args.server}{RESET}')
    print('=' * 55)

    results = run(args.server)
    fails = [r for r in results if r['status'] == 'fail']
    warns = [r for r in results if r['status'] == 'warn']
    passes = [r for r in results if r['status'] == 'pass']

    for r in results:
        icon = {
            'pass': f'{GREEN}✓{RESET}',
            'warn': f'{YELLOW}⚠{RESET}',
            'fail': f'{RED}✗{RESET}',
        }.get(r['status'], '?')
        if r['status'] != 'pass':
            print(f"  {icon} [{r['check']}] [{r['page']}] {r['detail']}")

    print()
    print('=' * 55)
    if fails:
        print(f"{RED}{BOLD}✗ {len(fails)} CRITICAL{RESET}  |  {YELLOW}{len(warns)} warnings{RESET}  |  {GREEN}{len(passes)} passed{RESET}")
        return 1
    elif warns:
        print(f"{GREEN}{BOLD}✓ All critical passed{RESET}  |  {YELLOW}{len(warns)} warnings{RESET}  |  {GREEN}{len(passes)} passed{RESET}")
        return 0
    else:
        print(f"{GREEN}{BOLD}✓ All {len(passes)} checks passed{RESET}")
        return 0


if __name__ == '__main__':
    sys.exit(main())
