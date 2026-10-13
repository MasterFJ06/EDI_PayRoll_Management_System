# EPMS API Contracts

## Base URL

Development:

`http://127.0.0.1:8000`

API prefix:

`/api/v1`

Swagger:

`/docs`

ReDoc:

`/redoc`

---

# Current Implemented Endpoints

## Authentication

### POST /api/v1/auth/register

Registers a user.

Current application request/response schemas are defined in:

`app/application/identity/schemas.py`

---

### POST /api/v1/auth/login

Authenticates a user and returns the existing access JWT fields plus an opaque
refresh token. The refresh token is returned only to the caller; the server
persists only its SHA-256 hash. Each login creates a separate refresh session.

Authentication uses the existing identity application service and security infrastructure.

### POST /api/v1/auth/refresh

Request body:

- `refresh_token`: non-empty opaque refresh credential

Success (`200 OK`) returns `access_token`, `refresh_token`, and `token_type`.
The submitted token is consumed and replaced transactionally. Rotation retains
the token family and uses the configured refresh lifetime. A consumed-token
replay revokes that family. Invalid, expired, revoked, or replayed credentials
all return the same HTTP 401 response:

```json
{"detail":"Invalid or expired refresh token."}
```

Malformed request bodies return HTTP 422. The refresh credential itself
authenticates this operation; an access JWT is not required.

### POST /api/v1/auth/logout

Request body:

- `refresh_token`: non-empty opaque refresh credential

Success returns `204 No Content` and revokes every active refresh credential
in the associated token family. Repeating logout for a known token is
idempotent. Unknown credentials return the same generic HTTP 401 response used
by refresh. Malformed request bodies return HTTP 422. Existing access JWTs
remain valid until normal expiry; protected routes continue checking active
users and current persisted RBAC.

---

# Organization

## POST /api/v1/departments

Creates a department.

Current request:

- department_code
- department_name

Current response:

- department_id
- department_code
- department_name
- status

---

## POST /api/v1/designations

Creates a designation.

Current request:

- designation_code
- designation_name

Current response:

- designation_id
- designation_code
- designation_name
- status

---

# Employee

## POST /api/v1/employees

Creates an employee.

Current request fields:

- employee_code
- user_id
- first_name
- last_name
- department_id
- designation_id
- manager_employee_id
- joining_date
- employment_end_date (optional; nullable date and inclusive employment end)

Current response fields:

- employee_id
- employee_code
- user_id
- first_name
- last_name
- department_id
- designation_id
- manager_employee_id
- joining_date
- employment_end_date
- employment_status

---

# Attendance

## POST /api/v1/attendance

Creates an attendance record.

Current request fields:

- employee_id
- attendance_date
- check_in_time
- check_out_time
- attendance_status

Attendance statuses:

- PRESENT
- ABSENT
- HALF_DAY
- ON_LEAVE
- HOLIDAY

The database enforces uniqueness for:

`employee_id + attendance_date`

Duplicate attendance for the same employee/date is rejected.

---

# Leave Management

All Leave Management endpoints require an active user authenticated with a Bearer access token. Successful creation returns HTTP 201. Business rule violations use the centralized HTTP 409 response.

## POST /api/v1/leave-types

Creates a leave type.

Request fields:

- `leave_type_code` (string, 1–30 characters)
- `leave_type_name` (string, 1–100 characters)
- `description` (optional string, up to 500 characters)
- `payroll_treatment` (`PAID` or `UNPAID`, required; explicit and never inferred)
- `is_active` (boolean, defaults to `true`)

Response fields: `leave_type_id`, `leave_type_code`, `leave_type_name`, `description`, `payroll_treatment`, `is_active`.

Requires `workforce.leave_type.manage`. Payroll treatment is mandatory and is
restricted to `PAID` or `UNPAID`. There is no Leave Type update endpoint, so the
treatment cannot be changed through the current API. Payroll-reference
immutability for Leave Type treatment is deferred until the authoritative
Payroll/Workforce reference contract exists; no Payroll reference is inferred.

## POST /api/v1/leave-balances

Creates an employee leave balance for a leave type and year.

Request fields:

- `employee_id` (positive integer)
- `leave_type_id` (positive integer)
- `balance_year` (integer, 0–65535)
- `allocated_days` and `used_days` (decimal, nonnegative, up to four integer and two fractional digits; both default to `0.00`)

Response fields: `leave_balance_id`, `employee_id`, `leave_type_id`, `balance_year`, `allocated_days`, `used_days`.

## POST /api/v1/leave-requests

Creates a leave request.

Request fields:

