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

# Decision 5 — Payroll Run State Machine

The supported Payroll Run transitions are:

- `CREATED → PROCESSING`
- `PROCESSING → PROCESSED`
- `PROCESSING → FAILED`
- `FAILED → PROCESSING` through controlled retry only
- `PROCESSED → FINALIZED`

Invalid transitions are rejected. `FINALIZED` is terminal. Retry is only
`FAILED → PROCESSING`; `CREATED`, `PROCESSING`, `PROCESSED`, and `FINALIZED`
runs cannot be retried. `/process` remains limited to `CREATED` runs.

---

# Decision 10 — Payroll Retry Transaction

Retry reconciliation and activation of the new attempt use one database
transaction through the existing Unit of Work. That transaction includes the
Payroll Run row lock, failed result/component cleanup, failed-attempt temporary
Workforce snapshot cleanup, attempt increment, `started_at` refresh, lease
creation, state transition, and retry audit record. Any failure rolls back the
entire transaction; the run remains `FAILED` and no partial reconciliation or
new attempt is committed.

---

# Decision 11 — Payroll Retry and Idempotency

Retry is a controlled operation available only for `FAILED` runs. The retry
claim is serialized so exactly one concurrent request succeeds and increments
`attempt_number` once; competing requests receive a conflict. No idempotency key
is required for this conditional state transition. A successful retry receives
fresh compensation and Workforce snapshots. `/process` remains `CREATED`-only.

---

# Decision 17 — Failed Payroll Attempt Data

Payroll Results and Payroll Result Components from a failed attempt are
non-authoritative while the run is `FAILED` and are reconciled before retry.
Issues and audit records survive retry. Per-employee temporary Workforce
snapshots remain available while the run is `FAILED` and are deleted as part of
retry reconciliation. No attempt-history table is introduced.

Retry locks the parent Payroll Run first and verifies that its status is
`FAILED`, its current `attempt_number` is the expected failed attempt, and no
payslip is attached. Finalized data is never reconciled. If reconciliation
fails, the whole transaction rolls back, the run remains `FAILED`, and the old
attempt artifacts remain intact.

Every attempt-owned write validates the current Payroll Run attempt under the
parent-row lock, including the run ID, attempt number, `PROCESSING` status, and a
valid lease where applicable. A payslip found on a `FAILED` run is an invariant
violation that blocks retry; payslips are never modified or deleted during
reconciliation.

The operational lease duration is `PAYROLL_ATTEMPT_LEASE_SECONDS = 900`
(15 minutes). The expiration is stored in `payroll_runs.attempt_lease_expires_at`
using a database timestamp. The active owner renews the lease; guarded writes
validate it, and crash recovery uses it. Lease renewal and recovery are later
implementation work. No heartbeat cadence is established here.

---

# Decision 18 — Payroll Processing Issues

Payroll Processing Issues survive retry. Unresolved issues remain blocking.
Issue creation must be fenced to the active Payroll Run attempt. No
`attempt_number` column is required on issues at this time.

---

# Decision 19 — Payroll Run Finalization

`FINALIZED` is terminal. Final Payroll Results and their workforce snapshots
are immutable. Payslips are generated only after finalization and are never
reconciled or modified by retry. Finalization follows the same parent Payroll
Run locking discipline used by attempt-owned writes. Retry is unavailable after
`PROCESSED` or `FINALIZED`.

---

# Decision 21 — Payroll Retry API and Authorization

Payroll retry is a separate authenticated operation requiring
`payroll.run.retry`. The actor is derived from the authenticated user. It is
available only for `FAILED` runs; `/process` remains `CREATED`-only. The
contractual endpoint and HTTP behavior are recorded in `API_CONTRACTS.md`.

---

# Decision 22 — Payroll Retry Audit

Retry and reconciliation use the existing audit infrastructure. The retry
event is `PAYROLL_RUN_RETRY_CLAIMED` and may record the run ID, old and new
attempt numbers, deleted result/component/snapshot counts, actor, and
correlation ID. Audit details must not include salary amounts, gross earnings,
deductions, net salary, or other sensitive payroll data. No audit table is
added.

