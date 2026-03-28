"""
Supabase Sync Module
====================
Pulls latest data from the local PostgreSQL database and POSTs it to the
Lovable edge function after every pipeline run.

Endpoint: https://itoinsaotwsmidbosqbq.supabase.co/functions/v1/ingest-metrics

Tables synced:
  - performance_metrics
  - reports
  - agent_messages
  - optimization_actions
  - agent_heartbeats
  - budget_snapshots
"""
import json
import logging
import os
from datetime import date, datetime

import requests
from dotenv import load_dotenv

import db

load_dotenv()

logger = logging.getLogger(__name__)

INGEST_ENDPOINT = os.getenv(
    "SUPABASE_INGEST_ENDPOINT",
    "https://itoinsaotwsmidbosqbq.supabase.co/functions/v1/ingest-metrics",
)

TABLES = [
    "campaigns",
    "ad_groups",
    "ads",
    "performance_metrics",
    "reports",
    "agent_messages",
    "optimization_actions",
    "agent_heartbeats",
    "budget_snapshots",
]

# How many rows to pull per table per sync (most recent by primary key / id)
ROW_LIMIT = 500

# Cleanup retention windows
METRICS_RETENTION_DAYS   = 90   # keep 90 days of performance_metrics
MESSAGES_RETENTION_DAYS  = 7    # keep 7 days of processed agent_messages


def pre_sync_cleanup() -> dict:
    """
    Purge stale data from PostgreSQL before syncing to Lovable.

    - performance_metrics: delete rows older than METRICS_RETENTION_DAYS
    - agent_messages: delete processed (done/error) rows older than MESSAGES_RETENTION_DAYS
    - campaigns: mark as REMOVED any campaign not updated in 90 days (soft delete)

    Returns a dict summarising rows deleted per table.
    """
    deleted = {}
    with db.get_db() as (conn, cur):

        # 1. Old performance metrics
        cur.execute(
            """DELETE FROM performance_metrics
               WHERE metric_date < CURRENT_DATE - INTERVAL '%s days'""",
            (METRICS_RETENTION_DAYS,),
        )
        deleted["performance_metrics"] = cur.rowcount

        # 2. Processed agent messages
        cur.execute(
            """DELETE FROM agent_messages
               WHERE status IN ('done', 'error')
                 AND processed_at < NOW() - INTERVAL '%s days'""",
            (MESSAGES_RETENTION_DAYS,),
        )
        deleted["agent_messages"] = cur.rowcount

        # 3. Campaigns not synced in 90 days — soft-delete by marking REMOVED
        cur.execute(
            """UPDATE campaigns
               SET status = 'REMOVED', updated_at = NOW()
               WHERE last_synced_at < NOW() - INTERVAL '90 days'
                 AND status != 'REMOVED'""",
        )
        deleted["campaigns_marked_removed"] = cur.rowcount

    logger.info(
        "pre_sync_cleanup: metrics_deleted=%d messages_deleted=%d campaigns_removed=%d",
        deleted["performance_metrics"],
        deleted["agent_messages"],
        deleted["campaigns_marked_removed"],
    )
    return deleted


def _serialize(obj):
    """JSON-serialise types that json.dumps can't handle natively."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    import decimal
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serialisable")


def _fetch_table(cur, table: str) -> list[dict]:
    """
    Pull the most recent ROW_LIMIT rows from a table.
    Falls back gracefully if the table doesn't exist.
    """
    try:
        cur.execute(
            f"""
            SELECT *
            FROM {table}
            ORDER BY id DESC
            LIMIT %s
            """,
            (ROW_LIMIT,),
        )
        rows = [dict(row) for row in cur.fetchall()]
        # Ensure performance_metrics rows always carry the platform field
        if table == "performance_metrics":
            for row in rows:
                if not row.get("platform"):
                    row["platform"] = "google_ads"
        return rows
    except Exception as exc:
        logger.warning("supabase_sync: could not query table '%s': %s", table, exc)
        return []


def collect_payload() -> dict:
    """Query all tracked tables and return a structured payload."""
    payload: dict[str, list[dict]] = {}
    with db.get_db() as (conn, cur):
        for table in TABLES:
            rows = _fetch_table(cur, table)
            payload[table] = rows
            logger.debug("supabase_sync: fetched %d rows from %s", len(rows), table)
    return payload


def post_to_edge_function(payload: dict) -> bool:
    """
    POST the payload to the Supabase edge function.
    Returns True on success, False on any error.
    """
    api_key = os.getenv("INGEST_API_KEY", "")
    if not api_key:
        logger.error("supabase_sync: INGEST_API_KEY not set — skipping sync")
        return False

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }

    try:
        body = json.dumps(payload, default=_serialize)
        response = requests.post(
            INGEST_ENDPOINT,
            data=body,
            headers=headers,
            timeout=30,
        )
        if response.ok:
            logger.info(
                "supabase_sync: POST succeeded — status=%d tables=%s",
                response.status_code,
                list(payload.keys()),
            )
            return True
        else:
            logger.error(
                "supabase_sync: POST failed — status=%d body=%s",
                response.status_code,
                response.text[:500],
            )
            return False
    except requests.exceptions.RequestException as exc:
        logger.error("supabase_sync: network error — %s", exc)
        return False


def sync(pipeline_run_id: str | None = None) -> dict:
    """
    Main entry point called by the orchestrator after every pipeline run.

    Returns a result dict with keys: success, tables_synced, row_counts, error.
    """
    logger.info("supabase_sync: starting sync (run_id=%s)", pipeline_run_id)

    try:
        cleanup = pre_sync_cleanup()
    except Exception as exc:
        logger.warning("supabase_sync: cleanup failed (non-fatal) — %s", exc)
        cleanup = {}

    try:
        payload = collect_payload()
    except Exception as exc:
        logger.error("supabase_sync: failed to collect data — %s", exc, exc_info=True)
        return {"success": False, "error": str(exc)}

    row_counts = {table: len(rows) for table, rows in payload.items()}

    # Attach metadata so the edge function knows which pipeline run this came from
    payload["_meta"] = {
        "pipeline_run_id": pipeline_run_id,
        "synced_at": datetime.utcnow().isoformat() + "Z",
        "tables": TABLES,
        "row_counts": row_counts,
    }

    success = post_to_edge_function(payload)

    if success:
        db.heartbeat("supabase_sync", "success", metadata={"row_counts": row_counts})
    else:
        db.heartbeat("supabase_sync", "error", error="POST to edge function failed")

    result = {
        "success": success,
        "tables_synced": TABLES,
        "row_counts": row_counts,
        "cleanup": cleanup,
    }
    if not success:
        result["error"] = "POST to edge function failed — see logs for details"

    logger.info("supabase_sync: done — success=%s row_counts=%s", success, row_counts)
    return result


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [supabase_sync] %(levelname)s — %(message)s")
    result = sync(pipeline_run_id="manual")
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["success"] else 1)
