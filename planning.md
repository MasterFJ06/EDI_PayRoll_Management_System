# EPMS — MASTER PROJECT HANDOFF CONTEXT AND CONTINUATION PLAN

## 1. PROJECT OVERVIEW

We are developing an **Employee Payroll Management System (EPMS)**.

The backend is being developed in **Python using FastAPI**, with **MySQL** as the database and **SQLAlchemy** for persistence.

The project is intended to be a properly layered backend rather than a quick CRUD application.

The main architectural flow is:

```text
Frontend
   ↓
FastAPI API
   ↓
Application / Service Layer
   ↓
Domain Layer
   ↓
Infrastructure / Repository Layer
   ↓
SQLAlchemy
   ↓
MySQL
```

The **backend is the source of truth**.

A frontend prototype already exists, but the frontend was generated earlier and contains many fields, assumptions and workflows that do not exactly match the backend.

Therefore:

> **Do NOT modify the backend merely to satisfy the current frontend UI.**
>
> The frontend must eventually be corrected to match the actual backend/database/domain contracts.

---

# 2. IMPORTANT RULE FOR CONTINUATION

The project is already partially implemented.

The next developer/model must **NOT restart the project from scratch**.

Before writing anything:

1. Inspect the existing implementation.
2. Identify what already exists.
3. Preserve working architecture.
4. Preserve working tests.
5. Extend the existing architecture consistently.
6. Do not duplicate existing modules.
7. Do not replace working implementations with simpler architectures.
8. Do not redesign the project unnecessarily.

The goal is:

```text
Existing working foundation
          +
Incremental implementation
          ↓
Complete EPMS
```

not:

```text
Existing project
      ↓
Delete/rewrite
      ↓
New project
```

---

# 3. CURRENT DEVELOPMENT STATUS

At the current point, these backend areas have been implemented and tested:

### Completed backend modules

```text
1. Authentication / Identity
2. Departments
3. Designations
4. Employees
5. Attendance
```

Supporting architecture has also been implemented:

```text
6. Domain layer
7. Application/service layer
8. Repository pattern
9. Unit of Work
10. FastAPI dependency injection
11. Centralized exception handling
12. Automated tests
```

The backend currently runs successfully.

---

# 4. DATABASE STATUS

The project uses MySQL.

The authoritative database definition is:

```text
database/schema.sql
```

The schema contains **27 tables**.

The database name currently used is:

```text
employee_payroll_db
```

Do not invent a different database name unless there is a deliberate migration/configuration decision.

The project uses relational database principles including:

```text
Primary Keys
Foreign Keys
Unique Constraints
Check Constraints
Indexes
Referential Integrity
```

The storage engine is InnoDB.

The schema is the source of truth for future backend implementation.

Do not create random additional database structures merely to make a frontend screen work.

---

# 5. DATABASE IMPORTANT NOTE

There was a MySQL compatibility issue with the employee self-manager check constraint.

The original schema attempted to enforce the employee self-manager restriction using a check involving an auto-increment employee ID.

MySQL rejected this constraint.

That schema constraint was therefore removed/commented out.

The corresponding business rule should be handled in the application/domain layer where appropriate.

This has already been fixed in Git.

Do not reintroduce the invalid MySQL constraint without a technically valid redesign.

---

# 6. GIT STATUS / IMPORTANT CHANGE

A schema fix has already been committed:

```text
d49d185
Fix MySQL employee schema constraint
```

Other recent development commits include:

```text
2838e09
Attendance implementation
```

and:

```text
240a226
Employee module implementation
```

The GitHub repository is:

```text
https://github.com/Sharvil-tech/Employee-payroll-management-system1.git
```

Main branch:

```text
main
```

The working tree should be preserved rather than reset casually.

---

# 7. BACKEND ARCHITECTURE

The project follows a layered / clean architecture style.

The intended responsibility of each layer is:

## API layer

Handles:

```text
HTTP requests
HTTP responses
Path/query/body parameters
Authentication dependencies
API status codes
```

It should NOT contain large amounts of business logic.

---

## Application layer

Contains:

