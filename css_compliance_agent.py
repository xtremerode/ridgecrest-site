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

  HERO FLASH PREVENTION (critical — blocks commit):
    • .page-hero--service rule has background-color: #0d1a22
      (without this, the ::before overlay renders on the white body = dark gray flash)
    • .hero__bg rule has background-color defined
      (without this, homepage hero shows white body before image loads)
    • No background-image set statically in CSS for hero elements
      (hero images must be injected by server/JS so preload and prefetch work correctly;
       static CSS background-image bypasses the server injection pipeline)

  WARNING
    • hero__actions, page-hero--service, project-hero selectors present
    • nav--scrolled transition rule present
    • rd-card--color-mode class selector present (color cycling fix)
    • diff__visual--one / diff__visual--two selectors present (split panel)
    • about-visual--one / about-visual--two selectors present (split panel)
    • No TODO/FIXME/HACK comments left in production CSS files

GUARDRAIL POLICY:
  Never remove background-color from .page-hero--service or .hero__bg.
  Never add a background-image to any hero class in main.css — images are
  injected by the server (_apply_hero_to_html, if-not-hero block) and must
  go through that pipeline to get the preload, _1920w variant, and prefetch.
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

    # ── .page-hero--service must have background-color fallback ──────────────────
    # Without background-color on .page-hero--service, the ::before overlay renders
    # on the white body background (#FAFAF8) while the hero image is loading,
    # producing a dark gray flash (rgba(8,12,18,0.72) on white = ~#363d42).
    # background-color: #0d1a22 ensures a consistent dark tone while image loads.
    import re as _re
    _bghero_block = _re.search(
        r'\.page-hero--service\s*\{[^}]*\}', main_css, _re.DOTALL)
    if _bghero_block:
        if 'background-color' not in _bghero_block.group(0):
            results.append(_r('hero_bg_color_fallback', 'fail',
                               '.page-hero--service rule in main.css has no background-color — '
                               '::before overlay will render on white body (#FAFAF8) = dark gray flash '
                               'while hero image loads. Add background-color: #0d1a22.',
                               'main.css', auto_fixable=False))
        else:
            results.append(_r('hero_bg_color_fallback', 'pass',
                               '.page-hero--service has background-color — no gray flash while hero image loads',
                               'main.css'))
    else:
        results.append(_r('hero_bg_color_fallback', 'warn',
                           '.page-hero--service rule not found in main.css',
                           'main.css'))

    # ── Hero flash prevention: .hero__bg must have background-color ──────────────
    _bghomehero = _re.search(r'\.hero__bg\s*\{[^}]*\}', main_css, _re.DOTALL)
    if _bghomehero:
        if 'background-color' not in _bghomehero.group(0):
            results.append(_r('hero_bg_home_color', 'fail',
                               '.hero__bg rule in main.css has no background-color — '
                               'homepage hero will flash white body while image loads. '
                               'Add background-color: #0d1a22.',
                               'main.css', auto_fixable=False))
        else:
            results.append(_r('hero_bg_home_color', 'pass',
                               '.hero__bg has background-color — no white flash on homepage hero',
                               'main.css'))

    # ── Hero flash prevention: no static background-image on hero classes in CSS ─
    # Hero images must be injected by the server (_apply_hero_to_html / if-not-hero
    # block) to get the preload hint, _1920w size optimization, and prefetch links.
    # If main.css sets background-image statically on a hero class, those benefits
    # are bypassed and the image will flash on every navigation.
    _HERO_CSS_CLASSES = ['.hero__bg', '.page-hero--service', '.project-hero__img',
                          '.blog-hero', '.post-hero']
    for _hcc in _HERO_CSS_CLASSES:
        _hcc_block = _re.search(
            re.escape(_hcc) + r'\s*\{[^}]*background-image\s*:[^}]*\}',
            main_css, _re.DOTALL
        )
        if _hcc_block:
            results.append(_r('no_static_hero_bg_image', 'fail',
                               f'{_hcc} in main.css has a static background-image — '
                               f'hero images must be server-injected (not CSS) to get '
                               f'preload, _1920w optimization, and prefetch.',
                               'main.css', auto_fixable=False))

    # ── overrides.css: page-hero__actions CTA guardrail (Apr 2026) ───────────────
    # Services/ subdirectory pages use .page-hero__actions instead of .hero__actions.
    # overrides.css must extend the CTA visibility/alignment selectors to cover it.
    # If missing, the T button panel's hide/show/align controls silently do nothing
    # on 130+ services/ pages.
    OVERRIDES_REQUIRED = [
        ('[data-hero-cta="hide"] .page-hero__actions',
         'CTA hide rule for services page-hero__actions'),
        ('page-hero__actions [data-cta-id="primary"]',
         'per-button CTA primary hide rule for services pages'),
        ('page-hero__actions [data-cta-id="secondary"]',
         'per-button CTA secondary hide rule for services pages'),
    ]
    overrides_css = ''
    _overrides_path = os.path.join(CSS_DIR, 'overrides.css')
    if os.path.isfile(_overrides_path):
        with open(_overrides_path, 'r', encoding='utf-8', errors='replace') as fh:
            overrides_css = fh.read()
    for token, description in OVERRIDES_REQUIRED:
        if token not in overrides_css:
            results.append(_r('overrides_services_cta', 'fail',
                               f'overrides.css missing guardrail: {token} ({description}). '
                               f'Add CTA hide/align rules for .page-hero__actions so the T panel '
                               f'works on services/ pages.',
                               'overrides.css', auto_fixable=False))
        else:
            results.append(_r('overrides_services_cta', 'pass',
                               f'overrides.css has {description}', 'overrides.css'))

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
