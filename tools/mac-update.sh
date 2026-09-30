#!/bin/bash
# Keep the Mac copy of UniQR in step with main.
#
# Run it by hand, or let launchd run it at login and every half hour. It
# refuses to touch the repo unless it is on main with nothing uncommitted, so
# work in progress on another branch is never disturbed.
#
#   ./tools/mac-update.sh            # update from main
#   UNIQR_REPO=~/code/uniqr ...      # if the repo lives somewhere else
#
# Everything it does is written to ~/Library/Logs/uniqr-update.log

set -u

REPO="${UNIQR_REPO:-$HOME/Downloads/uniqr}"
LOG="$HOME/Library/Logs/uniqr-update.log"
PYTHON="${UNIQR_PYTHON:-python3}"

mkdir -p "$(dirname "$LOG")"
say() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG"; }

cd "$REPO" 2>/dev/null || { say "no repo at $REPO - set UNIQR_REPO"; exit 1; }

branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)
if [ "$branch" != "main" ]; then
  say "on branch '$branch', not main. Leaving it alone."
  exit 0
fi
if [ -n "$(git status --porcelain)" ]; then
  say "there are uncommitted changes here. Leaving them alone."
  exit 0
fi

before=$(git rev-parse HEAD)
git fetch --quiet origin main || { say "could not reach GitHub"; exit 1; }
if ! git merge --ff-only --quiet origin/main; then
  say "cannot fast-forward: this copy has commits main does not. Leaving it alone."
  exit 1
fi
after=$(git rev-parse HEAD)

if [ "$before" = "$after" ]; then
  say "already up to date at $(git rev-parse --short HEAD)"
  exit 0
fi
say "updated $(git rev-parse --short "$before") -> $(git rev-parse --short "$after")"

# Dependencies change too. zxing-cpp was added at one point, and a copy with
# stale packages ran the new code badly rather than failing outright.
if ! "$PYTHON" -m pip install --quiet --requirement requirements.txt >>"$LOG" 2>&1; then
  say "pip install reported problems - see the log"
fi

# Restart it only if it was already running, so this never starts the app
# behind your back.
if pgrep -f "uniqr.*app\.py" >/dev/null 2>&1; then
  say "restarting the running app"
  pkill -f "uniqr.*app\.py" >/dev/null 2>&1
  sleep 1
  (cd "$REPO" && nohup "$PYTHON" app.py >>"$LOG" 2>&1 &)
else
  say "app was not running, so nothing to restart"
fi

say "done"
