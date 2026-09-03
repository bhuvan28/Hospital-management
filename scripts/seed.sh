#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../backend"
python - <<'PY'
from app.database import SessionLocal
from app.seed import run_seed
db = SessionLocal()
try:
    run_seed(db)
finally:
    db.close()
print("Development seed complete.")
PY