---

# Decision 12A — Employment Interval Representation

An employee's single supported employment interval is represented on the employee
record: `joining_date` is the start and nullable `employment_end_date` is the end.
Both boundaries are inclusive; a null end date means open-ended employment. The end
date must be on or after the joining date. Current `employment_status` does not
override these dates when evaluating past payroll periods.

`employment_history` records organizational assignment changes (department,
designation, and manager) only. Its effective dates do not define employment dates.
Rehire and multiple independent employment intervals are out of scope and require a
separate architecture decision.

Future payroll eligibility may select an employee for a calendar period when
`joining_date <= payroll_period_end` and (`employment_end_date` is null or
`employment_end_date >= payroll_period_start`). This decision establishes the data
model only; it does not itself implement eligibility resolution, proration, or
calculation.

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

---

# Decision 24 — Compensation Applicability & Snapshot Boundary

The compensation snapshot boundary is the processing-start timestamp persisted by
the atomic `CREATED` to `PROCESSING` Payroll Run transition. Assignment and revision
effective intervals are inclusive: `effective_from <= snapshot_date` and
(`effective_to IS NULL` or `effective_to >= snapshot_date`). Adjacent intervals are
valid. More than one applicable employee salary assignment is ambiguous and blocking;
no latest-date, creation-time, or ID precedence may be applied. A future retry must
resolve a fresh compensation snapshot at its new processing-start timestamp.
`attempt_number` increments atomically on each successful initial claim or retry
claim and fences stale workers from writing to a later attempt. The immutable
compensation representation is persisted in the temporary Workforce snapshot
table according to Decision 30; the assignment and revision applicability rules
in this decision are unchanged.

---

# Decision 25 — Compensation Revision Scope

An applicable `EmployeeSalaryAssignment.salary_revision_id` is the authoritative
reference to exactly one salary revision. Only that referenced revision is checked
for existence and inclusive effective-date applicability. Other revisions belonging
to the same salary structure are ignored for selection; no revision precedence or
multiple-applicable-revision selection rule is defined.

---

# Decision 26 — Payroll Processing Issue Semantics

An `OPEN` Payroll Processing Issue is blocking; a `RESOLVED` issue is non-blocking.
Every unresolved issue blocks successful Payroll processing completion. Compensation
unavailability or ambiguity for an eligible employee creates an OPEN issue through
the existing issue infrastructure. Employees excluded by Payroll eligibility are a
normal outcome and do not receive compensation issues. Issues survive retry, and
issue creation must be fenced to the active attempt as defined in Decision 18.
Issues do not require a persisted `attempt_number` column at this time.

---

# Decision 29 — Overtime Calculation Inputs

Overtime uses the applicable fixed EARNING overtime-base component and the
payroll month's full Work Calendar working-day count. The hourly overtime rate
is the monthly overtime base divided by that full-month working-day count and
then divided by eight. The denominator counts every date classified as
`WORKING_DAY` in the complete payroll calendar month; it is not restricted by
an employee's employment range or compensation segments.

OT timestamp anomaly treatment is defined in Decision 36.

---

# Decision 30 — Consistent Workforce Snapshot

After an attempt is atomically claimed, Payroll materializes Workforce inputs using
one consistent read transaction. It stores one immutable temporary snapshot row per
Payroll Run and employee, tagged with the current `attempt_number` and snapshot
timestamp. Temporary snapshots survive while the run is `PROCESSING` or `FAILED`.

The snapshot preserves employee-specific daily calendar classifications needed
for attendance, leave, overtime, and compensation-segment evaluation. It also
preserves `monthly_working_day_count`: the count of dates classified as
`WORKING_DAY` across the complete payroll calendar month, derived from the
authoritative Work Calendar during the B.5 consistent read. This full-month
denominator is calendar-wide for the payroll month and is independent of the
employee-specific employment range, including mid-month joining or leaving. The
two date scopes are distinct: employee-specific dates supply employee inputs;
the full-month count supplies the overtime hourly-rate denominator in Decision
29. Phase 2B-5 consumes this frozen count and must not query the live Work
Calendar during financial calculation. No additional table is required; the
value is part of the existing Workforce snapshot.

