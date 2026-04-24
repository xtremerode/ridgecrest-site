"""
Server Currency Agent
=====================
Verifies the running preview server was started AFTER the last modification
to key source files (preview_server.py, main.css, main.js).

If a key file was modified AFTER the server process started, the server is
running stale code. A restart is required before that commit can be valid.

This enforces the rule: any edit to preview_server.py, main.css, or main.js
must be followed by a server restart before committing (CLAUDE.md §36).

Exports: run(fix=False) -> List[Dict]
"""
import os
import subprocess
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Files that require a server restart when changed
KEY_FILES = [
    ('preview_server.py',     os.path.join(BASE_DIR, 'preview_server.py')),
    ('main.css',              os.path.join(BASE_DIR, 'preview', 'css', 'main.css')),
    ('main.js',               os.path.join(BASE_DIR, 'preview', 'js', 'main.js')),
]

# Grace period: files modified within this many seconds of server start are OK
# (handles the case where a restart script touches files at the same moment)
GRACE_SECONDS = 5


def _get_server_start_time():
    """
    Return (start_timestamp, pid_list) for the preview_server.py process
    currently listening on port 8081.

    Uses ss to find the PID bound to :8081, then reads /proc/<pid>/stat for
    the start time. Falls back to the most recently started preview_server.py
    process if ss lookup fails. Returns (None, []) if no server is running.
    """
    try:
        # Primary: find PID listening on port 8081
        ss_result = subprocess.run(
            ['ss', '-tlnp', 'sport', '= :8081'],
            capture_output=True, text=True
        )
        listening_pid = None
        for line in ss_result.stdout.splitlines():
            if ':8081' in line and 'pid=' in line:
                # format: ... users:(("python3",pid=12345,fd=6))
                import re
                m = re.search(r'pid=(\d+)', line)
                if m:
                    listening_pid = m.group(1)
                    break

        # Fallback: all preview_server.py processes — use most recently started
        result = subprocess.run(
            ['pgrep', '-f', 'preview_server.py'],
            capture_output=True, text=True
        )
        all_pids = [p.strip() for p in result.stdout.strip().split('\n') if p.strip()]
        if not all_pids:
            return None, []

        clk_tck = os.sysconf('SC_CLK_TCK')
        with open('/proc/uptime') as f:
            uptime_secs = float(f.read().split()[0])
        boot_time = time.time() - uptime_secs

        def _pid_start(pid):
            try:
                with open(f'/proc/{pid}/stat') as f:
                    stat = f.read()
                after_paren = stat.split(')')[-1].split()
                starttime_ticks = int(after_paren[19])
                return boot_time + (starttime_ticks / clk_tck)
            except Exception:
                return None

        if listening_pid and listening_pid in all_pids:
            ts = _pid_start(listening_pid)
            if ts:
                return ts, [listening_pid]

        # Fallback: use the most recently started process
        pid_times = [(pid, _pid_start(pid)) for pid in all_pids]
        pid_times = [(pid, ts) for pid, ts in pid_times if ts is not None]
        if not pid_times:
            return None, []

        latest_pid, latest_ts = max(pid_times, key=lambda x: x[1])
        return latest_ts, [latest_pid]

    except Exception:
        return None, []


def run(fix=False):
    results = []
    agent = 'server_currency_agent'

    server_start, pids = _get_server_start_time()

    if server_start is None:
        results.append({
            'agent': agent,
            'check': 'server_running',
            'status': 'fail',
            'detail': 'preview_server.py process not found — server is not running',
            'page': '',
            'auto_fixable': False,
        })
        return results

    start_str = datetime.fromtimestamp(server_start).strftime('%Y-%m-%d %H:%M:%S')
    results.append({
        'agent': agent,
        'check': 'server_running',
        'status': 'pass',
        'detail': f'Server running (PID {",".join(pids)}, started {start_str})',
        'page': '',
        'auto_fixable': False,
    })

    any_stale = False
    for fname, fpath in KEY_FILES:
        if not os.path.exists(fpath):
            results.append({
                'agent': agent,
                'check': f'file_exists_{fname}',
                'status': 'warn',
                'detail': f'{fname} not found on disk — skipping currency check',
                'page': '',
                'auto_fixable': False,
            })
            continue

        mtime = os.path.getmtime(fpath)
        mtime_str = datetime.fromtimestamp(mtime).strftime('%H:%M:%S')

        if mtime > server_start + GRACE_SECONDS:
            any_stale = True
            results.append({
                'agent': agent,
                'check': f'stale_{fname}',
                'status': 'fail',
                'detail': (
                    f'{fname} was modified at {mtime_str} but server started at '
                    f'{datetime.fromtimestamp(server_start).strftime("%H:%M:%S")} — '
                    f'server is running STALE code. Restart the server before committing.'
                ),
                'page': '',
                'auto_fixable': False,
            })
        else:
            results.append({
                'agent': agent,
                'check': f'current_{fname}',
                'status': 'pass',
                'detail': f'{fname} — server started after last modification (current)',
                'page': '',
                'auto_fixable': False,
            })

    return results