```text
Use cases
Application services
Workflow orchestration
Repository interaction
Unit-of-Work usage
Business-operation coordination
```

The application layer tells the system **what operation needs to happen**.

---

## Domain layer

Contains:

```text
Entities
Domain rules
Business invariants
Domain validation
Domain-specific behavior
```

The domain should remain independent of FastAPI and database-specific implementation.

---

## Infrastructure layer

Contains:

```text
SQLAlchemy models
Database engine
Database session
Repositories
Unit of Work
Persistence implementation
```

This layer handles the actual technical interaction with MySQL.

---

# 8. CURRENT BACKEND DIRECTORY CONCEPT

The project follows a structure similar to:

```text
app/
│
├── api/
│   ├── dependencies/
│   └── v1/
│       ├── endpoints/
│       └── router.py
│
├── application/
│   ├── identity/
│   ├── organization/
│   ├── employee/
│   └── attendance/
│
├── domain/
│   ├── organization/
│   ├── employee/
│   └── attendance/
│
├── infrastructure/
│   ├── database/
│   └── persistence/
│
├── core/
│   ├── config.py
│   ├── exceptions.py
│   └── security-related components
│
└── main.py
```

Future modules must follow the same architectural pattern.

---

# 9. API VERSIONING

Current API prefix:

```text
/api/v1
```

All future API modules should follow this versioning convention.

Do not create random unversioned endpoint paths unless there is a deliberate architectural reason.

---

# 10. AUTHENTICATION STATUS

Authentication has been implemented.

It includes the basic identity flow:

```text
Registration
Login
Password hashing
JWT
Current-user dependency
User status handling
```

The security layer includes JWT functionality and password hashing.

Current tests exist for:

```text
tests/security/test_password.py
tests/security/test_jwt.py
tests/api/test_current_user.py
```

Authentication is one of the completed foundations.

Do not rewrite authentication simply because a future frontend implementation is inconvenient.

---

# 11. JWT CONFIGURATION NOTE

The project uses:

```text
JWT_SECRET_KEY
```

in `.env`.

A local `.env` should use an adequately long secret.

The current test environment produced a warning because the configured secret was below the recommended 32-byte HMAC key length.

This is currently a **warning, not a test failure**.

A cleanup task may later replace the development secret with a stronger secret of at least 32 bytes.

Do not hard-code secrets into Git.

---

# 12. ORGANIZATION MODULE STATUS

Two organizational master-data modules exist:

```text
Departments
Designations
```

The backend supports the organizational relationships required for employee creation.

The general structure is:

```text
API
 ↓
Service
 ↓
Domain
 ↓
Repository
 ↓
Database
```

The organization API has already been tested.

The backend should remain authoritative for the fields that departments/designations actually contain.

Do not add frontend-only concepts such as arbitrary department descriptions or organizational hierarchy fields unless they are actually part of the database/domain requirements.

---

# 13. EMPLOYEE MODULE STATUS

Employee management has been implemented.

The employee schema includes concepts such as:

```text
employee_id
employee_code
user_id
first_name
last_name
department_id
designation_id
manager_employee_id
joining_date
employment_status
created_at
updated_at
```

Employment status is based on:

```text
ACTIVE
INACTIVE
TERMINATED
```

Business validation includes cases such as:

```text
duplicate employee code
missing user
missing department
missing designation
invalid manager
terminated manager
invalid relationship/state
```

Employee tests already exist.

The employee API is already working and tested.

---

# 14. ATTENDANCE MODULE STATUS

Attendance is implemented.

The authoritative attendance database structure contains:

```text
attendance_id
employee_id
attendance_date
check_in_time
check_out_time
attendance_status
created_at
updated_at
```

Canonical attendance statuses currently are:

```text
PRESENT
ABSENT
HALF_DAY
ON_LEAVE
HOLIDAY
```

There is a uniqueness rule on:

```text
(employee_id, attendance_date)
```

so one employee cannot have duplicate attendance records for the same date.

There is also time validation ensuring checkout does not occur before check-in when both are supplied.

Attendance has:

```text
domain logic
service logic
repository
API
schemas
SQLAlchemy model
tests
```

Attendance is a completed backend module.

