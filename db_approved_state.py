"""
DB Approved State Agent — Web Development QA Agency
====================================================
Validates that all admin-owned settings in system_settings match their
approved production values. Also checks card_settings for test artifacts
that would mask hero images on live pages.

WHY THIS AGENT EXISTS
---------------------
Two categories of regression have caused repeated bugs:

1. Admin panel saves test values during development (e.g., nav opacity set
   to 0.3 while testing) — those values persist in DB and override the
   server-injected CSS variables on every page load.

2. Admin testing with solid-color mode leaves card_settings rows with
   mode='color', image=NULL — these rows override hero images with a dark
   solid color, causing pages to show a blank dark panel instead of the hero.

This agent catches both before they ship.

Checks (critical = blocks commit):
  CRITICAL
    • Test artifact card_settings rows: mode='color' AND image IS NULL
      (these override hero/card images with a solid color; left over from
       admin testing; must be deleted before ship)

  WARNING (will not block commit but indicates drift from approved values)
    • nav_band_opacity: approved 0.6, floor 0.4
    • nav_scrolled_opacity: approved 0.94, floor 0.7
    • nav_blur_radius: approved 8.0, floor 4.0
    • about_visual_mode: approved 'one'
    • home_diff_mode: approved 'one'
"""
import sys
from typing import List, Dict, Any

# ── Approved system_settings values ──────────────────────────────────────────
# Each entry: key → {'type': 'numeric'|'string', 'approved': ..., 'min': ..., 'label': ...}
# 'min' only for numeric. 'approved' is the production-confirmed value.
APPROVED = {
    'nav_band_opacity': {
        'type': 'numeric',
        'approved': 0.6,
        'min': 0.4,
        'label': 'Nav band opacity (pre-scroll)',
        'source': 'opacity 0.6 approved 2026-04-08 (overrides.css comment) + Henry confirmation 2026-04-22',
    },
    'nav_scrolled_opacity': {
        'type': 'numeric',
        'approved': 0.94,
        'min': 0.7,
        'label': 'Nav scrolled opacity',
        'source': 'Henry confirmation 2026-04-22',
    },
    'nav_blur_radius': {
        'type': 'numeric',
        'approved': 8.0,
        'min': 4.0,
        'label': 'Nav backdrop blur (px)',
        'source': 'Original CSS default blur(8px); Henry confirmation 2026-04-22',
    },
    'about_visual_mode': {
        'type': 'string',
        'approved': 'one',
        'label': 'About page visual mode (one|two)',
        'source': 'Production default — split panel is dev-only',
    },
    'home_diff_mode': {
        'type': 'string',
        'approved': 'one',
        'label': 'Home differentiator zone mode (one|two)',
        'source': 'Production default — split panel is dev-only',
    },
}


def _r(check: str, status: str, detail: str = '', page: str = '',
        auto_fixable: bool = False) -> Dict[str, Any]:
    return {
        'agent': 'db_approved_state',
        'check': check,
        'status': status,
        'detail': detail,
        'page': page,
        'auto_fixable': auto_fixable,
    }


def run(fix: bool = False) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    try:
        import db as _db
    except ImportError:
        return [_r('db_import', 'warn',
                   'db module not available — DB state checks skipped')]

    # ── system_settings: approved values ─────────────────────────────────────
    try:
        with _db.get_db() as (conn, cur):
            cur.execute("SELECT key, value FROM system_settings")
            rows = {r['key']: r['value'] for r in cur.fetchall()}
    except Exception as exc:
        return [_r('db_connect', 'warn',
                   f'Could not read system_settings: {exc}')]

    for key, spec in APPROVED.items():
        raw = rows.get(key)
        label = spec['label']
        approved = spec['approved']

        if raw is None:
            results.append(_r('approved_setting', 'warn',
                               f'{key} not found in system_settings — '
                               f'using server default (approved: {approved})',
                               page=key))
            continue

        if spec['type'] == 'numeric':
            try:
                val = float(raw)
            except (ValueError, TypeError):
                results.append(_r('approved_setting', 'warn',
                                   f'{key} = {raw!r} — not a number', page=key))
                continue
            floor = spec.get('min', 0)
            if val < floor:
                results.append(_r('approved_setting', 'fail',
                                   f'{label}: DB value is {val} — below minimum floor {floor}. '
                                   f'Approved production value is {approved}. '
                                   f'This is likely a test artifact. '
                                   f'Fix: UPDATE system_settings SET value=\'{approved}\' WHERE key=\'{key}\';',
                                   page=key))
            elif val != approved:
                results.append(_r('approved_setting', 'warn',
                                   f'{label}: DB value is {val} (approved {approved}) — '
                                   f'intentional change or drift? Source: {spec["source"]}',
                                   page=key))
            else:
                results.append(_r('approved_setting', 'pass',
                                   f'{label}: {val} ✓ (approved value)',
                                   page=key))

        else:  # string
            if raw != approved:
                results.append(_r('approved_setting', 'warn',
                                   f'{label}: DB value is {raw!r} (approved {approved!r}) — '
                                   f'intentional change or test artifact?',
                                   page=key))
            else:
                results.append(_r('approved_setting', 'pass',
                                   f'{label}: {raw!r} ✓ (approved value)',
                                   page=key))

    # ── card_settings: test artifact detection ────────────────────────────────
    # Records with mode='color' AND image IS NULL are test artifacts: the admin
    # panel was used in color-cycling mode during development but the card was
    # never returned to image mode. These rows override the hero image with a
    # solid dark color on every page load, causing blank dark panels.
    try:
        with _db.get_db() as (conn, cur):
            cur.execute(
                """SELECT card_id, color, updated_at
                   FROM card_settings
                   WHERE mode = 'color' AND (image IS NULL OR image = '')
                   ORDER BY updated_at DESC"""
            )
            artifacts = cur.fetchall()
    except Exception as exc:
        results.append(_r('card_test_artifacts', 'warn',
                           f'Could not query card_settings: {exc}'))
        artifacts = []

    if artifacts:
        for row in artifacts:
            results.append(_r('card_test_artifacts', 'fail',
                               f"card_settings['{row['card_id']}'] has mode='color', image=NULL, "
                               f"color={row['color']!r} (updated {row['updated_at']}) — "
                               f"this overrides the hero/card image with a solid color. "
                               f"Test artifact — delete or reset to image mode before ship. "
                               f"Fix: DELETE FROM card_settings WHERE card_id='{row['card_id']}';",
                               page=row['card_id'], auto_fixable=True))
    else:
        results.append(_r('card_test_artifacts', 'pass',
                           'No test-artifact card_settings rows (mode=color, image=NULL)'))

    return results


if __name__ == '__main__':
    results = run()
    fails  = [r for r in results if r['status'] == 'fail']
    warns  = [r for r in results if r['status'] == 'warn']
    passes = [r for r in results if r['status'] == 'pass']

    GREEN  = '\033[32m'
    YELLOW = '\033[33m'
    RED    = '\033[31m'
    RESET  = '\033[0m'

    for r in passes:
        print(f"  {GREEN}✓{RESET} [{r['check']}] {r['detail']}")
    for r in warns:
        print(f"  {YELLOW}⚠{RESET} [{r['check']}] {r.get('page','')} — {r['detail']}")
    for r in fails:
        print(f"  {RED}✗{RESET} [{r['check']}] {r.get('page','')} — {r['detail']}")

    print(f"\n{len(fails)} critical, {len(warns)} warnings, {len(passes)} passed")
    sys.exit(1 if fails else 0)
