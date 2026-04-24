"""
Web Development QA Orchestrator
================================
Runs all web-dev QA agents and produces a unified report.
Mirrors the RMA orchestrator pattern but focused on the website build.

Agents run (in order):
  1. server_health_agent    — dev server up, all pages 200
  2. html_compliance_agent  — hero IDs, card IDs, CTA attributes, hero flash prevention
  3. css_compliance_agent   — required selectors, no baked CDN URLs, hero bg-color guardrails
  4. js_compliance_agent    — postMessage handlers, hero injection tokens, _HERO_CLASSES
  5. admin_panel_agent      — BG panel wiring, picker API saves
  6. server_currency_agent  — server restarted after last edit to preview_server.py/main.css/main.js
  7. visual_overlay_agent   — Playwright: edit pill visible & not occluded on hover (Rule 11)

Exit codes:
  0  — all clear (zero critical fails)
  1  — one or more CRITICAL failures

Usage:
  python web_dev_orchestrator.py          # full report
  python web_dev_orchestrator.py --quiet  # only print failures + summary
  python web_dev_orchestrator.py --fix    # pass fix=True to each agent (future)

Pre-commit mode (invoked by .git/hooks/pre-commit):
  python web_dev_orchestrator.py --pre-commit
  Exits 1 on any critical fail, prints compact summary.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GUARDRAIL POLICY — HERO FLASH PREVENTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The dark-background flash before hero images load has been reported and
"fixed" multiple times. Every agent now enforces a layer of the fix.
ANY code change that touches hero-related code MUST re-run this orchestrator
before being considered complete.

Four layers — ALL must pass:

Layer 1 — JS: _HERO_CLASSES in main.js (js_compliance_agent)
  _swapAll() must skip all 5 hero class names. Checked by js_compliance_agent.

Layer 2 — Server: _hero_display_path() in preview_server.py (js_compliance_agent)
  Hero images served as _1920w variants (~500KB vs 2-5MB full-res).
  Functions _HERO_FALLBACK_PATH, _NAV_PREFETCH_SLUGS, _get_nav_hero_paths must exist.

Layer 3 — CSS: background-color on hero elements (css_compliance_agent)
  .page-hero--service and .hero__bg must have background-color: #0d1a22.
  No static background-image on hero classes in CSS (bypasses server pipeline).

Layer 4 — Live server: preload + css_bg + prefetch on served pages (html_compliance_agent)
  Every served page must have fetchpriority="high" preload, CSS background-image
  in <style> before JS, and <link rel="prefetch"> for all nav pages' heroes.
  This is checked by hitting the live server on http://147.182.242.54:8081.

Rule: When any new feature is added that touches heroes, CTAs, or page templates,
immediately add a corresponding check to the appropriate agent. Guardrails must
grow with the codebase. Never ship a hero-related change without re-running this.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import argparse
import sys
from typing import List, Dict, Any

# ── Agent imports ─────────────────────────────────────────────────────────────
# Each agent exports run() -> List[Dict[str, Any]]
# with keys: agent, check, status ('pass'|'fail'|'warn'), detail, page, auto_fixable

def _import_agent(name: str):
    try:
        mod = __import__(name)
        return mod
    except ImportError as exc:
        return None


AGENTS = [
    ('server_health_agent',    'Server Health'),
    ('html_compliance_agent',  'HTML Compliance'),
    ('css_compliance_agent',   'CSS Compliance'),
    ('js_compliance_agent',    'JS Compliance'),
    ('admin_panel_agent',      'Admin Panel'),
    ('page_state_guard',       'Page State Guard'),
    ('db_approved_state',      'DB Approved State'),
    ('server_currency_agent',  'Server Currency'),
    ('visual_overlay_agent',   'Visual Overlay (Playwright)'),
]

# ANSI colours
GREEN  = '\033[32m'
YELLOW = '\033[33m'
RED    = '\033[31m'
CYAN   = '\033[36m'
BOLD   = '\033[1m'
RESET  = '\033[0m'


def _icon(status: str) -> str:
    return {
        'pass': f'{GREEN}✓{RESET}',
        'warn': f'{YELLOW}⚠{RESET}',
        'fail': f'{RED}✗{RESET}',
    }.get(status, '?')


def run_all(fix: bool = False, quiet: bool = False,
            pre_commit: bool = False) -> List[Dict[str, Any]]:
    all_results: List[Dict[str, Any]] = []

    for module_name, label in AGENTS:
        mod = _import_agent(module_name)
        if mod is None:
            all_results.append({
                'agent': module_name,
                'check': 'agent_import',
                'status': 'fail',
                'detail': f'Could not import {module_name} — file missing?',
                'page': '',
                'auto_fixable': False,
            })
            continue

        if not quiet:
            print(f"\n{CYAN}{BOLD}── {label} ──────────────────────────────{RESET}")

        try:
            results = mod.run(fix=fix)
        except Exception as exc:
            results = [{
                'agent': module_name,
                'check': 'agent_run',
                'status': 'fail',
                'detail': f'{module_name}.run() raised: {exc}',
                'page': '',
                'auto_fixable': False,
            }]

        for r in results:
            all_results.append(r)
            status = r.get('status', '?')
            if pre_commit and status == 'pass':
                continue   # compact pre-commit output: skip passes
            if quiet and status == 'pass':
                continue
            page   = r.get('page', '')
            detail = r.get('detail', '')
            check  = r.get('check', '')
            loc    = f' [{page}]' if page else ''
            print(f"  {_icon(status)} [{check}]{loc} {detail}")

    return all_results


def _summary(results: List[Dict[str, Any]]) -> tuple:
    fails  = [r for r in results if r['status'] == 'fail']
    warns  = [r for r in results if r['status'] == 'warn']
    passes = [r for r in results if r['status'] == 'pass']
    return fails, warns, passes


def main() -> int:
    parser = argparse.ArgumentParser(description='Web Dev QA Orchestrator')
    parser.add_argument('--quiet',      action='store_true', help='Only print failures')
    parser.add_argument('--fix',        action='store_true', help='Run auto-fix on agents that support it')
    parser.add_argument('--pre-commit', action='store_true', help='Compact output mode for git hook')
    args = parser.parse_args()

    pre_commit = args.pre_commit
    quiet      = args.quiet or pre_commit

    if not quiet:
        print(f"\n{BOLD}Web Dev QA Agency — Full Compliance Run{RESET}")
        print("=" * 50)

    results = run_all(fix=args.fix, quiet=quiet, pre_commit=pre_commit)
    fails, warns, passes = _summary(results)

    print()
    print("=" * 50)
    if fails:
        print(f"{RED}{BOLD}✗ {len(fails)} CRITICAL failure(s){RESET}  |  "
              f"{YELLOW}{len(warns)} warning(s){RESET}  |  "
              f"{GREEN}{len(passes)} passed{RESET}")
        if pre_commit:
            print(f"\n{RED}Pre-commit gate: BLOCKED.{RESET} Fix critical issues above before committing.")
        return 1
    elif warns:
        print(f"{GREEN}{BOLD}✓ All critical checks passed{RESET}  |  "
              f"{YELLOW}{len(warns)} warning(s){RESET}  |  "
              f"{GREEN}{len(passes)} passed{RESET}")
        return 0
    else:
        print(f"{GREEN}{BOLD}✓ All checks passed{RESET}  ({len(passes)} checks)")
        return 0


if __name__ == '__main__':
    sys.exit(main())
