#!/usr/bin/env bash
# Tests for setup.sh: the options the /setup skill and CI use, re-runs, finishing a
# run that stopped halfway, and the python3 stop. Every case runs in a fresh copy of
# the kit, so your own vault/ and memory/ are never touched. Exits with the number
# of failed cases.
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
no_blanks() { ! grep -rqE '\{\{(ASSISTANT_NAME|USER_NAME|USER_ROLE|PRIMARY_LANGUAGE)\}\}|_YOUR_NAME_HERE_' "$1/vault" "$1/memory" "$1/config/user.config.yaml"; }
fresh() {  # a copy of the kit as a clone has it: tracked and new files, file modes kept
  mkdir -p "$1"
  (cd "$KIT" && git ls-files -co --exclude-standard -z | tar --null -T - -cf -) | tar -xf - -C "$1"
}
run() {  # run <dir> <args...>: setup with no keyboard; output in <dir>.out, exit code in RC
  local d="$1"; shift
  (cd "$d" && ./setup.sh "$@" </dev/null >"$d.out" 2>&1); RC=$?
}
FULL=(--assistant Maya --user 'Sam O"Brien' --role PM --language German --persona 3 --focus 'ships things' --no-integrations --non-interactive)

echo "setup.sh"

D="$T/help"; fresh "$D"; run "$D" --help
check "--help exits 0"                         [ "$RC" -eq 0 ]
check "--help names every option"              sh -c 'for o in --assistant --user --role --language --persona --focus --integrations --no-integrations --non-interactive; do grep -qF -- "$o" "$1" || exit 1; done' _ "$D.out"
check "--help creates nothing"                 [ ! -e "$D/vault" ]

D="$T/full"; fresh "$D"; run "$D" "${FULL[@]}"
check "all options: exit 0"                    [ "$RC" -eq 0 ]
check "all options: no question was asked"     hasnot "$D.out" "Pick 1-6 (or the name) ["
check "all options: values land in the config" sh -c 'grep -qF "name: \"Maya\"" "$1" && grep -qF "role: \"PM\"" "$1" && grep -qF "primary_language: \"German\"" "$1" && grep -qF "preset: \"engineer\"" "$1"' _ "$D/config/user.config.yaml"
check "a quote in a name is escaped in YAML"   has "$D/config/user.config.yaml" 'name: "Sam O\"Brien"'
check "and plain in MEMORY.md"                 has "$D/memory/MEMORY.md" '**Sam O"Brien**'
check "focus text lands in role file"          has "$D/memory/topics/role-and-priorities.md" "ships things"
check "no blanks left anywhere"                no_blanks "$D"

run "$D" --assistant Other --user Other --non-interactive
check "re-run: exit 0"                         [ "$RC" -eq 0 ]
check "re-run: says it is already set up"      has "$D.out" "Already set up"
check "re-run: keeps the first answers"        has "$D/config/user.config.yaml" 'name: "Maya"'
check "re-run: prints what is on disk"         has "$D.out" 'called "Maya"'

D="$T/defaults"; fresh "$D"; run "$D" --non-interactive
check "defaults only: exit 0"                  [ "$RC" -eq 0 ]
check "defaults: assistant is Aide"            has "$D/config/user.config.yaml" 'name: "Aide"'
check "defaults: persona is generalist"        has "$D/config/user.config.yaml" 'preset: "generalist"'
check "defaults: no name leaves a stand-in"    has "$D/memory/MEMORY.md" "_YOUR_NAME_HERE_"
run "$D" --user Maya --non-interactive
check "name repair: exit 0"                    [ "$RC" -eq 0 ]
check "name repair: stand-in replaced"         no_blanks "$D"
check "name repair: name in MEMORY.md"         has "$D/memory/MEMORY.md" "**Maya**"
check "name repair: assistant kept"            has "$D/config/user.config.yaml" 'name: "Aide"'

D="$T/halfrun"; fresh "$D"
cp -R "$D/vault.example" "$D/vault"; cp -R "$D/memory.example" "$D/memory"
cp "$D/config/user.config.yaml.template" "$D/config/user.config.yaml"
run "$D" "${FULL[@]}"
check "half-run repair: exit 0"                [ "$RC" -eq 0 ]
check "half-run repair: says it stopped early" has "$D.out" "stopped early"
check "half-run repair: blanks filled"         no_blanks "$D"
check "half-run repair: persona applied"       has "$D/config/user.config.yaml" 'preset: "engineer"'

D="$T/nopy"; fresh "$D"; mkdir -p "$T/fakebin"
printf '#!/bin/sh\nexit 1\n' > "$T/fakebin/python3"; chmod +x "$T/fakebin/python3"
(cd "$D" && PATH="$T/fakebin:$PATH" ./setup.sh "${FULL[@]}" </dev/null >"$D.out" 2>&1); RC=$?
check "no python3: exit 1"                     [ "$RC" -eq 1 ]
check "no python3: plain message"              has "$D.out" "Setup needs Python 3"
check "no python3: nothing created"            sh -c '[ ! -e "$1/vault" ] && [ ! -e "$1/memory" ] && [ ! -e "$1/config/user.config.yaml" ]' _ "$D"

D="$T/p4"; fresh "$D"; run "$D" --persona 4 --non-interactive
check "persona by number"                      has "$D/config/user.config.yaml" 'preset: "sales"'
D="$T/pname"; fresh "$D"; run "$D" --persona founder --non-interactive
check "persona by name"                        has "$D/config/user.config.yaml" 'preset: "founder"'
D="$T/pbad"; fresh "$D"; run "$D" --persona bogus --non-interactive
check "unknown persona falls back"             sh -c 'grep -qF "preset: \"generalist\"" "$1" && grep -qF "did not recognize" "$2"' _ "$D/config/user.config.yaml" "$D.out"

D="$T/badflag"; fresh "$D"; run "$D" --colour blue
check "unknown option exits 2"                 [ "$RC" -eq 2 ]
run "$D" --user
check "option without a value exits 2"         [ "$RC" -eq 2 ]
check "a bad option creates nothing"           [ ! -e "$D/vault" ]

D="$T/interactive"; fresh "$D"
(cd "$D" && printf 'Zed\nMaya\nPM\nGerman\n3\nships things\nn\n' | ./setup.sh >"$D.out" 2>&1); RC=$?
check "seven typed answers: exit 0"            [ "$RC" -eq 0 ]
check "seven typed answers land in order"      sh -c 'grep -qF "name: \"Zed\"" "$1" && grep -qF "name: \"Maya\"" "$1" && grep -qF "primary_language: \"German\"" "$1" && grep -qF "preset: \"engineer\"" "$1"' _ "$D/config/user.config.yaml"

D="$T/clean"; fresh "$D"
(cd "$D" && git init -q && git add -A && git -c user.email=t@t -c user.name=t commit -qm kit) >/dev/null 2>&1
run "$D" --non-interactive
check "setup leaves the kit files unmodified"  sh -c '[ -z "$(git -C "$1" status --porcelain)" ]' _ "$D"

echo
echo "setup: $pass passed, $fail failed"
exit "$fail"
