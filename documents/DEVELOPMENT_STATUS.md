# EPMS Development Status

Last documented milestone:

Leave Management Phase 2 API implementation, automated verification, Swagger review, and authenticated live smoke test completed.

---

# Completed

## Identity & Access Management

Status: COMPLETE

Implemented:

- user registration
- authentication
- password hashing
- JWT access token
- current-user authentication dependency
- reusable database-backed role/permission authorization dependency
- user repository
- refresh-token infrastructure
- centralized error handling

Security:

- Argon2id password hashing
- JWT access tokens
- active-user validation
- persisted user-role and role-permission checks; inactive roles grant no permissions
- protected API endpoints

The seed catalog defines the `Payroll Administrator` role and the granular payroll
permissions. It does not assign any user to that role. Payroll authorization currently
supports `payroll.run.create` and `payroll.run.read`; no Payroll API operations are
implemented by this prerequisite.

---

## Organization Management

Status: COMPLETE

Implemented:

- Department domain entity
- Designation domain entity
- Department repository
- Designation repository
- Department service
- Designation service
- API endpoints
- request/response schemas
- domain tests
- service tests
- repository tests
- API tests

---

## Employee Management

Status: COMPLETE

Implemented:

- Employee domain entity
- Employee ORM model
- Employee repository
- Employee application service
- employee request/response schemas
- employee API endpoint
- employee validation
- department validation
- designation validation
- user linkage validation
- manager validation
- tests

Business rule:

An employee cannot be their own manager.

---

## Attendance Management

Status: COMPLETE

Implemented:

- Attendance domain entity
- Attendance ORM model
- Attendance repository
- Attendance application service
- Attendance request/response schemas
- attendance API endpoint
- employee existence validation
- duplicate employee/date validation
- check-in/check-out validation
- tests

Attendance statuses:

- PRESENT
- ABSENT
- HALF_DAY
- ON_LEAVE
- HOLIDAY

Database uniqueness:

`(employee_id, attendance_date)`

---

## Leave Management — Phase 1

Status: CORE BACKEND LAYERS COMPLETE (API NOT IMPLEMENTED)

Implemented:

- LeaveType, LeaveBalance, and LeaveRequest domain entities and schema-backed rules
- SQLAlchemy models matching the existing leave table definitions
- Leave type, balance, and request repositories
- application request/response schemas and create services
- Unit of Work repository integration
- domain, application, and repository tests

API endpoints, reporting, and payroll integration are not part of this phase.

Verification:

- 38 focused Leave Management tests passed
- 166 full-suite tests passed
- One existing Starlette/httpx test-client deprecation warning remains

---

## Leave Management — Phase 2 (API)

Status: COMPLETE

Implemented:

- authenticated `POST /api/v1/leave-types`
- authenticated `POST /api/v1/leave-balances`
- authenticated `POST /api/v1/leave-requests`
- generated OpenAPI/Swagger operations using the Phase 1 request/response schemas
- API tests for authentication, successful creation, request validation, and business-rule failures

Verification:

- 22 Leave API tests passed
- 61 focused Leave Management tests passed
- 189 full-suite tests passed
- Swagger UI loaded and displayed all three protected Leave Management operations
- Live Swagger UI and generated OpenAPI were verified
- Synthetic development user ID 3 registered and authenticated through the API
- Synthetic leave type ID 1 created; repeating its code returned HTTP 409

The live smoke test added only the synthetic account and one synthetic Leave Type. Existing development records were not modified or deleted.

---

## Compensation / Salary Management — Phase 1 (Core Backend Layers)

Status: COMPLETE (API NOT IMPLEMENTED)

Implemented for the five authoritative Compensation tables:

- SalaryStructure, SalaryComponent, SalaryRevision, SalaryRevisionComponent, and EmployeeSalaryAssignment domain entities
- schema-aligned SQLAlchemy models, constraints, indexes, defaults, timestamps, and foreign-key behavior
- five Compensation repository contracts and SQLAlchemy repositories
- request/response schemas and create services for structures, components, revisions, revision components, and employee salary assignments
- Unit of Work integration using the existing shared SQLAlchemy session
- domain, application, repository, and Unit of Work tests

Deferred because no authoritative rule defines the behavior:

