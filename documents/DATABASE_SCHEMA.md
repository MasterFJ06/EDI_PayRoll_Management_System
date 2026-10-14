# EPMS Database Schema

## Authority

The physical database schema is defined by:

`database/schema.sql`

This document summarizes the authoritative schema.

Do not add, remove, rename, or restructure tables based only on frontend requirements.

---

# Authoritative Tables

The current EPMS schema contains exactly 34 authoritative tables.

## 1. Identity & Access

1. users
2. refresh_tokens
3. roles
4. permissions
5. user_roles
6. role_permissions

---

## 2. Organization

7. departments
8. designations

---

## 3. Employee Management

9. employees
10. employment_history

---

## 4. Workforce Operations

11. attendance_records
12. leave_types
13. leave_balances
14. leave_requests
15. leave_request_days

---

## 5. Compensation / Payroll

16. salary_structures
17. salary_components
18. salary_revisions
19. salary_revision_components
20. employee_salary_assignments
21. payroll_runs
22. payroll_run_workforce_snapshots
23. payroll_results
24. payroll_result_components
25. payroll_processing_issues
26. payslips

---

## 6. Administration & Governance

27. audit_events
28. audit_event_changes
29. security_events

---

## 7. System Configuration

30. system_settings

## 8. Workforce Architecture Foundation

31. work_calendar_versions
32. work_calendar_weekly_rules
33. work_calendar_date_overrides
34. workforce_overtime_policy_versions

`refresh_tokens` stores only SHA-256 token hashes, expiry/revocation timestamps,
the owning user, and a session-family identifier used for rotation and scoped
replay/logout revocation. Plaintext refresh credentials are returned only at
issuance and are never persisted.

---

# Important Relationships

## Users

`users`

Primary identity record.

`refresh_tokens.user_id`
→ `users.user_id`

Refresh-token rows persist only the SHA-256 digest and use `family_id` to scope
rotation replay and logout revocation to one login session.

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

stores generated payslip records. `document_path` is nullable until document
generation is implemented; record-only payslips have no document path.

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
