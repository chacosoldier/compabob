#!/usr/bin/env bash
# Tests for hooks/hook-plan-premortem.py: feed ExitPlanMode payloads and check
# the deny decision in both directions (valid pre-mortems pass, near misses stay
# denied), plus the transcript-scoped plan-file lookup. Every case must exit 0.
set -u
cd "$(dirname "$0")/.." || exit 1
HOOK="hooks/hook-plan-premortem.py"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
pass=0; fail=0

payload() { python3 -c 'import json,sys; print(json.dumps({"tool_name":"ExitPlanMode","tool_input":{"plan":sys.argv[1]}}))' "$1"; }

run_case() {  # run_case <name> <deny|pass> <payload>
  local name="$1" want="$2" out rc denied=0
  out=$(printf '%s' "$3" | python3 "$HOOK" 2>/dev/null); rc=$?
  printf '%s' "$out" | grep -q '"permissionDecision": "deny"' && denied=1
  if [ "$rc" -eq 0 ] && { { [ "$want" = deny ] && [ "$denied" = 1 ]; } || { [ "$want" = pass ] && [ "$denied" = 0 ]; }; }; then
    pass=$((pass+1)); echo "  ok    $name"
  else
    fail=$((fail+1)); echo "  FAIL  $name (rc=$rc, out=${out:0:120})"
  fi
}

TRIG=$'# Plan\nWe deploy to production on Friday.\n\n'
B3=$'- a fails\n- b fails\n- c fails\n'

run_case "low-stakes plan passes"                       pass "$(payload $'# Plan\nRename a heading in the README.\n')"
run_case "trigger with no pre-mortem is denied"         deny "$(payload "$TRIG")"
run_case "wide-blast trigger is denied"                 deny "$(payload $'# Plan\nEmail all customers about the change.\n')"
run_case "sunk-cost trigger is denied"                  deny "$(payload $'# Plan\nA full rewrite of the importer.\n')"
run_case "pre-mortem, phrase in heading, passes"        pass "$(payload "$TRIG"$'## Pre-mortem (strategy-advisor)\n'"$B3")"
run_case "pre-mortem, phrase in body, passes"           pass "$(payload "$TRIG"$'## Premortem\nRun with strategy-advisor.\n'"$B3"$'\n## Steps\n1. go\n')"
run_case "only two bullets is denied"                   deny "$(payload "$TRIG"$'## Pre-mortem (strategy-advisor)\n- a\n- b\n')"
run_case "three bullets, no strategy-advisor, denied"   deny "$(payload "$TRIG"$'## Pre-mortem\n'"$B3")"
run_case "phrase only in a later section is denied"    deny "$(payload "$TRIG"$'## Pre-mortem\n'"$B3"$'\n## Risks (strategy-advisor)\n- x\n')"
run_case "other tool is ignored"                        pass '{"tool_name":"Bash","tool_input":{"command":"ls"}}'
run_case "garbage input fails open"                     pass 'not json'

# Plan-file lookup: the plan is a file named in THIS session's transcript.
mkdir -p "$T/.claude/plans"
printf '%s' "$TRIG" > "$T/.claude/plans/mine.md"
printf '# Plan\nTypo fix.\n' > "$T/.claude/plans/other.md"
printf '{"type":"user","message":{"content":"create your plan at %s/.claude/plans/mine.md"}}\n' "$T" > "$T/transcript.jsonl"
run_case "plan file named in the transcript is checked" deny \
  "{\"tool_name\":\"ExitPlanMode\",\"tool_input\":{},\"transcript_path\":\"$T/transcript.jsonl\"}"
printf '{"type":"user","message":{"content":"no plan mentioned"}}\n' > "$T/t2.jsonl"
run_case "no plan in this session passes (never reads other plans)" pass \
  "{\"tool_name\":\"ExitPlanMode\",\"tool_input\":{},\"transcript_path\":\"$T/t2.jsonl\"}"

echo
echo "pre-mortem gate: $pass passed, $fail failed"
exit "$fail"