- salary calculation and interpretation of configured components
- revision or assignment overlap rules
- effective-date rules beyond the schema's end-date checks
- percentage ceilings or payroll calculation behavior

Payroll processing, Compensation API endpoints, and frontend integration are not part of this phase. `database/schema.sql` was not modified and no migration was created.

Verification:

- 60 Compensation-focused tests passed
- 44 affected existing Employee, Attendance, Leave, and Unit of Work tests passed
- 249 full-suite tests passed
- One existing Starlette/httpx test-client deprecation warning remains

---

## Compensation / Salary Management — Phase 2 (API)

Status: COMPLETE

Implemented authenticated create endpoints for salary structures, salary components, salary revisions, salary revision components, and employee salary assignments. The endpoints reuse the Phase 1 request/response schemas, application services, and existing Unit of Work dependency. No list, update, or delete endpoints were added.

Verification:

- 34 Compensation API tests passed
- 94 total Compensation tests passed
- 283 full-suite tests passed
- `/docs` and `/openapi.json` returned HTTP 200; all five authenticated POST operations and their schemas appear in generated OpenAPI
- Live registration/login succeeded for synthetic development user ID 4 (`codex_comp2_a243fc7025ba`)
- Authenticated salary structure creation succeeded with HTTP 201 (synthetic salary structure ID 1)
- Repeating the structure code returned HTTP 409 (`BUSINESS_RULE_VIOLATION`)
- An unauthenticated create returned HTTP 401
- No existing development records were modified or deleted
- One existing Starlette/httpx test-client deprecation warning remains

Payroll processing, calculation semantics, and undefined effective-date overlap rules remain deferred.

---

## Payroll Management — Phase 1 (Core Backend Layers)

Status: CORE BACKEND LAYERS IMPLEMENTED (API NOT IMPLEMENTED)

Implemented for the five authoritative Payroll tables:

- PayrollRun, PayrollResult, PayrollResultComponent, PayrollProcessingIssue, and Payslip domain entities
- SQLAlchemy models for all five tables, with schema-aligned columns, unsigned types, constraints, indexes, defaults, timestamps, foreign-key actions, and InnoDB engine settings
- five Payroll repository contracts and SQLAlchemy repositories using the shared Unit of Work session
- create request/response schemas and application services for payroll runs, supplied payroll results, result components, processing issues, and payslips
- Unit of Work integration, including shared-session commit and rollback behavior
- schema-backed domain validation for allowed status/type values, payroll month/ranges, nonnegative earnings/deductions/components, net salary consistency, calculation order range, and processing-issue resolution consistency
- focused domain, application, ORM mapping, repository, and Unit of Work tests

No payroll earnings or deduction formulas were implemented. A supplied net salary is checked against the schema equation but is not derived. Schema-supported status values are accepted; no status transitions are implemented. No concurrent processing engine was implemented. Cross-record QA rules are undefined; current validation enforces only schema-backed invariants, with broader QA behavior deferred. Attendance and Leave were not integrated because the Payroll schema defines no direct foreign-key relationships to them.

`database/schema.sql` was not modified, no migration was created, no Payroll API or API tests were added, and the frontend was not changed. Existing Compensation implementation was left unchanged.

Verification:

- 31 Payroll-focused tests passed
- 238 existing Identity/security, Employee, Attendance, Leave, and Compensation tests passed
- 314 full-suite tests passed
- SQLAlchemy MySQL DDL was inspected against all five authoritative table definitions
- `git diff --check` passed
- One existing Starlette/httpx test-client deprecation warning remains

---

## Payroll Management — Phase 2A (Payroll Run Creation & Retrieval)

Status: IMPLEMENTED (AUTOMATED VALIDATION PASSED; LIVE MYSQL SMOKE NOT RUN)

Implemented:

- `POST /api/v1/payroll/runs`, authorized by `payroll.run.create`
- `GET /api/v1/payroll/runs/{run_id}`, authorized by `payroll.run.read`
- server-derived `initiated_by_user_id` from the authenticated current user
- Payroll Run response DTOs, duplicate-period conflict handling, and missing-run 404
- atomic Unit of Work commit with rollback on a database unique-period collision

Payroll processing, retry, finalization, calculation, results, issues, and payslip
generation remain unimplemented.

Verification:

- 48 focused Payroll Phase 2A and Phase 1 tests passed
- 338 full-suite tests passed
- Live MySQL smoke test was not performed

---

## Payroll Management — Phase 2B-1 (Run Claim)

Status: IMPLEMENTED (AUTOMATED VALIDATION; LIVE MYSQL SMOKE NOT RUN)

Implemented:

- `POST /api/v1/payroll/runs/{run_id}/process`, authorized by
  `payroll.run.process`
- atomic `CREATED` to `PROCESSING` claim using a conditional database update and
  `started_at` timestamp
- rejection of duplicate or invalid-state claims with HTTP 409; missing runs return
  HTTP 404
- application-level orchestration boundary; employee eligibility is implemented in
  Phase 2B-2 below, with no payroll calculation or generated payroll artifacts
- atomic `PROCESSING` to `FAILED` transition and audit event when an unexpected
  orchestration failure occurs
- processing-started and processing-failed events recorded through ORM mappings for
  the existing `audit_events` and `audit_event_changes` tables, with correlation ID
  where available

No schema or migration changes were made. Payroll calculation, results/components,
processing issues, retry, finalization, worker pools, and payslips remain unimplemented.

Verification:

- Focused processing, API, repository concurrency, Audit mapping, Unit of Work, Payroll
  Phase 1/2A, authorization, and RBAC tests: 50 passed
- 356 full-suite tests passed
- Live MySQL smoke test was not performed; the RBAC seed does not assign a user the
  `Payroll Administrator` role, and no development privilege assignment was made.

---

## Payroll Management — Phase 2B-2 (Employee Eligibility)

Status: IMPLEMENTED (AUTOMATED VALIDATION)

Implemented deterministic internal classification of Employee records against the
calendar month of a Payroll Run. The resolver uses `joining_date` and nullable
`employment_end_date` with inclusive interval overlap, and captures the applicable
employment portion for eligible employee IDs. Non-overlapping employees are explicitly
listed as excluded. The existing Employee repository returns records ordered by
employee ID.

The processing endpoint still returns only the Payroll Run response with status
`PROCESSING`. This phase does not use employment status or employment history for
eligibility and does not add compensation, proration, workforce, QA, result, issue,
retry, finalization, or payslip behavior. An empty population is returned as an empty
eligibility result and does not itself change run state or create an issue.

Verification:

- 83 Payroll-focused tests passed
- 382 full-suite tests passed
- One existing Starlette/httpx test-client deprecation warning remains

---

# Current Test Baseline

At the Attendance milestone:

128 tests passed.

There is currently one warning related to Starlette/httpx test client compatibility.

Do not remove tests because of the warning.

---

# Database Baseline

The development database is:

`employee_payroll_db`

The authoritative schema contains 27 tables.

The database has been successfully initialized.

---

# Real Smoke Test Baseline

The authenticated API chain has been successfully tested.

Known development records include:

- User ID 1
- Department ID 1
- Designation ID 1
- Employee ID 1
- Attendance ID 1

Do not delete these records during normal development unless explicitly instructed.

---

# Git Checkpoints

Known implementation checkpoints:

- `240a226` — Implement employee management module
- `2838e09` — Attendance Management
- `d49d185` — Fix MySQL employee schema constraint

Remote repository:

`https://github.com/Sharvil-tech/Employee-payroll-management-system1.git`

---

# Next Phase

Compensation / Salary Management Phase 2 and Payroll Phases 1, 2A, 2B-1, 2B-2,
and 2B-3 are implemented. Period segmentation, calculation, and later processing
stages remain unimplemented.

---

## Employee Employment Interval — Decision 12A Prerequisite

Status: IMPLEMENTED

Implemented nullable `employees.employment_end_date` as an inclusive employment end
date, with `joining_date` as the inclusive start. Open-ended intervals use a null end
date; same-day intervals are valid; an end before the start is rejected by the Employee
domain model. Current `employment_status` remains independent, and `employment_history`
continues to represent organizational assignment history. Decision 12A established the
employment data model; Payroll eligibility was implemented separately in Phase 2B-2.

The authoritative `database/schema.sql` is updated. The repository has an Alembic
configuration but no existing revision files or migration history; schema changes are
maintained directly in the authoritative SQL file, so no migration revision was added.

