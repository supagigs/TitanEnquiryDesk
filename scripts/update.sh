#!/usr/bin/env bash
# Update Titan Enquiry Desk to a tag or branch safely.
# Usage: scripts/update.sh <bench-path> <site> <git-ref>
set -euo pipefail
BENCH=${1:?bench path}; SITE=${2:?site name}; REF=${3:?tag or branch, e.g. v1.0.0}
cd "$BENCH/apps/titan_desk"
if [ -n "$(git status --porcelain)" ]; then
  echo "Local changes found in apps/titan_desk:"; git status --short
  echo "Commit or stash them first. Nothing was changed."; exit 1
fi
PREV=$(git rev-parse HEAD)
cd "$BENCH"
echo "Backing up $SITE..."; bench --site "$SITE" backup --with-files
cd apps/titan_desk && git fetch --tags origin "$REF" && git checkout --quiet "$REF" 2>/dev/null || git checkout --quiet FETCH_HEAD
cd "$BENCH"
bench --site "$SITE" migrate
bench build --app titan_desk
bench --site "$SITE" clear-cache
echo "Updated from $PREV to $(git -C apps/titan_desk rev-parse HEAD)."
echo "Rollback: git -C apps/titan_desk checkout $PREV && bench --site $SITE restore <latest backup in sites/$SITE/private/backups> && bench build --app titan_desk"