Do not alter the canonical backend attendance statuses just to match frontend terminology.

---

# 15. TESTING STATUS

Automated testing is already implemented.

The framework being used is:

```text
pytest
```

Current test suite:

```text
128 tests
128 passed
```

The latest fresh-machine run produced:

```text
128 passed, 51 warnings
```

This means the existing tests are functioning on another Windows environment.

Warnings currently include:

```text
Starlette/httpx deprecation warning
JWT insecure key-length warning
```

These are cleanup items, not current blockers.

---

# 16. TEST DIRECTORY STRUCTURE

Current testing structure is approximately:

```text
tests/
│
├── api/
│   ├── test_attendance.py
│   ├── test_current_user.py
│   ├── test_employee.py
│   ├── test_health.py
│   └── test_organization.py
│
├── application/
│   └── identity/
│       └── test_user_service.py
│
├── security/
│   ├── test_jwt.py
│   └── test_password.py
│
├── unit/
│   ├── application/
│   │   ├── attendance/
│   │   ├── employee/
│   │   └── organization/
│   │
│   ├── domain/
│   │   ├── attendance/
│   │   ├── employee/
│   │   └── organization/
│   │
│   └── infrastructure/
│       └── persistence/
│           └── repositories/
│               └── test_attendance_repository.py
│
└── conftest.py
```

---

# 17. TESTING PHILOSOPHY

Future development must continue the same testing philosophy.

For each new module:

```text
Requirement
    ↓
Expected behavior
    ↓
Valid test cases
    ↓
Invalid test cases
    ↓
Business-rule test cases
    ↓
API tests
    ↓
Persistence tests where appropriate
    ↓
Run entire test suite
```

Do not only test the happy path.

For every module, ask:

```text
What should succeed?
What should fail?
What business rule can be violated?
What database constraint matters?
What happens with missing relationships?
What happens with duplicate data?
What happens with invalid state?
```

---

# 18. TEST TYPES TO CONTINUE USING

The project currently uses several testing levels.

### Domain/unit tests

Test business rules independently.

### Application/service tests

Test application workflows and service behavior.

### API tests

Test FastAPI HTTP behavior.

### Security tests

Test password/JWT behavior.

### Repository tests

Test persistence-related behavior where appropriate.

Future modules should follow this same pattern.

---

# 19. `conftest.py`

`tests/conftest.py` is used for shared pytest setup and reusable fixtures.

Future test code should reuse existing fixtures rather than duplicating setup unnecessarily.

Before creating new fixtures:

> Inspect the existing `conftest.py`.

Do not create five versions of the same test setup.

---

# 20. IMPORTANT TESTING PRINCIPLE

A passing test suite does not mean the system is mathematically guaranteed to have no bugs.

It means:

> All currently defined automated scenarios passed.

Future development must update the test suite whenever behavior is added or changed.

A feature is not considered complete merely because the implementation runs.

---

# 21. FRONTEND STATUS

A frontend prototype exists.

It is a React + TypeScript + Vite project.

The UI contains screens for concepts such as:

```text
Dashboard
Users
Roles & Permissions
Departments
Designations
Employee Directory
My Profile
Attendance
Leave
Salary Structures
Payroll Processing
Deductions & Tax
Payroll Validation
Payslips
Salary Reports
Leave Alerts
Exports
Audit Logs
Backup & Restore
System Monitoring
```

However:

> The current frontend is largely a prototype using mock/localStorage data and fake authentication.

It is **NOT yet the source of truth**.

The frontend should not be treated as proof that those backend modules already exist.

---

# 22. FRONTEND PROTOTYPE PROBLEMS

The frontend currently contains data fields that don't necessarily exist in the backend.

Examples include employee concepts such as:

```text
email
phone
DOB
gender
employmentType
address
emergencyContact
```

Some frontend organization models also contain extra concepts not represented in the current backend schema.

Attendance also contains frontend-only concepts such as:

```text
Late
workingHours
overtimeHours
remarks
```

while the backend currently uses:

```text
PRESENT
ABSENT
HALF_DAY
ON_LEAVE
HOLIDAY
```