Verification: 55 focused Employee domain, service, API, and ORM tests passed; 365 full
suite tests passed. The existing Starlette/httpx test-client deprecation warning
remains.

---

## Payroll Management — Phase 2B-3 (Compensation Snapshot)

Status: IMPLEMENTED (AUTOMATED VALIDATION)

After the atomic `CREATED` to `PROCESSING` claim is committed, processing reloads
the Payroll Run and uses its persisted `started_at` timestamp as the compensation
snapshot boundary. Only employees eligible under Phase 2B-2 are considered.
Applicable assignments and their directly referenced revisions use inclusive
effective-date intervals. Zero or overlapping assignments, missing or ineffective
referenced revisions, and existing-domain-detected invalid component configuration
create OPEN Payroll Processing Issues. OPEN issues are blocking. The immutable
snapshot copies assignment, revision, and component configuration into frozen
application dataclasses.

This phase does not calculate salary amounts, prorate or segment compensation,
integrate attendance/leave/overtime, create Payroll Results, complete the Payroll
Run, retry, or finalize it. It adds no schema, migration, public endpoint, or API
response fields.

Verification:

- 26 focused snapshot, repository, orchestrator, and process API tests passed
- 92 Payroll-focused tests passed
- 95 Compensation-focused tests passed
- 395 full-suite tests passed
- One existing Starlette/httpx test-client deprecation warning remains

---

## Payroll Management — Phase 2B-4 (Period Segmentation)

Status: IMPLEMENTED (AUTOMATED VALIDATION)

The segmentation stage consumes the Phase 2B-2 eligible employee ranges and
Phase 2B-3 compensation snapshot. For each employee with a valid 2B-3 snapshot,
it intersects the employment processing range with each employee salary
assignment and its directly referenced salary revision effective interval.
Inclusive interval boundaries are swept into ordered, non-overlapping segments.
Compensation overlaps, gaps, missing referenced revisions, and invalid component
configuration create OPEN Payroll Processing Issues; no precedence or carry-forward
is applied. Employees already excluded by 2B-2 do not reach segmentation.

No working-day, calendar-payable-day, proration, or salary calculation is performed.
No Payroll Results, segment table, schema change, API endpoint, or response fields
were added. Runs remain in PROCESSING.

Verification:

- 42 focused segmentation, snapshot, repository, orchestrator, and API tests passed
- 110 Payroll-focused tests passed
- 95 Compensation-focused tests passed
- 411 full-suite tests passed
- One existing Starlette/httpx test-client deprecation warning remains

---

## Workforce Architecture — Phase 1 (Schema & Migration Foundation)

Status: IMPLEMENTED; EXISTING-DATA BACKFILL REQUIRES OWNER APPROVAL

Added the five Workforce foundation tables and the three approved columns for
Leave Type payroll treatment, Salary Revision OT-base designation, and nullable
Payroll Result Workforce snapshot JSON. The existing Leave Type create contract
now requires an explicit `PAID` or `UNPAID` treatment. No treatment is inferred
from leave names or descriptions. The migration requires an explicit complete
Leave Type ID-to-treatment mapping when legacy Leave Types exist; it initializes
the OT-base flag to `FALSE` and does not designate any existing component.

No overtime workflow, leave approval/allocation service, Workforce snapshot
orchestration, or Payroll 2B-5 behavior is implemented here.
Payroll Result creation remains valid with a null Workforce snapshot.

## Workforce Architecture — Phase 2 (Work Calendar)

Status: IMPLEMENTED; validation results are recorded with this phase's review.

Implemented the organization-wide immutable Work Calendar version and date
override workflows, date classification and working-day counting services,
RBAC permissions, and audit events. Calendar corrections are blocked whenever
an affected monthly Payroll Run is not `FAILED`. No overtime, leave workflow,
Workforce snapshot, or Payroll 2B-5 behavior was added.

Verification: 29 focused Work Calendar, Organization, Unit of Work, audit, and
RBAC tests passed; 449 full-suite tests passed. MySQL smoke testing was not run:
the local database does not yet contain the three Phase 1 Work Calendar tables.

---

## Workforce Architecture — Phase 3 (Leave Payroll Treatment, Allocation & Lifecycle)

Status: IMPLEMENTED (AUTOMATED VALIDATION)