- `employee_id`, `leave_type_id` (positive integers)
- `start_date`, `end_date` (dates)
- `requested_days` (positive decimal, up to four integer and two fractional digits)
- `reason` (optional string, up to 1000 characters)
- `allocations` (non-empty list of `{leave_date, day_fraction}` where `day_fraction` is an exact decimal from `0.01` through `1.00` at hundredth precision)

New requests always start as `PENDING`; status, reviewer, and review timestamps
cannot be supplied by the client. Allocation dates must be unique, fall inside
the inclusive request period, and classify as `WORKING_DAY` under the
organization Work Calendar. The exact Decimal allocation sum must equal
`requested_days`. Cross-period requests are supported without changing the
aggregate; each date allocation remains authoritative.

Response fields preserve the request data and include `allocations` with each
date and exact decimal fraction.

## Leave Request Lifecycle

The following operations require their corresponding permission and derive the
actor from authentication:

- `POST /api/v1/leave-requests/{id}/approve` — `workforce.leave.approve`; requires a known `PAID`/`UNPAID` Leave Type treatment, valid allocations, and no approved allocation overlap for the same employee/date.
- `POST /api/v1/leave-requests/{id}/reject` — `workforce.leave.reject`.
- `POST /api/v1/leave-requests/{id}/cancel` — `workforce.leave.cancel`; pending and approved requests may be cancelled.

Allowed transitions are `PENDING → APPROVED`, `PENDING → REJECTED`,
`PENDING → CANCELLED`, and `APPROVED → CANCELLED`. Invalid transitions,
unresolved treatment, invalid allocations, and approved overlaps return HTTP
409. Missing requests return 404. Every operation records an audit event.

Pydantic request validation failures return HTTP 422. Schema-backed domain rule failures, such as reversed dates or inconsistent review fields, use the centralized HTTP 409 response.

---

# Compensation / Salary Management

All Compensation endpoints require an active user authenticated with a Bearer access token and the persisted `compensation.write` permission. This permission is assigned only to the `Payroll Administrator` role. Unauthenticated requests return HTTP 401; authenticated users without the permission receive HTTP 403 through the existing authorization dependency. Successful creation returns HTTP 201. Pydantic request validation failures return HTTP 422. Missing referenced records, duplicate values protected by application/database uniqueness, and schema-backed domain rule failures return HTTP 409 through the centralized error handler.

## POST /api/v1/salary-structures

Creates a salary structure.

Request fields:

- `structure_code` (string, 1–30 characters)
- `structure_name` (string, 1–100 characters)
- `description` (optional string, up to 500 characters)
- `status` (`ACTIVE` or `INACTIVE`; defaults to `ACTIVE`)

Successful response: HTTP 201 with `salary_structure_id`, `structure_code`, `structure_name`, `description`, and `status`.

The structure code is unique. Duplicate codes return HTTP 409.

## POST /api/v1/salary-components

Creates a salary component.

Request fields:

- `component_code` (string, 1–30 characters)
- `component_name` (string, 1–100 characters)
- `component_type` (`EARNING` or `DEDUCTION`)
- `status` (`ACTIVE` or `INACTIVE`; defaults to `ACTIVE`)

Successful response: HTTP 201 with `salary_component_id`, `component_code`, `component_name`, `component_type`, and `status`.

The component code is unique. Duplicate codes return HTTP 409.

## POST /api/v1/salary-revisions

Creates a revision for an existing salary structure.

Request fields:

- `salary_structure_id` (positive integer referencing an existing structure)
- `revision_number` (integer, 0–4,294,967,295)
- `effective_from` (date)
- `effective_to` (optional date; must not precede `effective_from`)

Successful response: HTTP 201 with `salary_revision_id`, `salary_structure_id`, `revision_number`, `effective_from`, and `effective_to`.

The pair `(salary_structure_id, revision_number)` is unique. A missing structure or duplicate pair returns HTTP 409.

## POST /api/v1/salary-revision-components

Adds a component to an existing salary revision.

Request fields:

- `salary_revision_id` (positive integer referencing an existing revision)
- `salary_component_id` (positive integer referencing an existing component)
- `calculation_type` (`FIXED` or `PERCENTAGE`)
- `fixed_amount` (optional nonnegative decimal, up to 15 digits and 2 decimal places)
- `percentage_value` (optional nonnegative decimal, up to 8 digits and 4 decimal places)
- `base_component_id` (optional positive integer referencing an existing component)
- `is_overtime_base` (required boolean; defaults are not inferred by the server)

