#!/usr/bin/env bash
# Backup the RMH HCTM UKM PostgreSQL database. Run on the host or inside the compose network.
set -euo pipefail

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"
FILE="${BACKUP_DIR}/rmh_hctm_${TIMESTAMP}.sql.gz"

if [[ -n "${DATABASE_URL:-}" ]]; then
  echo "Using DATABASE_URL for backup"
fi

CONTAINER="${POSTGRES_CONTAINER:-$(docker compose ps -q postgres)}"
if [[ -z "$CONTAINER" ]]; then
  echo "Postgres container not found. Start the stack or set POSTGRES_CONTAINER." >&2
  exit 1
fi

docker exec -e PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}" "$CONTAINER" \
  pg_dump -U "${POSTGRES_USER:-rmh}" -d "${POSTGRES_DB:-rmh_hctm}" --clean --if-exists \
  | gzip > "$FILE"

echo "Backup written to $FILE"