New Leave Types require explicit `PAID` or `UNPAID` treatment and creation is
audited. The existing development Leave Type ID 1 remains unresolved and is
blocked from approval until its treatment is known. Payroll-reference
immutability for Leave Type treatment is deferred until the authoritative
Payroll/Workforce reference contract exists; no Payroll reference was invented.

Leave Requests are created only in `PENDING` with required per-date Decimal
allocations. Dates must fall inside the inclusive request period and classify as
`WORKING_DAY` under the existing Work Calendar. Allocation totals must equal the
request aggregate exactly. Approval validates treatment and allocations,
serializes by locking the Employee row, prevents approved employee/date overlap,
transitions status conditionally, and audits in the same Unit of Work. Rejection
and cancellation use the same transactional state/audit pattern. Cross-month
allocations are retained per date without Payroll consumption.

Verification:

- 108 focused Leave domain, application, API, and repository tests passed
- 210 affected Leave, Work Calendar, RBAC/auth, audit, and Payroll regression tests passed
- 495 full-suite tests passed
- One existing Starlette/httpx test-client deprecation warning remains
- Disposable MySQL validation was not run: the configured `payroll_app` account
  lacks `CREATE DATABASE` privilege, so a disposable database could not be created.
  No development database data or schema was changed for testing.

The development database contains legacy Leave Type ID 1 and Salary Revision /
Component IDs 1/1 without authoritative payroll-treatment or OT-base mapping.
The migration must not be run against that database until the Leave Type mapping
is approved. No development data has been changed by this phase.

---

## Workforce Architecture — Phase 4 (Decision 29 Overtime)

Status: IMPLEMENTED (AUTOMATED VALIDATION; MYSQL NOT RUN)

Implemented versioned immutable OT policy create/read APIs, effective-date
resolution, and the two Workforce OT policy permissions. Policy creation uses
the existing Unit of Work and audit tables. No schema or migration change was
made. Policy versions cannot overlap. Existing policy rows are not updated;
the current schema/API has no correction lineage or correction operation.

Added explicit `is_overtime_base` input for new Compensation revision-component
configuration. The server does not infer legacy designations; a designated base
must be one FIXED EARNING component, at most one may be designated per revision,
and OT derivation rejects revisions with zero or multiple valid bases.

Added an internal non-persisting OT derivation service over existing Attendance,
Work Calendar, policy, and Compensation repositories. It splits worked intervals
at local midnight, uses the calendar IANA timezone, derives attendance elapsed
minutes without minute rounding, applies the calendar 480-minute rule and policy
multiplier, uses full-month Work Calendar working-day counts, resolves date-level
compensation configuration, and rounds only the final amount to cents using
ROUND_HALF_UP. Missing/invalid timestamps, excessive duration, and DST-invalid
local times return nonblocking anomalies. No OT endpoint, fact table, Payroll
integration, Decision 30, or Payroll 2B-5 behavior was added.

Verification results and the correction limitation are recorded in the Phase 4
handoff report. The configured database was not modified for testing.

Verification:

- 40 focused OT domain, application, API, and repository tests passed
- 384 affected OT, Attendance, Work Calendar, Compensation, Leave, RBAC, Audit,
  and Payroll regression tests passed
- 537 full-suite tests passed
- One existing Starlette/httpx test-client deprecation warning remains
- MySQL validation was not run because the configured application account does
  not have `CREATE DATABASE` privilege for a disposable test database.

---

## Workforce Architecture — Phase 5 (Payroll Input Contracts and Read Services)

Status: IMPLEMENTED (AUTOMATED VALIDATION; MYSQL NOT RUN)

Added an internal immutable Workforce Payroll Input Reader for inclusive employee
date ranges. It returns per-date Attendance values and explicit missing-row markers,
approved per-date Leave allocations with treatment and fractional values, Work
Calendar classifications/timezones, effective OT policy values, and Compensation
segments from the shared `CompensationSegmentationResolver` contract. Invalid
calendar/policy/leave/compensation data and OT-base configuration are returned as
structured conditions; Attendance timestamp anomalies use the Phase 4 anomaly
representation and local-time validation. Missing Attendance remains an input
anomaly and is not converted to a payroll payable fraction here.

