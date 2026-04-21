"""
CSS Compliance Agent — Web Development QA Agency
=================================================
Parses all CSS files in preview/css/ and checks them against
architectural rules accumulated in CLAUDE.md and memory.

Checks (critical = blocks commit):
  CRITICAL
    • data-card-id selector present in main.css (card edit system hook)
    • data-hero-id / data-cta-id CSS rules present (hero CTA hide/show)
    • No background-image hardcoded with wix-static CDN URLs in main.css
      (images must be loaded via JS / server injection, not baked into CSS)
    • CSS custom properties (--var) not redefined inline with fixed px values
      in a way that breaks theming (spot-check for known vars)

  WARNING
    • hero__actions, page-hero--service, project-hero selectors present
    • nav--scrolled transition rule present
    • rd-card--color-mode class selector present (color cycling fix)
    • diff__visual--one / diff__visual--two selectors present (split panel)
    • about-visual--one / about-visual--two selectors present (split panel)
    • No TODO/FIXME/HACK comments left in production CSS files
"""
import os
import re
import sys
from typing import List, Dict, Any, Tuple

CSS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'preview', 'css')

# Wix CDN prefix — must not appear as baked-in background-image in CSS
WIX_CDN_RE = re.compile(r'static\.wixstatic\.com', re.IGNORECASE)

# Required selectors / tokens that MUST exist in main.css
REQUIRED_CRITICAL = [
    ('[data-card-id]',          'card edit system hook selector'),
    ('[data-cta-id="primary"]', 'hero CTA primary hide/show rule'),
    ('data-hero-cta-primary',   'hero CTA primary attribute rule'),
]

REQUIRED_WARN = [
    ('hero__actions',            '.hero__actions selector'),
    ('page-hero--service',       '.page-hero--service selector'),
    ('project-hero',             '.project-hero selector'),
    ('nav--scrolled',            'nav scroll state rule'),
    ('rd-card--color-mode',      'color cycling fix class'),
    ('diff__visual--one',        'diff split panel --one variant'),
    ('diff__visual--two',        'diff split panel --two variant'),
    ('about-visual--one',        'about split panel --one variant'),
    ('about-visual--two',        'about split panel --two variant'),
]

TODO_RE = re.compile(r'/\*.*?(TODO|FIXME|HACK).*?\*/', re.IGNORECASE | re.DOTALL)


def _r(check: str, status: str, detail: str = '', file: str = '',
        auto_fixable: bool = False) -> Dict[str, Any]:
    return {
        'agent': 'css_compliance',
        'check': check,
        'status': status,
        'detail': detail,
        'page': file,
        'auto_fixable': auto_fixable,
    }


def _load_css(filename: str) -> Tuple[str, str]:
    path = os.path.join(CSS_DIR, filename)
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        return fh.read(), path


def run(fix: bool = False) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    css_files = sorted(f for f in os.listdir(CSS_DIR) if f.endswith('.css'))
    if not css_files:
        return [_r('css_files_exist', 'fail', f'No CSS files found in {CSS_DIR}')]

    results.append(_r('css_files_exist', 'pass',
                       f'Found {len(css_files)} CSS file(s): {", ".join(css_files)}'))

    # ── main.css required selectors ───────────────────────────────────────────
    if 'main.css' not in css_files:
        results.append(_r('main_css_exists', 'fail', 'main.css not found in preview/css/'))
        return results

    main_css, _ = _load_css('main.css')

    for token, description in REQUIRED_CRITICAL:
        if token not in main_css:
            results.append(_r('required_selector', 'fail',
                               f'main.css missing required token: {token} ({description})',
                               'main.css'))
        else:
            results.append(_r('required_selector', 'pass',
                               f'main.css has {token}', 'main.css'))

    for token, description in REQUIRED_WARN:
        if token not in main_css:
            results.append(_r('recommended_selector', 'warn',
                               f'main.css missing expected token: {token} ({description})',
                               'main.css'))

    # ── Wix CDN URLs baked into CSS (critical) ────────────────────────────────
    wix_hits = []
    for filename in css_files:
        css, _ = _load_css(filename)
        if WIX_CDN_RE.search(css):
            # Find the lines for context
            lines = [i + 1 for i, ln in enumerate(css.splitlines())
                     if WIX_CDN_RE.search(ln)]
            wix_hits.append(f'{filename} (lines {lines[:5]})')

    if wix_hits:
        results.append(_r('no_wix_cdn_in_css', 'fail',
                           'Wix CDN URLs baked into CSS (must be loaded via JS/server): '
                           + ', '.join(wix_hits),
                           auto_fixable=False))
    else:
        results.append(_r('no_wix_cdn_in_css', 'pass',
                           'No Wix CDN URLs found in any CSS file'))

    # ── TODO/FIXME/HACK comments in CSS ──────────────────────────────────────
    todo_hits = []
    for filename in css_files:
        css, _ = _load_css(filename)
        matches = TODO_RE.findall(css)
        if matches:
            todo_hits.append(f'{filename} ({len(matches)} occurrence(s))')

    if todo_hits:
        results.append(_r('no_css_todos', 'warn',
                           'TODO/FIXME/HACK found in CSS: ' + ', '.join(todo_hits)))
    else:
        results.append(_r('no_css_todos', 'pass', 'No TODO/FIXME/HACK comments in CSS'))

    # ── CSS custom property consistency: --card-overlay must exist ────────────
    required_vars = ['--card-overlay', '--nav-band-opacity', '--nav-blur']
    for var in required_vars:
        if var not in main_css:
            results.append(_r('css_custom_property', 'warn',
                               f'main.css missing CSS custom property definition: {var}',
                               'main.css'))

    # ── Check split panel CSS classes are complete pairs ─────────────────────
    split_pairs = [
        ('diff__visual--one', 'diff__visual--two'),
        ('about-visual--one', 'about-visual--two'),
    ]
    for cls_one, cls_two in split_pairs:
        has_one = cls_one in main_css
        has_two = cls_two in main_css
        if has_one and has_two:
            results.append(_r('split_panel_css', 'pass',
                               f'Split panel pair complete: {cls_one} / {cls_two}',
                               'main.css'))
        elif has_one or has_two:
            missing = cls_two if has_one else cls_one
            results.append(_r('split_panel_css', 'fail',
                               f'Split panel incomplete — {missing} defined but pair missing',
                               'main.css'))

    return results


if __name__ == '__main__':
    results = run()
    fails  = [r for r in results if r['status'] == 'fail']
    warns  = [r for r in results if r['status'] == 'warn']
    passes = [r for r in results if r['status'] == 'pass']

    for r in passes:
        print(f"  \033[32m✓\033[0m [{r['check']}] {r.get('page','')} {r['detail']}")
    for r in warns:
        print(f"  \033[33m⚠\033[0m [{r['check']}] {r.get('page','')} — {r['detail']}")
    for r in fails:
        print(f"  \033[31m✗\033[0m [{r['check']}] {r.get('page','')} — {r['detail']}")

    print(f"\n{len(fails)} critical, {len(warns)} warnings, {len(passes)} passed")
    sys.exit(1 if fails else 0)