For `FIXED`, `fixed_amount` is required and `percentage_value` and `base_component_id` must be null. For `PERCENTAGE`, `percentage_value` and `base_component_id` are required and `fixed_amount` must be null. These combinations follow the database check constraint; this endpoint does not calculate salary values.

Successful response: HTTP 201 with `salary_revision_id`, `salary_component_id`, `calculation_type`, `fixed_amount`, `percentage_value`, `base_component_id`, and `is_overtime_base`.

The revision/component pair is unique. At most one component per revision may be designated as the OT base. A designated OT base must be an EARNING with FIXED calculation. Missing references, an invalid calculation-field combination, a duplicate pair, or an invalid OT-base designation returns HTTP 409. Existing components are not inferred or changed.

## POST /api/v1/employee-salary-assignments

Assigns an existing salary revision to an existing employee.

Request fields:

- `employee_id` (positive integer referencing an existing employee)
- `salary_revision_id` (positive integer referencing an existing revision)
- `effective_from` (date)
- `effective_to` (optional date; must not precede `effective_from`)

Successful response: HTTP 201 with `salary_assignment_id`, `employee_id`, `salary_revision_id`, `effective_from`, and `effective_to`.

Missing employee or revision references and reversed dates return HTTP 409. The schema defines no assignment uniqueness or overlap rule.

## Compensation Error Responses

- HTTP 401: unauthenticated or invalid/expired access token; the existing authentication response format applies.
- HTTP 422: invalid request body or field values; the FastAPI/Pydantic validation response applies.
- HTTP 409: centralized business-rule response with `detail` and an `error` object containing `code`, `message`, and `request_id`.
- HTTP 500: centralized unexpected-error response with an `error` object containing `code`, a generic `message`, and `request_id`.

---

# Payroll Management — Phase 2A

Payroll Run creation requires the `payroll.run.create` permission. Run retrieval requires
`payroll.run.read`. Both permissions are evaluated using the authenticated user's current
RBAC assignments.

## POST /api/v1/payroll/runs

Creates a Payroll Run in `CREATED` status.

Request fields:

- `year` (integer, 1–65,535)
- `month` (integer, 1–12)

The authenticated user's ID is recorded as `initiated_by_user_id`; client-supplied identity
fields are ignored. Successful response: HTTP 201 with `payroll_run_id`, `payroll_year`,
`payroll_month`, `status`, and `initiated_by_user_id`. A duplicate year/month period
returns HTTP 409, including a collision enforced by the database unique constraint.

## GET /api/v1/payroll/runs/{run_id}

Retrieves a Payroll Run for users with `payroll.run.read`. Successful response: HTTP 200
with the same Payroll Run fields returned by the create operation. A missing run returns
HTTP 404. Employees and other users without the permission receive HTTP 403.

Phase 2A created and retrieved Payroll Runs. Processing claims the run and internally
resolves eligible and excluded employees from their employment-date overlap with the
payroll month. It returns the run status only and performs no payroll calculations or
Payroll Result, component, or payslip creation. Compensation and segmentation blockers
may create OPEN Payroll Processing Issues during processing.

For these endpoints, unauthenticated requests return HTTP 401, authenticated requests
without the required permission return HTTP 403, invalid period input returns HTTP 422,
duplicate periods return HTTP 409, and unexpected failures use the centralized HTTP 500
response.

## Payroll Management — Phase 2B-1 (Run Claim)

### POST /api/v1/payroll/runs/{run_id}/process

Requires `payroll.run.process` and an active authenticated user. This operation
atomically claims a run only when its current status is `CREATED`, sets `started_at`,
and returns HTTP 200 with the existing Payroll Run response fields and status
`PROCESSING`. The operation does not calculate payroll or create results, components,
or payslips. Compensation/segmentation blockers may create OPEN Payroll Processing
Issues. The request has no body; client-supplied state is not accepted.

A missing run returns HTTP 404. A run in any status other than `CREATED` returns HTTP
409. Simultaneous/duplicate requests are serialized by the conditional database update;
only one can claim the run and subsequent attempts return HTTP 409 without resetting
`started_at`. Unauthenticated and unauthorized requests return HTTP 401 and HTTP 403.
Unexpected orchestration failures use the centralized HTTP 500 response and attempt an
atomic `PROCESSING` to `FAILED` transition. A started or failed lifecycle transition is
recorded in the existing audit tables and includes the request correlation ID when
available. Calculation and result/payslip artifact generation remain outside
the implemented processing request contract.

The processing workflow also resolves the internal Phase 2B-2 employee eligibility
outcome. This does not change the HTTP response contract: eligible and excluded
employee classifications are not returned by this endpoint.