The reader is internal and read-only. It does not persist snapshots, Payroll
Results, Payroll Processing Issues, OT facts, or any other data. No public API,
schema change, migration, Decision 30 snapshot, or Payroll 2B-5 integration was
added. The existing Work Calendar service, Attendance repository, Leave repository,
overtime policy repository, Unit of Work, Phase 4 anomaly detection, and Phase 5A/5A.1
Compensation contracts are reused.

Verification:

- 36 focused Workforce input, Attendance, and Leave repository tests passed
- 334 affected Workforce, Attendance, Leave, Work Calendar, Compensation, Payroll,
  and API
  regression tests passed
- 576 full-suite tests passed
- One existing Starlette/httpx test-client deprecation warning remains
- `git diff --check` passed; Git reports existing LF-to-CRLF conversion warnings
- Disposable MySQL validation was not run because the configured `payroll_app`
  account lacks `CREATE DATABASE` privilege; no development database was modified.

---

## Payroll Architecture — Decisions 17, 24, and 30 Schema Foundation (Phase A)

Status: IMPLEMENTED (PERSISTENCE FOUNDATION; MYSQL MIGRATION CYCLE NOT RUN)

Added the persisted Payroll Run attempt generation and nullable lease-expiration
fields, plus the Payroll-owned `payroll_run_workforce_snapshots` table with one
temporary JSON row per Payroll Run and employee. Added the immutable persistence
contract, repository primitives, and registration in the existing Unit of Work.
The result snapshot column and financial constraints remain unchanged. No attempt
claiming, lease behavior, retry, Workforce snapshot materialization, payroll
calculation, or API behavior was implemented.

Verification:

- 24 focused Payroll domain, persistence foundation, and Unit of Work tests passed
- 127 Payroll-focused regression tests passed
- 582 full-suite tests passed
- One existing Starlette/httpx test-client deprecation warning remains
- `git diff --check` passed
- MySQL connectivity was confirmed read-only, but Alembic reported no current
  revision and the configured account cannot create a disposable database. The
  migration upgrade/downgrade cycle was not run against the development database.

---

## Payroll Architecture — Workforce Snapshot Materialization (Phase B.5)

Status: IMPLEMENTED (AUTOMATED VALIDATION; LIVE MYSQL NOT RUN)

The Payroll processing flow now establishes a scoped MySQL `REPEATABLE READ`
consistent snapshot after the claim commit. Eligibility, compensation resolution,
period segmentation, and Workforce input collection share the same Unit of Work
Session and connection. A database `CURRENT_TIMESTAMP(6)` is captured within that
read boundary. Immutable JSON input snapshots and attempt-fenced blocking issues
are persisted after the read transaction ends. Failed-attempt snapshots remain
available for the existing B.3 retry cleanup. No Payroll calculation, result,
component, QA, finalization, payslip, schema, or API behavior was added.

Verification:

- 81 focused Workforce snapshot, reader, orchestrator, repository, and UoW tests passed
- 474 unit tests passed
- Full suite did not complete because TestClient tests hang at
  `tests/api/test_authorization.py::test_permission_dependency_allows_authenticated_user_with_permission`
  and `tests/api/test_attendance.py::test_create_attendance_requires_authentication`
- MySQL/MySQL-dialect model and SQL compilation tests passed; live MySQL transaction
  semantics were not exercised because the sandbox denied the configured local
  socket connection (`WinError 10013`)
- `git diff --check` passed

---

## Reporting & Analytics — Phase 2B-9A Finalized Payroll Summary

Implemented the read-only `GET /api/v1/reports/payroll/runs/{run_id}` summary
for finalized Payroll Runs. It uses a run-scoped SQL aggregate over persisted
Payroll Result gross, deduction, and net columns and returns the persisted result
count. It does not recalculate payroll, load employee/workforce/component
details, or write an audit event. The `report.payroll.read` permission is
included in the seed catalog and assigned only to the Payroll Administrator
role. An anomalous finalized run with zero results returns 409, consistent with
the existing zero-eligible QA blocker. No schema change or migration was added.

Verification:

- Reporting service and Payroll Result repository tests: 16 passed
- Focused database safety and schema preparation tests: 58 passed
- Full `tests/unit`: 630 passed
- Real-MySQL suite: 17 tests collected; runtime not executed locally
- API TestClient tests stalled in this Windows environment without output; the
  API contract test is included in the manually triggered CI workflow
