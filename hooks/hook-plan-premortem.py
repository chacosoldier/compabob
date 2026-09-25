#!/usr/bin/env python3
"""PreToolUse(ExitPlanMode) hook: require a pre-mortem on high-stakes plans.

A mandatory pre-mortem on every plan is ceremony. But a plan that is hard to
undo, touches many people, or commits weeks of work deserves one adversarial
pass before it is approved, while optimism is strongest. This hook reads the
plan being approved, and if it matches any trigger below, denies the exit until
the plan has a "## Pre-mortem" section written with the strategy-advisor agent.

Triggers (any one):
  irreversible   deploy to production, drop or delete data, force-push, sign a
                 contract, publish publicly, send to everyone, quit a job
  wide blast     shared systems, all users or customers, company-wide
  sunk cost      multi-week work, major refactor, full rewrite

Passes when the plan has "## Pre-mortem" with at least 3 bullets and the word
"strategy-advisor" in that section (heading included).

Where the plan comes from: tool_input.plan when Claude Code sends it; otherwise
the newest plan file under ~/.claude/plans/ that THIS session's transcript
names, so a plan from another project or session is never checked by mistake.
Fails open: any error, or no plan found, exits 0.
"""

import json
import os
import re
import sys

TRIGGERS = {
    "irreversible": r"deploy(ing)? to prod|to production|in prod\b|drop (table|column|database)|delete (the )?(table|database|all|every)"
    r"|force.push|sign (the |a )?(contract|nda|lease|offer)|publish(ed)? (to|on) (linkedin|the blog|social)|post publicly"
    r"|send (it )?to (all|every|the whole)|mass (email|mailing)|(resign|quit) (my|the) (job|role)",
    "wide-blast": r"shared (system|infra|database|drive|calendar)|all users|all customers|customer.facing|company.wide"
    r"|every (customer|user|employee)",
    "sunk-cost": r"multi.week|several weeks|multiple weeks|major refactor|full rewrite|rebuild from scratch|months of work",
}
PLAN_PATH = re.compile(r"(/[^\s\"'`<>]*/\.claude/plans/[\w.-]+\.md)")


def plan_from_transcript(path: str) -> str:
    try:
        with open(path, errors="ignore") as fh:
            names = PLAN_PATH.findall(fh.read())
    except OSError:
        return ""
    for name in reversed(names):
        if os.path.isfile(name):
            with open(name, errors="ignore") as fh:
                return fh.read()
    return ""


def has_premortem(plan: str) -> bool:
    m = re.search(r"^## *pre.?mortem.*?(?=^## |\Z)", plan, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    if not m:
        return False
    section = m.group(0)
    bullets = len(re.findall(r"^\s*[-*]\s+\S", section, re.MULTILINE))
    return bullets >= 3 and "strategy-advisor" in section.lower()


def main() -> int:
    data = json.load(sys.stdin)
    if not isinstance(data, dict) or data.get("tool_name") != "ExitPlanMode":
        return 0
    plan = (data.get("tool_input") or {}).get("plan") or plan_from_transcript(data.get("transcript_path") or "")
    if not plan:
        return 0
    lower = plan.lower()
    fired = [name for name, pattern in TRIGGERS.items() if re.search(pattern, lower)]
    if not fired or has_premortem(plan):
        return 0
    reason = (
        f"This plan looks high-stakes ({', '.join(fired)}). Before approval: (1) run the strategy-advisor agent with "
        "the plan and the prompt 'Run a pre-mortem: six months from now this plan failed. List the top failure "
        "modes and what we would wish we had done differently.' (2) Add a '## Pre-mortem' section to the plan with "
        "at least three failure modes, one bullet each, naming strategy-advisor as the source, and fold any fixes "
        "into the plan. (3) Call ExitPlanMode again."
    )
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a planning gate must never break a session
        sys.exit(0)