Retry deletes the failed attempt's temporary snapshots atomically with failed
Payroll Result and component reconciliation and activation of the next attempt.
Attempt-owned snapshot reads and writes are fenced by run ID, current attempt,
`PROCESSING` status, and a valid lease where applicable, coordinated through the
parent Payroll Run row lock. A successful snapshot is copied into its Payroll
Result; the final Payroll Result retains that snapshot immutably. No attempt-history
table or duplicate Workforce fact tables are introduced.

---

# Decision 31 — Workforce Consistent Read Boundary

Decision 30's consistent Workforce read is established explicitly using MySQL
8.x/InnoDB semantics and `REPEATABLE READ`. The application must not rely on the
MySQL server's global or default transaction isolation setting. The Workforce
snapshot phase begins a dedicated transaction after the Payroll Run's successful
`CREATED` to `PROCESSING` claim has committed, and explicitly establishes an
InnoDB consistent snapshot. SQLAlchemy implicit transaction autobegin alone is
not the architectural guarantee.

All data used to materialize the Decision 30 snapshot—including eligibility
and Workforce source data, Attendance, Leave, Work Calendar, Overtime Policy,
and Compensation inputs—must be read through the same SQLAlchemy Session and
database connection in that transaction. Individual input categories must not
use separate sessions or connections.

The snapshot metadata timestamp is obtained from database `CURRENT_TIMESTAMP(6)`
within the established snapshot transaction. It describes the snapshot
operation; the InnoDB consistent snapshot establishes the read boundary. Python
wall-clock time is not authoritative for this timestamp.

The consistent-read transaction is for input acquisition and snapshot
materialization. It does not claim or transition the Payroll Run, create Payroll
Results or financial components, or mutate Attendance, Leave, Calendar,
Overtime Policy, or Compensation data. The claim transaction and Workforce
snapshot transaction remain separate. Snapshot persistence remains subject to
the active-attempt fencing in Decisions 17 and 18; this read mechanism does not
replace Payroll Run locking, attempt-number validation, `PROCESSING` validation,
or lease validation.

Each retry attempt establishes a new consistent-read transaction and a fresh
snapshot. A failed attempt's temporary snapshot remains available while the run
is `FAILED`; retry deletes it as part of the existing reconciliation transaction
before activating the next attempt. Tables participating in the authoritative
Workforce snapshot use InnoDB so the documented consistent-read semantics apply.

---

# Decision 32 — Workforce-Derived Payroll Component Representation

`payroll_result_components` continues to identify real salary components and
retains its uniqueness per Payroll Result and salary component. Workforce-derived
payroll effects do not create synthetic salary components or additional result
component rows.

Attendance and approved Leave effects modify the calculated amount of applicable
existing EARNING salary components. Overtime is incorporated into the calculated
amount of the existing designated overtime-base EARNING component, which must be
FIXED. The final amount for each existing salary component is persisted once.

The Payroll Result's `workforce_calculation_snapshot` preserves the frozen
Workforce inputs and their calculation effects, including attendance, Leave,
payable fractions, unpaid Leave effects, overtime minutes and hours, overtime
base, `monthly_working_day_count`, hourly rate inputs, multiplier, calculated
Workforce-derived amounts, applicable policy/version information, and source
identifiers where applicable. This preserves the distinction between base
compensation and Workforce-derived effects for historical auditability.

Gross earnings, total deductions, and net salary continue to be derived from
the final Payroll Result Component amounts: gross is the sum of EARNING
components, deductions are the sum of DEDUCTION components, and net is gross
minus deductions. Attendance or Leave reductions to an EARNING component reduce
gross; they do not automatically create a separate deduction component.

