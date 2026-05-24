#!/usr/bin/env bash
# Compabob — update to the latest kit version.
# Your vault/, memory/, and config/ are git-ignored and are NEVER touched by this.
set -uo pipefail

cd "$(dirname "$0")"

bold() { printf '\033[1m%s\033[0m\n' "$1"; }
say()  { printf '  %s\n' "$1"; }

bold ""
bold "Compabob — update"
echo "Your data (vault/, memory/, config/user.config.yaml, .mcp.json, .env) is git-ignored."
echo "An update cannot touch those files."
echo

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "This folder is not a git clone, so there is nothing to update from."
  echo "To receive updates, clone the repo with git instead of downloading a zip."
  exit 1
fi

BRANCH="$(git branch --show-current 2>/dev/null || echo main)"

if ! git fetch --quiet origin "$BRANCH" 2>/dev/null; then
  echo "Could not reach the remote. Check your internet connection and try again."
  exit 1
fi

LOCAL="$(git rev-parse @ 2>/dev/null || echo "")"
REMOTE="$(git rev-parse "origin/$BRANCH" 2>/dev/null || echo "")"
if [ -z "$REMOTE" ]; then
  echo "No remote branch origin/$BRANCH found. Nothing to update."
  exit 0
fi
if [ "$LOCAL" = "$REMOTE" ]; then
  bold "Already up to date."
  exit 0
fi

say "A newer version is available. Updating..."

STASHED=0
if ! git diff --quiet || ! git diff --cached --quiet; then
  say "You have edits to kit files. Setting them aside while updating..."
  if git stash push --quiet -m "compabob update $(date '+%Y-%m-%d %H:%M')"; then
    STASHED=1
  fi
fi

if git merge --no-edit "origin/$BRANCH" >/dev/null 2>&1; then
  say "Pulled the latest kit:"
  # Show what changed so the user does not need a separate `git log`. Capped
  # at 10 lines so a big merge does not flood the terminal.
  git log --no-merges --oneline "$LOCAL..HEAD" 2>/dev/null | head -10 | sed 's/^/    /'
else
  echo
  echo "The update needs a manual merge. Run 'git status' to see which files."
  echo "Your vault/, memory/, and config/ are safe regardless."
  [ "$STASHED" = 1 ] && echo "Your set-aside edits are saved: restore them with 'git stash pop'."
  exit 1
fi

if [ "$STASHED" = 1 ]; then
  if git stash pop >/dev/null 2>&1; then
    say "Re-applied your own kit edits on top of the update."
  else
    echo
    echo "Your edits overlap with the update. Run 'git status', open the marked files,"
    echo "resolve the conflicts, then 'git add' them. Your vault/memory/config are untouched."
    exit 1
  fi
fi

echo
bold "Update complete."
echo "Run 'bash scripts/init.sh' to confirm everything is healthy."