### Approved Retry Contract

`POST /api/v1/payroll/runs/{run_id}/retry` is the approved contract for controlled
Payroll Run retry. It requires an active authenticated user with
`payroll.run.retry`; the actor is derived from that authenticated user. Only a run
in `FAILED` may be retried. The operation reconciles failed results, result
components, and failed-attempt temporary Workforce snapshots, then activates the
next attempt atomically. It does not modify issues, audit history, or payslips.
The existing `/process` operation remains `CREATED`-only.

Success returns HTTP 200 using the existing Payroll Run response fields, with
status `PROCESSING`. `attempt_number` may remain internal. Unauthenticated
requests return HTTP 401; authenticated users without the permission receive HTTP
403; a missing run returns HTTP 404; a wrong state, stale attempt, or attached
payslip invariant returns HTTP 409. Concurrent retry requests are serialized so
exactly one succeeds and the loser receives HTTP 409.

The expected attempt number used by the retry application service is resolved
internally from the requested Payroll Run; it is not part of the public request
or response contract. The transactional retry operation revalidates the attempt
under the Payroll Run row lock.

### Expired Payroll Attempt Recovery — Decision 45

`POST /api/v1/payroll/runs/{run_id}/recover` accepts no request body and requires
an active authenticated operator with the persisted `payroll.run.recover`
permission, assigned to the existing Payroll Administrator role. The actor is
derived from the authenticated user. Recovery succeeds only for a currently
`PROCESSING` run whose non-null active-attempt lease has expired according to
database time. It locks the parent Payroll Run and atomically changes the state
to `FAILED`, clears the lease, and writes the
`PAYROLL_RUN_ATTEMPT_RECOVERED` audit event. The event records the run ID,
expired attempt number, actor, prior/new status, prior lease expiration,
database-generated occurrence timestamp, and request correlation ID when
available.

Success returns HTTP 200 with the existing Payroll Run response and status
`FAILED`; attempt number is unchanged. Missing runs return HTTP 404. A
non-`PROCESSING` run, missing or unexpired lease, stale state, repeated request,
or concurrent losing request returns HTTP 409. Unauthenticated and unauthorized
requests return HTTP 401 and HTTP 403. Concurrent requests are serialized by
the parent-row lock and conditional transition, so at most one succeeds.

Recovery does not reconcile attempt artifacts, increment the attempt, restart,
or finalize the run. The existing retry endpoint remains the only transition
from `FAILED` to `PROCESSING` and performs the existing attempt reconciliation.
Attempt-owned writers and lease renewal continue to validate the current
processing attempt and its unexpired lease, fencing stale workers. The state
transition and audit event share one Unit of Work transaction. No scheduler or
background worker is introduced.

### Approved Payroll Run Finalization Contract

`POST /api/v1/payroll/runs/{run_id}/finalize` requires an active authenticated
user with the persisted `payroll.run.finalize` permission. It accepts no request
body; the actor is derived from the authenticated user. The operation locks the
parent Payroll Run, verifies that its current status is `PROCESSED`, rechecks
blocking OPEN issues and the payslip invariant under that lock, then transitions
the run to terminal `FINALIZED`. The status transition, `finalized_at` timestamp,
and `PAYROLL_RUN_FINALIZED` audit event are committed atomically. Final Payroll
Results and Workforce snapshots remain immutable, and this operation does not
generate payslips.

Success returns HTTP 200 using the existing Payroll Run response fields, with
status `FINALIZED`. Unauthenticated requests return HTTP 401; authenticated
users without the permission receive HTTP 403; a missing run returns HTTP 404;
a run in any state other than `PROCESSED`, an OPEN issue, or a violated payslip
invariant returns HTTP 409. Concurrent or repeated requests are serialized by
the parent-row lock and conditional state transition: exactly one request may
succeed, and competing or subsequent requests receive HTTP 409.

### Phase 2B-8A — Individual Payslip Record Generation

`POST /api/v1/payroll/runs/{run_id}/results/{result_id}/payslip` creates one
Payslip database record for a Payroll Result. It requires an active authenticated
user with the persisted `payroll.payslip.create` permission. The authenticated
user is recorded as `generated_by_user_id`; clients cannot supply the generator
identity. The request body contains only `payslip_number`, which is required by
the existing schema. A dedicated Payslip response contains `payslip_id`,
`payroll_result_id`, `payslip_number`, `generated_by_user_id`, `generated_at`,
and nullable `document_path` (null because this increment creates no document).