These mismatches must eventually be resolved **in the frontend**, unless a legitimate backend requirement is identified.

---

# 23. FRONTEND AUTHENTICATION STATUS

The frontend currently has prototype/mock authentication.

It uses local/mock storage and fake token behavior.

This must eventually be replaced with the real backend authentication flow:

```text
React
 ↓
POST /api/v1/auth/login
 ↓
FastAPI
 ↓
JWT
 ↓
Frontend stores/uses actual authentication state
 ↓
Authenticated API calls
```

Do not keep fake authentication in the production version.

---

# 24. FRONTEND INTEGRATION ORDER

Do NOT connect every screen to the backend simultaneously.

Use this order:

```text
1. Authentication
2. Departments
3. Designations
4. Employees
5. Attendance
6. Leave
7. Compensation / Salary Structures
8. Payroll processing
9. Deductions / Tax
10. Payroll validation
11. Payslips
12. Reporting
13. Audit / administration
14. Infrastructure/admin utilities
```

Each frontend module should only be connected once its backend contract is stable.

---

# 25. FRONTEND INTEGRATION PRINCIPLE

The process must be:

```text
Database/schema
      ↓
Domain model
      ↓
Application service
      ↓
API endpoint
      ↓
API schema
      ↓
Frontend type
      ↓
Frontend service
      ↓
Frontend component
```

Do not reverse this and invent backend fields because the UI designer happened to include them.

---

# 26. REMAINING MAJOR BACKEND WORK

The biggest remaining work is to implement the business modules that are already represented in the system/database requirements but do not yet have the same level of backend implementation as employee and attendance.

These should be developed incrementally.

The likely major areas are:

```text
Leave Management
Salary / Compensation Management
Payroll Processing
Deductions & Tax
Payroll Validation
Payslips
Payroll Reports
Notifications / Leave Alerts
Exports
Audit Logging
Administration / System Monitoring
Backup / Restore
```

Important:

> Verify the exact existing schema, code structure, and requirements before implementing each one.

Do not assume that a frontend page means the backend behavior has already been specified.

---

# 27. MODULE IMPLEMENTATION TEMPLATE

Every new backend module should follow the established pattern.

For example, for Leave:

```text
app/
├── api/v1/endpoints/leave.py
│
├── application/leave/
│   ├── leave_service.py
│   └── schemas.py
│
├── domain/leave/
│   └── leave.py
│
└── infrastructure/persistence/
    ├── models/leave.py
    └── repositories/leave_repository.py
```

And tests:

```text
tests/
├── api/test_leave.py
├── unit/
│   ├── domain/leave/test_leave.py
│   ├── application/leave/test_leave_service.py
│   └── infrastructure/persistence/repositories/
│       └── test_leave_repository.py
```

The exact names can follow the existing conventions.

The key point is architectural consistency.

---

# 28. HOW TO IMPLEMENT EACH FUTURE MODULE

For each module, follow this sequence.

## Step A — Inspect schema

Read:

```text
database/schema.sql
```

Identify:

```text
tables
columns
primary keys
foreign keys
unique constraints
check constraints
indexes
relationships
```

---

## Step B — Define domain behavior

Ask:

```text
What is the entity?
What state can it have?
What actions are allowed?
What business rules must never be violated?
```

Create domain logic accordingly.

---

## Step C — Define application service

Create the use-case/service layer.

Examples:

```text
create
update
get
list
approve
reject
calculate
process
validate
finalize
```

Only implement operations actually required by the system.

---

## Step D — Add repository abstraction

Define what persistence operations are required.

Do not expose SQLAlchemy implementation details to the domain.

---

## Step E — Implement SQLAlchemy model

Map the table into the infrastructure layer.

Respect the existing schema.

Do not redesign the database casually.

---

## Step F — Implement repository

Implement the required database operations.

Use the existing repository conventions.

---

## Step G — Add Unit of Work interaction

Where multiple database changes must belong together:

```text
begin transaction
perform operations
commit
or rollback on failure
```

Use the existing Unit of Work pattern.

---

## Step H — Add API schemas

Define request/response validation through Pydantic schemas.

