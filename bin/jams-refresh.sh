#!/bin/bash
# Fortnightly jam refresh, run by launchd on the owner's Mac. No agent involved.
# Works in its own clone, syncs from itch.io, builds, and opens a pull request when anything changed.
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
REPO=https://github.com/twitu/indiegopunk-site.git
DIR="$HOME/.cache/indiegopunk-jams/repo"
GIT=(git -c credential.helper= -c "credential.helper=!gh auth git-credential")
echo "=== $(date '+%Y-%m-%d %H:%M:%S') jams refresh"

if [ ! -d "$DIR/.git" ]; then mkdir -p "$(dirname "$DIR")"; "${GIT[@]}" clone -q "$REPO" "$DIR"; fi
cd "$DIR"
"${GIT[@]}" fetch -q origin main
git checkout -q -B work origin/main

python3 bin/jams_sync.py --write | tee /tmp/jams-sync.txt
python3 bin/jams.py build
if git diff --quiet -- calendars/jams.json; then echo "no changes"; exit 0; fi

B="jams-sync-$(date +%Y%m%d)"
git checkout -q -B "$B"
git add calendars sitemap.xml
git -c user.name="jams-bot" -c user.email="jams-bot@users.noreply.github.com" commit -q -m "calendars: itch.io sync"
"${GIT[@]}" push -q -f origin "$B"
{ echo "Automatic itch.io sync from the owner's Mac. Check each new jam (format, team, prize, theme, end date), then merge."
  echo; echo '```'; cat /tmp/jams-sync.txt; echo '```'; } > /tmp/jams-body.md
gh pr create --title "Jam sync $(date +%Y-%m-%d)" --body-file /tmp/jams-body.md --base main --head "$B" || echo "PR exists or failed: see above"
