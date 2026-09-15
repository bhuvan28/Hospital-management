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

Dashboard finance totals are computed in a dedicated service (no donor or sponsor names). Viewers receive those aggregates plus occupancy/census counts, never current occupants or waitlist identities. Donation category lookups require finance or settings permission. Room check-in follows the live occupant, not only the stored room status flag. Occupancy-trend reports accept monthly or annual grain. Census reports accept optional ward, state, gender and status filters. Petty-cash and donation updates validate uniqueness and category existence. Production Compose binds the API to localhost only.

Stay history is readable via `GET /api/stays` and `GET /api/rooms/{id}`. Room responses include a derived `occupancy_status` (open stay or maintenance), independent of a stale stored flag. Waitlist enrolment is rejected when the family already occupies a room. Patient and finance audit snapshots include guardians, assessment, and the full set of edited fields. Report date ranges with start after end return 422. Audit rows are immutable in application code as well as via the PostgreSQL trigger. Length-of-stay reports include families still in-house, measured to the report end date. Occupancy Excel exports use the operational heading Occupancy Rate. The room board exposes stay history and a check-out date form.

Duty officers can check a waiting family into a vacant room from the waiting list; check-in still auto-resolves the open waitlist row. `GET /api/rooms` accepts `occupancy_status` so the waitlist check-in picker lists vacant rooms only. Authenticated users can change their own password (`POST /api/auth/change-password`); the audit row records `password_changed` and never stores the secret. Changing a password increments `session_epoch` so previous JWTs stop working. Administrators cannot deactivate themselves or remove the last active admin. The room board filters by live occupancy, searches room/patient/registration, and refreshes every 30 seconds. Donation summaries include monthly category and type totals and respect list date/type/category filters. Finance ledgers export to Excel for donations, petty cash, and meal sponsorships. Occupancy and census Excel files use staff-facing headings. The operations dashboard refreshes every 30 seconds. Expired API sessions redirect to login. Dashboard check-out tables show the check-out date.

Login, failed login, and logout write audit rows without passwords. Five failed sign-ins for the same email lock that address for 15 minutes. Ward/clinic, state, and donation-category changes are audited. Patient list/detail include derived `house_status` (`in_house` / `waiting` / `none`) and optional `room_number`. Check-in and waitlist pickers use `available_for=check_in|waitlist` so an occupying family is not offered again. Social workers can search by NRIC or guardian details; duty officers cannot. Administrators can rename lookups and edit a user's name or email. Tablet widths collapse the sidebar behind a menu button. Duty officers can export the room board and waiting list to Excel. Finance officers can export donation, petty cash, and meal-sponsorship ledgers. Audit Excel export is metadata only. Waiting-list resolve accepts optional remarks.

## Open questions (not invented)

1. Exact social-worker room-fee assessment fields — isolated JSON + notes section
2. Patient data retention period — not implemented as auto-purge
3. Final hosting location — compose is host-agnostic
4. Meaning/expansion of PPK and PK — not hardcoded as business rules
5. Whether donations/petty cash later link to families — v1 is house-level only
