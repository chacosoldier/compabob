#!/usr/bin/env bash
# Everything CI runs, runnable locally:  bash tests/run-all.sh
set -u
cd "$(dirname "$0")/.." || exit 1
FAIL=0
step() { echo; echo "== $1"; }

step "shell syntax (bash -n)"
while IFS= read -r f; do bash -n "$f" || { echo "  FAIL  $f"; FAIL=$((FAIL+1)); }; done < <(git ls-files '*.sh')
echo "  done"

step "python compiles"
while IFS= read -r f; do python3 -m py_compile "$f" 2>/dev/null || { echo "  FAIL  $f"; FAIL=$((FAIL+1)); }; done < <(git ls-files '*.py')
echo "  done"

step "shellcheck (warnings and errors)"
if command -v shellcheck >/dev/null 2>&1; then
  git ls-files -z '*.sh' | xargs -0 shellcheck -S warning || { echo "  FAIL  shellcheck"; FAIL=$((FAIL+1)); }
  echo "  done"
else
  echo "  skipped (shellcheck not installed; CI runs it)"
fi

step "JSON files parse"
for f in scripts/integrations-catalog.json .claude/settings.json; do
  python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$f" || { echo "  FAIL  $f"; FAIL=$((FAIL+1)); }
done
echo "  done"

step "no em dashes in kit files (the style gate's own rule)"
if git grep -n $'\xe2\x80\x94' -- . ; then echo "  FAIL  em dashes above"; FAIL=$((FAIL+1)); else echo "  none"; fi

step "hooks";       bash tests/hook-smoke.sh        || FAIL=$((FAIL+1))
step "frontmatter"; python3 tests/check-frontmatter.py || FAIL=$((FAIL+1))
step "docs vs tree"; python3 tests/check-drift.py   || FAIL=$((FAIL+1))
for t in tests/test-*.sh; do
  [ -f "$t" ] || continue
  step "$t"; bash "$t" || FAIL=$((FAIL+1))
done

echo
[ "$FAIL" -eq 0 ] && echo "ALL PASSED" || echo "$FAIL STEP(S) FAILED"
exit "$FAIL"
