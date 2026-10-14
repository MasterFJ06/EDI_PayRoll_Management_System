# EPMS Development and Operations Runbook

This runbook covers local development and the repository's isolated CI test
workflow. It is not a production deployment guide. Do not point these setup
steps at a shared or production database.

## Prerequisites

- Python 3.12 or later (the MySQL runtime workflow uses Python 3.12).
- MySQL 8 for local database-backed development. The CI workflow uses an
  ephemeral MySQL 8.0 service.
- Git and a terminal. Commands below use Windows PowerShell unless noted.
- A local MySQL account with the privileges required for the operation. The
  repository does not provision MySQL accounts or grants.

## Create the Python environment

From the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, either follow the local organization policy
for script execution or invoke the environment directly, for example:
`.\.venv\Scripts\python.exe -m pytest -q tests\unit`.

## Configure the application

Create a private local environment file:

```powershell
Copy-Item .env.example .env
```

Set the values in `.env` for the local environment. `DATABASE_HOST`,
`DATABASE_PORT`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, and
`JWT_SECRET_KEY` are required by the settings model. `JWT_ALGORITHM`,
`ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`,
`PAYROLL_WORKER_COUNT`, `APP_NAME`, `APP_ENV`, `DEBUG`, and `CORS_ORIGINS`
have defaults or example values in the repository. Generate a unique local
signing secret rather than reusing an example or production value:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Keep `.env` private; it is ignored by Git. Do not paste credentials into source
files, tickets, logs, or committed documentation. Restart the application after
changing settings because configuration is cached when the process starts.

**Database-name mismatch to correct:** `.env.example` currently names the
database `employee_payroll`, while `database/schema.sql` explicitly creates
and selects `employee_payroll_db`. For a fresh initialization using that
snapshot, set `DATABASE_NAME=employee_payroll_db` in `.env`. The schema file
does not accept a database name parameter.

## Initialize a fresh local development database

Only do this against a dedicated, empty local development database/instance.
First verify the host and database name in `.env` and ensure the fixed name
`employee_payroll_db` is not used by another project or contains data that must
be preserved. The schema snapshot creates/selects that fixed database and
creates its tables; it is not a reset script and this repository provides no
safe database wipe command. Stop if the target is not known to be empty and
disposable.

From the repository root, an administrator can import the snapshot from
PowerShell using `cmd.exe` redirection (the SQL itself contains its `CREATE
DATABASE` and `USE` statements):

```powershell
cmd.exe /d /c "mysql --host=127.0.0.1 --port=3306 --user=YOUR_LOCAL_DB_ADMIN --password < database\schema.sql"
```

Replace the account placeholder with a locally provisioned database account;
the client prompts for its password. Confirm the command targets the intended
local MySQL instance before entering credentials. This imports the current
34-table authoritative snapshot in `database/schema.sql`.

Apply the RBAC catalog seed separately after the schema exists:

```powershell
cmd.exe /d /c "mysql --host=127.0.0.1 --port=3306 --user=YOUR_LOCAL_DB_ADMIN --password --database=employee_payroll_db < database\seed.sql"
```

`database/seed.sql` uses `INSERT IGNORE` for its role, permission, and
role-permission catalog entries. It creates neither users nor user-role
assignments, and it does not remove extra existing grants. This seed is not a
database reset or a general production provisioning procedure.

### Migration order and limits

For a **fresh database**, import `database/schema.sql` and then, if needed,
`database/seed.sql`. Do not run Alembic over the current schema snapshot: it
already contains the structures represented by the repository's migrations,
including `refresh_tokens`.