This representation uses the existing tables and requires no schema, table, or
API change. The salary-component dependency graph is determined only by the
configured salary revision components and is evaluated before Workforce-derived
effects are applied. Percentage components use the compensation calculation
amount of their configured base component, before any Workforce-derived addition
or reduction. Workforce effects do not create or modify dependency edges. Final
Payroll Result Component amounts include applicable Workforce effects, and the
historical calculation snapshot preserves the compensation calculation amount,
Workforce-derived adjustment, and final amount separately.

For example, when Basic compensation is 30,000, overtime added to Basic is 2,000,
and HRA is 20% of Basic, HRA is calculated as 6,000 from the 30,000 compensation
amount. The final Basic Payroll Result Component amount is 32,000; overtime does
not change HRA's percentage base. Similarly, an unpaid-leave reduction of 3,000
makes Basic's final amount 27,000 while a percentage component based on Basic
continues to use the 30,000 compensation calculation amount.

---

# Decision 33 — Compensation Proration and Workforce Earning Allocation

This decision clarifies the compensation proration rule referred to as D14 and
supplements Decisions 29, 30, and 32. It does not change the component
representation or percentage-base rule in Decision 32.

The Payroll period is one calendar month. Compensation segments are inclusive
and are bounded by the intersection of the Payroll period, the employee's
joining and employment end dates, and the applicable compensation effective
dates.

For each segment, each FIXED monthly component amount is prorated using working
days:

```text
segment compensation
    = monthly component compensation
      × segment working-day count
      ÷ monthly_working_day_count
```

The segment working-day count is the number of dates classified as
`WORKING_DAY` within that inclusive compensation segment. The denominator is
`monthly_working_day_count`, the frozen count of `WORKING_DAY` dates across the
complete Payroll calendar month under Decisions 29 and 30. It is not limited by
the employee's employment interval or compensation segment and is not a
calendar-day count. Monetary calculations use Decimal arithmetic.

Percentage components are evaluated independently within each applicable
compensation segment. The salary-component dependency graph uses that segment's
compensation amounts after fixed-component proration and before any
Workforce-derived adjustment. Workforce effects do not alter percentage bases
or dependency edges, consistent with Decision 32.

For each compensation segment, Payroll derives an effective payable fraction
from the frozen Workforce snapshot. For each `WORKING_DAY` date, the attendance
payable fraction is 1.00 for PRESENT, 0.50 for HALF_DAY, and 0.00 for ABSENT.
A missing Attendance row on a `WORKING_DAY` has an effective PRESENT fraction
of 1.00, consistent with the B.5 snapshot semantics. Attendance HOLIDAY does
not override the authoritative Work Calendar classification.

Only approved Leave affects the payable fraction. PENDING and REJECTED Leave
are ignored. An approved PAID Leave allocation contributes a payable fraction
of 1.00 for its date. An approved UNPAID Leave allocation subtracts its
`day_fraction` from that date's attendance payable fraction. CANCELLED Leave
follows the frozen snapshot semantics. Each date's resulting fraction is
capped at 1.00 and floored at 0.00. The segment payable fraction is the sum of
the effective date fractions divided by the segment working-day count.

After the compensation dependency graph has produced segment compensation
amounts, the segment payable fraction is applied uniformly to every regular
EARNING component:

```text
final regular earning
    = segment compensation amount × segment payable fraction
```

This adjustment is represented in the final amount of each existing salary
component. Payroll does not create synthetic Attendance or Leave salary
components. Percentage components continue to use their compensation amounts
before this adjustment, as required by Decision 32.

Overtime remains independent of the Attendance/Leave payable fraction. It is
calculated from the frozen Workforce snapshot under Decision 29, including its
full-month `monthly_working_day_count` denominator and applicable frozen
multiplier. The overtime adjustment is added separately to the designated
overtime-base EARNING component. The regular Attendance/Leave payable fraction
does not reduce overtime.

---

# Decision 34 — Payroll Treatment of Attendance ON_LEAVE

This decision defines the financial treatment of `Attendance.ON_LEAVE` as a
specific case of the Decision 33 payable-fraction rules. The frozen approved
per-date Leave allocation from `leave_request_days` is authoritative for the
financial treatment of an `ON_LEAVE` date.