Do not leak arbitrary internal SQLAlchemy objects directly to clients.

---

## Step I — Add FastAPI endpoints

Keep endpoint logic thin.

The endpoint should primarily:

```text
receive request
resolve dependencies
call service
return response
```

---

## Step J — Add tests

Write:

```text
domain tests
service tests
API tests
repository tests where useful
```

Then run:

```powershell
pytest
```

---

## Step K — Swagger smoke test

Once automated tests pass:

```text
http://127.0.0.1:8000/docs
```

Test the actual endpoint manually.

---

# 29. LEAVE MODULE — LIKELY LOGICAL FLOW

Leave management should be designed carefully because it affects attendance and potentially payroll.

Potential conceptual flow:

```text
Employee
   ↓
Leave Request
   ↓
Validation
   ↓
Approval / Rejection
   ↓
Leave Status
   ↓
Attendance / Payroll implications
```

Do not invent exact leave statuses, approval roles, leave types or calculations until the schema/requirements are inspected.

---

# 30. SALARY / COMPENSATION MODULE

Salary/compensation should establish the employee's compensation structure before payroll processing.

Conceptually:

```text
Employee
   ↓
Salary Structure
   ↓
Earnings
   ↓
Allowances
   ↓
Deductions
   ↓
Payroll calculation
```

The exact table structure already exists in the database schema and must be followed.

Do not calculate payroll from frontend-only values.

---

# 31. PAYROLL PROCESSING

Payroll is one of the most important remaining areas.

The expected conceptual dependency chain is approximately:

```text
Employee
   +
Attendance
   +
Leave
   +
Salary Structure
   +
Deductions / Tax
   ↓
Payroll Calculation
   ↓
Payroll Record
   ↓
Validation
   ↓
Finalized Payroll
   ↓
Payslip
```

Payroll must not be implemented as a random "total salary = X" CRUD module.

It needs explicit calculation rules and proper validation.

---

# 32. PAYROLL VALIDATION

Payroll validation should act as a quality gate.

Conceptually:

```text
Calculated payroll
       ↓
Validation checks
       ↓
Problems?
   ↙       ↘
 yes       no
 ↓          ↓
reject     approve/finalize
```

Validation rules need to come from the actual requirements/schema/domain model.

---

# 33. PAYSLIPS

Payslips depend on completed/finalized payroll.

The system should not allow an invalid or unfinished payroll state to masquerade as a finalized payslip.

Conceptually:

```text
Payroll
   ↓
Validated
   ↓
Finalized
   ↓
Payslip generated
```

---

# 34. REPORTING

Reports should be based on actual backend data.

Examples may include:

```text
salary reports
payroll summaries
attendance reports
leave reports
employee reports
```

Do not create hard-coded dashboard numbers.

---

# 35. AUDIT LOGGING

Audit logs should eventually record important state-changing actions.

Conceptually:

```text
Who?
What action?
Which record?
When?
What changed?
```

This is particularly important for payroll and employee-management systems.

Do not implement an audit system that stores meaningless duplicate events.

---

# 36. ADMINISTRATION / SYSTEM FEATURES

The UI contains features such as:

```text
Backup & Restore
System Monitoring
Exports
```

These should be approached later, after the core business flow works.

Priority should be:

```text
Core business correctness
       ↓
Security
       ↓
Data integrity
       ↓
Testing
       ↓
Frontend integration
       ↓
Reports/admin utilities
```

Do not spend early development time polishing low-priority administration screens while payroll itself is incomplete.

---

# 37. RECOMMENDED DEVELOPMENT PRIORITY

The remaining work should be tackled in roughly this order:

```text
PHASE 1
Leave management

PHASE 2
Salary / compensation

PHASE 3
Deductions and tax

PHASE 4
Payroll calculation / processing

PHASE 5
Payroll validation

PHASE 6
Payslips

PHASE 7
Reports

PHASE 8
Audit logs

PHASE 9
Exports / alerts

PHASE 10
Admin/system utilities

PHASE 11
Frontend API integration

PHASE 12
Final testing / integration / cleanup
```

The order can be adjusted when schema relationships require it, but the core principle is:

