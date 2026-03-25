"""
Creative Agent
==============
Uses Claude (claude-sonnet-4-6) to generate ad copy for Google Ads, Meta Ads,
and Microsoft Ads for Ridgecrest Designs.

Platforms:
  google    — Responsive Search Ads (headlines + descriptions + callouts + sitelinks)
  meta      — Facebook/Instagram Ads (primary text + headline + description + link description)
  microsoft — Responsive Search Ads (same structure as Google)

Character limits are hard-enforced with word-boundary trimming. A warning is
logged any time trimming is applied so prompts can be tightened.

Run standalone:  python creative_agent.py
"""
import os
import re
import json
import logging
import sys
from datetime import date

import anthropic
from dotenv import load_dotenv

load_dotenv()

import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [creative_agent] %(levelname)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

from config import (
    LANDING_PAGE_URL as LANDING_PAGE,
    INQUIRY_FORM_URL as INQUIRY_FORM,
)

AGENT_NAME   = "creative_agent"

_BRAND_MD_PATH = os.path.join(os.path.dirname(__file__), "BRAND.md")


def _load_brand_voice() -> str:
    """
    Load BRAND.md and extract the sections relevant to prompt generation.
    Returns a condensed brand voice block for injection into Claude prompts.
    Falls back to a short inline summary if the file is missing.
    """
    try:
        with open(_BRAND_MD_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        # Extract §1–§8 (voice, tone, power words, forbidden words, formulas,
        # patterns, CTAs, themes) — skip §9–§11 which are formatting notes and
        # the raw reference bank (too long for a prompt context block).
        # We split on ## 9. to drop everything from §9 onward.
        if "## 9." in content:
            content = content.split("## 9.")[0]
        return content.strip()
    except FileNotFoundError:
        logger.warning("BRAND.md not found at %s — using inline fallback", _BRAND_MD_PATH)
        return """
Ridgecrest Designs brand voice:
- Premium, luxury-focused, precise
- Process-oriented and technically fluent
- Trustworthy and high-touch
- Never leads with low price or discounts
- Emphasizes: photorealistic 3D renders, integrated design-build, deep permitting knowledge,
  flawless execution, attention to detail, strong teams, long-term relationships
- Speaks to affluent homeowners age 35–55 seeking a seamless, expertly managed experience
- Pre-qualifies: messaging attracts serious premium projects and naturally filters low-budget leads
- Power words: seamless, photorealistic 3D renders, from concept to completion,
  one team one vision one point of contact, white-glove, discerning, flawless execution
- Forbidden: affordable, cheap, free, #1, best in Bay Area, licensed and insured,
  free estimate, quality you can trust, above and beyond
- CTAs: always "private consultation" — NEVER "free consultation" or "free estimate"
"""


BRAND_VOICE = _load_brand_voice()

# ---------------------------------------------------------------------------
# Platform character limits (hard enforcement) and prompt targets (with buffer)
# ---------------------------------------------------------------------------

PLATFORM_LIMITS = {
    "google": {
        "headline":       30,
        "description":    90,
        "display_path":   15,
        "callout":        25,
        "sitelink_title": 25,
        "sitelink_desc":  35,
    },
    "meta": {
        "primary_text":    125,
        "headline":         40,
        "description":      30,
        "link_description": 30,
    },
    "microsoft": {
        "headline":      30,
        "description":   90,
        "display_path":  15,
    },
}

# Prompt targets leave a 2–5 char buffer before the hard limit
PLATFORM_TARGETS = {
    "google": {
        "headline":       28,
        "description":    85,
        "display_path":   13,
        "callout":        22,
        "sitelink_title": 22,
        "sitelink_desc":  32,
    },
    "meta": {
        "primary_text":    120,
        "headline":         38,
        "description":      28,
        "link_description": 28,
    },
    "microsoft": {
        "headline":     28,
        "description":  85,
        "display_path": 13,
    },
}

# ---------------------------------------------------------------------------
# Service categories
# ---------------------------------------------------------------------------

SERVICE_CATEGORIES = {
    "design_build":       {"label": "Design-Build",            "budget_floor": None,    "priority": 1, "description": "Full-service design-build for luxury custom homes and major remodels"},
    "custom_home":        {"label": "Custom Home",             "budget_floor": "$5M–$10M", "priority": 1, "description": "Luxury custom home construction from $5M to $10M+"},
    "whole_house_remodel":{"label": "Whole House Remodel",     "budget_floor": "$1M+",  "priority": 2, "description": "Complete whole-home renovations starting at $1M+"},
    "kitchen_remodel":    {"label": "Kitchen Remodel",         "budget_floor": "$150K+","priority": 3, "description": "High-end kitchen remodels starting at $150,000"},
    "bathroom_remodel":   {"label": "Bathroom Remodel",        "budget_floor": "$60K+", "priority": 3, "description": "Luxury bathroom remodels starting at $60,000"},
    "master_bathroom":    {"label": "Master Bathroom Remodel", "budget_floor": "$100K+","priority": 3, "description": "Premium master bathroom remodels starting at $100,000"},
}

TARGET_CITIES = [
    "Pleasanton", "Walnut Creek", "San Ramon", "Dublin", "Orinda",
    "Moraga", "Danville", "Alamo", "Lafayette", "Rossmoor", "Sunol", "Diablo"
]

# BRAND_VOICE is loaded dynamically from BRAND.md above — do not define a static fallback here.

# ---------------------------------------------------------------------------
# Word-boundary trimming
# ---------------------------------------------------------------------------

def _is_complete_sentence(text: str) -> bool:
    """Return True if text ends with sentence-closing punctuation."""
    return text.rstrip().endswith((".", "!", "?", ")"))


def _trim_to(text: str, limit: int, field_name: str = "field") -> str:
    """
    Trim text to at most `limit` characters at the last word boundary.
    NEVER cuts mid-word. NEVER adds ellipsis or dashes.
    Logs a WARNING whenever trimming is required.
    Logs an ERROR if trimming produces an incomplete sentence — the prompt
    targets should be tightened so Claude generates copy that fits.
    """
    if len(text) <= limit:
        return text
    cut = text[:limit]
    last_space = cut.rfind(" ")
    trimmed = cut[:last_space].rstrip() if last_space > 0 else cut
    logger.warning(
        "TRIM REQUIRED — %s: %d→%d chars | '%s' → '%s'",
        field_name, len(text), len(trimmed), text, trimmed
    )
    if not _is_complete_sentence(trimmed):
        logger.error(
            "INCOMPLETE SENTENCE after trim — %s: '%s' — regenerate this copy",
            field_name, trimmed
        )
    return trimmed


# ---------------------------------------------------------------------------
# Platform-aware limit enforcement
# ---------------------------------------------------------------------------

def _headline_display_len(h: str) -> int:
    """Google/Microsoft count {KeyWord:Default Text} as len('Default Text')."""
    return len(re.sub(r'\{KeyWord:([^}]*)\}', r'\1', h, flags=re.IGNORECASE))


def _enforce_limits(brief: dict, platform: str) -> dict:
    """
    Hard-enforce platform character limits via word-boundary trimming.
    Validates every field before returning. Logs a warning per trimmed field.
    """
    limits = PLATFORM_LIMITS.get(platform, PLATFORM_LIMITS["google"])

    if platform in ("google", "microsoft"):
        # Headlines: measure with KI substitution for Google/Microsoft
        cleaned_headlines = []
        for h in brief.get("headlines", []):
            effective = _headline_display_len(h)
            if effective > limits["headline"]:
                h = _trim_to(h, limits["headline"], f"{platform}/headline")
            cleaned_headlines.append(h)
        brief["headlines"] = cleaned_headlines

        # Descriptions
        brief["descriptions"] = [
            _trim_to(d, limits["description"], f"{platform}/description")
            for d in brief.get("descriptions", [])
        ]

        if platform == "google":
            # Callouts
            brief["callout_extensions"] = [
                _trim_to(c, limits["callout"], "google/callout")
                for c in brief.get("callout_extensions", [])
            ]
            # Sitelinks
            for sl in brief.get("sitelink_extensions", []):
                if "title" in sl:
                    sl["title"] = _trim_to(sl["title"], limits["sitelink_title"], "google/sitelink_title")
                for line in ("description_line_1", "description_line_2"):
                    if line in sl:
                        sl[line] = _trim_to(sl[line], limits["sitelink_desc"], f"google/{line}")

    elif platform == "meta":
        for var in brief.get("variations", []):
            for field, key in (
                ("primary_text",    "primary_text"),
                ("headline",        "headline"),
                ("description",     "description"),
                ("link_description","link_description"),
            ):
                if key in var and var[key]:
                    var[key] = _trim_to(var[key], limits[field], f"meta/{field}")

    return brief


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_brief(brief: dict, platform: str) -> list[str]:
    """Return a list of validation errors (empty = valid)."""
    errors = []
    limits = PLATFORM_LIMITS.get(platform, PLATFORM_LIMITS["google"])

    if platform in ("google", "microsoft"):
        for h in brief.get("headlines", []):
            eff = _headline_display_len(h)
            if eff > limits["headline"]:
                errors.append(f"[{platform}] Headline {eff} chars (max {limits['headline']}): '{h}'")
        for d in brief.get("descriptions", []):
            if len(d) > limits["description"]:
                errors.append(f"[{platform}] Description {len(d)} chars (max {limits['description']}): '{d}'")
            if not _is_complete_sentence(d):
                errors.append(f"[{platform}] Incomplete sentence in description: '{d}'")
        if platform == "google":
            for c in brief.get("callout_extensions", []):
                if len(c) > limits["callout"]:
                    errors.append(f"[google] Callout {len(c)} chars (max {limits['callout']}): '{c}'")
            for sl in brief.get("sitelink_extensions", []):
                t = sl.get("title", "")
                if len(t) > limits["sitelink_title"]:
                    errors.append(f"[google] Sitelink title {len(t)} chars: '{t}'")
                for line in ("description_line_1", "description_line_2"):
                    v = sl.get(line, "")
                    if len(v) > limits["sitelink_desc"]:
                        errors.append(f"[google] Sitelink {line} {len(v)} chars: '{v}'")

    elif platform == "meta":
        for i, var in enumerate(brief.get("variations", []), 1):
            for field, key in (
                ("primary_text",    "primary_text"),
                ("headline",        "headline"),
                ("description",     "description"),
                ("link_description","link_description"),
            ):
                val = var.get(key, "")
                if len(val) > limits[field]:
                    errors.append(
                        f"[meta] Var {i} {field} {len(val)} chars (max {limits[field]}): '{val}'"
                    )
    return errors


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

def _google_prompt(service_info: dict, city: str, budget_note: str, kw_default: str) -> str:
    t = PLATFORM_TARGETS["google"]
    return f"""You are a Google Ads copywriter for Ridgecrest Designs, a high-end design-build firm
in Pleasanton, California. Generate a complete Responsive Search Ad (RSA) creative brief.

Service: {service_info['label']}{budget_note}
Service description: {service_info['description']}
Target city: {city}
Landing page: {LANDING_PAGE}

=== BRAND REFERENCE (read before writing any copy) ===
{BRAND_VOICE}
=== END BRAND REFERENCE ===

Apply the brand reference above as follows:
- Pull headline vocabulary from §3 (Power Words) — use the exact phrases listed there
- NEVER use any word or phrase listed in §4 (Forbidden Words)
- Model headline structure on §5 (Headline Formulas A–F)
- Descriptions must match §2 (Search ad descriptions): one or two complete sentences,
  differentiator + outcome, end with a period, never vague

CHARACTER LIMITS — GOOGLE ADS (HARD):
- Headlines: 30 characters MAX each. Write to target ≤ {t['headline']} chars to leave a buffer.
  For keyword insertion placeholders {{KeyWord:Default}}, the character count uses the Default text length.
  Keep default text ≤ {t['headline']} chars.
- Descriptions: 90 characters MAX each. Write to target ≤ {t['description']} chars.
  Count every character including spaces and punctuation. VERIFY before returning.
  Every description MUST be a complete sentence ending with a period, question mark,
  or exclamation mark. NEVER let a description trail off mid-sentence.
- Callouts: 25 chars MAX, target ≤ {t['callout']}. Short noun phrases only.
- Sitelink titles: 25 chars MAX, target ≤ {t['sitelink_title']}.
  Sitelink description lines: 35 chars MAX, target ≤ {t['sitelink_desc']}.
- Do NOT use exclamation marks in headlines
- Do NOT use superlatives ("best", "#1") without third-party verification
- Include at least 2 headlines with the city name "{city}"
- Include at least 1 keyword insertion headline: {{{{KeyWord:{kw_default}}}}}
- Provide 10–15 headline options, 4–6 description options

Return ONLY valid JSON, no markdown fences, no explanation:
{{
  "headlines": ["headline 1", ...],
  "descriptions": ["description 1", ...],
  "callout_extensions": ["callout 1", ...],
  "sitelink_extensions": [
    {{"title": "...", "description_line_1": "...", "description_line_2": "...", "url": "{LANDING_PAGE}"}}
  ],
  "messaging_angle": "brief summary of the angle taken"
}}

BEFORE RETURNING: count every headline and description character-by-character.
Trim any that exceed the targets. The hard limits are 30/90 — do not exceed them."""


def _microsoft_prompt(service_info: dict, city: str, budget_note: str, kw_default: str) -> str:
    t = PLATFORM_TARGETS["microsoft"]
    return f"""You are a Microsoft Advertising copywriter for Ridgecrest Designs, a high-end
design-build firm in Pleasanton, California. Generate a Responsive Search Ad creative brief.

Service: {service_info['label']}{budget_note}
Service description: {service_info['description']}
Target city: {city}
Landing page: {LANDING_PAGE}

=== BRAND REFERENCE (read before writing any copy) ===
{BRAND_VOICE}
=== END BRAND REFERENCE ===

Apply the brand reference above as follows:
- Pull headline vocabulary from §3 (Power Words) — use the exact phrases listed there
- NEVER use any word or phrase listed in §4 (Forbidden Words)
- Model headline structure on §5 (Headline Formulas A–F)
- Descriptions must match §2 (Search ad descriptions): one or two complete sentences,
  differentiator + outcome, end with a period, never vague
- Microsoft audiences skew slightly older/professional — emphasize process and reliability

CHARACTER LIMITS — MICROSOFT ADS (HARD):
- Headlines: 30 characters MAX each. Write to target ≤ {t['headline']} chars.
  Keyword insertion {{Param1:Default}} counts as default text length.
- Descriptions: 90 characters MAX each. Write to target ≤ {t['description']} chars.
  Count every character including spaces and punctuation. VERIFY before returning.
- Include at least 2 headlines mentioning "{city}"
- Provide 10–15 headline options, 4–6 description options

DESCRIPTION RULES (CRITICAL):
- Every description MUST be a complete, standalone sentence.
- Every description MUST end with a period, question mark, or exclamation mark.
- NEVER write a description that trails off mid-sentence.
- Write short, punchy sentences that fit entirely within 90 characters.
- If a thought requires more than 90 characters, split it into two shorter sentences
  and use only the first one, or rephrase it more concisely.
- WRONG: "Luxury kitchen remodels starting at $150K. Ridgecrest Designs handles design,"
- RIGHT: "Luxury kitchen remodels from $150K, fully managed from design to completion."

Return ONLY valid JSON, no markdown fences, no explanation:
{{
  "headlines": ["headline 1", ...],
  "descriptions": ["description 1", ...],
  "messaging_angle": "brief summary of the angle taken"
}}

BEFORE RETURNING: read every description aloud. Does it end with a period? Is it a
complete thought? If not, rewrite it. Hard limits: headlines ≤ 30 chars, descriptions ≤ 90 chars."""


def _meta_prompt(service_info: dict, city: str, budget_note: str, n_variations: int = 3) -> str:
    t = PLATFORM_TARGETS["meta"]
    lim = PLATFORM_LIMITS["meta"]
    return f"""You are a Meta (Facebook/Instagram) Ads copywriter for Ridgecrest Designs,
a high-end design-build firm in Pleasanton, California.

Generate {n_variations} distinct ad variations for a Meta feed ad campaign.
Each variation should test a different copy angle drawn from §6 (Primary Text Patterns).

Service: {service_info['label']}{budget_note}
Service description: {service_info['description']}
Target audience: Affluent homeowners age 35–55, families with children, East Bay zip codes,
  predominantly female, interested in home improvement and luxury living.
Target city area: {city} and surrounding East Bay communities
Landing page: {LANDING_PAGE}

=== BRAND REFERENCE (read before writing any copy) ===
{BRAND_VOICE}
=== END BRAND REFERENCE ===

Apply the brand reference above as follows:
- Pull vocabulary exclusively from §3 (Power Words) — use the exact phrases listed there
- NEVER use any word or phrase listed in §4 (Forbidden Words)
- Structure primary_text using §6 patterns:
    Variation 1: Pattern 1 (Problem → Positioning → Proof with 🚫/👉 bullets)
    Variation 2: Pattern 2 (Contrast — cookie-cutter vs. custom) or Pattern 4 (Short Punchy)
    Variation 3: Choose the most compelling remaining pattern for this service
- Headlines must follow §5 formulas (A–F)
- CTAs must follow §7: always "private consultation", never "free estimate"
- Include the closing phrase "to experience the Ridgecrest difference" in at least one variation
- Include the scarcity line "We accept only 4–5 projects per year" in at least one variation

CHARACTER LIMITS — META ADS (HARD):
- primary_text: {lim['primary_text']} chars MAX. Write to target ≤ {t['primary_text']} chars.
  This is the main body copy above the image. Can include line breaks.
  Conversational tone, speak directly to the reader. First 125 chars show before "See more".
- headline: {lim['headline']} chars MAX. Write to target ≤ {t['headline']} chars.
  Short, punchy benefit statement. No punctuation needed.
- description: {lim['description']} chars MAX. Write to target ≤ {t['description']} chars.
  Short support line shown under the headline in the link preview.
- link_description: {lim['link_description']} chars MAX. Write to target ≤ {t['link_description']} chars.
  Optional extra context shown in some placements.

Rules:
- Each variation must have a distinct angle — do not repeat the same message
- NO exclamation marks in headlines
- Do NOT use superlatives ("best", "#1") without attribution
- Mention the city or East Bay region in at least 1 variation
- The primary_text should feel natural in a social feed, not like a search ad
- Include a soft call-to-action in the primary_text (e.g., "Schedule a call", "See our work")

Return ONLY valid JSON, no markdown fences, no explanation:
{{
  "variations": [
    {{
      "angle": "one-word label for the copy angle",
      "primary_text": "...",
      "headline": "...",
      "description": "...",
      "link_description": "..."
    }}
  ],
  "messaging_angle": "overall strategy summary"
}}

BEFORE RETURNING: count every field character-by-character.
Hard limits: primary_text={lim['primary_text']}, headline={lim['headline']},
description={lim['description']}, link_description={lim['link_description']}.
Trim anything that exceeds the targets."""


# ---------------------------------------------------------------------------
# Creative generation
# ---------------------------------------------------------------------------

def _call_claude(prompt: str, client: anthropic.Anthropic) -> dict:
    """Call Claude and parse JSON response."""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text.strip()
    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = re.sub(r'^```(?:json)?\n?', '', raw)
        raw = re.sub(r'\n?```$', '', raw)
    return json.loads(raw.strip())


def generate_creative_brief(
    service_category: str,
    city: str,
    service_info: dict,
    client: anthropic.Anthropic,
    platform: str = "google",
    n_variations: int = 3,
) -> dict:
    """
    Generate an ad creative brief for the specified platform.

    platform: "google" | "meta" | "microsoft"
    n_variations: number of distinct variations (used by Meta only)
    """
    if platform not in PLATFORM_LIMITS:
        raise ValueError(f"Unknown platform '{platform}'. Must be one of: {list(PLATFORM_LIMITS)}")

    budget_note = f"\nProject minimum: {service_info['budget_floor']}" if service_info.get("budget_floor") else ""

    if platform in ("google", "microsoft"):
        kw_combined = f"{service_info['label']} {city}"
        kw_default = kw_combined if len(kw_combined) <= 28 else service_info["label"]
        if platform == "google":
            prompt = _google_prompt(service_info, city, budget_note, kw_default)
        else:
            prompt = _microsoft_prompt(service_info, city, budget_note, kw_default)
    else:
        prompt = _meta_prompt(service_info, city, budget_note, n_variations)

    brief = _call_claude(prompt, client)
    brief["platform"] = platform

    # Hard-enforce limits with word-boundary trimming
    brief = _enforce_limits(brief, platform)

    # Validate — log any remaining issues (should be zero after enforcement)
    errors = validate_brief(brief, platform)
    if errors:
        for err in errors:
            logger.error("VALIDATION FAILED after enforcement: %s", err)
        brief["_validation_errors"] = errors

    return brief


# ---------------------------------------------------------------------------
# DB storage
# ---------------------------------------------------------------------------

def _ensure_platform_column():
    """Add platform column to creative_briefs if it doesn't exist yet."""
    with db.get_db() as (conn, cur):
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'creative_briefs' AND column_name = 'platform'
        """)
        if not cur.fetchone():
            cur.execute("ALTER TABLE creative_briefs ADD COLUMN platform VARCHAR(20) DEFAULT 'google'")
            logger.info("Added 'platform' column to creative_briefs")


def store_brief(
    brief: dict,
    service_category: str,
    platform: str = "google",
    ad_group_id: int | None = None,
) -> int:
    """Persist a creative brief to the DB."""
    _ensure_platform_column()

    # For Meta, store variations in the headlines/descriptions columns as JSON arrays
    if platform == "meta":
        headlines_json    = json.dumps([v.get("headline", "")     for v in brief.get("variations", [])])
        descriptions_json = json.dumps([v.get("primary_text", "") for v in brief.get("variations", [])])
        callouts_json     = json.dumps([v.get("description", "")  for v in brief.get("variations", [])])
        sitelinks_json    = json.dumps(brief.get("variations", []))  # full variation data
    else:
        headlines_json    = json.dumps(brief.get("headlines", []))
        descriptions_json = json.dumps(brief.get("descriptions", []))
        callouts_json     = json.dumps(brief.get("callout_extensions", []))
        sitelinks_json    = json.dumps(brief.get("sitelink_extensions", []))

    with db.get_db() as (conn, cur):
        cur.execute(
            """INSERT INTO creative_briefs
               (ad_group_id, service_category, platform, headlines, descriptions,
                callout_extensions, sitelink_extensions, messaging_angle, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'draft')
               RETURNING id""",
            (
                ad_group_id,
                service_category,
                platform,
                headlines_json,
                descriptions_json,
                callouts_json,
                sitelinks_json,
                brief.get("messaging_angle", ""),
            )
        )
        return cur.fetchone()["id"]


# ---------------------------------------------------------------------------
# Push approved ads to Google Ads
# ---------------------------------------------------------------------------

def push_rsa_to_google(client_ga, customer_id: str, brief_id: int) -> bool:
    """Push an approved Google creative brief as a Responsive Search Ad."""
    if client_ga is None:
        logger.warning("No Google Ads client — skipping RSA push for brief %d", brief_id)
        return False

    with db.get_db() as (conn, cur):
        cur.execute(
            """SELECT cb.*, ag.google_ad_group_id
               FROM creative_briefs cb
               LEFT JOIN ad_groups ag ON ag.id = cb.ad_group_id
               WHERE cb.id = %s AND cb.status = 'approved'""",
            (brief_id,)
        )
        brief = cur.fetchone()

    if not brief or not brief["google_ad_group_id"]:
        logger.warning("Brief %d not found, not approved, or no ad group", brief_id)
        return False

    try:
        ad_service  = client_ga.get_service("AdGroupAdService")
        ad_op       = client_ga.get_type("AdGroupAdOperation")
        ad_group_ad = ad_op.create
        ad_group_ad.ad_group = client_ga.get_service("AdGroupService").ad_group_path(
            customer_id, brief["google_ad_group_id"]
        )
        ad_group_ad.status = client_ga.enums.AdGroupAdStatusEnum.ENABLED

        rsa        = ad_group_ad.ad.responsive_search_ad
        headlines  = json.loads(brief["headlines"])  if isinstance(brief["headlines"],  str) else brief["headlines"]
        descriptions = json.loads(brief["descriptions"]) if isinstance(brief["descriptions"], str) else brief["descriptions"]

        for i, h in enumerate(headlines[:15]):
            headline = rsa.headlines.add()
            headline.text = h
            if i < 3:
                headline.pinned_field = client_ga.enums.ServedAssetFieldTypeEnum.HEADLINE_1 + i
        for d in descriptions[:4]:
            desc = rsa.descriptions.add()
            desc.text = d

        ad_group_ad.ad.final_urls.append(LANDING_PAGE)
        response  = ad_service.mutate_ad_group_ads(customer_id=customer_id, operations=[ad_op])
        new_ad_id = response.results[0].resource_name

        with db.get_db() as (conn, cur):
            cur.execute("UPDATE creative_briefs SET status='deployed', deployed_at=NOW() WHERE id=%s", (brief_id,))
            cur.execute(
                """INSERT INTO ads (google_ad_id, ad_group_id, ad_type, headlines, descriptions,
                                    final_urls, ai_generated, creative_notes)
                   VALUES (%s, %s, 'RESPONSIVE_SEARCH_AD', %s, %s, %s, TRUE, %s)""",
                (new_ad_id, brief["ad_group_id"],
                 brief["headlines"], brief["descriptions"],
                 json.dumps([LANDING_PAGE]),
                 f"Generated from creative brief #{brief_id}")
            )
        logger.info("RSA pushed to Google Ads: %s", new_ad_id)
        return True

    except Exception as e:
        logger.error("Failed to push RSA for brief %d: %s", brief_id, e)
        return False


# ---------------------------------------------------------------------------
# Generate all briefs for launch
# ---------------------------------------------------------------------------

def generate_launch_briefs(
    client_claude: anthropic.Anthropic,
    categories: list[str] | None = None,
    cities: list[str] | None = None,
    platforms: list[str] | None = None,
) -> list[dict]:
    """Generate creative briefs for every service × city × platform combination."""
    cats  = categories or list(SERVICE_CATEGORIES.keys())
    locs  = cities     or TARGET_CITIES
    plats = platforms  or ["google"]
    results = []

    for plat in plats:
        for cat in cats:
            service_info = SERVICE_CATEGORIES[cat]
            for city in locs:
                logger.info("Generating %s brief: %s × %s", plat, cat, city)
                try:
                    brief    = generate_creative_brief(cat, city, service_info, client_claude, platform=plat)
                    errors   = validate_brief(brief, plat)
                    brief_id = store_brief(brief, cat, platform=plat)

                    result = {
                        "brief_id":         brief_id,
                        "platform":         plat,
                        "service_category": cat,
                        "city":             city,
                        "validation_errors": errors,
                        "messaging_angle":  brief.get("messaging_angle", ""),
                    }
                    if plat == "meta":
                        result["variation_count"] = len(brief.get("variations", []))
                    else:
                        result["headline_count"]    = len(brief.get("headlines", []))
                        result["description_count"] = len(brief.get("descriptions", []))

                    results.append(result)
                    logger.info("Brief %d stored: [%s] %s × %s", brief_id, plat, cat, city)
                except Exception as e:
                    logger.error("Error generating [%s] brief for %s×%s: %s", plat, cat, city, e)
                    results.append({"platform": plat, "service_category": cat, "city": city, "error": str(e)})

    return results


# ---------------------------------------------------------------------------
# Ad copy refresh (underperforming ads)
# ---------------------------------------------------------------------------

def refresh_underperforming_ads(client_claude: anthropic.Anthropic, lookback_days: int = 14) -> list[dict]:
    """Identify low-CTR Google ads and generate fresh creative variants."""
    from datetime import timedelta
    window_start = date.today() - timedelta(days=lookback_days - 1)

    with db.get_db() as (conn, cur):
        cur.execute(
            """SELECT
                   a.id, a.google_ad_id, a.ad_group_id, a.headlines, a.descriptions,
                   ag.name AS ad_group_name,
                   cb.service_category,
                   AVG(pm.ctr) AS avg_ctr,
                   SUM(pm.clicks) AS total_clicks,
                   SUM(pm.impressions) AS total_impressions
               FROM ads a
               JOIN ad_groups ag ON ag.id = a.ad_group_id
               LEFT JOIN creative_briefs cb ON cb.ad_group_id = a.ad_group_id AND cb.status = 'deployed'
               LEFT JOIN performance_metrics pm
                      ON pm.entity_type = 'ad' AND pm.entity_id = a.id AND pm.metric_date >= %s
               WHERE a.status = 'ENABLED'
               GROUP BY a.id, a.google_ad_id, a.ad_group_id, a.headlines, a.descriptions,
                        ag.name, cb.service_category
               HAVING SUM(pm.impressions) > 500 AND AVG(pm.ctr) < 0.02""",
            (window_start,)
        )
        underperforming = [dict(r) for r in cur.fetchall()]

    refreshed = []
    for ad in underperforming:
        cat = ad.get("service_category") or "design_build"
        if cat not in SERVICE_CATEGORIES:
            cat = "design_build"
        service_info = SERVICE_CATEGORIES[cat]
        city = next((c for c in TARGET_CITIES if c.lower() in (ad["ad_group_name"] or "").lower()), "Pleasanton")

        logger.info("Refreshing ad %s (CTR=%.2f%%) for '%s'",
                    ad["google_ad_id"], float(ad["avg_ctr"] or 0) * 100, ad["ad_group_name"])
        try:
            brief    = generate_creative_brief(cat, city, service_info, client_claude, platform="google")
            brief_id = store_brief(brief, cat, platform="google", ad_group_id=ad["ad_group_id"])
            refreshed.append({"original_ad_id": ad["id"], "new_brief_id": brief_id,
                               "service_category": cat, "city": city,
                               "previous_ctr": float(ad["avg_ctr"] or 0)})
        except Exception as e:
            logger.error("Failed to refresh ad %s: %s", ad["google_ad_id"], e)

    return refreshed


# ---------------------------------------------------------------------------
# Process incoming messages
# ---------------------------------------------------------------------------

def process_messages(client_claude: anthropic.Anthropic):
    """Handle requests from other agents."""
    messages = db.receive_messages(AGENT_NAME)
    for msg in messages:
        try:
            mtype   = msg["message_type"]
            payload = msg["payload"] if isinstance(msg["payload"], dict) else json.loads(msg["payload"])

            if mtype == "generate_creative_brief_request":
                cat      = payload.get("service_category", "design_build")
                city     = payload.get("city", "Pleasanton")
                platform = payload.get("platform", "google")
                svc      = SERVICE_CATEGORIES.get(cat, SERVICE_CATEGORIES["design_build"])
                brief    = generate_creative_brief(cat, city, svc, client_claude, platform=platform)
                brief_id = store_brief(brief, cat, platform=platform, ad_group_id=payload.get("ad_group_id"))
                db.send_message(
                    from_agent=AGENT_NAME, to_agent=msg["from_agent"],
                    message_type="creative_brief_ready",
                    payload={"brief_id": brief_id, "category": cat, "city": city, "platform": platform}
                )
            elif mtype == "refresh_ads_request":
                refreshed = refresh_underperforming_ads(client_claude)
                db.send_message(
                    from_agent=AGENT_NAME, to_agent=msg["from_agent"],
                    message_type="ads_refreshed",
                    payload={"refreshed_count": len(refreshed), "details": refreshed}
                )
            db.ack_message(msg["id"])
        except Exception as e:
            db.ack_message(msg["id"], error=str(e))
            logger.error("Error processing message %d: %s", msg["id"], e)


# ---------------------------------------------------------------------------
# Test: generate 3 variations per platform for kitchen remodel
# ---------------------------------------------------------------------------

def test_kitchen_remodel(client_claude: anthropic.Anthropic, city: str = "Pleasanton") -> None:
    """
    Generate 3 ad variations per platform for kitchen remodel and print
    every field with its character count.
    """
    service_info = SERVICE_CATEGORIES["kitchen_remodel"]

    print("\n" + "=" * 70)
    print("CREATIVE TEST — Kitchen Remodel | Ridgecrest Designs")
    print(f"City: {city}  |  Variations per platform: 3")
    print("=" * 70)

    for platform in ("google", "microsoft", "meta"):
        print(f"\n{'─' * 70}")
        print(f"PLATFORM: {platform.upper()}")
        print(f"{'─' * 70}")

        limits  = PLATFORM_LIMITS[platform]
        targets = PLATFORM_TARGETS[platform]

        brief = generate_creative_brief(
            "kitchen_remodel", city, service_info, client_claude,
            platform=platform, n_variations=3
        )

        if platform in ("google", "microsoft"):
            headlines    = brief.get("headlines", [])
            descriptions = brief.get("descriptions", [])

            # Show 3 "variation groups" by cycling
            groups = min(3, max(len(headlines), len(descriptions)))
            for i in range(groups):
                print(f"\n  — Variation {i+1} —")
                # Pick up to 3 headlines per variation
                h_slice = headlines[i*3 : i*3 + 3] if i*3 < len(headlines) else headlines[-3:]
                for h in h_slice:
                    eff = _headline_display_len(h)
                    flag = " ✓" if eff <= limits["headline"] else " ✗ OVER"
                    print(f"  H ({eff:2d}/{limits['headline']}){flag}: {h}")
                # Pick 1 description per variation
                if i < len(descriptions):
                    d = descriptions[i]
                    flag = " ✓" if len(d) <= limits["description"] else " ✗ OVER"
                    print(f"  D ({len(d):2d}/{limits['description']}){flag}: {d}")

            if platform == "google":
                callouts = brief.get("callout_extensions", [])[:6]
                if callouts:
                    print(f"\n  Callouts (max {limits['callout']} chars):")
                    for c in callouts:
                        flag = " ✓" if len(c) <= limits["callout"] else " ✗ OVER"
                        print(f"    ({len(c):2d}){flag}: {c}")

        elif platform == "meta":
            for i, var in enumerate(brief.get("variations", []), 1):
                print(f"\n  — Variation {i} [{var.get('angle', '')}] —")
                pt = var.get("primary_text", "")
                hl = var.get("headline", "")
                ds = var.get("description", "")
                ld = var.get("link_description", "")

                def flag(val, lim):
                    return "✓" if len(val) <= lim else "✗ OVER"

                print(f"  Primary text ({len(pt):3d}/{limits['primary_text']}) {flag(pt, limits['primary_text'])}:")
                # Wrap at 70 chars for readability
                for chunk in [pt[j:j+70] for j in range(0, len(pt), 70)]:
                    print(f"    {chunk}")
                print(f"  Headline     ({len(hl):3d}/{limits['headline']}) {flag(hl, limits['headline'])}: {hl}")
                print(f"  Description  ({len(ds):3d}/{limits['description']}) {flag(ds, limits['description'])}: {ds}")
                print(f"  Link desc    ({len(ld):3d}/{limits['link_description']}) {flag(ld, limits['link_description'])}: {ld}")

        # Summary
        errors = validate_brief(brief, platform)
        print(f"\n  Validation: {'PASS — no limit violations' if not errors else 'FAIL — ' + str(errors)}")
        angle = brief.get("messaging_angle", "")
        if angle:
            print(f"  Angle: {angle}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(generate_all: bool = False):
    """
    generate_all=True: create full launch brief set
    generate_all=False: process messages + refresh underperforming ads
    """
    logger.info("=== Creative Agent starting (generate_all=%s) ===", generate_all)
    db.heartbeat(AGENT_NAME, "alive")

    claude_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    process_messages(claude_client)

    results = {}

    if generate_all:
        logger.info("Generating full launch brief set...")
        priority_cats = ["design_build", "custom_home", "whole_house_remodel"]
        briefs = generate_launch_briefs(
            claude_client,
            categories=priority_cats,
            cities=TARGET_CITIES[:3],
            platforms=["google"],
        )
        results["launch_briefs"] = briefs
        results["brief_count"]   = len(briefs)
        logger.info("Generated %d launch briefs", len(briefs))
    else:
        refreshed = refresh_underperforming_ads(claude_client)
        results["refreshed_ads"] = len(refreshed)

    db.send_message(
        from_agent=AGENT_NAME, to_agent="reporting_agent",
        message_type="creative_work_complete",
        payload=results, priority=7
    )
    db.heartbeat(AGENT_NAME, "alive", metadata=results)
    logger.info("=== Creative Agent done ===")
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ridgecrest Creative Agent")
    parser.add_argument("--generate-all", action="store_true",
                        help="Generate full launch creative brief set")
    parser.add_argument("--test", action="store_true",
                        help="Run kitchen remodel test across all 3 platforms")
    parser.add_argument("--city", default="Pleasanton",
                        help="City for test run (default: Pleasanton)")
    args = parser.parse_args()

    if args.test:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        test_kitchen_remodel(_client, city=args.city)
    else:
        run(generate_all=args.generate_all)