`Attendance.ON_LEAVE` is a Workforce indicator that the date is governed by its
applicable Leave allocation. It does not itself represent a payable fraction,
and it does not independently add or subtract pay. For a `WORKING_DAY` with
`ON_LEAVE` Attendance, Payroll must resolve the frozen approved Leave allocation
for that date and use its treatment and `day_fraction` as follows:

- APPROVED PAID Leave: payable fraction equals the allocated `day_fraction`.
- APPROVED UNPAID Leave: payable fraction equals `1.00 - day_fraction`.

If no approved Leave allocation exists for that date, Payroll creates an
employee-level blocking Payroll Processing Issue and does not calculate a
financial amount for that employee. PENDING, REJECTED, or otherwise
non-approved Leave does not satisfy the `ON_LEAVE` Attendance row and results
in the same blocking condition. Payroll must not infer PRESENT, ABSENT, PAID,
or UNPAID, and must not treat `ON_LEAVE` as ABSENT automatically.

The resolved `ON_LEAVE` payable fraction participates in the existing Decision
33 segment payable-fraction calculation. It is applied through that calculation
to regular EARNING components; no synthetic `ON_LEAVE` or Leave salary
component is created. It is not added to or subtracted from pay a second time
through the Attendance status itself.

Examples for a `WORKING_DAY`:

| Attendance and frozen Leave allocation | Payable fraction / outcome |
| --- | --- |
| ON_LEAVE + APPROVED PAID allocation 1.00 | 1.00 |
| ON_LEAVE + APPROVED UNPAID allocation 1.00 | 0.00 |
| ON_LEAVE + APPROVED PAID allocation 0.50 | 0.50 |
| ON_LEAVE + APPROVED UNPAID allocation 0.50 | 0.50 |
| ON_LEAVE + no approved allocation | Employee-level blocking issue |
| ON_LEAVE + PENDING or REJECTED Leave | Employee-level blocking issue |

The existing Attendance rules remain unchanged: PRESENT is 1.00, HALF_DAY is
0.50, ABSENT is 0.00, and missing Attendance on a `WORKING_DAY` is 1.00.
Overtime remains independent of the Attendance/Leave payable fraction and
continues to follow Decision 29.

---

# Decision 35 — Payroll Treatment of Attendance HOLIDAY

The Work Calendar is authoritative for classifying each date as
`WORKING_DAY`, `NON_WORKING_DAY`, or `HOLIDAY`. `Attendance.HOLIDAY` is a
non-authoritative attendance marker; it cannot convert a `WORKING_DAY` into a
holiday or otherwise override the Work Calendar classification.

When the Work Calendar classifies a date as `WORKING_DAY`, an Attendance status
of `HOLIDAY` is treated as equivalent to missing Attendance for the Decision 33
payable-fraction calculation. The payable fraction is 1.00, and no blocking
issue is created solely because the Attendance status is `HOLIDAY`. This is
consistent with the existing rule that missing Attendance on a `WORKING_DAY`
has payable fraction 1.00.

When the Work Calendar classifies a date as `NON_WORKING_DAY` or `HOLIDAY`, the
date is excluded from the segment working-day payable calculation. An
`Attendance.HOLIDAY` marker on such a date does not independently add or remove
pay. No synthetic payroll component is created for `Attendance.HOLIDAY`.

This rule does not change Decision 34: `Attendance.ON_LEAVE` remains distinct
and is financially treated through its frozen approved per-date Leave
allocation. Overtime classification remains based on the authoritative Work
Calendar under Decision 29 and is independent of the `Attendance.HOLIDAY`
marker.

Examples:

| Work Calendar classification | Attendance status | Payroll treatment |
| --- | --- | --- |
| WORKING_DAY | HOLIDAY | Payable fraction 1.00 |
| WORKING_DAY | Missing | Payable fraction 1.00 |
| HOLIDAY | HOLIDAY | Excluded from segment working-day payable calculation |
| NON_WORKING_DAY | HOLIDAY | Excluded from segment working-day payable calculation |