The Payroll Run must be `FINALIZED`, and the specified Payroll Result must belong
to that run. Generation reads the persisted Payroll Result and Payroll Result
Components without recalculating financial values or modifying payroll results,
components, Workforce snapshots, or run state. The result's persisted financial
values retain Decision 37 precision and rounding. This increment is individual;
bulk generation, employee self-service, payslip read/download, and PDF/document
creation are out of scope.

Success returns HTTP 201. Missing runs, missing results, and results that do not
belong to the specified run return HTTP 404. A non-finalized run and an existing
payslip for the result return HTTP 409. Database uniqueness on
`payroll_result_id` and `payslip_number` is authoritative; an expected
concurrent uniqueness collision also returns HTTP 409. Missing/invalid
authentication returns HTTP 401, insufficient permission returns HTTP 403, and
unexpected errors use the centralized sanitized HTTP 500 response.

The operation locks the parent Payroll Run and verifies the current finalized
state before creating the record. Payslip insertion and `PAYSLIP_GENERATED`
audit insertion use the same Unit of Work transaction. The event records the
authenticated actor, payslip resource identifier, run/result identifiers, and
request correlation ID when available; it must not record salary amounts.
Failure rolls back both writes.

The `payslips.document_path` column is nullable for record-only payslips. A null
value means no document has been generated; an empty, fabricated, or placeholder
path is prohibited. The `payroll.payslip.create` permission is included in the
seed catalog and Payroll Administrator role assignment. No employee
self-service or document-storage contract is established here.

### Phase 2B-9A — Finalized Payroll Run Summary

`GET /api/v1/reports/payroll/runs/{run_id}` requires the persisted
`report.payroll.read` permission, initially assigned only to the existing
Payroll Administrator role. The endpoint returns a read-only summary for a
`FINALIZED` Payroll Run: `payroll_run_id`, `payroll_year`, `payroll_month`,
`status`, `initiated_by_user_id`, `employee_result_count`, `total_gross_pay`,
`total_deductions`, and `total_net_pay`.

The three monetary totals and the result count are aggregated from persisted
`payroll_results` rows scoped to the requested run. Stored gross, deduction,
and net amounts are authoritative; the endpoint does not recalculate payroll,
sum components, read Workforce snapshots, or return employee-level data,
component details, or personal labels. It does not write a report-read audit
event. No historical-label guarantee is established for future reporting
features.

Unauthenticated requests return HTTP 401 and authenticated users without the
permission return HTTP 403. A missing run returns HTTP 404. Existing runs
whose state is not `FINALIZED` return HTTP 409 without querying or exposing
their financial totals. QA prevents a zero-eligible run from reaching
`PROCESSED`, and finalization is gated by QA issues; an anomalous finalized run
with no persisted Payroll Results therefore returns HTTP 409 rather than
fabricated zero totals.

Dashboards, CSV exports, and employee self-service reports remain deferred.
The later Finalized Payroll Component Breakdown contract below defines a
separate report over persisted component rows without changing this summary.

### Phase 2B-9B — Paginated Employee Payroll Results

`GET /api/v1/reports/payroll/runs/{run_id}/results` requires authentication
and the persisted `report.payroll.read` permission, assigned only to Payroll
Administrator. A missing run returns HTTP 404. A run that is not `FINALIZED`
returns HTTP 409. Authentication and permission failures return HTTP 401 and
HTTP 403; invalid query parameters or cursors return HTTP 422.

The read-only response contains `payroll_run_id`, `results`, and `pagination`.
Each result contains only `payroll_result_id`, `payroll_run_id`, `employee_id`,
`salary_assignment_id`, persisted `gross_earnings`, `total_deductions`,
`net_salary`, `employee_code`, and `employee_name`. Financial values come from
the persisted Payroll Result and are not recalculated. Employee labels come
from current Employee master data, are not historical labels, and are returned
as null if unavailable. The query uses a left outer join for labels.

`limit` defaults to 50 and accepts values from 1 through 100. Results are
ordered by `employee_id` and then `payroll_result_id`, both ascending. The
opaque cursor is a deterministic, integrity-protected encoding bound to the
requested run and the last result pair. Each query fetches at most `limit + 1`
rows; `pagination` contains `limit`, `has_more`, and nullable `next_cursor`.
There is no offset pagination or separate total-count query. Components,
snapshots, attendance/leave details, contact/security data, and unrelated
fields are not returned. No report-read audit event is written.

### Finalized Payroll Component Breakdown Report

`GET /api/v1/reports/payroll/runs/{run_id}/components` requires a positive
`run_id`, authentication, and the persisted `report.payroll.read` permission,
assigned to Payroll Administrator. This permission covers finalized Payroll
Run summaries, Payroll Results, and component details; it does not implicitly
grant access to HR Administrators or employees. Missing or invalid
authentication returns HTTP 401; authenticated users without the permission
receive HTTP 403.

