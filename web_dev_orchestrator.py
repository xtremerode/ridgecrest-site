"""
Web Development QA Orchestrator
================================
Runs all web-dev QA agents and produces a unified report.
Mirrors the RMA orchestrator pattern but focused on the website build.

Agents run (in order):
  1. server_health_agent   — dev server up, all pages 200
  2. html_compliance_agent — hero IDs, card IDs, CTA attributes
  3. css_compliance_agent  — required selectors, no baked CDN URLs
  4. js_compliance_agent   — postMessage handlers, hero injection tokens
  5. admin_panel_agent     — BG panel wiring, picker API saves

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
    ('server_health_agent',   'Server Health'),
    ('html_compliance_agent', 'HTML Compliance'),
    ('css_compliance_agent',  'CSS Compliance'),
    ('js_compliance_agent',   'JS Compliance'),
    ('admin_panel_agent',     'Admin Panel'),
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