> **Implement dependencies before dependent features.**

---

# 38. DO NOT IMPLEMENT ALL MODULES IN ONE STEP

For every feature:

```text
One module
   ↓
Implementation
   ↓
Tests
   ↓
Swagger/manual verification
   ↓
Full pytest
   ↓
Commit
   ↓
Next module
```

This prevents the project from becoming impossible to debug.

---

# 39. GIT WORKFLOW FOR FUTURE DEVELOPMENT

After completing a logical module:

```powershell
git status
```

Then:

```powershell
git add .
git commit -m "Implement <module>"
git push origin main
```

Avoid giant commits containing ten unrelated features.

Use meaningful commits.

Example:

```text
Implement leave management
```

or:

```text
Add payroll validation rules
```

---

# 40. REGRESSION TESTING RULE

After every significant module:

```powershell
pytest
```

The previously passing tests must continue to pass.

For example:

```text
Before leave:
128 passed

After leave:
128 + leave tests passed
```

The exact number depends on how many tests are added.

Never judge a new module only from its new tests.

Run the **entire suite**.

---

# 41. CURRENT WARNING CLEANUP TASKS

These are not immediate blockers, but eventually clean them up.

### Warning 1

Current test environment shows a Starlette/httpx deprecation warning.

The installed testing stack should eventually be updated according to the compatible versions used by the project.

Do this as a controlled dependency update, then rerun all tests.

### Warning 2

JWT secret is currently too short for the library's recommended HMAC key length.

Replace the development secret with a properly generated longer secret.

Again:

```text
Do not hard-code it.
Do not commit it.
```

---

# 42. ENVIRONMENT CONFIGURATION

Local `.env` contains environment-specific settings such as:

```env
DATABASE_USER=root
DATABASE_PASSWORD=<local-mysql-password>
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_NAME=employee_payroll_db
JWT_SECRET_KEY=<strong-secret>
```

Never expose real passwords or secrets in source control.

A future `.env.example` should contain placeholders rather than real credentials.

---

# 43. FRESH-SYSTEM REPRODUCIBILITY

The backend has already been successfully reproduced on another Windows system.

The verified sequence was:

```text
Python environment
      ↓
venv
      ↓
pip install -r requirements.txt
      ↓
MySQL
      ↓
employee_payroll_db
      ↓
schema.sql
      ↓
.env
      ↓
pytest
      ↓
128 passed
      ↓
uvicorn
      ↓
application startup successful
```

This is important evidence that the project foundation is reproducible.

---

# 44. FRONTEND FUTURE WORK

Once the backend business modules are sufficiently complete:

Replace prototype/mock services with real API calls.

The frontend already has an API client boundary.

The eventual architecture should become:

```text
React component
    ↓
Frontend service
    ↓
API client
    ↓
FastAPI
    ↓
Application service
    ↓
Domain
    ↓
Repository
    ↓
MySQL
```

Do not allow React components to contain database/business rules.

---

# 45. FRONTEND SERVICE MIGRATION

The existing mock services should gradually be replaced.

Do not rewrite the whole frontend.

Preserve:

```text
UI design
layout
components
navigation
visual styling
UX where sensible
```

Replace:

```text
mockData
localStorage CRUD
fake authentication
fake tokens
frontend-only assumptions
```

with real API integration.

---

# 46. FRONTEND DATA TYPES

The frontend TypeScript types must eventually match backend Pydantic/API schemas.

Example:

```text
Backend:
employment_status = ACTIVE | INACTIVE | TERMINATED
```

Frontend should use the same contract.

Do not create:

```text
ACTIVE
INACTIVE
TERMINATED
ON_NOTICE
RETIRED
LEFT
etc.
```

unless those states are actually supported by the backend requirements.

---

# 47. API CONTRACT RULE

For every frontend feature:

First identify:

```text
HTTP method
endpoint
request body
response body
status codes
authentication requirement
error behavior
```

Then implement the frontend service.

Do not make the frontend "guess" the API.

---

# 48. ERROR HANDLING

The backend has centralized exception handling.

Current domain-related categories include concepts such as:

```text
BusinessRuleViolation
InvalidDomainState
DomainError
unexpected Exception
```

HTTP responses use a structured error envelope containing information such as:

```text
code
message
request_id
```

Future modules must raise/use the existing exception architecture rather than inventing unrelated error response formats.

---

# 49. DEPENDENCY INJECTION

The backend uses FastAPI dependency injection.

Existing important dependency concepts include:

```text
current authenticated user
Unit of Work
```

Future endpoints should reuse these dependencies.

Do not manually construct database sessions inside endpoint functions if the established dependency architecture already handles this.

---

# 50. UNIT OF WORK RULE

The existing Unit of Work pattern is important.

It provides transaction coordination.

Conceptually:

```text
service
   ↓
Unit of Work
   ↓
repositories
   ↓
commit / rollback
```

Use it whenever a business operation involves multiple persistence changes that should succeed or fail together.

Do not bypass the Unit of Work with arbitrary direct SQLAlchemy sessions.

---

# 51. REPOSITORY RULE

Repositories abstract persistence.

The domain/application layer should not become tightly coupled to SQLAlchemy implementation details.

Future modules should follow the repository convention already established.

---

# 52. DOMAIN RULE

The domain layer should own actual business rules.

For example:

```text
A particular status transition is invalid.
A manager cannot be terminated while still assigned.
A payroll cannot be finalized while validation fails.
A leave request violates some business constraint.
```

The exact rules should be implemented where they belong rather than stuffing all business logic into endpoints.

---

# 53. DEFINITION OF "DONE" FOR A BACKEND MODULE

A module is **not done** merely because:

```text
the table exists
```

or:

```text
the endpoint returns 200
```

A complete module should have:

```text
database mapping
+
domain model/rules
+
application service
+
repository
+
Unit of Work integration where needed
+
Pydantic schemas
+
FastAPI endpoints
+
error handling
+
automated tests
+
Swagger smoke testing
+
full regression test
```

---

# 54. DEFINITION OF "DONE" FOR FRONTEND MODULE

A frontend module is done only when:

```text
UI
+
TypeScript types
+
API service
+
authentication handling
+
loading state
+
error state
+
success handling
+
backend-compatible validation
+
real API integration
```

Mock localStorage behavior should not remain in the final connected version.

---

# 55. IMPORTANT: DON'T OVERENGINEER

The project should be well architected, but do not add complexity for its own sake.

Avoid:

```text
unnecessary microservices
unnecessary event buses
unnecessary caching
unnecessary abstractions
unnecessary frameworks
```

The current stack is sufficient:

```text
FastAPI
Pydantic
SQLAlchemy
MySQL
pytest
React
TypeScript
Vite
```

Build a solid monolithic application with clean internal layers.

---

# 56. PRACTICAL WORKING STYLE FOR THE NEXT MODEL

For each new request, the model should follow:

```text
1. Inspect existing code.
2. Identify affected module.
3. Identify schema dependencies.
4. Identify existing architectural convention.
5. Plan small change.
6. Implement.
7. Add/update tests.
8. Run targeted tests.
9. Run full pytest.
10. Run Swagger smoke test.
11. Only then move on.
```

Do not make large batches of speculative changes.

---

# 57. BEFORE IMPLEMENTING ANY FUTURE MODULE

Always inspect:

```text
database/schema.sql
existing neighboring module
existing repository style
existing service style
existing domain style
existing API style
existing tests
```

For example, before creating Leave:

Inspect:

```text
attendance
employee
organization
```

because Leave may depend on these.

---

# 58. NEVER BREAK THE EXISTING MODULES

Existing modules:

```text
Authentication
Organization
Employee
Attendance
```

are foundational.

New modules should integrate with them.

Do not rewrite them unless an actual defect is discovered.

When making a change:

```text
new feature must not break old feature
```

Verify with regression tests.

---

# 59. CURRENT PROJECT MATURITY

The project is currently at:

```text
FOUNDATION + CORE HR MODULES COMPLETE
```

not yet at:

```text
FULL PAYROLL SYSTEM COMPLETE
```

This distinction is important.

Completed:

