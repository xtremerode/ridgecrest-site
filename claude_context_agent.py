#!/usr/bin/env python3
"""
claude_context_agent.py — Directory-scoped CLAUDE.md context manager

Two modes:
  --inbound  "<prompt>"   Detect which directories the prompt affects and print
                          the relevant CLAUDE.md files to stdout (for hook injection).
  --outbound "<rule>"     Classify a new rule and show a dry-run diff of where it
                          would be written. Requires --confirm to actually write.
  --audit                 Scan all CLAUDE.md files for duplicate content across files.

Usage:
  python3 claude_context_agent.py --inbound "$PROMPT_TEXT"
  python3 claude_context_agent.py --outbound "new rule text" [--confirm]
  python3 claude_context_agent.py --audit
"""

import argparse
import os
import re
import sys
from pathlib import Path

REPO_DIR = Path(__file__).parent.resolve()

# ── Directory → CLAUDE.md file mapping ────────────────────────────────────────
CLAUDE_FILES = {
    "agency":  REPO_DIR / "ridgecrest-agency" / "CLAUDE.md",
    "preview": REPO_DIR / "preview" / "CLAUDE.md",
    "root":    REPO_DIR / "CLAUDE.md",
}

# ── Signal word classifier ─────────────────────────────────────────────────────
# Each bucket lists keywords that strongly indicate the prompt/rule belongs there.
# Multiple buckets can match — all matched files are loaded (false positives are
# acceptable; false negatives cause missing rules which are worse).

SIGNALS = {
    "agency": [
        "campaign", "meta", "google ads", "microsoft ads", "msft", "budget",
        "cpl", "spend", "audience", "pixel", "conversion", "keyword",
        "ad set", "adset", "creative", "impressions", "clicks", "landing page",
        "inquiry form", "booking", "lead gen", "platform", "rma",
        "ridgecrest-agency", "ridgecrest_agency", "compliance_agent",
        "agency_mode", "current_status", "px_change_log", "playbook",
    ],
    "preview": [
        "preview/", ".html", "gallery", "card", "lightbox", "image", "webp",
        "hero", "overlay", "thumbnail", "carousel", "masonry", "pill",
        "render button", "rotate button", "setupcard", "savecard",
        "data-card-id", "data-src", "data-hero-id", "project page",
        "service page", "main.css", "main.js", "gallery.js", "lightbox.js",
        "screenshot", "_960w", "_1920w", "_480w", "_mv2",
        "preview_server", "visual_overlay", "playwright",
    ],
    "root": [
        "feature lock", "feature_lock", "guardrail", "pre-commit", "git commit",
        "execute_task", "execution mode", "discussion mode", "session continuity",
        "handoff", "active_session", "current_status", "pg_dump", "backup",
        "git filter", "filter-repo", "rule 17", "rule 19", "rule 21", "rule 22",
        "rule 23", "rule 25", "rule 26", "agent conduct", "photo studio",
        "open gap", "known gap", "pending fix",
    ],
}


def classify(text: str) -> list[str]:
    """Return list of bucket names that match the text. Always includes 'root'
    as a fallback if nothing else matches."""
    text_lower = text.lower()
    matched = []
    for bucket, signals in SIGNALS.items():
        if any(sig in text_lower for sig in signals):
            matched.append(bucket)
    if not matched:
        matched = ["root"]
    return matched


