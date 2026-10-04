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

# Authentication

Protected endpoints use the current authenticated-user dependency.

The current authentication flow is:

Client
→ Bearer JWT
→ FastAPI authentication dependency
→ JWT validation
→ user lookup
→ active user

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