The endpoint is read-only and returns `payroll_run_id`, `components`, and
`pagination`. Each component row contains exactly
`payroll_result_component_id`, `payroll_run_id`, `payroll_result_id`,
`employee_id`, `employee_code`, `employee_name`, `salary_component_id`,
`component_code`, `component_name`, `component_type`, `amount`, and
`calculation_order`. The component ID, result ID, salary component ID,
persisted component type, persisted amount, and calculation order come from
the Payroll Result Component. Run ID comes from its associated Payroll Run;
employee ID comes from its Payroll Result. Employee code and full name use
current Employee master data, and component code and name use the current
Salary Component definition. Employee labels may be null when unavailable.
Current labels are not historical snapshots. Inactive Salary Component
definitions are included. Contact details, credentials, manager details,
free-text fields, Workforce snapshots, and unrelated data are excluded.

Amounts are returned as persisted without recalculation or modification. The
endpoint does not return gross, deductions, net, component sums, or other
derived financial totals. The existing Payroll summary and Payroll Results
reports remain the sources for their contracted totals.

The report includes one row per persisted Payroll Result Component belonging
to a Payroll Result in the requested run and never includes another run's
rows. A missing run returns HTTP 404; an existing run not in `FINALIZED`
state returns HTTP 409. Invalid run IDs, filters, limits, or cursors return
HTTP 422. A finalized run with zero persisted component rows returns HTTP 200
with an empty component page; it is not independently converted to a
conflict. Payroll QA remains a separate responsibility.

The schema foreign key from `payroll_result_components.salary_component_id`
to `salary_components.salary_component_id` uses `ON DELETE RESTRICT`. If an
inconsistent persisted row nevertheless references a missing definition,
the report detects the integrity anomaly, does not silently omit the
component, and fails safely with a sanitized HTTP 500 integrity error using
the centralized error response. Raw SQL, database internals, and sensitive
record contents are not exposed.

Optional filters are exact `employee_id`, exact `salary_component_id`, and
`component_type` (`EARNING` or `DEDUCTION`). `limit` defaults to 50 and
accepts values from 1 through 100. Results use bounded keyset pagination,
fetching at most `limit + 1` rows, ordered ascending by
`(payroll_result_id, salary_component_id)`. The pagination object contains
`limit`, `has_more`, and nullable `next_cursor`.

The opaque cursor uses the configured HMAC-SHA256 signing key, a
component-report-specific discriminator, and binds report identity, requested
run ID, active filters, and the last returned key tuple. Malformed, tampered,
cross-run, cross-filter, and cross-report cursors return HTTP 422. No index or
migration is introduced; any future index proposal requires query-plan and
workload evidence.

Run-state verification and component reads occur within the same Unit of Work
transaction. The report does not write data or emit a report-read audit event.
It respects the terminal `FINALIZED` state and existing immutability of final
Payroll Results and Workforce snapshots.

### Phase 2B-9C-1 — Organization-Wide Employee Report

`GET /api/v1/reports/employees` requires authentication and the persisted
`report.employee.read` permission, initially assigned only to the
`HR Administrator` role. Authentication and permission failures return HTTP
401 and 403. Invalid filters, limits, or cursors return HTTP 422.

The response contains `employees` and `pagination`. Each employee object
contains exactly `employee_id`, `employee_code`, `first_name`, `last_name`,
`department_id`, `department_name`, `designation_id`, `designation_name`,
`joining_date`, `employment_end_date`, and `employment_status`. Department
and designation labels use current master data and are nullable; they are not
historical labels. User IDs, manager IDs, contact details, credentials, and
security fields are excluded.

The report includes all supported employment statuses by default. Optional
exact filters are `employee_code`, `department_id`, `designation_id`, and
`employment_status` (`ACTIVE`, `INACTIVE`, or `TERMINATED`). Unknown IDs return
a successful empty page if no employee matches. `limit` defaults to 50 and
accepts 1 through 100. Employees are ordered by ascending `employee_id`; the
integrity-protected opaque cursor is bound to this report and the active
filters. Each query fetches at most `limit + 1` rows. `pagination` contains
`limit`, `has_more`, and nullable `next_cursor`. There is no offset pagination
or separate total-count query. This endpoint does not produce an audit event.

Dashboard, export, and employee self-service reports remain deferred.

### Phase 2B-9C-2 — Organization-Wide Attendance Report

