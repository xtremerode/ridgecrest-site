"""
HTML Compliance Agent — Web Development QA Agency
==================================================
Parses all HTML pages in preview/ and checks them against
architectural rules accumulated in CLAUDE.md and memory.

Checks (critical = blocks commit):
  CRITICAL
    • data-hero-id present on every hero container element
    • No element with both data-hero-id AND data-card-id
    • All data-card-id values globally unique across all pages
    • No data-card-id on .page-hero--service (stripped by _strip_hero_card_ids)
    • No CTA links pointing directly to elevate-scheduling or base44.app
      (all CTAs must go through start-a-project.html — iframe embed is the exception)

  WARNING
    • hero__actions class present inside every hero
    • data-cta-id="primary" present inside every hero with actions
    • data-gradient-id present on hero overlay elements
    • data-cta-id="secondary" present (main pages only, project pages exempt)
"""
import os
import re
import sys
from typing import List, Dict, Any

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False

PREVIEW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'preview')

# Pages that intentionally have no hero (no check needed)
NO_HERO_PAGES = {'sitemap.html', 'allprojects.html'}

# Project pages: only primary CTA required, secondary is optional
PROJECT_PAGE_PATTERN = re.compile(
    r'^(alamo-luxury|castro-valley-villa|danville-dream|danville-hilltop|'
    r'lafayette-bistro|lafayette-luxury|lakeside-cozy-cabin|'
    r'livermore-farmhouse-chic|napa-retreat|newark-minimal-kitchen|'
    r'orinda-kitchen|pleasanton-cottage-kitchen|pleasanton-custom|'
    r'pleasanton-garage|san-ramon-eclectic-bath|san-ramon|'
    r'sierra-mountain-ranch|sunol-homestead)\.html$'
)


def _r(check: str, status: str, detail: str = '', page: str = '',
        auto_fixable: bool = False) -> Dict[str, Any]:
    return {
        'agent': 'html_compliance',
        'check': check,
        'status': status,   # 'pass' | 'fail' | 'warn'
        'detail': detail,
        'page': page,
        'auto_fixable': auto_fixable,
    }


def _is_hero_container(tag) -> bool:
    """True if this BS4 tag is a top-level hero container element."""
    classes = tag.get('class', [])
    if isinstance(classes, str):
        classes = classes.split()
    # Home page hero
    if tag.name == 'section' and 'hero' in classes and 'hero__bg' not in classes:
        return True
    # Service/inner page hero
    if 'page-hero--service' in classes:
        return True
    # Project page hero
    if 'project-hero' in classes:
        return True
    return False


