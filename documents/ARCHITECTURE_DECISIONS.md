# EPMS Architecture Decisions

This document records major architecture decisions that must not be casually reversed.

---

# ADP-001 — Identity & Access Management

Identity and Access Management is consolidated as one bounded context.

Responsibilities include:

- users
- authentication
- roles
- permissions
- user-role assignment
- role-permission assignment

Authentication and RBAC are not treated as unrelated independent modules.

---

# ADP-002 — Organization and Employee Management

Organization Management and Employee Management are separate bounded contexts.

Organization Management owns:

- departments
- designations

Employee Management owns:

- employee records
- employment relationships
- employee organizational assignments

This separation prevents organizational reference data from becoming tightly coupled to employee lifecycle behavior.

---

# ADP-003 — Workforce and Payroll Separation

Workforce Operations and Payroll Management are separate.

Workforce Operations owns:

- attendance
- leave

Payroll Management owns:

- salary structures
- salary revisions
- employee salary assignments
- payroll processing
- payroll results
- payslips

Attendance and leave are inputs to payroll but are not themselves payroll entities.

---

# ADP-004 — Team 3 Decomposition

Reporting & Analytics contains:

- salary reports
- dashboard analytics
- leave balance alerts
- report exports

Administration & Governance contains:

- audit events
- security events

System Infrastructure contains:

- backup and restore
- system monitoring

Reporting & Analytics does not introduce additional authoritative tables at the current architecture stage.

---

# EDR-001 — Identity Consolidation

Identity-related functionality is consolidated rather than splitting authentication, users, roles, and permissions into independent bounded contexts.

---

# EDR-002 — Organization vs Employee

Departments/designations are organizational reference data.

Employee records represent employee lifecycle and organizational assignment.

They remain separate responsibilities.

---

# EDR-003 — Attendance vs Leave

Attendance and leave are separate concerns.

Attendance records represent attendance state.

Leave requests/balances/types represent leave lifecycle.

---

# EDR-004 — Salary Structure vs Payroll Processing

Salary definition/configuration is separate from payroll execution.

Salary structures/components define compensation.

Payroll runs/results represent processing.

---

# EDR-005 — Payroll Validation

Payroll validation is treated as an independent quality-assurance responsibility inside payroll processing.

Validation must not be reduced to UI-only validation.

---

# Repository / Infrastructure Decision

Repositories use the existing Unit of Work and SQLAlchemy infrastructure.

The current implementation uses ORM models directly in some application services.

Do not introduce a mapper layer simply for theoretical purity unless an explicit architecture decision is made.

---

# Error Handling Decision

Domain exceptions are translated centrally by the FastAPI exception handling layer.

Do not introduce unrelated endpoint-specific error formats.

---

# Frontend Decision

The frontend is not an architectural authority.

The backend/domain/database architecture defines what the frontend should represent.

Frontend mock fields must not force changes to the backend.