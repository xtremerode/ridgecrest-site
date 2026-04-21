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
    html_files = sorted(
        f for f in os.listdir(PREVIEW_DIR)
        if f.endswith('.html')
        and f not in NO_HERO_PAGES
        and not f.startswith('admin')
    )

    # Global card-id registry: id → list of pages
    card_id_registry: Dict[str, List[str]] = {}

    # ── Per-file checks ────────────────────────────────────────────────────────
    hero_pass = True
    for filename in html_files:
        path = os.path.join(PREVIEW_DIR, filename)
        page = filename
        is_project = bool(PROJECT_PAGE_PATTERN.match(filename))

        with open(path, 'r', encoding='utf-8', errors='replace') as fh:
            html = fh.read()

        soup = BeautifulSoup(html, 'html.parser')

        # ── Card ID uniqueness ──────────────────────────────────────────────
        for el in soup.find_all(attrs={'data-card-id': True}):
            cid = el['data-card-id']
            card_id_registry.setdefault(cid, []).append(page)

        # ── data-card-id on .page-hero--service (architectural violation) ──
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
            if hero.get('data-card-id'):
                results.append(_r(
                    'no_dual_id', 'fail',
                    f"hero '{hero_id}' has both data-hero-id AND "
                    f"data-card-id='{hero['data-card-id']}' — architectural violation",
                    page, auto_fixable=True
                ))
                hero_pass = False

            # ── hero__actions class present ───────────────────────────────
            actions_el = (
                hero.find(class_='hero__actions') or
                hero.find(class_='project-hero__right')
            )
            if not actions_el:
                results.append(_r(
                    'hero_has_actions', 'warn',
                    f"hero '{hero_id}' has no .hero__actions or .project-hero__right",
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
                hero.find(attrs={'data-gradient-id': True}) or
                (hero.parent and hero.parent.find(attrs={'data-gradient-id': True}))
            )
            if not gradient_el:
                results.append(_r(
                    'hero_gradient_id', 'warn',
                    f"hero '{hero_id}': no [data-gradient-id] overlay found",
                    page, auto_fixable=False
                ))

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

    # ── Summary pass entries (one per check category if no failures) ───────────
    if hero_pass and not any(r['check'] == 'hero_has_id' and r['status'] == 'fail'
                             for r in results):
        results.append(_r('hero_attributes', 'pass',
                          f"All hero elements have data-hero-id ({len(html_files)} pages checked)"))
    if not dup_found:
        total_ids = sum(len(v) for v in card_id_registry.values())
        results.append(_r('card_id_unique', 'pass',
                          f"{len(card_id_registry)} card IDs across {len(html_files)} pages — all unique"))

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