def run(fix: bool = False) -> List[Dict[str, Any]]:
    if not _HAS_BS4:
        return [_r('bs4_available', 'warn',
                   'BeautifulSoup not installed — HTML checks skipped. '
                   'Run: pip install beautifulsoup4')]

    results: List[Dict[str, Any]] = []

    # Root-level pages
    _root_files = sorted(
        f for f in os.listdir(PREVIEW_DIR)
        if f.endswith('.html')
        and f not in NO_HERO_PAGES
        and not f.startswith('admin')
    )

    # services/ subdirectory pages (guardrail: every services/ hero must have data-hero-id)
    _svc_dir = os.path.join(PREVIEW_DIR, 'services')
    _svc_files = []
    if os.path.isdir(_svc_dir):
        _svc_files = sorted(
            os.path.join('services', f)
            for f in os.listdir(_svc_dir)
            if f.endswith('.html') and '.bak_' not in f
        )

    html_files = _root_files + _svc_files

    # Global card-id registry: id → list of pages
    card_id_registry: Dict[str, List[str]] = {}

    # ── Per-file checks ────────────────────────────────────────────────────────
    hero_pass = True
    for filename in html_files:
        path = os.path.join(PREVIEW_DIR, filename)
        page = filename
        is_project = bool(PROJECT_PAGE_PATTERN.match(os.path.basename(filename)))
        is_service = filename.startswith('services/')

        with open(path, 'r', encoding='utf-8', errors='replace') as fh:
            html = fh.read()

        soup = BeautifulSoup(html, 'html.parser')

        # ── Card ID uniqueness ──────────────────────────────────────────────
        # For services/ pages, skip data-card-id on the hero element itself —
        # it is stripped by _strip_hero_card_ids() at serve time and is not
        # a "real" card for uniqueness purposes.
        for el in soup.find_all(attrs={'data-card-id': True}):
            if is_service and 'page-hero--service' in el.get('class', []):
                continue  # hero card-id stripped at serve time
            cid = el['data-card-id']
            card_id_registry.setdefault(cid, []).append(page)

        # ── data-card-id on .page-hero--service (architectural violation) ──
        # Root-level pages: hero must NOT have data-card-id — card system and hero
        # overlay are separate and having both causes conflicts.
        # services/ pages: data-card-id may co-exist with data-hero-id in static HTML
        # because _strip_hero_card_ids() removes it at serve time. Not a violation.
        if not is_service:
            for el in soup.find_all(class_='page-hero--service'):
                if el.get('data-card-id'):
                    results.append(_r(
                        'no_card_id_on_service_hero', 'fail',
                        f"data-card-id='{el['data-card-id']}' on .page-hero--service "
                        f"(must be stripped by server — will shadow hero overlay)",
                        page, auto_fixable=True
                    ))
                    hero_pass = False

        # ── Find hero container elements ────────────────────────────────────
        heroes = [tag for tag in soup.find_all(True) if _is_hero_container(tag)]

        if not heroes:
            # Pages like team, services, start-a-project may have no classic hero
            continue

        for hero in heroes:
            # ── data-hero-id present ──────────────────────────────────────
            hero_id = hero.get('data-hero-id')
            if not hero_id:
                results.append(_r(
                    'hero_has_id', 'fail',
                    f"<{hero.name} class=\"{' '.join(hero.get('class',[]))}\"> "
                    f"missing data-hero-id",
                    page, auto_fixable=False
                ))
                hero_pass = False
                continue  # can't do further checks without the ID

            # ── data-hero-id + data-card-id on same element (critical) ───
            # services/ pages are exempt: data-card-id is stripped by the server at
            # serve time via _strip_hero_card_ids(). In static HTML both may coexist.
            if hero.get('data-card-id') and not is_service:
                results.append(_r(
                    'no_dual_id', 'fail',
                    f"hero '{hero_id}' has both data-hero-id AND "
                    f"data-card-id='{hero['data-card-id']}' — architectural violation",
                    page, auto_fixable=True
                ))
                hero_pass = False

            # ── hero__actions class present ───────────────────────────────
            # services/ pages use .page-hero__actions; main/project pages use
            # .hero__actions or .project-hero__right
            actions_el = (
                hero.find(class_='hero__actions') or
                hero.find(class_='project-hero__right') or
                hero.find(class_='page-hero__actions')
            )
            if not actions_el:
                results.append(_r(
                    'hero_has_actions', 'warn',
                    f"hero '{hero_id}' has no .hero__actions, .page-hero__actions, "
                    f"or .project-hero__right",
                    page, auto_fixable=False
                ))
            else:
                # ── data-cta-id="primary" ─────────────────────────────────
                primary_cta = actions_el.find(attrs={'data-cta-id': 'primary'})
                if not primary_cta:
                    results.append(_r(
                        'hero_cta_primary', 'warn',
                        f"hero '{hero_id}': no [data-cta-id=\"primary\"] in actions",
                        page, auto_fixable=False
                    ))

                # ── data-cta-id="secondary" (main pages only) ─────────────
                if not is_project:
                    secondary_cta = actions_el.find(attrs={'data-cta-id': 'secondary'})
                    if not secondary_cta:
                        results.append(_r(
                            'hero_cta_secondary', 'warn',
                            f"hero '{hero_id}': no [data-cta-id=\"secondary\"] "
                            f"(expected on non-project pages)",
                            page, auto_fixable=False
                        ))

            # ── data-gradient-id on overlay ───────────────────────────────
            gradient_el = (
                (hero if hero.get('data-gradient-id') else None) or  # on element itself
                hero.find(attrs={'data-gradient-id': True}) or        # inside element
                (hero.parent and hero.parent.find(attrs={'data-gradient-id': True}))
            )
            if not gradient_el:
                results.append(_r(
                    'hero_gradient_id', 'warn',
                    f"hero '{hero_id}': no [data-gradient-id] overlay found",
                    page, auto_fixable=False
                ))

    # ── Global: no direct external CTA links ──────────────────────────────────
    # All CTAs must route through start-a-project.html.
    # start-a-project.html itself is exempt (it embeds the iframe intentionally).
    BANNED_CTA_DOMAINS = ['elevate-scheduling-6b2fdec8.base44.app', 'base44.app']
    for filename in html_files:
        if filename == 'start-a-project.html':
            continue
        path = os.path.join(PREVIEW_DIR, filename)
        with open(path, 'r', encoding='utf-8', errors='replace') as fh:
            raw = fh.read()
        for domain in BANNED_CTA_DOMAINS:
            if domain in raw:
                results.append(_r(
                    'no_external_cta', 'fail',
                    f"Direct link to {domain} found — must route through start-a-project.html",
                    filename, auto_fixable=True
                ))
                hero_pass = False
                break

    # ── Global: card-id duplicates ─────────────────────────────────────────────
    dup_found = False
    for cid, pages in card_id_registry.items():
        if len(pages) > 1:
            results.append(_r(
                'card_id_unique', 'fail',
                f"data-card-id='{cid}' appears on multiple pages: {', '.join(pages)}",
                auto_fixable=False
            ))
            dup_found = True
            hero_pass = False

    # ── Global: undo_log gradient coverage check ─────────────────────────────
    # Catches a repeat of the Apr 2026 gradient-loss incident: the undo_log SELECT
    # query did not include gradient columns, so gradient edits were lost when
    # test-artifact records were deleted. This check reads preview_server.py and
    # verifies that the SELECT in admin_card_update captures gradient fields.
    server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'preview_server.py')
    if os.path.exists(server_path):
        with open(server_path, 'r', encoding='utf-8', errors='replace') as fh:
            server_src = fh.read()
        # The SELECT that precedes _log_undo in admin_card_update must include gradient_type
        # Look for SELECT ... gradient_type near _log_undo
        import re as _re
        has_grad_in_undo = bool(_re.search(
            r'SELECT[^;]*gradient_type[^;]*FROM card_settings[^;]*\n[^\n]*_log_undo',
            server_src, _re.DOTALL
        ))
        if not has_grad_in_undo:
            results.append(_r(
                'undo_log_gradient_coverage', 'warn',
                'preview_server.py admin_card_update SELECT before _log_undo may not include '
                'gradient_type — gradient edits may not be recoverable via undo. '
                'Ensure SELECT captures gradient_type, gradient_tint, gradient_opacity, '
                'gradient_direction, gradient_distance.',
                auto_fixable=False
            ))
        else:
            results.append(_r(
                'undo_log_gradient_coverage', 'pass',
                'admin_card_update undo_log SELECT includes gradient columns'
            ))

    # ── Summary pass entries (one per check category if no failures) ───────────
    if hero_pass and not any(r['check'] == 'hero_has_id' and r['status'] == 'fail'
                             for r in results):
        results.append(_r('hero_attributes', 'pass',
                          f"All hero elements have data-hero-id "
                          f"({len(_root_files)} root + {len(_svc_files)} services pages checked)"))
    if not dup_found:
        total_ids = sum(len(v) for v in card_id_registry.values())
        results.append(_r('card_id_unique', 'pass',
                          f"{len(card_id_registry)} card IDs across {len(html_files)} pages — all unique"))

    # ── Hero flash prevention: live server check ─────────────────────────────────
    # Every served page must have: preload, CSS background-image in <style>, and
    # cross-page prefetch links. This is the only way to guarantee no dark-navy flash.
    import urllib.request as _urlreq
    _SERVER = 'http://147.182.242.54:8081'
    _FLASH_PAGES = [
        ('index', f'{_SERVER}/view/index.html'),
        ('about', f'{_SERVER}/view/about.html'),
        ('process', f'{_SERVER}/view/process.html'),
        ('contact', f'{_SERVER}/view/contact.html'),
        ('blog', f'{_SERVER}/blog'),
    ]
    _flash_fails = []
    _flash_checked = 0
    for _fpslug, _fpurl in _FLASH_PAGES:
        try:
            _req = _urlreq.Request(_fpurl, headers={'User-Agent': 'Mozilla/5.0'})
            with _urlreq.urlopen(_req, timeout=4) as _resp:
                _fhtml = _resp.read().decode('utf-8', errors='replace')
            _has_preload  = 'rel="preload" as="image"' in _fhtml
            _has_css_bg   = 'background-image:url(' in _fhtml and '<style>' in _fhtml
            _has_prefetch = 'rel="prefetch" as="image"' in _fhtml
            _flash_checked += 1
            if not (_has_preload and _has_css_bg):
                _flash_fails.append(_fpslug)
                results.append(_r('hero_flash_prevention', 'fail',
                                   f'{_fpslug}: missing preload={not _has_preload} '
                                   f'css_bg={not _has_css_bg}', _fpslug))
            elif not _has_prefetch:
                results.append(_r('hero_flash_prevention', 'warn',
                                   f'{_fpslug}: missing prefetch links (cross-page cache warm)', _fpslug))
        except Exception as _fe:
            results.append(_r('hero_flash_prevention', 'warn',
                               f'{_fpslug}: server unreachable ({_fe})', _fpslug))
    if _flash_checked > 0 and not _flash_fails:
        results.append(_r('hero_flash_prevention', 'pass',
                           f'All {_flash_checked} sampled pages have preload + CSS bg-image'))

    return results


if __name__ == '__main__':
    results = run()
    fails = [r for r in results if r['status'] == 'fail']
    warns = [r for r in results if r['status'] == 'warn']
    passes = [r for r in results if r['status'] == 'pass']

    for r in passes:
        print(f"  \033[32m✓\033[0m [{r['check']}] {r['detail']}")
    for r in warns:
        print(f"  \033[33m⚠\033[0m [{r['check']}] {r.get('page','')} — {r['detail']}")
    for r in fails:
        print(f"  \033[31m✗\033[0m [{r['check']}] {r.get('page','')} — {r['detail']}")

    print(f"\n{len(fails)} critical, {len(warns)} warnings, {len(passes)} passed")
    sys.exit(1 if fails else 0)
