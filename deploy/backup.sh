#!/usr/bin/env bash
# Backs up the database to backups/<db>-<date>.archive.gz and keeps the newest 14 backups.
#
#   deploy/backup.sh                 MongoDB running on this machine
#   IN_DOCKER=1 deploy/backup.sh     the docker compose deployment (run from the project folder)
#
# Daily at 03:00 with cron:  0 3 * * * cd /path/to/VIT_GPA_Tracker && IN_DOCKER=1 deploy/backup.sh
set -euo pipefail
source "$(dirname "$0")/mongo_tools.sh"

DIR="${BACKUP_DIR:-backups}"
mkdir -p "$DIR"
FILE="$DIR/$DB-$(date +%Y-%m-%d-%H%M%S).archive.gz"
mongo_tool mongodump --quiet --db "$DB" --archive --gzip > "$FILE"
echo "Backed up $DB to $FILE"

ls -1t "$DIR/$DB"-*.archive.gz | tail -n +15 | xargs -r rm --
