"""
config.py — Single source of truth for all business rules and configuration.
=============================================================================
All agents import constants from here. Never define these values in agent files.

Rules sourced from: CLAUDE.md §8, GUARDRAILS.md
Credentials sourced from: .env

If a required env var is missing, a warning is logged at import time.
Business rule defaults reflect the current CLAUDE.md / GUARDRAILS.md values.
"""
import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _env(key: str, default=None, required: bool = False):
    """Load an env var. Warn if required and missing."""
    val = os.getenv(key, default)
    if required and not val:
        logger.warning("CONFIG: required env var %s is not set", key)
    return val


# ---------------------------------------------------------------------------
# Budget guardrails (GUARDRAILS.md §1 / CLAUDE.md §8)
# ---------------------------------------------------------------------------

WEEKLY_BUDGET_CEILING_USD   = float(_env("WEEKLY_BUDGET_CEILING_USD",   "1000.00"))
WEEKLY_BUDGET_FLOOR_USD     = float(_env("WEEKLY_BUDGET_FLOOR_USD",     "500.00"))
WEEKLY_UNDERSPEND_ALERT_USD = float(_env("WEEKLY_UNDERSPEND_ALERT_USD", "400.00"))
DAILY_BUDGET_SOFT_CAP_USD   = float(_env("DAILY_BUDGET_SOFT_CAP_USD",   "250.00"))
MIN_CAMPAIGN_DAILY_BUDGET   = float(_env("MIN_CAMPAIGN_DAILY_BUDGET",   "10.00"))

# Backward-compat alias used in several agents
DAILY_BUDGET_CAP_USD = DAILY_BUDGET_SOFT_CAP_USD

# ---------------------------------------------------------------------------
# Active ad days (CLAUDE.md §8)
# ---------------------------------------------------------------------------

ACTIVE_DAYS = {"friday", "saturday", "sunday", "monday"}

# ---------------------------------------------------------------------------
# Performance targets (CLAUDE.md §10)
# ---------------------------------------------------------------------------

TARGET_CPL_LOW   = float(_env("TARGET_CPL_LOW",   "150.00"))
TARGET_CPL_HIGH  = float(_env("TARGET_CPL_HIGH",  "500.00"))
TARGET_CPL_IDEAL = float(_env("TARGET_CPL_IDEAL", "300.00"))

# ---------------------------------------------------------------------------
# Optimizer thresholds (GUARDRAILS.md §1–2)
# ---------------------------------------------------------------------------

MIN_SPEND_FOR_PAUSE        = float(_env("MIN_SPEND_FOR_PAUSE",        "30.00"))
MIN_CLICKS_FOR_BID_CHANGE  = int(  _env("MIN_CLICKS_FOR_BID_CHANGE",  "20"))
BID_INCREASE_PCT           = float(_env("BID_INCREASE_PCT",           "0.15"))
BID_DECREASE_PCT           = float(_env("BID_DECREASE_PCT",           "0.20"))
MAX_BUDGET_INCREASE_PCT    = float(_env("MAX_BUDGET_INCREASE_PCT",    "0.20"))
MAX_BUDGET_REALLOC_PCT     = float(_env("MAX_BUDGET_REALLOC_PCT",     "0.30"))
MAX_KEYWORD_BID_INCREASE_PCT = float(_env("MAX_KEYWORD_BID_INCREASE_PCT", "0.25"))
MAX_KEYWORD_BID_DECREASE_PCT = float(_env("MAX_KEYWORD_BID_DECREASE_PCT", "0.30"))
MAX_KEYWORD_PAUSES_PER_DAY   = int(  _env("MAX_KEYWORD_PAUSES_PER_DAY",   "3"))
MIN_ACTIVE_KEYWORDS          = int(  _env("MIN_ACTIVE_KEYWORDS",          "5"))
MIN_DAYS_BEFORE_PAUSE        = int(  _env("MIN_DAYS_BEFORE_PAUSE",        "3"))
MIN_RUN_INTERVAL_MINUTES     = int(  _env("MIN_RUN_INTERVAL_MINUTES",     "60"))