```text
architecture
database foundation
authentication
organization
employee
attendance
testing foundation
```

Remaining:

```text
leave
salary
deductions/tax
payroll
validation
payslips
reports
audit/admin
frontend real integration
final QA
```

Do not claim the entire payroll workflow is already implemented.

---

# 60. TEAM MEMBER #10 — TESTING CONTRIBUTION

One team member is specifically responsible for:

```text
Testing and Quality Assurance
```

That role should understand:

```text
pytest
test cases
unit tests
API tests
domain tests
service tests
repository tests
security tests
fixtures
mocks
assertions
regression testing
smoke testing
```

The person should be able to demonstrate:

```text
tests/
```

and explain how requirements became test cases.

Current evidence:

```text
pytest
128 passed
```

---

# 61. TEST CASE DESIGN EXAMPLE

For employee creation:

### Positive case

```text
Valid employee
        ↓
Create request
        ↓
Employee created
```

### Negative case

```text
Duplicate employee code
        ↓
Create request
        ↓
Business rule violation
        ↓
Error response
```

### Another negative case

```text
Missing department
        ↓
Create request
        ↓
Validation/business error
```

This same philosophy should be used for every future module.

---

# 62. FINAL DEVELOPMENT ROADMAP

The overall roadmap is:

```text
                    EPMS
                     │
          ┌──────────┴──────────┐
          │                     │
       BACKEND               FRONTEND
          │                     │
          ▼                     ▼
 Authentication             Prototype
 Organization                   │
 Employee                       │
 Attendance                     │
          │                     │
          ▼                     │
      Leave                     │
          │                     │
      Salary                    │
          │                     │
   Deductions/Tax               │
          │                     │
      Payroll                   │
          │                     │
    Validation                  │
          │                     │
     Payslips                   │
          │                     │
      Reports                   │
          │                     │
    Audit/Admin                 │
          │                     │
          └──────────┬──────────┘
                     ▼
             REAL API INTEGRATION
                     │
                     ▼
              SYSTEM QA / UAT
                     │
                     ▼
              FINAL PROJECT
```

---

# 63. FINAL RULES FOR THE NEXT MODEL

These rules are especially important:

```text
RULE 1:
Do not redo completed modules.

RULE 2:
Do not trust the current frontend as the backend specification.

RULE 3:
database/schema.sql is authoritative for database structure.

RULE 4:
Backend architecture is authoritative for implementation structure.

RULE 5:
New functionality must follow the existing layered architecture.

RULE 6:
Every meaningful feature requires tests.

RULE 7:
Run the full pytest suite after significant changes.

RULE 8:
Preserve existing passing tests.

RULE 9:
Use existing exceptions, repositories, Unit of Work and dependency patterns.

RULE 10:
Do not put business logic into FastAPI endpoints unnecessarily.

RULE 11:
Do not hard-code passwords, JWT secrets or database credentials.

RULE 12:
Implement dependent modules in dependency order.

RULE 13:
Do not mark a module complete until implementation + tests + API verification are done.

RULE 14:
Prefer small, verifiable increments over large rewrites.

RULE 15:
When uncertain about a future module, inspect the schema and existing project before making assumptions.
```

---

# 64. THE IMMEDIATE NEXT TASK

The immediate next development stage should **not** be frontend polishing.

The priority is:

```text
Review current completed backend
        ↓
Identify exact remaining schema/business modules
        ↓
Implement Leave Management
        ↓
Test Leave
        ↓
Implement Salary/Compensation
        ↓
Test
        ↓
Implement Deductions/Tax
        ↓
Test
        ↓
Implement Payroll
        ↓
Test
        ↓
Validation
        ↓
Payslips
        ↓
Reports
        ↓
Admin/Audit/Exports
        ↓
Integrate frontend
        ↓
Full system QA
```

Before each stage, inspect the existing project rather than assuming missing pieces.

---

## ONE-SENTENCE PROJECT STATE

> **EPMS currently has a working FastAPI/MySQL layered backend with authentication, organization, employee and attendance functionality, supported by 128 passing automated tests, while the major remaining work is the payroll-related business modules and subsequent real frontend/API integration.**
