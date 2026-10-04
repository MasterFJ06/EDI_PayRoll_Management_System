# EPMS Database Schema

## Authority

The physical database schema is defined by:

`database/schema.sql`

This document summarizes the authoritative schema.

Do not add, remove, rename, or restructure tables based only on frontend requirements.

---

# Authoritative Tables

The current EPMS schema contains exactly 27 authoritative tables.

## 1. Identity & Access

1. users
2. roles
3. permissions
4. user_roles
5. role_permissions

---

## 2. Organization

6. departments
7. designations

---

## 3. Employee Management

8. employees
9. employment_history

---

## 4. Workforce Operations

10. attendance_records
11. leave_types
12. leave_balances
13. leave_requests

---

## 5. Compensation / Payroll

14. salary_structures
15. salary_components
16. salary_revisions
17. salary_revision_components
18. employee_salary_assignments
19. payroll_runs
20. payroll_results
21. payroll_result_components
22. payroll_processing_issues
23. payslips

---

## 6. Administration & Governance

24. audit_events
25. audit_event_changes
26. security_events

---

## 7. System Configuration

27. system_settings

---

# Important Relationships

## Users

`users`

Primary identity record.

---

## Roles

`user_roles`

connects users to roles.

`role_permissions`

connects roles to permissions.

---

## Organization

`employees.department_id`
→ `departments.department_id`

`employees.designation_id`
→ `designations.designation_id`

---

## Employees

`employees.user_id`
→ `users.user_id`

`employees.manager_employee_id`
→ `employees.employee_id`

---

## Attendance

`attendance_records.employee_id`
→ `employees.employee_id`

Unique business key:

`(employee_id, attendance_date)`

Attendance statuses:

- PRESENT
- ABSENT
- HALF_DAY
- ON_LEAVE
- HOLIDAY

---

## Leave

`leave_types`

defines available leave categories.

`leave_balances`

stores employee leave balances.

`leave_requests`

stores employee leave requests.

The detailed constraints must be taken from `database/schema.sql`.

---

## Salary

Salary structures define salary templates.

Salary components define salary components.

Salary revisions represent changes to structures/components.

Employee salary assignments connect employees to applicable salary structures.

---

## Payroll

`payroll_runs`

represents payroll processing runs.

`payroll_results`

represents employee-level payroll results.

`payroll_result_components`

stores component-level payroll results.

`payroll_processing_issues`

stores processing/validation issues.

`payslips`

stores generated payslip records.

---

## Audit

`audit_events`

stores audit events.

`audit_event_changes`

stores changes associated with audit events.

---

## Security

`security_events`

stores security-related events.

---

## Configuration

`system_settings`

stores system-level settings.

---

# Important Rule

If a task appears to require a table or column not listed here:

1. Inspect `database/schema.sql`.
2. Determine whether the structure already exists.
3. If it does not exist, do not invent it.
4. Stop and request an architectural/schema decision.