---

# Decision 36 — Payroll Treatment of OT Timestamp Anomalies

This decision supplements Decision 29 and defines when OT timestamp anomalies
are nonblocking and when they prevent reliable employee-level financial
calculation. Blocking conditions use the existing Payroll Processing Issue
infrastructure and issue semantics.

Ambiguous or nonexistent local timestamps caused by a daylight-saving-time
transition make OT unusable for the affected interval. Payroll records a
nonblocking anomaly, does not infer OT for that interval, and does not create an
employee-level blocking issue solely for this case.

Missing check-in or check-out, reversed or otherwise invalid worked intervals,
calendar timezone changes during an overnight attendance interval that prevent
consistent calculation, and any other timestamp anomaly that makes worked
duration unreliable create an employee-level OPEN, blocking Payroll Processing
Issue. Payroll must not silently treat an indeterminate interval as zero OT and
must not produce an authoritative successful financial result for the affected
employee.

Valid overnight attendance is split at local midnight. Each date's interval is
calculated using that date's frozen Work Calendar classification, applicable
frozen OT policy, and applicable compensation segment. Worked-minute calculations
retain exact precision.

Only the explicitly specified ambiguous/nonexistent DST case is a nonblocking
anomaly. Other unusable timestamp cases follow the blocking rule above unless an
existing approved decision explicitly specifies otherwise. All attempt-owned
writes remain subject to existing attempt fencing and Unit of Work transaction
boundaries. OPEN issues block successful completion under Decision 26.

---

# Decision 37 — Monetary Rounding and Aggregation

Monetary calculations use Python `Decimal`; binary floating-point is not used.
`ROUND_HALF_UP` to two decimal places is applied at each salary-component
boundary.

For each compensation segment, fixed monthly component compensation is prorated
using the approved full-month denominator and rounded to two decimal places
before it can serve as a percentage dependency base. Percentage components use
their designated base component's rounded pre-Workforce compensation amount;
each percentage amount is rounded to two decimal places at its component
boundary, preserving the deterministic dependency DAG order.

The segment payable fraction is applied to each segment's regular EARNING
component compensation amount, and the adjusted segment component amount is
rounded to two decimal places. Workforce adjustments do not retroactively
change percentage dependency bases.

OT retains exact worked minutes and unrounded intermediate rates and interval
amounts. OT amounts are accumulated by the real designated OT-base salary
component across the payroll period, then rounded once to two decimal places.
Daily interval OT amounts are not rounded independently.

Already-rounded segment component amounts are summed to obtain each component's
period compensation amount. The rounded period OT adjustment is added to the
designated component and the final component amount is rounded to two decimal
places. The calculation snapshot preserves compensation, Workforce adjustment,
OT adjustment, and final amount separately.

Gross is the sum of final EARNING component amounts; deductions are the sum of
final DEDUCTION component amounts; net equals gross minus deductions. No
independent rounding operation is applied to totals already derived from
cent-quantized final component amounts.

This decision supersedes conflicting implementation-level rounding choices. It
does not change schema, API contracts, salary component semantics, percentage
base behavior, or Workforce adjustment order, and it does not create synthetic
salary components. Future implementation work must test component-boundary
rounding, percentage dependency bases, segment aggregation, period-level OT
accumulation, and the difference between per-interval and accumulated OT
rounding.

---

# Decision 38 — Individual Payslip Record Generation

The first payslip-generation increment is an individual database record for one
Payroll Result. It is available only when the specified Payroll Run is
`FINALIZED` and the Payroll Result belongs to that run. The persisted Payroll
Result and Payroll Result Components are the source of all financial values;
generation performs no recalculation and does not modify Payroll Results,
components, Workforce snapshots, or Payroll Run state. Decision 37's monetary
values and precision remain unchanged.

