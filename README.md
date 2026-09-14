# RMH HCTM UKM Operations Platform

Self-hosted operations platform for **Ronald McDonald House** at **Hospital Canselor Tuanku Muhriz (HCTM), UKM**.

This is not a generic hospital ERP. It covers family intake, the live room board, waiting list, occupancy, house-level donations, petty cash, meal sponsorship, operational reports, and an immutable audit log.

Patient data, NRIC, diagnosis, guardian details and financial records stay on infrastructure you control. There is no Auth0, Firebase, Clerk, Supabase, external analytics, or external AI.

## Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js / React / TypeScript |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, Alembic |
| Database | PostgreSQL |
| Auth | Self-hosted JWT (httpOnly cookie + Bearer), Argon2id password hashing |
| Exports | Excel (openpyxl), PDF (ReportLab) |
| Deploy | Docker Compose |

## Repository layout

```
backend/     FastAPI app, Alembic migrations, pytest
frontend/    Next.js UI
scripts/     backup, restore, ensure-postgres
docs/        implementation notes
```

## Local development

### Option A — Docker Compose (recommended)

```bash
cp .env.example .env
# Edit .env: set SECRET_KEY, POSTGRES_PASSWORD, SEED_ADMIN_PASSWORD
docker compose -f docker-compose.dev.yml up --build
```

- UI: http://localhost:3000
- API / OpenAPI: http://localhost:8000/api/docs
- Health: http://localhost:8000/api/health

On first start the development stack runs migrations and loads **DEVELOPMENT ONLY** seed data.

The Compose **backend** service uses hostname `postgres` (the compose service name). A `.env` copied for host-side processes must keep `POSTGRES_HOST=localhost`. Using `postgres` outside the compose network causes SQLAlchemy/psycopg to fail with `Name or service not known`.

### Option B — Manual

PostgreSQL 16 and Python 3.12+ required. You can start only the database with Compose (`docker compose -f docker-compose.dev.yml up -d postgres`) and run the API on the host; still use `localhost`, not `postgres`.

```bash
# Database (native PostgreSQL, or the compose postgres service published on 5432)
createdb rmh_hctm
# or: ./scripts/ensure-postgres.sh

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=postgresql+psycopg://rmh:PASSWORD@localhost:5432/rmh_hctm
export SECRET_KEY=generate-a-long-random-string
export SEED_ON_STARTUP=true
export APP_ENV=development
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (another terminal)
cd frontend
npm install
export API_INTERNAL_URL=http://localhost:8000
npm run dev
```

## DEVELOPMENT ONLY seed accounts

These users exist only when `SEED_ON_STARTUP=true` (development). **Do not use them in production. Change every password before any shared environment.**

| Role | Email | Password |
| --- | --- | --- |
| Admin | admin@rmh.example.com | `DevAdmin!2026` (or `SEED_ADMIN_PASSWORD`) |
| Duty Officer | duty@rmh.example.com | `DevDuty!2026` |
| Social Worker | social@rmh.example.com | `DevSocial!2026` |
| Finance | finance@rmh.example.com | `DevFinance!2026` |
| Viewer | viewer@rmh.example.com | `DevViewer!2026` |

Seed also creates 18 vacant rooms (`01`–`18`), Malaysian states/regions, HCTM-oriented ward/clinic lookups, and donation categories. When `SEED_DEMO_RECORDS=true`, a few clearly fictional families, one sample stay, one waitlist row, and house-level finance samples are added so local dashboards are not empty. No real patient data is seeded.

## Roles and permissions

Permissions are enforced on **every protected API**. Hiding a navigation item is not authorization.

| Role | Access |
| --- | --- |
| Duty Officer / Front Desk | Room board, check-in/out, waiting list, ops dashboard. Cannot open donations or petty cash. Does not receive NRIC or diagnosis. |
| Admissions / Social Worker | Create and edit patient intake, including the isolated assessment section. |
| Operations Manager / Admin | Full access, including users, settings and audit log. |
| Finance / Donations Officer | Donations, petty cash, meal sponsorship. Cannot write patient records. |
| Read-only / Reporting Viewer | Aggregated reports only. No PII. |

## Occupancy

Occupancy rate is computed by the backend from **active room stays**, not from a typed percentage:

`occupied rooms / total rooms * 100`

Occupied rooms are rooms with an open stay (`check_out_date` is null). Users cannot type a percentage. Check-in/out run in a database transaction with row locks. A room cannot have two active occupants. A family cannot occupy two rooms at once. Check-in is allowed only when the room has no active occupant and is not in maintenance. Occupancy is computed from open stays, not from a typed percentage or a stale status flag. Database unique indexes and row locks protect concurrent check-in. Occupied rooms cannot be marked vacant or placed in maintenance without checking the occupant out. A family that already occupies a room cannot be added to the waiting list. Duty officers can check a waiting family into a vacant room from the waiting list; that check-in auto-resolves the waitlist row. Room APIs expose a derived occupancy status (`GET /api/rooms?occupancy_status=vacant|occupied|maintenance`) and stay history, including after check-out. The live room board can be filtered and refreshes every 30 seconds. Authenticated users can change their own password; administrators cannot deactivate themselves or remove the last active admin. Length-of-stay reports include families still in-house, measured to the report end date. Occupancy Excel exports use the operational heading Occupancy Rate. PostgreSQL also rejects updates and deletes against `audit_logs`; the application layer raises on audit mutation as well. Production Compose publishes PostgreSQL and the API on localhost only; the UI proxies backend traffic.