- GitHub Actions MySQL 8 runtime validation is pending; no live MySQL result is
  claimed

## Reporting & Analytics — Phase 2B-9B Employee Payroll Results Report

Implemented the read-only, finalized-run employee Payroll Result report at
`GET /api/v1/reports/payroll/runs/{run_id}/results`. It uses the existing
persisted `report.payroll.read` permission and a run-scoped keyset query ordered
by employee and result identifiers. The projection returns only persisted
financial totals, identifiers, and current Employee code/name labels. A
deterministic HMAC-protected cursor is bound to the requested run. Components,
snapshots, dashboards, exports, and employee self-service remain deferred. No
schema change, migration, index, permission, or report-read audit event was
added.

Verification:

- Reporting service and Payroll Result repository tests: 19 passed
- Focused database safety and schema preparation tests: 58 passed
- Full `tests/unit`: 640 passed
- Reporting API tests: 21 collected; execution stalled on the first TestClient
  request in the local Windows/Python 3.14 environment
- Strict MySQL suite: 18 tests collected; runtime not executed locally
- OpenAPI route, query parameters, and response statuses verified
- `git diff --check` passed
- Strict ephemeral MySQL 8 GitHub Actions validation remains pending; no live
  result is claimed

## Reporting & Analytics — Phase 2B-9C-1 Employee Report

Implemented `GET /api/v1/reports/employees` as an organization-wide,
read-only, keyset-paginated report. It requires the persisted
`report.employee.read` permission assigned only to the seeded HR Administrator
role. The query selects only approved employee fields, left joins current
department and designation names, applies exact optional filters, and uses a
filter-bound HMAC cursor. No schema change, migration, or index was added.

Local validation and strict ephemeral MySQL 8 GitHub Actions validation are
pending. No live MySQL result is claimed.

## Reporting & Analytics — Phase 2B-9C-2 Attendance Report

Implemented `GET /api/v1/reports/attendance` with the persisted
`report.attendance.read` permission assigned to the HR Administrator role.
The report supports inclusive date filters and optional employee, department,
and attendance-status filters, with bounded, filter-bound HMAC keyset
pagination. Employee, department, and designation labels come from current
master data. Focused local reporting, repository, RBAC-seed, and fixture tests:
31 passed with one Starlette deprecation warning. The Attendance Report API
TestClient run stalled without output in the local Windows environment and was
interrupted. Strict ephemeral MySQL 8 integration validation remains pending;
no live result is claimed.

## Reporting & Analytics — Phase 2B-9C-3 Leave Reports Contract

The organization-wide Leave allocation and balance report contracts are
approved for `GET /api/v1/reports/leave/allocations` and
`GET /api/v1/reports/leave/balances`. Both require the dedicated
`report.leave.read` permission assigned only to HR Administrator. The
allocation report is per persisted date allocation; the balance report
returns stored balance values without deriving remaining days or reconciling
against requests. Both use bounded, filter-bound HMAC keyset pagination and
current master-data labels. Each page reflects current persisted state, with
no cross-page snapshot guarantee. The `leave_request_days` table has no
date-leading index; any index proposal requires query-plan and workload
evidence. No schema, migration, or index change is authorized. Phase 3 has
implemented both authenticated endpoints and the persisted `report.leave.read`
permission for HR Administrator only. Local service, repository, Unit of Work,
and seed tests passed; local API TestClient execution stalled in the Windows
environment. No live MySQL validation is claimed.

Phase 4 adds isolated MySQL integration coverage for persisted Leave report
authorization, allocation and balance filtering/pagination, and cursor errors.
The strict serial integration inventory is 25 tests, and the workflow runs the
Leave report API contract tests. Local collection and offline checks pass;
ephemeral MySQL 8 runtime validation remains pending.

## Reporting & Analytics — Finalized Payroll Component Breakdown Contract

The read-only contract for
`GET /api/v1/reports/payroll/runs/{run_id}/components` is approved and
documented in Decision 44 and the API contract. It uses persisted Payroll
Result Component amounts, requires the existing `report.payroll.read`
permission for Payroll Administrator, and returns bounded filter-bound
keyset pages. The API route and focused API tests are implemented; isolated
MySQL runtime validation has not yet been performed. No runtime validation is
claimed for this report.
