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

Authenticates a user and returns an access JWT.

Authentication uses the existing identity application service and security infrastructure.

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
- `is_active` (boolean, defaults to `true`)

Response fields: `leave_type_id`, `leave_type_code`, `leave_type_name`, `description`, `is_active`.

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
- `status` (one of `PENDING`, `APPROVED`, `REJECTED`, `CANCELLED`; defaults to `PENDING`)
- `reviewed_by_employee_id` (optional positive integer)
- `reviewed_at` (optional datetime)
- `review_comment` (optional string, up to 1000 characters)

Response fields: `leave_request_id`, `employee_id`, `leave_type_id`, `start_date`, `end_date`, `requested_days`, `reason`, `status`, `reviewed_by_employee_id`, `reviewed_at`, `review_comment`.

Pydantic request validation failures return HTTP 422. Schema-backed domain rule failures, such as reversed dates or inconsistent review fields, use the centralized HTTP 409 response.

---

# Compensation / Salary Management

All Compensation endpoints require an active user authenticated with a Bearer access token. Successful creation returns HTTP 201. Pydantic request validation failures return HTTP 422. Missing referenced records, duplicate values protected by application/database uniqueness, and schema-backed domain rule failures return HTTP 409 through the centralized error handler.

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

For `FIXED`, `fixed_amount` is required and `percentage_value` and `base_component_id` must be null. For `PERCENTAGE`, `percentage_value` and `base_component_id` are required and `fixed_amount` must be null. These combinations follow the database check constraint; this endpoint does not calculate salary values.

Successful response: HTTP 201 with `salary_revision_id`, `salary_component_id`, `calculation_type`, `fixed_amount`, `percentage_value`, and `base_component_id`.

The revision/component pair is unique. Missing references, an invalid calculation-field combination, or a duplicate pair returns HTTP 409.

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

Phase 2A created and retrieved Payroll Runs. Processing is implemented separately
as a run claim only; payroll calculations and result, issue, or payslip creation
are not part of the process operation.

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
processing issues, or payslips. The request has no body; client-supplied state is not
accepted.

A missing run returns HTTP 404. A run in any status other than `CREATED` returns HTTP
409. Simultaneous/duplicate requests are serialized by the conditional database update;
only one can claim the run and subsequent attempts return HTTP 409 without resetting
`started_at`. Unauthenticated and unauthorized requests return HTTP 401 and HTTP 403.
Unexpected orchestration failures use the centralized HTTP 500 response and attempt an
atomic `PROCESSING` to `FAILED` transition. A started or failed lifecycle transition is
recorded in the existing audit tables and includes the request correlation ID when
available. Retry, finalization, calculation, and artifact generation are not implemented.

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

The development seed catalog includes the `Payroll Administrator` role and granular
permissions `payroll.run.create`, `payroll.run.read`, `payroll.run.process`,
`payroll.run.retry`, and `payroll.run.finalize`. No user is assigned to the role by the
seed data. Implemented Payroll Run operations are documented in the Phase 2A and
Phase 2B-1 sections above; retry, finalization, and payslip operations remain
unimplemented.

---

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