`GET /api/v1/reports/attendance` requires authentication and the persisted
`report.attendance.read` permission, assigned only to `HR Administrator`.
This permission is separate from `report.employee.read` and is not assigned to
Payroll Administrator. Missing or invalid authentication returns HTTP 401;
authenticated users without this permission receive HTTP 403. Invalid query
parameters or cursors return HTTP 422. The read-only endpoint does not emit a
report-read audit event.

The response contains `attendance_records` and `pagination`. Each attendance
record contains exactly `attendance_id`, `employee_id`, `employee_code`,
`first_name`, `last_name`, `department_id`, `department_name`,
`designation_id`, `designation_name`, `attendance_date`,
`attendance_status`, `check_in_time`, and `check_out_time`. Attendance fields
are persisted facts. Employee names, employee code, and department/designation
labels use current master data and are not historical labels. Department and
designation names may be null. `check_in_time` and `check_out_time` preserve
their nullable database values; a null timestamp is not interpreted. The
report excludes user IDs, manager IDs, contact data, credentials, and security
fields. It does not calculate hours, lateness, absenteeism, overtime, Leave
entitlement, or payroll impact.

Optional filters are inclusive `date_from` and `date_to`, positive
`employee_id` and `department_id`, and `attendance_status` (`PRESENT`,
`ABSENT`, `HALF_DAY`, `ON_LEAVE`, or `HOLIDAY`). `date_from` later than
`date_to` is invalid. There is no fixed maximum date span. Unknown employee or
department IDs produce an empty page if no rows match. `limit` defaults to 50
and accepts 1 through 100. Rows are ordered by ascending
`attendance_date`, then `attendance_id`; queries fetch at most `limit + 1`
rows. The deterministic HMAC-SHA256 protected opaque cursor is specific to
this report and bound to the active filters and last returned date/ID pair.
Malformed, tampered, wrong-report, or filter-mismatched cursors return HTTP
422. There is no offset pagination or total-count query.

### Phase 2B-9C-3 — Organization-Wide Leave Reports

Both Leave reports require authentication and the persisted
`report.leave.read` permission, assigned only to `HR Administrator`. Access is
organization-wide; there is no employee-self-service or manager-scoped
behavior. Payroll Administrator permissions remain separate. Authentication
and permission failures return HTTP 401 and 403. Invalid filters, limits, or
cursors return HTTP 422. The reports do not emit report-read audit events.

#### `GET /api/v1/reports/leave/allocations`

The response contains `allocations` and `pagination`. Each allocation contains
exactly `leave_request_id`, `leave_request_day_id`, `employee_id`,
`employee_code`, `first_name`, `last_name`, `department_id`,
`department_name`, `designation_id`, `designation_name`, `leave_type_id`,
`leave_type_name`, `start_date`, `end_date`, `requested_days`, `status`,
`leave_date`, and `day_fraction`. Allocation and request values come from
persisted Leave records. Employee, department, designation, and Leave Type
labels use current master data and are not historical snapshots. Request
reasons, reviewer comments and identifiers, payroll treatment, credentials,
contact details, and security fields are excluded. `requested_days` repeats
for every allocation and must not be summed across rows as a request total.

Optional exact filters are inclusive `date_from` and `date_to` on allocation
`leave_date`, positive `employee_id`, `department_id`, and `leave_type_id`, and
request `status`. All `PENDING`, `APPROVED`, `REJECTED`, and `CANCELLED`
allocations are included by default. A reversed date range or invalid status
returns HTTP 422. Unknown IDs return an empty page if no row matches.

#### `GET /api/v1/reports/leave/balances`

The response contains `balances` and `pagination`. Each balance contains
exactly `employee_id`, `employee_code`, `first_name`, `last_name`,
`department_id`, `department_name`, `designation_id`, `designation_name`,
`leave_type_id`, `leave_type_name`, `balance_year`, `allocated_days`, and
`used_days`. It returns one row per unique
`(employee_id, leave_type_id, balance_year)`. Balance amounts and year are
returned as persisted. The report includes inactive and terminated employees
by default; it does not calculate remaining days, reconcile values against
Leave Request allocations, or characterize `balance_year` as a calendar or
employment year. Optional exact filters are positive `employee_id`,
`department_id`, and `leave_type_id`, plus stored `balance_year`.
`balance_year` must be in the schema-supported range 0 through 65535.

