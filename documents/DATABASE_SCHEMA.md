# EPMS Database Schema

## Authority

The physical database schema is defined by:

`database/schema.sql`

This document summarizes the authoritative schema.

Do not add, remove, rename, or restructure tables based only on frontend requirements.

---

# Authoritative Tables

The current EPMS schema contains exactly 33 authoritative tables.

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
14. leave_request_days

---

## 5. Compensation / Payroll

15. salary_structures
16. salary_components
17. salary_revisions
18. salary_revision_components
19. employee_salary_assignments
20. payroll_runs
21. payroll_run_workforce_snapshots
22. payroll_results
23. payroll_result_components
24. payroll_processing_issues
25. payslips

---

## 6. Administration & Governance

26. audit_events
27. audit_event_changes
28. security_events

---

## 7. System Configuration

29. system_settings

## 8. Workforce Architecture Foundation

30. work_calendar_versions
31. work_calendar_weekly_rules
32. work_calendar_date_overrides
33. workforce_overtime_policy_versions

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

`employees.joining_date` is the inclusive employment start date.
`employees.employment_end_date` is a nullable DATE containing the inclusive end
date; null means employment is open-ended. When present, it must be on or after
`joining_date`.

`employment_history` represents organizational assignment history only and does
not determine employment intervals.

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

defines available leave categories and their required `payroll_treatment` (`PAID`
or `UNPAID`). Treatment is explicit and is never inferred from the name or
description.

`leave_balances`

stores employee leave balances.

`leave_requests`

stores employee leave requests.

`leave_request_days` stores unique per-request date allocations as `DECIMAL(4,2)`
fractions between 0.01 and 1.00. Leave request creation validates unique
in-period working dates against the Work Calendar and exact Decimal total equality.
Approval revalidates allocations and prevents approved date overlaps per employee.
Lifecycle changes and creation are audited transactionally.

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

represents payroll processing runs and includes the persisted attempt generation
and nullable processing lease expiration fields. This phase adds only the fields;
attempt claiming and lease behavior remain future work.

`payroll_run_workforce_snapshots`

stores one temporary JSON Workforce snapshot per Payroll Run and employee for the
current attempt, tagged with the attempt number and snapshot timestamp. It is a
Payroll-owned persistence mechanism. Workforce snapshot materialization is
implemented in Payroll Phase B.5; failed-attempt snapshot cleanup is part of the
existing B.3 retry reconciliation.

`payroll_results`

represents employee-level payroll results.
It includes nullable `workforce_calculation_snapshot` JSON so results created
before Workforce processing exists remain valid.

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

## Workforce Architecture Foundation

`work_calendar_versions` stores versioned organization-wide calendar settings;
`work_calendar_weekly_rules` defines ISO weekday classifications and fixed
scheduled minutes; `work_calendar_date_overrides` supports date-specific
working, non-working, and holiday classifications. Work Calendar application
services enforce overlap, date/rule validation, immutability, audit, and
FAILED-only correction checks against monthly Payroll Runs.
`workforce_overtime_policy_versions` stores effective-dated non-working
multipliers; its workflow remains future work.

`salary_revision_components.is_overtime_base` is a non-null boolean defaulting
to `FALSE`. Existing components are not designated automatically.

---

# Important Rule

If a task appears to require a table or column not listed here:

1. Inspect `database/schema.sql`.
2. Determine whether the structure already exists.
3. If it does not exist, do not invent it.
4. Stop and request an architectural/schema decision.