For an **existing database**, do not infer its migration state from its table
names. Back it up, identify its actual Alembic revision and schema/data
preconditions, then apply the repository migration chain in order with
`alembic upgrade head` only when that starting state is confirmed. The current
chain is `20261007_01` → `20261007_02` → `20261010_01` → `20261013_01`.
Revision `20261007_01` requires the pre-existing authoritative base tables. If
it finds existing Leave Types, it requires an owner-approved mapping for every
ID, supplied using Alembic's `leave_type_mapping` argument as documented in
that migration; payroll treatment must not be inferred. This repository does
not provide a clean-install baseline migration or an automated backup/restore
procedure. When the starting state is unclear, stop and obtain database-owner
guidance rather than running a migration.

## Start the API and check it

With `.env` configured and the database reachable:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Health endpoint: `GET http://127.0.0.1:8000/api/v1/health`

The health endpoint currently returns a static API process status. It does not
check MySQL connectivity or database readiness, so a healthy response is not a
database health check.

## Authentication and demonstration identities

There are no default demo usernames or passwords in the repository. Create a
synthetic, unique local account through `POST /api/v1/auth/register` in Swagger
or an HTTP client, using a non-real email and a private password of at least
eight characters. Registration creates an active user but does not assign a
role. Authenticate through `POST /api/v1/auth/login`; it returns an access JWT
and an opaque refresh token. Use the access token as a Bearer token for
protected requests. Refresh credentials are secrets: do not log, persist in
plaintext outside the client that needs them, or include them in screenshots.

### Persisted roles and permissions

On a clean schema after applying `database/seed.sql`, the seed assigns:

| Role | Seeded permissions |
| --- | --- |
| `Payroll Administrator` | `compensation.write`, `payroll.run.create`, `payroll.run.read`, `payroll.run.process`, `payroll.run.retry`, `payroll.run.recover`, `payroll.run.finalize`, `payroll.payslip.create`, `report.payroll.read` |
| `HR Administrator` | `report.employee.read`, `report.attendance.read`, `report.leave.read`, `workforce.leave.request.create_for_others`, `workforce.leave.balance.manage_for_others` |

These are persisted `role_permissions` grants. The API checks the current
user-role and role-permission rows; only active roles grant permissions.
Authentication and authorization are enforced by backend dependencies, not by
Swagger or frontend visibility. The catalog also contains permissions that
this seed does not grant to either role, including organization calendar,
Leave Type/lifecycle, and overtime-policy operations. Do not assume a role has
an unlisted permission. Existing database grants may differ from a clean seed
because the seed does not revoke extra rows.

The seed does not assign any user to a role. There is no user-role assignment
API or supported first-administrator bootstrap flow in the current repository.
The `user_roles` table requires an `assigned_by_user_id`; do not self-assign a
privileged role, treat registration as role provisioning, or run ad hoc grant
SQL without a separately authorized and auditable local bootstrap process. A
normal registered account is suitable for authentication checks; requests to
permission-protected operations should receive HTTP 403 until an authorized
role grant exists. Persisted-RBAC integration coverage provisions its own
isolated test records and is not a demo-account setup procedure.

## Run tests

Use the repository's pinned dependencies and run commands from its root:

```powershell
python -m pytest -q tests/unit
python -m pytest -q tests/api
```

The full unit suite does not establish live MySQL behavior. The API tests use
the project's API test setup and may depend on the supported Python/platform
TestClient environment.

For real-MySQL runtime validation, use the manually triggered **MySQL Payroll
Runtime Validation** workflow in `.github/workflows/mysql-payroll-runtime.yml`.
It provisions ephemeral MySQL 8, prepares/imports the authoritative schema
snapshot, sets `EPMS_REQUIRE_MYSQL_TESTS=1`, and runs the strict serial
integration inventory with zero-skip enforcement, database-safety tests, and
the full unit suite. It does not apply Alembic over the imported snapshot. Do
not point this workflow or local integration tests at a development or
production database.

