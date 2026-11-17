#!/usr/bin/env bash
# Restores a backup made by backup.sh.
#
#   deploy/restore.sh FILE              replaces the live database with the backup (asks first)
#   deploy/restore.sh FILE OTHER_DB     restores into OTHER_DB instead, leaving live data alone
#
# Prefix with IN_DOCKER=1 for the docker compose deployment.
set -euo pipefail
source "$(dirname "$0")/mongo_tools.sh"

FILE="$1"
TARGET="${2:-$DB}"
if [ "$TARGET" = "$DB" ]; then
  read -r -p "This replaces every record in '$DB' with $FILE. Type yes to continue: " answer
  [ "$answer" = "yes" ] || exit 1
fi
mongo_tool mongorestore --quiet --drop --archive --gzip --nsFrom "$DB.*" --nsTo "$TARGET.*" < "$FILE"
echo "Restored $FILE into $TARGET"