The endpoint is
`POST /api/v1/payroll/runs/{run_id}/results/{result_id}/payslip`. It requires
the authenticated actor to hold persisted permission `payroll.payslip.create`;
the actor is never accepted from request data. A request supplies only the
schema-required `payslip_number`. The response is a dedicated Payslip response
including `generated_at` and nullable `document_path`; null indicates no
document has been generated. Employee self-service, reads/downloads, bulk
generation, and document/PDF creation are outside this increment.

An existing payslip for the result returns HTTP 409. Database uniqueness on
`payroll_result_id` and `payslip_number` remains authoritative; an expected
concurrent uniqueness collision also returns HTTP 409. The missing run, missing
result, or result not belonging to the specified run returns HTTP 404. A
non-finalized run returns HTTP 409. Authentication and permission failures use
HTTP 401 and HTTP 403 respectively; unexpected failures use the centralized,
sanitized HTTP 500 response.

Generation uses the existing parent Payroll Run lock discipline. Payslip row
insertion and the `PAYSLIP_GENERATED` audit event share one Unit of Work
transaction. The event records the authenticated actor, new payslip resource
identifier, payroll run/result identifiers, and request correlation ID when
available; it excludes salary amounts and other financial values. Any failure
rolls back both writes.

For record-only payslips, `payslips.document_path` is nullable. A null value
means no document has been generated; empty, fabricated, and placeholder paths
are not permitted. The schema snapshot and migration preserve existing document
paths. No employee self-service or document-storage behavior is implied by this
decision.

---

# Decision 39 — Finalized Payroll Summary and Reporting Labels

The first Reporting & Analytics increment exposes an aggregate summary for one
`FINALIZED` Payroll Run. Its result count and gross, deduction, and net totals
come from the persisted `payroll_results` rows belonging to that run. Stored
Payroll Result totals are authoritative: reporting does not recalculate payroll,
reconstruct totals from components, read Workforce snapshots, or expose data
from a non-finalized run. A missing run returns 404; a non-finalized run returns
409. A finalized run with zero results is an invalid state and returns 409;
zero-result QA findings prevent a valid run from reaching finalization.

The summary requires persisted permission `report.payroll.read`, assigned only
to the Payroll Administrator role by the development seed. It is read-only and
does not produce an audit event. This increment returns no employee names or
salary-component labels. For later reporting features, labels may be resolved
from current master data; there is no historical-label guarantee.

Employee-level Payroll Result reports, component breakdowns, dashboards, CSV
exports, and employee self-service reports remain deferred. This decision adds
no database table or schema change.

---

# Decision 40 — Paginated Employee Payroll Results Report

Employee-level Payroll Result reporting is authorized for a `FINALIZED` Payroll
Run through `GET /api/v1/reports/payroll/runs/{run_id}/results`. Access requires
the existing persisted `report.payroll.read` permission, initially assigned
only to the Payroll Administrator role. This extends Decision 39 without
changing its summary contract or erasing its original deferrals.

The report reads only the authoritative persisted Payroll Result records for
the requested run and never recalculates payroll. A missing run returns HTTP
404 and a run that is not `FINALIZED` returns HTTP 409. The response includes
only the result identifier, run identifier, employee identifier, salary
assignment identifier, persisted gross earnings, total deductions, net salary,
and employee code/name labels. Employee labels come from current Employee
master data and are not historically snapshotted. The query uses a left outer
join so an unavailable label does not discard a persisted result.

Results are ordered by `employee_id` ascending and then
`payroll_result_id` ascending and use keyset pagination on that pair. The
default page limit is 50 and the maximum is 100. The opaque cursor contains the
requested run identifier and the last returned sort-key pair; malformed,
invalid, or cross-run cursors are rejected with HTTP 422. Each database query
is bounded to at most `limit + 1` rows to determine whether another page exists.
The query always filters by the requested run identifier. No offset pagination
or separate total-count query is used. Cursor payloads use deterministic
base64url JSON protected by HMAC-SHA256 with the configured application signing
key and a report-specific message prefix, so clients cannot alter a valid
cursor's run or position.

