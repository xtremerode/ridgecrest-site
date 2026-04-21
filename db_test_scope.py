"""
DB Test Scope — Web Development QA Agency
==========================================
Provides a context manager that snapshots DB tables before a test and
automatically restores them afterward. Prevents test-artifact records
(like accidental card_settings writes during BG panel testing) from
persisting to the live site.

Usage (in any agent or test script):
    from db_test_scope import DBTestScope

    with DBTestScope(tables=['card_settings', 'pages']):
        # make any DB changes here — they will be reverted on exit
        test_bg_panel()
    # DB is now exactly as it was before the with block

Command-line snapshot/restore:
    python db_test_scope.py snapshot            # save snapshot to /tmp/db_test_snapshot.json
    python db_test_scope.py restore             # restore from snapshot
    python db_test_scope.py restore path.json   # restore from specific file
    python db_test_scope.py diff                # show what changed since last snapshot

Tables protected by default (all DB-driven site content):
    card_settings, pages, system_settings, team_members, portfolio_projects
"""
import json
import os
import sys
import copy
from datetime import datetime, timezone
from typing import List, Optional

DEFAULT_SNAPSHOT_PATH = '/tmp/db_test_snapshot.json'
DEFAULT_TABLES = [
    'card_settings',
    'pages',
    'system_settings',
]

# Tables that should NEVER be touched during restore (leads, logs, etc.)
READONLY_TABLES = {
    'leads', 'agent_actions', 'agent_messages', 'heartbeats',
    'system_health', 'undo_log', 'image_labels',
}


def _get_conn():
    import db
    return db.get_connection()


def _snapshot_table(cur, table: str) -> List[dict]:
    """Return all rows of a table as a list of dicts."""
    cur.execute(f'SELECT * FROM "{table}"')
    cols = [d[0] for d in cur.description]
    rows = []
    for row in cur.fetchall():
        rows.append(dict(zip(cols, [str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v for v in row])))
    return rows


def take_snapshot(tables: Optional[List[str]] = None,
                  path: str = DEFAULT_SNAPSHOT_PATH) -> dict:
    """Snapshot the given tables to a JSON file. Returns the snapshot dict."""
    tables = tables or DEFAULT_TABLES
    tables = [t for t in tables if t not in READONLY_TABLES]

    conn = _get_conn()
    cur = conn.cursor()
    snapshot = {
        'taken_at': datetime.now(timezone.utc).isoformat(),
        'tables': {}
    }
    for table in tables:
        try:
            snapshot['tables'][table] = _snapshot_table(cur, table)
        except Exception as exc:
            print(f'[db_test_scope] WARNING: could not snapshot {table}: {exc}')
    conn.close()

    with open(path, 'w') as fh:
        json.dump(snapshot, fh, indent=2, default=str)
    print(f'[db_test_scope] Snapshot of {len(snapshot["tables"])} table(s) saved to {path}')
    return snapshot


def restore_snapshot(path: str = DEFAULT_SNAPSHOT_PATH) -> int:
    """Restore all tables from a snapshot file. Returns number of tables restored."""
    if not os.path.exists(path):
        print(f'[db_test_scope] ERROR: snapshot file not found: {path}')
        return 0

    with open(path) as fh:
        snapshot = json.load(fh)

    conn = _get_conn()
    cur = conn.cursor()
    restored = 0

    for table, rows in snapshot['tables'].items():
        if table in READONLY_TABLES:
            print(f'[db_test_scope] SKIP (readonly): {table}')
            continue
        try:
            # Delete all current rows
            cur.execute(f'DELETE FROM "{table}"')
            # Re-insert snapshot rows
            if rows:
                cols = list(rows[0].keys())
                placeholders = ', '.join(['%s'] * len(cols))
                col_names = ', '.join(f'"{c}"' for c in cols)
                insert_sql = f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders})'
                for row in rows:
                    values = [row[c] for c in cols]
                    cur.execute(insert_sql, values)
            print(f'[db_test_scope] Restored {table}: {len(rows)} row(s)')
            restored += 1
        except Exception as exc:
            conn.rollback()
            print(f'[db_test_scope] ERROR restoring {table}: {exc}')
            continue

    conn.commit()
    conn.close()
    print(f'[db_test_scope] Restore complete. {restored} table(s) restored from {snapshot["taken_at"]}')
    return restored


def diff_snapshot(path: str = DEFAULT_SNAPSHOT_PATH) -> dict:
    """Compare current DB state against snapshot. Returns dict of changes per table."""
    if not os.path.exists(path):
        return {}

    with open(path) as fh:
        snapshot = json.load(fh)

    conn = _get_conn()
    cur = conn.cursor()
    changes = {}

    for table, snap_rows in snapshot['tables'].items():
        try:
            current_rows = _snapshot_table(cur, table)
            snap_set = {json.dumps(r, sort_keys=True) for r in snap_rows}
            curr_set = {json.dumps(r, sort_keys=True) for r in current_rows}
            added   = [json.loads(r) for r in curr_set - snap_set]
            removed = [json.loads(r) for r in snap_set - curr_set]
            if added or removed:
                changes[table] = {'added': added, 'removed': removed}
        except Exception as exc:
            changes[table] = {'error': str(exc)}

    conn.close()
    return changes


class DBTestScope:
    """
    Context manager: snapshots DB tables on entry, restores on exit.

    with DBTestScope(tables=['card_settings']):
        # do stuff that modifies card_settings
    # card_settings is now restored to pre-test state

    Args:
        tables:      List of tables to protect. Defaults to DEFAULT_TABLES.
        snapshot_path: Where to store the snapshot (default /tmp/db_test_snapshot.json)
        verbose:     Print restore confirmation (default True)
        restore_on_success: If True (default), restore even if no exception was raised.
                     Set False to keep changes on success, only restore on failure.
    """

    def __init__(self, tables: Optional[List[str]] = None,
                 snapshot_path: str = DEFAULT_SNAPSHOT_PATH,
                 verbose: bool = True,
                 restore_on_success: bool = True):
        self.tables = tables or DEFAULT_TABLES
        self.snapshot_path = snapshot_path
        self.verbose = verbose
        self.restore_on_success = restore_on_success
        self._raised = False

    def __enter__(self):
        if self.verbose:
            print(f'[db_test_scope] Entering test scope — snapshotting: {self.tables}')
        take_snapshot(tables=self.tables, path=self.snapshot_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._raised = exc_type is not None
        if self._raised or self.restore_on_success:
            if self.verbose:
                reason = 'exception — reverting' if self._raised else 'test complete — reverting'
                print(f'[db_test_scope] {reason}')
            restore_snapshot(path=self.snapshot_path)
        else:
            if self.verbose:
                print('[db_test_scope] Test passed — keeping changes (restore_on_success=False)')
        return False  # never suppress exceptions


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'snapshot'
    path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_SNAPSHOT_PATH

    if cmd == 'snapshot':
        take_snapshot(path=path)

    elif cmd == 'restore':
        restore_snapshot(path=path)

    elif cmd == 'diff':
        changes = diff_snapshot(path=path)
        if not changes:
            print('No changes vs snapshot.')
        else:
            for table, delta in changes.items():
                if 'error' in delta:
                    print(f'{table}: ERROR — {delta["error"]}')
                    continue
                print(f'\n{table}:')
                for r in delta.get('added', []):
                    print(f'  + {r}')
                for r in delta.get('removed', []):
                    print(f'  - {r}')
    else:
        print(f'Unknown command: {cmd}. Use: snapshot | restore | diff')
        sys.exit(1)
