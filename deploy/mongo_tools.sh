# Shared by the backup scripts: which database, and where the MongoDB tools run.
DB="${GPA_TRACKER_DB:-gpa_tracker}"

# Runs a MongoDB tool (mongodump, mongorestore, mongosh) here, or inside the compose "mongo" container.
mongo_tool() {
  if [ -n "${IN_DOCKER:-}" ]; then docker compose exec -T mongo "$@"; else "$@"; fi
}