For a disposable browser/API smoke run, dispatch **EPMS Frontend and Backend
Smoke Test** in `.github/workflows/frontend-backend-smoke.yml`. It starts its
own ephemeral MySQL 8 service, rewrites the schema only through
`scripts/prepare_mysql_test_schema.py`, verifies the selected test database is
empty before catalog seeding, and starts FastAPI and Vite against that exact
target. A test-only script registers unique accounts through the normal API,
assigns only the seeded HR and Payroll roles using persisted `user_roles`
records, and writes one-time test credentials outside the checkout under the
runner's temporary directory. No role-assignment endpoint or production
bootstrap is added. The job does not upload screenshots, traces, videos, or
fixture credentials, and its ephemeral service is discarded when the job ends.

The current browser suite validates login, automatic refresh after access-token
expiry, logout revocation, invalid credentials, 401/403 behavior, employee
creation, own/cross-employee Leave authorization, and Compensation write
authorization. It does not process or finalize Payroll: that requires the full
calendar, overtime policy, compensation, and workforce fixture used by the
separate strict MySQL integration suite. Payroll finalization and finalized
payroll report/payslip browser flows remain untested by this smoke workflow.

## Run the frontend

The React/Vite application lives in `frontend/`. From the repository root,
configure its API URL and start the development server:

```powershell
Set-Location frontend
Copy-Item .env.example .env.local
npm install
npm run dev -- --host localhost
```

`VITE_API_BASE_URL` is the API root, defaulting to
`http://127.0.0.1:8000/api/v1`. The backend's configured default CORS origin is
`http://localhost:5173`; keep Vite on that origin unless the backend's
`CORS_ORIGINS` is deliberately configured for another local origin. The API
must be started separately as described above.

Sign in with an existing authorized account. Registration does not assign a
role, and this frontend does not provide administrator provisioning. The
dashboard checks the API process health endpoint, but there is no dashboard
summary or activity-feed endpoint, so those metrics are shown as unavailable
rather than fabricated.

Frontend checks available from this project are:

```powershell
npm run typecheck
npm run build
```

Access and refresh tokens are held in browser memory only. Reloading the page
requires signing in again. This avoids persisting bearer credentials in
browser storage, but does not eliminate the risk of a compromised browser
runtime or cross-site scripting. The API remains responsible for authorization.

## Common troubleshooting

- **Unknown database / cannot connect:** check that MySQL 8 is running, the
  host and port match `.env`, `DATABASE_NAME` is `employee_payroll_db` for the
  snapshot above, and the configured account has access. Do not respond by
  dropping or recreating an unverified database.
- **Schema already exists or import conflicts:** stop; the snapshot import is
  for a fresh target and does not reset existing data. Use a verified
  disposable instance or obtain database-owner guidance.
- **Migration reports missing base tables or Leave Type mapping:** verify the
  database's actual starting revision and obtain an explicit owner-approved
  `PAID`/`UNPAID` mapping for every existing Leave Type. Do not guess values.
- **HTTP 401:** authenticate, send the access token as `Authorization: Bearer
  <token>`, and confirm the user remains active.
- **HTTP 403:** authentication succeeded but the user's persisted roles do not
  grant the required permission. Check the intended seed and authorized role
  provisioning; do not weaken the endpoint's permission dependency.
- **Health succeeds but API database operations fail:** `/api/v1/health` is
  process-only; test the configured database connection separately through a
  normal application operation or the isolated MySQL workflow.
- **Settings changes have no effect:** restart Uvicorn so cached settings are
  reloaded.
- **Windows TestClient appears stalled:** do not report a pass or silently skip
  the tests. Use the supported CI workflow for runtime evidence and report the
  local run as incomplete.

## Verified operational gaps

- `.env.example` and `database/schema.sql` currently use different database
  names; the runbook calls out the required match but the example file itself
  has not been changed.
- User registration is available, but role assignment and first-operator
  bootstrap are not. A trusted provisioning workflow needs separate design
  before administrators can be safely onboarded through the application.
- No production deployment, backup/restore, database-account provisioning, or
  database-readiness health-check procedure is defined by this repository.
