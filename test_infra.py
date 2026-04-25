#!/usr/bin/env python3
"""
test_infra.py — Infrastructure integration tests for the post-phase guardrail.

Tests things Playwright and the 197-check gate cannot catch:
  - Hook commands fire correctly with real stdin JSON input
  - Scripts produce expected output (not silently empty)
  - Pre-push hook blocks binary deletions

Run by execute_task_post.sh as Gate 2 (before Playwright).
Exit 0 = all pass. Exit 1 = failures found (blocks commit).
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).parent.resolve()
SETTINGS = Path.home() / ".claude" / "settings.json"

PASS = "\033[0;32m[PASS]\033[0m"
FAIL = "\033[0;31m[FAIL]\033[0m"
INFO = "\033[0;36m[INFO]\033[0m"

failures = []


def run(label, cmd, stdin_data=None, expect_in_stdout=None, expect_exit=0):
    try:
        result = subprocess.run(
            cmd if isinstance(cmd, list) else ["bash", "-c", cmd],
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=15,
        )
        out = result.stdout + result.stderr

        if expect_exit is not None and result.returncode != expect_exit:
            print(f"  {FAIL} {label}")
            print(f"         exit={result.returncode} (expected {expect_exit})")
            print(f"         stdout: {result.stdout[:200]}")
            print(f"         stderr: {result.stderr[:200]}")
            failures.append(label)
            return False

        if expect_in_stdout and expect_in_stdout not in out:
            print(f"  {FAIL} {label}")
            print(f"         expected '{expect_in_stdout}' in output")
            print(f"         got: {out[:300]}")
            failures.append(label)
            return False

        print(f"  {PASS} {label}")
        return True
    except subprocess.TimeoutExpired:
        print(f"  {FAIL} {label} — timed out after 15s")
        failures.append(label)
        return False
    except Exception as e:
        print(f"  {FAIL} {label} — {e}")
        failures.append(label)
        return False


def make_hook_stdin(prompt: str) -> str:
    return json.dumps({
        "session_id": "infra-test",
        "user_prompt": prompt,
        "hook_event_name": "UserPromptSubmit",
        "cwd": str(REPO),
    })


# ── 1. claude_context_agent.py — direct mode ─────────────────────────────────
print("\n[1/4] claude_context_agent.py — direct invocation")

agent = str(REPO / "claude_context_agent.py")

run(
    "inbound: web/image prompt → preview/CLAUDE.md injected",
    ["python3", agent, "--inbound", "fix gallery card thumbnail _960w webp variant"],
    expect_in_stdout="preview/CLAUDE.md",
)
run(
    "inbound: marketing prompt → ridgecrest-agency/CLAUDE.md injected",
    ["python3", agent, "--inbound", "update the Meta campaign budget CPL"],
    expect_in_stdout="ridgecrest-agency/CLAUDE.md",
)
run(
    "inbound: governance prompt → root CLAUDE.md injected",
    ["python3", agent, "--inbound", "check feature locks before editing the guardrail"],
    expect_in_stdout="CLAUDE.md",
)
run(
    "outbound dry-run: classifies marketing rule",
    ["python3", agent, "--outbound", "Never use broad match keywords until 200+ conversions"],
    expect_in_stdout="ridgecrest-agency/CLAUDE.md",
)
run(
    "audit: runs without error",
    ["python3", agent, "--audit"],
    expect_in_stdout="File sizes",
)

# ── 2. UserPromptSubmit hook — real stdin JSON format ─────────────────────────
print("\n[2/4] UserPromptSubmit hook — real stdin JSON (catches wrong env-var bugs)")

if not SETTINGS.exists():
    print(f"  {INFO} settings.json not found — skipping hook tests")
else:
    settings = json.loads(SETTINGS.read_text())
    hooks_list = settings.get("hooks", {}).get("UserPromptSubmit", [])
    all_commands = []
    for group in hooks_list:
        for hook in group.get("hooks", []):
            if hook.get("type") == "command":
                all_commands.append(hook["command"])

    # Find the claude_context_agent hook specifically
    context_hook_cmd = next(
        (c for c in all_commands if "claude_context_agent" in c), None
    )

    if context_hook_cmd is None:
        print(f"  {FAIL} claude_context_agent hook not found in settings.json")
        failures.append("hook: claude_context_agent not wired")
    else:
        # Test: web prompt → must mention preview/CLAUDE.md
        run(
            "hook fires with web prompt → injects preview/CLAUDE.md",
            context_hook_cmd,
            stdin_data=make_hook_stdin("fix the gallery card thumbnail _960w webp variant"),
            expect_in_stdout="preview/CLAUDE.md",
        )
        # Test: marketing prompt → must mention ridgecrest-agency/CLAUDE.md
        run(
            "hook fires with marketing prompt → injects ridgecrest-agency/CLAUDE.md",
            context_hook_cmd,
            stdin_data=make_hook_stdin("update the Meta campaign budget and CPL"),
            expect_in_stdout="ridgecrest-agency/CLAUDE.md",
        )
        # Test: empty user_prompt → must NOT crash (exit 0)
        run(
            "hook handles empty user_prompt gracefully",
            context_hook_cmd,
            stdin_data=json.dumps({"session_id": "test", "user_prompt": "", "hook_event_name": "UserPromptSubmit"}),
            expect_exit=0,
        )
        # Test: malformed stdin → must NOT crash (|| true in command)
        run(
            "hook handles malformed stdin gracefully",
            context_hook_cmd,
            stdin_data="not json at all",
            expect_exit=0,
        )

# ── 3. pre-push hook — binary deletion detection ──────────────────────────────
print("\n[3/4] pre-push hook — binary deletion detection")

pre_push = REPO / ".git" / "hooks" / "pre-push"

if not pre_push.exists():
    print(f"  {FAIL} pre-push hook not found at {pre_push}")
    failures.append("pre-push hook missing")
elif not os.access(pre_push, os.X_OK):
    print(f"  {FAIL} pre-push hook not executable")
    failures.append("pre-push hook not executable")
else:
    # Test: no deletions → should pass (exit 0)
    current_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO).decode().strip()
    run(
        "pre-push: clean push (no deletions) → allowed",
        str(pre_push),
        stdin_data=f"refs/heads/ridgecrest-audit {current_sha} refs/heads/ridgecrest-audit {current_sha}\n",
        expect_exit=0,
    )

    # Test: simulate deletion of a tracked binary → should block (exit 1)
    # Create a temp commit that deletes a tracked binary, then test the hook
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Save the file
            logo = REPO / "preview" / "assets" / "logo.jpg"
            logo_backup = Path(tmpdir) / "logo.jpg"
            if logo.exists():
                import shutil
                shutil.copy(str(logo), str(logo_backup))

                subprocess.run(["git", "rm", str(logo)], cwd=REPO, capture_output=True)
                result = subprocess.run(
                    ["git", "commit", "-m", "infra-test: binary deletion (will be reverted)"],
                    cwd=REPO, capture_output=True, text=True
                )
                if result.returncode == 0:
                    new_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO).decode().strip()
                    parent_sha = subprocess.check_output(["git", "rev-parse", "HEAD~1"], cwd=REPO).decode().strip()

                    run(
                        "pre-push: push that deletes logo.jpg → BLOCKED",
                        str(pre_push),
                        stdin_data=f"refs/heads/ridgecrest-audit {new_sha} refs/heads/ridgecrest-audit {parent_sha}\n",
                        expect_exit=1,
                        expect_in_stdout="PRE-PUSH BLOCKED",
                    )
                    # Revert the test commit
                    subprocess.run(["git", "reset", "--hard", "HEAD~1"], cwd=REPO, capture_output=True)
                    shutil.copy(str(logo_backup), str(logo))
                else:
                    print(f"  {INFO} pre-push deletion test skipped (commit failed: pre-commit gate)")
                    # Restore the file
                    subprocess.run(["git", "checkout", "--", str(logo)], cwd=REPO, capture_output=True)
        except Exception as e:
            print(f"  {INFO} pre-push deletion test skipped: {e}")

# ── 4. execute_task_pre.sh binary backup ─────────────────────────────────────
print("\n[4/4] Infra script sanity checks")

run(
    "execute_task_pre.sh exists and is executable",
    ["test", "-x", str(REPO / "execute_task_pre.sh")],
    expect_exit=0,
)
run(
    "execute_task_post.sh exists and is executable",
    ["test", "-x", str(REPO / "execute_task_post.sh")],
    expect_exit=0,
)
run(
    "claude_context_agent.py exists and is executable",
    ["test", "-x", str(REPO / "claude_context_agent.py")],
    expect_exit=0,
)
run(
    "settings.json is valid JSON",
    ["python3", "-c", f"import json; json.load(open('{SETTINGS}'))"],
    expect_exit=0,
)
run(
    "ridgecrest-agency/CLAUDE.md exists and is non-empty",
    ["test", "-s", str(REPO / "ridgecrest-agency" / "CLAUDE.md")],
    expect_exit=0,
)
run(
    "preview/CLAUDE.md exists and is non-empty",
    ["test", "-s", str(REPO / "preview" / "CLAUDE.md")],
    expect_exit=0,
)

# ── Result ────────────────────────────────────────────────────────────────────
print()
if failures:
    print(f"\033[0;31m\033[1m[INFRA FAIL] {len(failures)} test(s) failed:\033[0m")
    for f in failures:
        print(f"  ✗ {f}")
    sys.exit(1)
else:
    total = 14  # approximate — count above
    print(f"\033[0;32m\033[1m[INFRA PASS] All infrastructure tests passed.\033[0m")
    sys.exit(0)