Component breakdowns, dashboards, exports, employee self-service, and
historical-label snapshots remain deferred. This decision adds no table,
schema change, migration, permission, or audit event.

---

# Decision 41 — Organization-Wide Employee Report

The read-only organization-wide employee report is available at
`GET /api/v1/reports/employees`. Access requires authenticated access and the
persisted `report.employee.read` permission. The development seed assigns this
permission only to the `HR Administrator` role. It does not add this permission
to `Payroll Administrator`, and the HR role does not receive payroll,
attendance, or leave report permissions through this decision.

The response contains exactly `employee_id`, `employee_code`, `first_name`,
`last_name`, `department_id`, `department_name`, `designation_id`,
`designation_name`, `joining_date`, `employment_end_date`, and
`employment_status`. Department and designation labels are resolved from
current master data; historical label accuracy is not guaranteed. The report
does not expose user, manager, contact, credential, security, or other
unapproved employee fields.

The report includes employees of every supported status by default and may be
filtered by exact employee code, department ID, designation ID, or supported
employment status. It uses keyset pagination ordered by ascending employee ID,
with a default limit of 50 and maximum of 100. The query is bounded to at most
`limit + 1` rows. Its opaque cursor is deterministic base64url JSON protected
by HMAC-SHA256 using the configured application signing key, has an
employee-report-specific discriminator, and is bound to the active filters.
Malformed, tampered, or filter-mismatched cursors return HTTP 422. Unknown
department or designation IDs produce an empty page when no employee matches.

Attendance reports, leave reports, dashboards, exports, payroll reports,
employee self-service, and historical labels remain outside this decision.
This decision adds no table, column, index, migration, calculation, or audit
event.

---

# Decision 42 — Organization-Wide Attendance Report

The read-only attendance report is available at
`GET /api/v1/reports/attendance`. Access requires authentication and the
persisted `report.attendance.read` permission. The development seed assigns
this permission only to the `HR Administrator` role. It remains distinct from
`report.employee.read` and all Payroll Administrator permissions; no user is
assigned to a role by seed data. The report does not emit a report-read audit
event.

Each row contains exactly `attendance_id`, `employee_id`, `employee_code`,
`first_name`, `last_name`, `department_id`, `department_name`,
`designation_id`, `designation_name`, `attendance_date`,
`attendance_status`, `check_in_time`, and `check_out_time`. Attendance facts
come from persisted `attendance_records`. Employee names, employee code, and
organizational labels are read from current Employee, Department, and
Designation master data; they are not historical snapshots. Department and
designation labels may be null when unavailable. Check-in and check-out values
preserve nullable persisted timestamps. Null timestamps do not imply any
attendance status or worked duration. No credentials, contact information,
user or manager identifiers, or security data are returned.

Optional filters are inclusive `date_from` and `date_to`, positive exact
`employee_id` and `department_id`, and `attendance_status` restricted to
`PRESENT`, `ABSENT`, `HALF_DAY`, `ON_LEAVE`, or `HOLIDAY`. A range where
`date_from` is later than `date_to` is invalid. Unknown employee or department
IDs return an empty page when no attendance row matches. There is no fixed
maximum date-range span. The report returns persisted attendance facts only;
it does not derive hours worked, lateness, absenteeism, overtime, Leave
entitlement, or payroll effects, and it does not reinterpret stored statuses.

The report uses keyset pagination ordered by ascending
`(attendance_date, attendance_id)`, with a default page limit of 50 and an
allowed range of 1 through 100. Each query fetches at most `limit + 1` rows;
there is no offset pagination or unbounded total-count query. The deterministic
base64url cursor is signed with HMAC-SHA256 using the configured application
signing key, has an attendance-report-specific discriminator, and is bound to
all active filters and the last returned date/ID pair. Malformed, tampered,
wrong-report, or filter-mismatched cursors are rejected with HTTP 422.

The existing attendance date index and employee/date unique key support the
report's date and employee access paths. This decision adds no table, column,
index, migration, calculation, or audit event. A new index requires
demonstrated query-plan and workload evidence.