Both reports use keyset pagination with `limit` defaulting to 50 and accepting
1 through 100. Allocation ordering is ascending `(leave_date,
leave_request_day_id)`; balance ordering is ascending
`(employee_id, leave_type_id, balance_year)`. Each query fetches at most
`limit + 1` rows. Deterministic opaque HMAC-SHA256-protected cursors are bound
to their report, all active filters, and the last returned key. The cursor
formats are distinct per report. Pagination contains `limit`, `has_more`, and
nullable `next_cursor`; there is no offset pagination, unbounded total-count
query, or cross-page snapshot guarantee. Each page reflects current persisted
state.

The `leave_request_days` table has no date-leading index. A bounded result
page does not bound rows scanned or sorted for date-filtered allocation
queries. Query-plan and workload evidence is required before proposing an
index. This reporting contract adds no schema, migration, or index and does
not change Leave accounting, lifecycle, remaining-balance semantics, or
existing Leave creation authorization.

---

# Authentication

Protected endpoints use the current authenticated-user dependency.

The current authentication flow is:

Client
→ Bearer JWT
→ FastAPI authentication dependency
→ JWT validation
→ user lookup
→ active user

## Backend authorization

Protected operations may declare a permission using the reusable
`require_permission(permission_code)` API dependency. The permission is evaluated against
the authenticated user's current `user_roles` and `role_permissions` records and only
active roles grant access. Missing or invalid authentication returns HTTP 401. An
authenticated user without the required permission returns HTTP 403. Clients cannot
provide the user identity, role, or permission used for the decision.

The development seed catalog includes the `Payroll Administrator` role and
granular permissions `payroll.run.create`, `payroll.run.read`,
`payroll.run.process`, `payroll.run.retry`, `payroll.run.recover`,
`payroll.run.finalize`,
`payroll.payslip.create`, and `report.payroll.read`, plus the
`HR Administrator` role with `report.employee.read` and
`report.attendance.read`. `payroll.run.recover` is assigned only to the
Payroll Administrator role. The approved `report.leave.read` permission and HR
role assignment are pending implementation. No user is assigned to either
role by the seed data. Implemented Payroll Run operations are
documented in the Phase 2A, Phase 2B-1, retry, and finalization sections above.
Individual payslip record generation is implemented without document
generation; payslip read/download operations remain unimplemented.

---

## Work Calendar

### POST /api/v1/work-calendar-versions

Requires `organization.calendar.manage`. Creates an immutable organization-wide
calendar version with `version_number`, inclusive `effective_from` and optional
`effective_to`, IANA `time_zone`, optional `replaces_version_id`, and exactly
seven weekly rules (`iso_weekday`, `classification`, `scheduled_minutes`). The
authenticated user is recorded as creator. Returns the version, rules, and
initially empty date override list (201). Effective-date overlap returns 409;
invalid request data returns 422.

### GET /api/v1/work-calendar-versions/{version_id}

Requires `organization.calendar.read`. Returns version metadata, creator user
identifier, all seven weekly rules, and date overrides. Missing versions return
404.

### POST /api/v1/work-calendar-versions/{version_id}/date-overrides

Requires `organization.calendar.manage`. Request fields are `override_date`,
`classification` (`WORKING_DAY`, `NON_WORKING_DAY`, or `HOLIDAY`), and optional
`label` (required and non-blank for `HOLIDAY`). Returns the created override
(201). Dates outside the version period, duplicates, and corrections while any
affected monthly Payroll Run is not `FAILED` return 409.

## Workforce Overtime Policy

### POST /api/v1/workforce/overtime-policy-versions

Requires `workforce.overtime_policy.manage`. Creates an immutable, effective-dated
policy version. Request fields are `version_number`, inclusive `effective_from`,
optional inclusive `effective_to`, and `non_working_multiplier` (nonnegative
DECIMAL(8,4)). The authenticated user is recorded as creator. Overlapping policy
periods or a duplicate version number return 409; invalid input returns 422.
Creation and audit are committed in the same Unit of Work.

### GET /api/v1/workforce/overtime-policy-versions/{policy_id}

Requires `workforce.overtime_policy.read`. Returns policy metadata, effective
dates, multiplier, and creator identifier. Missing policy versions return 404.

Policy versions are resolved by inclusive effective date; gaps have no applicable
policy and persisted overlaps are treated as invalid state. There is no policy
update/correction endpoint in this contract.

# Error Responses

The backend has centralized error handling.

Business rule violations use HTTP 409.

Invalid domain state uses HTTP 409.

Generic domain errors use HTTP 400.

Unexpected server errors use HTTP 500.

Error responses include an error code and request ID.

---

# Important Rule

Do not document future endpoints as implemented.

When a new module is implemented, update this document with the actual endpoint contracts.

The implementation and Pydantic schemas are the source of truth for exact request/response details.
