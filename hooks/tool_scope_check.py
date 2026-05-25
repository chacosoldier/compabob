#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""Check whether a tool is permitted under the active context.

Usage: python3 tool_scope_check.py <tool_name> <context> <scopes_yaml_path>
Stdout: JSON {"verdict": "allow"|"deny", "reason": "<str>"}
Exit: always 0 (callers check verdict, not exit code).

Fail-open: if anything goes wrong (missing args, YAML parse error, unknown
context), the verdict is "allow" with an explanatory reason. A broken guard
must never block real work — operators inspect logs to tighten it later.
"""
import fnmatch
import json
import sys


def main() -> None:
    if len(sys.argv) < 4:
        print(json.dumps({"verdict": "allow", "reason": "missing_args"}))
        return

    tool, context, scopes_path = sys.argv[1], sys.argv[2], sys.argv[3]

    try:
        import yaml  # noqa: PLC0415 — intentional late import (uv-injected dep)
        with open(scopes_path) as f:
            scopes = yaml.safe_load(f)
    except Exception as e:
        print(json.dumps({"verdict": "allow", "reason": f"yaml_error:{e}"}))
        return

    contexts = scopes.get("contexts", {})

    if context not in contexts:
        print(json.dumps({"verdict": "allow", "reason": f"unknown_context:{context}"}))
        return

    ctx = contexts[context]
    policy = ctx.get("policy", "allow_all")

    if policy == "allow_all":
        print(json.dumps({"verdict": "allow", "reason": "allow_all_context"}))
        return

    blocked = ctx.get("blocked_tools") or []
    allowed = ctx.get("allowed_tools") or []

    # Explicit block list wins over allowlist.
    for pattern in blocked:
        if fnmatch.fnmatch(tool, pattern):
            print(json.dumps({"verdict": "deny", "reason": f"blocked:{pattern}"}))
            return

    for pattern in allowed:
        if fnmatch.fnmatch(tool, pattern):
            print(json.dumps({"verdict": "allow", "reason": f"allowed:{pattern}"}))
            return

    print(json.dumps({"verdict": "deny", "reason": "not_in_allowlist"}))


main()
