# Implementation Plan — RMH HCTM UKM Operations Platform

This plan follows the PRD as the source of truth. It is not a generic hospital ERP.

## Product

Self-hosted operations platform for Ronald McDonald House at Hospital Canselor Tuanku Muhriz (HCTM), UKM:

- Family/patient intake (Social Worker)
- Live room board and check-in/out (Duty Officer)
- Waiting list and occupancy (computed, never manually entered)
- House-level donations, petty cash, meal sponsorship (Finance)
- Role-appropriate dashboards and operational reports
- Admin user management and immutable audit log

Patient data, NRIC, diagnosis, guardian details, and financial records stay on self-hosted infrastructure. No Auth0/Firebase/Clerk/Supabase, no external analytics, no external AI.

## Stack

| Layer | Choice |
| --- | --- |
| Frontend | Next.js (App Router), React, TypeScript |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2, Alembic |
| Database | PostgreSQL |
| Auth | Self-hosted JWT in httpOnly cookies + Bearer, Argon2id hashing |
| Exports | openpyxl (Excel), ReportLab (PDF) |
| Deploy | Docker Compose (frontend, backend, postgres) |

## Repository layout

```
backend/     FastAPI application, Alembic, tests
frontend/    Next.js UI
scripts/     backup, restore, seed helpers
docs/        PRD notes and open questions
```

## Build order

1. **Phase 0 — Foundation**: compose, env, health, logging, README
2. **Models + migrations + seed**: PRD entities, FKs, 18 rooms, lookups
3. **Auth + RBAC**: login/logout/me, users, permission dependencies
4. **Patient intake**: CRUD, search/filter, sensitive-field masking, audit
5. **Rooms + occupancy**: board, transactional check-in/out, occupancy math
6. **Waiting list**: days waited from dates
7. **Dashboard**: live queries, role-specific payloads
8. **Reports + Excel/PDF**
9. **Donations, petty cash, meal sponsorship**
10. **Audit log (admin, read-only)**
11. **Tests** covering the PRD acceptance criteria
12. **Docker hardening + documentation**

## RBAC (enforced on every protected API)

| Role | Can | Cannot |
| --- | --- | --- |
| Duty Officer | Rooms, stays, waitlist, ops dashboard, limited patient identity for occupancy | Donations, petty cash, NRIC/diagnosis, user admin |
| Social Worker | Create/edit patient intake, guardians, assessment section | Finance modules, user admin |
| Admin | Full access | — |
| Finance | Donations, petty cash, meals, finance reports | Patient write, NRIC/diagnosis |
| Viewer | Aggregated reports only | Any PII, mutations |

Hiding a nav item is never treated as authorization.

Cookie-authenticated mutations require a matching `X-CSRF-Token` header. Bearer API clients skip CSRF.

A room and a patient may each have only one open stay. Concurrent check-in is rejected by `SELECT … FOR UPDATE` plus unique partial indexes. Occupancy rate is occupied active stays / total rooms. Occupied rooms cannot be marked vacant without checkout.

Finance write actions (donations, petty cash, meals) are permission-gated in the UI and still enforced on the API. Meal sponsorships and donations support list filters, PATCH, and DELETE. Petty cash entries can be edited and deleted. Administrators can rename or delete unused rooms. The social-worker assessment JSON payload is preserved on edit. Audit rows are immutable in PostgreSQL.

## Open questions (not invented)

1. Exact social-worker room-fee assessment fields — isolated JSON + notes section
2. Patient data retention period — not implemented as auto-purge
3. Final hosting location — compose is host-agnostic
4. Meaning/expansion of PPK and PK — not hardcoded as business rules
5. Whether donations/petty cash later link to families — v1 is house-level only