def load_file(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


# ── INBOUND mode ──────────────────────────────────────────────────────────────
def inbound(prompt: str) -> None:
    """Print the CLAUDE.md files relevant to this prompt. Output is captured
    by the UserPromptSubmit hook and injected into Claude's context."""
    buckets = classify(prompt)

    injected = []
    for bucket in buckets:
        path = CLAUDE_FILES.get(bucket)
        if path and path.exists():
            content = path.read_text(encoding="utf-8")
            injected.append(
                f"\n{'='*60}\n"
                f"[claude_context_agent] Auto-loaded: {path.relative_to(REPO_DIR)}\n"
                f"{'='*60}\n{content}"
            )

    if injected:
        print("\n".join(injected))
    # If root is the only match and it's already loaded by Claude Code natively,
    # we still print nothing extra — Claude already has it.


# ── OUTBOUND mode ─────────────────────────────────────────────────────────────
def outbound(rule: str, confirm: bool = False) -> None:
    """Classify a new rule and show where it would be written.
    Requires --confirm to actually append it."""
    buckets = classify(rule)

    # Pick the single best bucket (first non-root if multiple match, else root)
    non_root = [b for b in buckets if b != "root"]
    target_bucket = non_root[0] if non_root else "root"
    target_path = CLAUDE_FILES[target_bucket]

    print(f"\n[claude_context_agent] New rule classification")
    print(f"  Target file : {target_path.relative_to(REPO_DIR)}")
    print(f"  All matches : {', '.join(buckets)}")
    print(f"\n  --- Proposed addition ---")
    print(f"  {rule}")
    print(f"  --- End ---")

    if not confirm:
        print(
            f"\n  DRY RUN — nothing written. Re-run with --confirm to append to "
            f"{target_path.relative_to(REPO_DIR)}."
        )
        return

    # Append under a "## Agent-Added Rules" section at the end of the file
    existing = load_file(target_path)
    section_header = "## Agent-Added Rules"
    if section_header not in existing:
        addition = f"\n\n---\n\n{section_header}\n\n- {rule}\n"
    else:
        addition = f"\n- {rule}\n"

    with open(target_path, "a", encoding="utf-8") as f:
        f.write(addition)

    print(f"\n  [WRITTEN] Rule appended to {target_path.relative_to(REPO_DIR)}")
    print("  Review with: git diff")


# ── AUDIT mode ────────────────────────────────────────────────────────────────
def audit() -> None:
    """Scan all CLAUDE.md files and report lines that appear verbatim in
    more than one file (duplication check)."""
    print("\n[claude_context_agent] Audit — scanning for duplicate content\n")

    contents: dict[str, list[str]] = {}
    for bucket, path in CLAUDE_FILES.items():
        if path.exists():
            lines = [
                l.strip() for l in path.read_text(encoding="utf-8").splitlines()
                if len(l.strip()) > 40  # ignore short lines / headers
            ]
            contents[str(path.relative_to(REPO_DIR))] = lines

    files = list(contents.keys())
    duplicates_found = False
    for i, fa in enumerate(files):
        for fb in files[i + 1:]:
            shared = set(contents[fa]) & set(contents[fb])
            if shared:
                duplicates_found = True
                print(f"  Duplicate content between {fa} and {fb}:")
                for line in sorted(shared)[:5]:
                    print(f"    · {line[:100]}")
                if len(shared) > 5:
                    print(f"    ... and {len(shared) - 5} more")
                print()

    if not duplicates_found:
        print("  No significant duplicates found.")

    print("\n  File sizes:")
    for bucket, path in CLAUDE_FILES.items():
        if path.exists():
            size = path.stat().st_size
            print(f"    {str(path.relative_to(REPO_DIR)):<45} {size:>6,} bytes")


# ── CLI ───────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--inbound",  metavar="PROMPT", help="Inject relevant CLAUDE.md(s) for this prompt")
    group.add_argument("--outbound", metavar="RULE",   help="Classify and (optionally) write a new rule")
    group.add_argument("--audit",    action="store_true", help="Check for duplicate content across files")
    parser.add_argument("--confirm", action="store_true", help="With --outbound: actually write (default is dry-run)")

    args = parser.parse_args()

    if args.inbound:
        inbound(args.inbound)
    elif args.outbound:
        outbound(args.outbound, confirm=args.confirm)
    elif args.audit:
        audit()


if __name__ == "__main__":
    main()
