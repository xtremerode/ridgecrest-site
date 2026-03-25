"""
Shared database utilities for all agents.
"""
import os
import json
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
import zoneinfo

_PT = zoneinfo.ZoneInfo("America/Los_Angeles")

def pacific_today():
    """Return today's date in Pacific time (not UTC server time)."""
    return datetime.now(_PT).date()

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://agent_user:StrongPass123!@localhost:5432/marketing_agent")

logger = logging.getLogger(__name__)


def get_connection():
    """Return a raw psycopg2 connection."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


@contextmanager
def get_db():
    """Context manager: yields a connection + cursor, commits or rolls back."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield conn, cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Agent message bus
# ---------------------------------------------------------------------------

def send_message(from_agent: str, to_agent: str, message_type: str,
                 payload: dict, priority: int = 5) -> int:
    with get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO agent_messages (from_agent, to_agent, message_type, payload, priority)
               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (from_agent, to_agent, message_type, json.dumps(payload), priority)
        )
        return cur.fetchone()["id"]


def receive_messages(agent_name: str, limit: int = 20) -> list[dict]:
    """Fetch pending messages for an agent and mark them as processing."""
    with get_db() as (conn, cur):
        cur.execute(
            """SELECT * FROM agent_messages
               WHERE (to_agent = %s OR to_agent = 'all')
                 AND status = 'pending'
               ORDER BY priority ASC, created_at ASC
               LIMIT %s
               FOR UPDATE SKIP LOCKED""",
            (agent_name, limit)
        )
        rows = cur.fetchall()
        ids = [r["id"] for r in rows]
        if ids:
            cur.execute(
                "UPDATE agent_messages SET status='processing' WHERE id = ANY(%s)",
                (ids,)
            )
        return [dict(r) for r in rows]


def ack_message(message_id: int, error: str | None = None):
    status = "error" if error else "done"
    with get_db() as (conn, cur):
        cur.execute(
            """UPDATE agent_messages
               SET status=%s, processed_at=NOW(), error_detail=%s
               WHERE id=%s""",
            (status, error, message_id)
        )


# ---------------------------------------------------------------------------
# Agent heartbeats
# ---------------------------------------------------------------------------

def heartbeat(agent_name: str, status: str = "alive",
              error: str | None = None, metadata: dict | None = None):
    with get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO agent_heartbeats (agent_name, status, last_run_at, run_count, error_count, last_error, metadata)
               VALUES (%s, %s, NOW(), 1, %s, %s, %s)
               ON CONFLICT (agent_name) DO UPDATE SET
                   status = EXCLUDED.status,
                   last_run_at = NOW(),
                   run_count = agent_heartbeats.run_count + 1,
                   error_count = agent_heartbeats.error_count + (CASE WHEN %s IS NOT NULL THEN 1 ELSE 0 END),
                   last_error = COALESCE(%s, agent_heartbeats.last_error),
                   last_success_at = CASE WHEN %s IS NULL THEN NOW() ELSE agent_heartbeats.last_success_at END,
                   metadata = COALESCE(%s::jsonb, agent_heartbeats.metadata)""",
            (agent_name, status, 1 if error else 0, error,
             json.dumps(metadata or {}),
             error, error, error, json.dumps(metadata) if metadata else None)
        )


# ---------------------------------------------------------------------------
# Optimization action log
# ---------------------------------------------------------------------------

def log_action(agent_name: str, action_type: str, entity_type: str,
               entity_id: int | None, before: dict, after: dict,
               reason: str, google_entity_id: str | None = None):
    with get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO optimization_actions
               (agent_name, action_type, entity_type, entity_id, google_entity_id,
                before_value, after_value, reason)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (agent_name, action_type, entity_type, entity_id, google_entity_id,
             json.dumps(before), json.dumps(after), reason)
        )
        return cur.fetchone()["id"]


def mark_action_applied(action_id: int, result: str = "success"):
    with get_db() as (conn, cur):
        cur.execute(
            "UPDATE optimization_actions SET applied=TRUE, applied_at=NOW(), result=%s WHERE id=%s",
            (result, action_id)
        )
