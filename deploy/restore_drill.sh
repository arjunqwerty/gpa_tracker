#!/usr/bin/env bash
# Proves the backups work: takes a fresh backup, restores it into a scratch database, checks
# every collection has the same number of documents, then drops the scratch database.
# Prefix with IN_DOCKER=1 for the docker compose deployment.
set -euo pipefail
cd "$(dirname "$0")/.."
source deploy/mongo_tools.sh

deploy/backup.sh
FILE="$(ls -1t "${BACKUP_DIR:-backups}/$DB"-*.archive.gz | head -n 1)"
deploy/restore.sh "$FILE" "${DB}_restore_drill"

COUNTS='db.getCollectionNames().sort().map(c => c + " " + db[c].countDocuments()).join("\n")'
live="$(mongo_tool mongosh --quiet "$DB" --eval "$COUNTS")"
restored="$(mongo_tool mongosh --quiet "${DB}_restore_drill" --eval "$COUNTS")"
mongo_tool mongosh --quiet "${DB}_restore_drill" --eval "db.dropDatabase()" > /dev/null

echo "$live"
if [ "$live" = "$restored" ]; then echo "Restore drill passed"; else echo "Restore drill FAILED"; diff <(echo "$live") <(echo "$restored"); exit 1; fi