## Social worker assessment

Exact room-fee assessment fields are **not confirmed** in the PRD. The intake form has a clearly separated assessment section with notes, optional `assessed_fee_amount`, and a JSON `payload` for future fields. No fee formula is invented.

## Reports and exports

Reports run on the server with date filters:

1. Daily occupancy rate
2. Monthly/annual occupancy trend
3. Patient census
4. Census by gender
5. Census by ward
6. Census by state
7. New vs returning
8. Guardian/sibling totals
9. Length-of-stay breakdown
10. Room rental income (sum of optional assessed amounts only)
11. Donation summary
12. Petty cash budget vs actual
13. Admission summary

Excel and PDF export: `GET /api/reports/{report}/export?format=xlsx|pdf`

## Database migrations

```bash
cd backend
alembic upgrade head          # apply
alembic downgrade -1          # roll back one revision
alembic revision -m "msg"     # new revision
```

The production backend container runs `alembic upgrade head` before serving traffic.

## Seed data

```bash
export SEED_ON_STARTUP=true   # development compose does this
# or
./scripts/seed.sh
```

Never seed real patient information.

## Backup and restore

```bash
export POSTGRES_PASSWORD=...
./scripts/backup.sh                 # writes backups/rmh_hctm_<timestamp>.sql.gz
./scripts/restore.sh backups/rmh_hctm_YYYYMMDDTHHMMSSZ.sql.gz
```

PostgreSQL data is stored in the `postgres_data` Docker volume.

## Production deployment

1. Copy `.env.example` to `.env` on the host.
2. Set a long random `SECRET_KEY`, a strong `POSTGRES_PASSWORD`, `APP_ENV=production`, `COOKIE_SECURE=true`, `SEED_ON_STARTUP=false`.
3. Put the UI origin in `CORS_ORIGINS` (HTTPS).
4. `docker compose up --build -d`
5. Place TLS termination (nginx, Caddy, or a reverse proxy) in front of port 3000. PostgreSQL is bound to `127.0.0.1:5432` in the production Compose file and should not be exposed on a public interface.
6. Create the first admin through a controlled seed or SQL only on a private network, then disable seed.
7. Schedule `scripts/backup.sh` (for example daily cron) and store archives offline.

### Updating

```bash
git pull
docker compose up --build -d
```

Migrations run automatically on backend start.

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

Coverage includes login, disabled users, leftover tokens after deactivation or password change, password change (wrong current password rejected, secrets never audited), login/logout audit without secrets, login lockout after repeated failures, last-admin protection, RBAC (Duty Officer vs finance, Finance vs patients, Viewer vs PII/finance lists, Social Worker vs finance/check-in), patient CRUD/search including NRIC/guardian search scoped to sensitive readers, house status (in house / waiting), room check-in/out, occupancy math and derived occupancy status, waitlist days, waitlist resolve remarks, waitlist-to-check-in resolution, vacant-room filter, occupied-patient rejection, donation/petty-cash/meal totals and monthly category summaries, all 13 report slugs, inverted date-range rejection, annual occupancy trend, Excel/PDF export, room-board/waitlist/audit operational Excel exports, stay history, lookup audit, and audit records including guardians/assessment and immutable logs.

Frontend production build:

```bash
cd frontend
npm install
npm run build
```

## PDPA / security notes

- Argon2id password hashing; passwords never written to the audit log
- JWT in httpOnly cookies plus a double-submit CSRF cookie (`X-CSRF-Token`) on mutating cookie-authenticated requests; Bearer tokens skip CSRF for API clients
- Password changes and admin password resets increment `session_epoch`, so leftover tokens stop working
- Login, failed login, and logout are written to the audit log without passwords or secrets
- Login rate-limited (5/minute) and temporarily locked after five failed attempts for the same email
- Social workers and administrators can search intake by NRIC or guardian name/contact; duty officers cannot
- Duty officers can export the live room board and waiting list to Excel. Audit Excel export is metadata only (no before/after snapshots)
- RBAC on the API, not only the UI
- NRIC and diagnosis omitted from responses unless the role has `patients:read_sensitive`
- ORM parameterized queries
- Security headers on API responses
- No secrets in source; configuration is environment-based
- No patient data sent to OpenAI, analytics SaaS, or external auth/logging services

## Open questions (not silently invented)

1. **Exact social-worker room-fee assessment fields** — isolated JSON + notes until confirmed.
2. **Patient data retention period** — no automatic purge in v1.
3. **Final hosting location** — Compose is host-agnostic.
4. **Meaning/expansion of PPK and PK** — not encoded as business rules.
5. **Whether donations/petty cash should later link to families** — v1 is house-level only, as specified.

See `docs/IMPLEMENTATION_PLAN.md` for the build sequence.

## API

FastAPI generates OpenAPI at `/api/docs` and `/api/openapi.json`.

Minimum routes from the PRD are implemented, plus auth, users, lookups, occupancy summary, dashboard, remaining reports, and audit.
