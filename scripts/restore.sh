#!/usr/bin/env bash
# Restore a gzipped pg_dump created by scripts/backup.sh
set -euo pipefail

ARCHIVE="${1:-}"
if [[ -z "$ARCHIVE" || ! -f "$ARCHIVE" ]]; then
  echo "Usage: $0 backups/rmh_hctm_YYYYMMDDTHHMMSSZ.sql.gz" >&2
  exit 1
fi

CONTAINER="${POSTGRES_CONTAINER:-$(docker compose ps -q postgres)}"
if [[ -z "$CONTAINER" ]]; then
  echo "Postgres container not found." >&2
  exit 1
fi

echo "Restoring $ARCHIVE into ${POSTGRES_DB:-rmh_hctm}. This replaces existing data."
gunzip -c "$ARCHIVE" | docker exec -i -e PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}" "$CONTAINER" \
  psql -U "${POSTGRES_USER:-rmh}" -d "${POSTGRES_DB:-rmh_hctm}"

echo "Restore complete."
