#!/usr/bin/env bash
# Tests for hooks/hook-session-start.sh: the setup notices, the one-time first-hour
# nudge, the kit-changed and locally-edited notices, and the memory-size notice.
# Runs the hook against throwaway copies of the kit. Exits with the number of failures.
set -u
cd "$(dirname "$0")/.." || exit 1
KIT="$PWD"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
pass=0; fail=0
unset COMPABOB_RUN_CONTEXT

check() {  # check <name> <command...>
  local name="$1"; shift
  if "$@"; then pass=$((pass+1)); echo "  ok    $name"; else fail=$((fail+1)); echo "  FAIL  $name"; fi
}
has()    { grep -qF -- "$2" "$1"; }
hasnot() { ! grep -qF -- "$2" "$1"; }
fresh() {
  mkdir -p "$1"
  (cd "$KIT" && git ls-files -co --exclude-standard -z | tar --null -T - -cf -) | tar -xf - -C "$1"
  (cd "$1" && git init -q && git add -A && git -c user.email=t@t -c user.name=t commit -qm kit) >/dev/null 2>&1
}
hook() {  # hook <dir> [source]: output in $OUT
  OUT="$1.hook.$RANDOM"
  printf '{"session_id":"t","source":"%s"}' "${2:-startup}" \
    | CLAUDE_PROJECT_DIR="$1" bash "$1/hooks/hook-session-start.sh" >"$OUT" 2>&1
}
setup() { (cd "$1" && ./setup.sh --user Sam --non-interactive </dev/null >/dev/null 2>&1); }

echo "session-start"

D="$T/none"; fresh "$D"; hook "$D"
check "no setup: offers /setup"                 has "$OUT" "Setup has not run"
COMPABOB_RUN_CONTEXT=scheduled hook "$D"
check "scheduled run: no setup notice"          hasnot "$OUT" "Setup has not run"

D="$T/blank"; fresh "$D"; cp -R "$D/memory.example" "$D/memory"; hook "$D"
check "placeholders left: says unfinished"      has "$OUT" "Setup did not finish"

D="$T/noname"; fresh "$D"; (cd "$D" && ./setup.sh --non-interactive </dev/null >/dev/null 2>&1); hook "$D"
check "no name: asks for one"                   has "$OUT" "Setup ran without a name"

D="$T/done"; fresh "$D"; setup "$D"; hook "$D"
check "after setup: no setup notice"            sh -c '! grep -qE "Setup (has not run|did not finish|ran without)" "$1"' _ "$OUT"
check "after setup: first-hour nudge"           has "$OUT" "First session after setup"
check "nudge leaves a marker"                   [ -f "$D/.tmp/first-hour-nudge.done" ]
hook "$D"
check "nudge shows once"                        hasnot "$OUT" "First session after setup"
rm "$D/.tmp/first-hour-nudge.done"; printf '# Kickoff\n\nReal notes.\n' > "$D/vault/Meetings/real.md"; hook "$D"
check "a real note: no nudge"                   hasnot "$OUT" "First session after setup"
check "setup leaves no kit edits to report"     hasnot "$OUT" "Kit files edited locally"

D="$T/git"; fresh "$D"; setup "$D"; hook "$D"
check "first session: no kit-changed notice"    hasnot "$OUT" "The kit changed"
echo "# local" >> "$D/CHANGELOG.md"; (cd "$D" && git -c user.email=t@t -c user.name=t commit -qam update) >/dev/null 2>&1
hook "$D" compact
check "after compaction: no kit-changed notice" hasnot "$OUT" "The kit changed"
hook "$D"
check "after an update: kit-changed notice"     has "$OUT" "(1 commit(s))"
hook "$D"
check "kit-changed notice shows once"           hasnot "$OUT" "The kit changed"
echo "# mine" >> "$D/CONSTITUTION.md"; hook "$D"
check "a local kit edit is named"               has "$OUT" "Kit files edited locally and not in the upstream kit: CONSTITUTION.md"

D="$T/big"; fresh "$D"; setup "$D"; python3 -c "print('x' * 13000)" >> "$D/memory/MEMORY.md"; hook "$D"
check "oversized MEMORY.md is flagged"          has "$OUT" "over the 12288-byte cap"

D="$T/nostdin"; fresh "$D"; setup "$D"
(CLAUDE_PROJECT_DIR="$D" bash "$D/hooks/hook-session-start.sh" </dev/null >/dev/null 2>&1); RC=$?
check "empty input: exits 0"                    [ "$RC" -eq 0 ]

echo
echo "session-start: $pass passed, $fail failed"
exit "$fail"
