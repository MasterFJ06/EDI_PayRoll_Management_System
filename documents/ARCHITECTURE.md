# EPMS Architecture

## 1. System

Employee Payroll Management System (EPMS)

EPMS is a database-driven enterprise-style employee management and payroll system.

The system provides:

- identity and access management
- organization management
- employee management
- workforce operations
- payroll management
- reporting and analytics
- administration and governance
- system infrastructure

---

# 2. Bounded Contexts

The system is divided into eight bounded contexts.

## 2.1 Identity & Access Management

Responsibilities:

- user registration
- authentication
- password management
- roles
- permissions
- user-role assignment
- role-permission assignment
- access control

---

## 2.2 Organization Management

Responsibilities:

- departments
- designations
- organizational structure

---

## 2.3 Employee Management

Responsibilities:

- employee records
- employee identity linkage
- employment status
- department assignment
- designation assignment
- manager relationships
- employment history

---

## 2.4 Workforce Operations

Responsibilities:

- attendance
- leave types
- leave balances
- leave requests

---

## 2.5 Payroll Management

Responsibilities:

- salary structures
- salary components
- salary revisions
- salary revision components
- employee salary assignments
- payroll runs
- payroll results
- payroll result components
- payroll processing issues
- payslips

Payroll validation is treated as an independent QA responsibility within payroll processing.

---

## 2.6 Reporting & Analytics

Responsibilities:

- salary reports
- dashboard analytics
- leave balance alerts
- report exports

This context does not introduce additional authoritative database tables at the current architecture stage.

---

## 2.7 Administration & Governance

Responsibilities:

- audit events
- audit event changes
- security events
- administrative governance

---

## 2.8 System Infrastructure

Responsibilities:

- backup and restore
- system monitoring
- infrastructure-level operational concerns

---

# 3. Backend Layers

The backend follows:

React client/UI
↓
FastAPI REST API
↓
Application / Use Cases / Unit of Work
↓
Domain entities / rules / services
↓
Infrastructure / repositories / SQLAlchemy
↓
MySQL

---

# 4. API Layer

FastAPI provides REST endpoints.

API version prefix:

`/api/v1`

API endpoints should remain thin.

Business rules belong in the application/domain layers.

---

# 5. Application Layer

Application services implement use cases and orchestrate:

- repositories
- domain entities
- transaction boundaries
- application validation

---

# 6. Domain Layer

The domain layer contains:

- entities
- value objects
- domain exceptions
- domain behavior
- repository contracts

Domain code should not depend on FastAPI.

---

# 7. Infrastructure Layer

Infrastructure contains:

- SQLAlchemy models
- repositories
- database engine
- sessions
- Unit of Work
- security infrastructure
- concurrency infrastructure
- logging infrastructure

---

# 8. Transaction Management

The application uses Unit of Work.

The Unit of Work coordinates repositories sharing a database session.

Current repository groups include:

- users
- refresh tokens
- departments
- designations
- employees
- attendance

Additional repositories will be added as modules are implemented.

---

# 9. Security

Security architecture includes:

- HTTPS in deployed environments
- short-lived JWT access tokens
- revocable/rotated refresh tokens
- Argon2id password hashing
- backend RBAC
- object-level authorization
- DTO validation
- parameterized database access

### Role-Based Authorization

The persisted authorization chain is
`users → user_roles → roles → role_permissions → permissions`.
Protected APIs use the validated current user from the JWT dependency and the reusable
`require_permission(permission_code)` dependency. Permission checks read current role and
permission assignments from the shared Unit of Work session; inactive roles do not grant
permissions. Missing/invalid authentication returns HTTP 401, and an authenticated user
without the required permission receives HTTP 403. Role assignment is not exposed as an
API operation by this authorization prerequisite.

---

# 10. Concurrency

Payroll processing is expected to support controlled concurrent processing.

Planned controls:

- bounded worker pool
- independent database session per worker
- persisted processing state
- row locking
- unique constraints
- conditional updates
- consistent lock ordering
- bounded deadlock retry

---

# 11. Frontend

The current frontend is a visual prototype.

It is not the architectural authority.

The frontend must adapt to the backend contracts.