# ---------------------------------------------------------------------------
# Escalation thresholds (GUARDRAILS.md §6)
# ---------------------------------------------------------------------------

ESCALATION_CPL_USD              = float(_env("ESCALATION_CPL_USD",              "1000.00"))
ESCALATION_WEEKLY_SPEND_USD     = float(_env("ESCALATION_WEEKLY_SPEND_USD",     "1100.00"))
ESCALATION_DAILY_SPEND_USD      = float(_env("ESCALATION_DAILY_SPEND_USD",      "300.00"))
ESCALATION_KEYWORD_SPEND_USD    = float(_env("ESCALATION_KEYWORD_SPEND_USD",    "75.00"))
ESCALATION_API_FAILURE_HOURS    = int(  _env("ESCALATION_API_FAILURE_HOURS",    "26"))
HIGH_SPEND_DECISION_USD         = float(_env("HIGH_SPEND_DECISION_USD",         "50.00"))
WEEKLY_UNDERSPEND_ALERT_USD     = float(_env("WEEKLY_UNDERSPEND_ALERT_USD",     "400.00"))
UNDERSPEND_ALERT_USD            = WEEKLY_UNDERSPEND_ALERT_USD / 4
MAX_SINGLE_CAMPAIGN_INCREASE_PCT = float(_env("MAX_SINGLE_CAMPAIGN_INCREASE_PCT", "0.20"))
MAX_BUDGET_REALLOCATION_PCT     = float(_env("MAX_BUDGET_REALLOCATION_PCT",     "0.30"))
MIN_CAMPAIGN_DAILY_BUDGET_USD   = MIN_CAMPAIGN_DAILY_BUDGET

# ---------------------------------------------------------------------------
# Analysis / reporting defaults
# ---------------------------------------------------------------------------

LOOKBACK_DAYS             = int(_env("LOOKBACK_DAYS",             "7"))
RECOMMENDATION_TTL_HOURS  = int(_env("RECOMMENDATION_TTL_HOURS",  "48"))
NEW_CAMPAIGN_GRACE_DAYS   = int(_env("NEW_CAMPAIGN_GRACE_DAYS",   "3"))

# ---------------------------------------------------------------------------
# Platform credentials (required — no hardcoded fallbacks)
# ---------------------------------------------------------------------------

META_AD_ACCOUNT_ID         = _env("META_AD_ACCOUNT_ID",         required=True)
META_PIXEL_ID              = _env("META_PIXEL_ID",              required=True)
META_AUDIENCE_ID           = _env("META_AUDIENCE_ID",           required=True)
META_CONVERSION_INQUIRY_ID = _env("META_CONVERSION_INQUIRY_ID", required=True)
META_CONVERSION_BOOKING_ID = _env("META_CONVERSION_BOOKING_ID", required=True)

# ---------------------------------------------------------------------------
# URLs (required)
# ---------------------------------------------------------------------------

LANDING_PAGE_URL       = _env("LANDING_PAGE_URL",       required=True)
INQUIRY_FORM_URL       = _env("INQUIRY_FORM_URL",        required=True)
INQUIRY_SUBMITTED_URL  = _env("INQUIRY_SUBMITTED_URL",  required=True)
BOOKING_CONFIRMED_URL  = _env("BOOKING_CONFIRMED_URL",  required=True)
COMMAND_CENTER_URL     = _env("COMMAND_CENTER_URL",     required=True)
SUPABASE_URL           = _env("SUPABASE_URL",           required=True)

# ---------------------------------------------------------------------------
# Email (required)
# ---------------------------------------------------------------------------

ALERT_EMAIL = _env("ALERT_EMAIL", required=True)
ALERT_FROM  = _env("ALERT_FROM",  required=True)

# ---------------------------------------------------------------------------
# Meta API
# ---------------------------------------------------------------------------

META_API_VERSION = _env("META_API_VERSION", "v21.0")
META_BASE_URL    = f"https://graph.facebook.com/{META_API_VERSION}"
