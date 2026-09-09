#!/usr/bin/env bash
# Make PostgreSQL reachable on localhost:5432 with the development role/database.
# Prefers Docker Compose when the daemon is available; otherwise uses native PostgreSQL.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-rmh_hctm}"
POSTGRES_USER="${POSTGRES_USER:-rmh}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-rmh_dev_only}"

server_accepts_connections() {
  if command -v pg_isready >/dev/null 2>&1; then
    pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" >/dev/null 2>&1
    return $?
  fi
  (echo >/dev/tcp/"$POSTGRES_HOST"/"$POSTGRES_PORT") >/dev/null 2>&1
}

wait_for_server() {
  local tries="${1:-30}"
  local i
  for i in $(seq 1 "$tries"); do
    if server_accepts_connections; then
      return 0
    fi
    sleep 1
  done
  return 1
}

app_can_connect() {
  command -v psql >/dev/null 2>&1 || return 1
  PGPASSWORD="$POSTGRES_PASSWORD" psql \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -c "SELECT 1" >/dev/null 2>&1
}

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1 && [[ -f docker-compose.dev.yml ]]; then
  docker compose -f docker-compose.dev.yml up -d postgres
  if wait_for_server 40 && app_can_connect; then
    echo "PostgreSQL is ready via Docker Compose at ${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
    exit 0
  fi
  echo "Docker Compose postgres started but the app role cannot connect yet; trying native PostgreSQL." >&2
fi

if ! command -v psql >/dev/null 2>&1 && ! command -v pg_isready >/dev/null 2>&1; then
  echo "PostgreSQL client tools are not installed and Docker is unavailable." >&2
  echo "Install PostgreSQL 16+ (or Docker) and re-run $0." >&2
  exit 1
fi

if command -v pg_lsclusters >/dev/null 2>&1; then
  while read -r version name port status _; do
    if [[ "${status:-}" == "down" ]]; then
      sudo pg_ctlcluster "$version" "$name" start || true
    fi
    POSTGRES_PORT="${port:-$POSTGRES_PORT}"
  done < <(pg_lsclusters --no-header || true)
elif command -v service >/dev/null 2>&1; then
  sudo service postgresql start || true
fi

wait_for_server 40 || {
  echo "PostgreSQL did not become ready on ${POSTGRES_HOST}:${POSTGRES_PORT}." >&2
  exit 1
}

if command -v sudo >/dev/null 2>&1 && id -u postgres >/dev/null 2>&1; then
  sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${POSTGRES_USER}') THEN
    CREATE ROLE ${POSTGRES_USER} LOGIN PASSWORD '${POSTGRES_PASSWORD}' SUPERUSER;
  ELSE
    ALTER ROLE ${POSTGRES_USER} WITH LOGIN SUPERUSER PASSWORD '${POSTGRES_PASSWORD}';
  END IF;
END
\$\$;
SELECT 'CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${POSTGRES_DB}')\gexec
SQL
fi

if app_can_connect; then
  echo "PostgreSQL is ready at ${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
  exit 0
fi

echo "PostgreSQL is running but role '${POSTGRES_USER}' cannot connect to '${POSTGRES_DB}'." >&2
exit 1
