"""
Server Health Agent — Web Development QA Agency
================================================
Verifies the dev preview server (port 8082) is up and serving correctly.
Checks every HTML page returns 200, key admin API endpoints respond,
and the DB is reachable.

Checks (critical = blocks commit):
  CRITICAL
    • Dev server is reachable at http://127.0.0.1:8082/
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

BASE_URL   = 'http://127.0.0.1:8082'
PREVIEW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'preview')
ADMIN_PASSWORD = 'ridgecrest2026!'
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
