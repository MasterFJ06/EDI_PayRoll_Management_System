from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Mapping, Sequence

from app.application.common.unit_of_work import UnitOfWork
from app.application.payroll.employee_eligibility_resolver import (
    EmployeeEligibilityResult,
)
from app.application.payroll.payroll_processing_issue_service import (
    PayrollProcessingIssueService,
)
from app.application.payroll.schemas import PayrollProcessingIssueCreateRequest
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.audit_event import AuditEventModel
from app.infrastructure.persistence.models.audit_event_change import (
    AuditEventChangeModel,
)


_CANONICAL_ROUNDING_METADATA = "ROUND_HALF_UP to 0.01 at component boundaries"


@dataclass(frozen=True)
class PayrollQualityAssuranceOutcome:
    status: str
    successful_employee_ids: tuple[int, ...]
    failed_employee_ids: tuple[int, ...]
    open_issue_ids: tuple[int, ...]


@dataclass(frozen=True)
class _Finding:
    code: str
    message: str
    employee_id: int | None = None


class PayrollQualityAssuranceService:
    """Validates persisted payroll artifacts and gates the active run attempt."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def evaluate_and_transition(
        self,
        payroll_run_id: int,
        attempt_number: int,
        actor_user_id: int,
        correlation_id: str | None,
        eligibility: EmployeeEligibilityResult,
        expected_salary_assignment_ids: Mapping[int, int],
    ) -> PayrollQualityAssuranceOutcome:
        # This parent lock serializes QA with every attempt-owned artifact writer.
        if self.uow.payroll_runs.lock_active_attempt(
            payroll_run_id, attempt_number
        ) is None:
            raise BusinessRuleViolation(
                "Payroll processing attempt is no longer active for QA."
            )

        eligible_ids = tuple(
            employee.employee_id for employee in eligibility.eligible_employees
        )
        excluded_ids = eligibility.excluded_employee_ids
        eligible = set(eligible_ids)
        excluded = set(excluded_ids)
        findings: list[_Finding] = []

        if not eligible_ids:
            findings.append(
                _Finding(
                    "PAYROLL_QA_ZERO_ELIGIBLE_EMPLOYEES",
                    "Payroll QA cannot accept a run with zero eligible employees.",
                )
            )
        if len(eligible_ids) != len(eligible):
            findings.append(
                _Finding(
                    "PAYROLL_QA_DUPLICATE_EMPLOYEE_ACCOUNTING",
                    "Eligibility contains a duplicate employee identity.",
                )
            )
        if len(excluded_ids) != len(excluded):
            findings.append(
                _Finding(
                    "PAYROLL_QA_DUPLICATE_EMPLOYEE_ACCOUNTING",
                    "Exclusions contain a duplicate employee identity.",
                )
            )
        if eligible & excluded:
            findings.append(
                _Finding(
                    "PAYROLL_QA_EMPLOYEE_ACCOUNTING_OVERLAP",
                    "An employee is classified as both eligible and excluded.",
                )
            )

        results = self.uow.payroll_results.list_by_run(payroll_run_id)
        workforce_snapshots = self.uow.payroll_run_workforce_snapshots.list_by_run_and_attempt(
            payroll_run_id, attempt_number
        )
        workforce_snapshots_by_employee = {
            row.employee_id: row for row in workforce_snapshots
        }
        result_ids = {row.payroll_result_id for row in results}
        components = self.uow.payroll_result_components.list_by_run(payroll_run_id)
        referenced_component_ids = {
            row.salary_component_id for row in components
        }
        component_definitions = {
            row.salary_component_id: row
            for row in self.uow.salary_components.get_by_ids(referenced_component_ids)
        }
        issues = self.uow.payroll_processing_issues.list_by_run(payroll_run_id)

        results_by_employee: dict[int, list[object]] = defaultdict(list)
        for result in results:
            results_by_employee[result.employee_id].append(result)
            if result.payroll_run_id != payroll_run_id:
                findings.append(
                    _Finding(
                        "PAYROLL_QA_RESULT_RUN_MISMATCH",
                        "A persisted Payroll Result is associated with another run.",
                        result.employee_id,
                    )
                )

        components_by_result: dict[int, list[object]] = defaultdict(list)
        for component in components:
            components_by_result[component.payroll_result_id].append(component)
            if component.payroll_result_id not in result_ids:
                findings.append(
                    _Finding(
                        "PAYROLL_QA_ORPHAN_RESULT_COMPONENT",
                        "A Payroll Result Component has no result in this run.",
                    )
                )

        open_issues_by_employee: dict[int, list[object]] = defaultdict(list)
        open_issues = []
        for issue in issues:
            if issue.status == "OPEN":
                open_issues.append(issue)
                if issue.employee_id is not None:
                    open_issues_by_employee[issue.employee_id].append(issue)
            elif issue.status != "RESOLVED":
                findings.append(
                    _Finding(
                        "PAYROLL_QA_INVALID_ISSUE_STATUS",
                        "A Payroll Processing Issue has an unsupported status.",
                        issue.employee_id,
                    )
                )

        for result in results:
            if result.employee_id not in eligible:
                findings.append(
                    _Finding(
                        "PAYROLL_QA_UNEXPECTED_RESULT_EMPLOYEE",
                        "A Payroll Result exists for an employee who is not eligible in this run.",
                    )
                )

        successful: set[int] = set()
        for employee_id in sorted(eligible):
            employee_results = results_by_employee.get(employee_id, [])
            if not employee_results:
                if not open_issues_by_employee.get(employee_id):
                    findings.append(
                        _Finding(
                            "PAYROLL_QA_RESULT_MISSING",
                            "An eligible employee has no persisted result or documented blocking issue.",
                            employee_id,
                        )
                    )
                continue
            if len(employee_results) != 1:
                findings.append(
                    _Finding(
                        "PAYROLL_QA_DUPLICATE_EMPLOYEE_RESULT",
                        "An eligible employee does not have exactly one Payroll Result.",
                        employee_id,
                    )
                )
                continue

            result = employee_results[0]
            result_findings = _validate_employee_result(
                result,
                components_by_result.get(result.payroll_result_id, []),
                component_definitions,
                payroll_run_id,
                attempt_number,
                employee_id,
                expected_salary_assignment_ids.get(employee_id),
                workforce_snapshots_by_employee.get(employee_id),
            )
            findings.extend(
                _Finding(code, message, employee_id)
                for code, message in result_findings
            )
            if not result_findings and not open_issues_by_employee.get(employee_id):
                successful.add(employee_id)

        failed = eligible - successful
        existing_open_keys = {
            (issue.employee_id, issue.issue_code) for issue in open_issues
        }
        created_keys: set[tuple[int | None, str]] = set()
        created_issue_ids: list[int] = []
        issue_service = PayrollProcessingIssueService(self.uow)
        for finding in _unique_findings(findings):
            key = (finding.employee_id, finding.code)
            if key in existing_open_keys or key in created_keys:
                continue
            response = issue_service.create(
                PayrollProcessingIssueCreateRequest(
                    payroll_run_id=payroll_run_id,
                    employee_id=finding.employee_id,
                    issue_code=finding.code,
                    issue_message=finding.message,
                    status="OPEN",
                ),
                attempt_number,
                commit=False,
            )
            created_issue_ids.append(response.payroll_issue_id)
            created_keys.add(key)

        # Do not count an employee with an open issue, even if a result exists.
        successful.difference_update(open_issues_by_employee)
        failed = eligible - successful
        for employee_id in sorted(failed):
            if not open_issues_by_employee.get(employee_id) and not any(
                key[0] == employee_id for key in created_keys
            ):
                response = issue_service.create(
                    PayrollProcessingIssueCreateRequest(
                        payroll_run_id=payroll_run_id,
                        employee_id=employee_id,
                        issue_code="PAYROLL_QA_EMPLOYEE_UNACCOUNTED",
                        issue_message=(
                            "An eligible employee is neither successfully processed "
                            "nor documented by a blocking issue."
                        ),
                        status="OPEN",
                    ),
                    attempt_number,
                    commit=False,
                )
                created_issue_ids.append(response.payroll_issue_id)
                created_keys.add((employee_id, "PAYROLL_QA_EMPLOYEE_UNACCOUNTED"))

        qa_failed = bool(findings or open_issues or created_issue_ids)
        # Existing OPEN issues always block, including run-level and historical issues.
        target_status = "FAILED" if qa_failed else "PROCESSED"
        if target_status == "FAILED":
            transitioned = self.uow.payroll_runs.mark_failed_if_processing(
                payroll_run_id, attempt_number
            )
            action = "PAYROLL_RUN_PROCESSING_FAILED"
        else:
            transitioned = self.uow.payroll_runs.mark_processed_if_processing(
                payroll_run_id, attempt_number
            )
            action = "PAYROLL_RUN_PROCESSING_COMPLETED"
        if not transitioned:
            self.uow.rollback()
            raise BusinessRuleViolation(
                "Payroll processing attempt changed before QA could transition the run."
            )

        self.uow.audit_events.add(
            AuditEventModel(
                actor_user_id=actor_user_id,
                action_type=action,
                resource_type="PAYROLL_RUN",
                resource_id=payroll_run_id,
                correlation_id=correlation_id,
            ),
            [
                AuditEventChangeModel(
                    field_name="status",
                    old_value="PROCESSING",
                    new_value=target_status,
                )
            ],
        )
        self.uow.commit()

        blocking_ids = tuple(
            issue.payroll_issue_id for issue in open_issues
        ) + tuple(created_issue_ids)
        return PayrollQualityAssuranceOutcome(
            status=target_status,
            successful_employee_ids=tuple(sorted(successful)),
            failed_employee_ids=tuple(sorted(failed)),
            open_issue_ids=blocking_ids,
        )


def _validate_employee_result(
    result: object,
    components: Sequence[object],
    component_definitions: Mapping[int, object],
    payroll_run_id: int,
    attempt_number: int,
    employee_id: int,
    expected_salary_assignment_id: int | None,
    workforce_snapshot: object | None,
) -> list[tuple[str, str]]:
    errors: list[tuple[str, str]] = []

    def fail(code: str, message: str) -> None:
        errors.append((code, message))

    if result.payroll_run_id != payroll_run_id or result.employee_id != employee_id:
        fail("PAYROLL_QA_RESULT_IDENTITY_INVALID", "Persisted Payroll Result identity is inconsistent.")
    if (
        expected_salary_assignment_id is None
        or result.salary_assignment_id != expected_salary_assignment_id
    ):
        fail("PAYROLL_QA_RESULT_ASSIGNMENT_INVALID", "Payroll Result does not match the frozen salary assignment.")

    component_ids = [item.salary_component_id for item in components]
    if len(component_ids) != len(set(component_ids)):
        fail("PAYROLL_QA_COMPONENT_DUPLICATE", "A Payroll Result contains duplicate salary components.")

    component_totals = {"EARNING": Decimal("0"), "DEDUCTION": Decimal("0")}
    persisted_components: dict[int, object] = {}
    for component in components:
        if component.payroll_result_id != result.payroll_result_id:
            fail("PAYROLL_QA_COMPONENT_RESULT_MISMATCH", "A component references another Payroll Result.")
        definition = component_definitions.get(component.salary_component_id)
        if definition is None:
            fail("PAYROLL_QA_COMPONENT_DEFINITION_MISSING", "A result component has no authoritative salary component.")
            continue
        if component.component_type != definition.component_type:
            fail("PAYROLL_QA_COMPONENT_TYPE_MISMATCH", "A result component type differs from its salary component definition.")
        if component.component_type not in component_totals:
            fail("PAYROLL_QA_COMPONENT_TYPE_INVALID", "A result component has an unsupported type.")
            continue
        amount = _finite_decimal(component.amount)
        if amount is None or amount < 0:
            fail("PAYROLL_QA_COMPONENT_AMOUNT_INVALID", "A result component amount is invalid.")
            continue
        component_totals[component.component_type] += amount
        persisted_components[component.salary_component_id] = component

    gross = _finite_decimal(result.gross_earnings)
    deductions = _finite_decimal(result.total_deductions)
    net = _finite_decimal(result.net_salary)
    if gross is None or deductions is None or net is None:
        fail("PAYROLL_QA_RESULT_TOTAL_INVALID", "Persisted Payroll Result totals are invalid.")
    else:
        if gross != component_totals["EARNING"]:
            fail("PAYROLL_QA_GROSS_MISMATCH", "Gross earnings do not equal persisted EARNING components.")
        if deductions != component_totals["DEDUCTION"]:
            fail("PAYROLL_QA_DEDUCTIONS_MISMATCH", "Deductions do not equal persisted DEDUCTION components.")
        if net != gross - deductions:
            fail("PAYROLL_QA_NET_MISMATCH", "Net salary does not equal gross earnings minus deductions.")

    snapshot = result.workforce_calculation_snapshot
    if not isinstance(snapshot, Mapping):
        fail("PAYROLL_QA_SNAPSHOT_MISSING", "Required Workforce calculation snapshot is missing or malformed.")
        return errors
    if workforce_snapshot is None:
        fail(
            "PAYROLL_QA_WORKFORCE_SNAPSHOT_MISSING",
            "No frozen Workforce snapshot exists for the result's current attempt.",
        )
    elif (
        workforce_snapshot.payroll_run_id != payroll_run_id
        or workforce_snapshot.employee_id != employee_id
        or workforce_snapshot.attempt_number != attempt_number
    ):
        fail(
            "PAYROLL_QA_WORKFORCE_SNAPSHOT_INVALID",
            "Frozen Workforce snapshot identity differs from the Payroll Result.",
        )
    metadata = snapshot.get("rule_metadata")
    calculation = snapshot.get("financial_calculation")
    if (
        snapshot.get("payroll_run_id") != payroll_run_id
        or snapshot.get("employee_id") != employee_id
        or snapshot.get("attempt_number") != attempt_number
        or not isinstance(metadata, Mapping)
        or metadata.get("financial_calculation") != "performed"
        or not isinstance(calculation, Mapping)
        or calculation.get("calculation_status") != "CALCULATED"
        or calculation.get("payroll_run_id") != payroll_run_id
        or calculation.get("employee_id") != employee_id
        or calculation.get("attempt_number") != attempt_number
        or not isinstance(calculation.get("segments"), list)
        or not calculation.get("segments")
        or calculation.get("rounding") != _CANONICAL_ROUNDING_METADATA
        or not isinstance(calculation.get("components"), list)
    ):
        fail("PAYROLL_QA_SNAPSHOT_INVALID", "Calculation snapshot metadata or structure is inconsistent.")
        return errors

    if workforce_snapshot is not None:
        frozen_payload = _json_value(workforce_snapshot.snapshot)
        result_inputs = {
            key: value
            for key, value in snapshot.items()
            if key != "financial_calculation"
        }
        result_metadata = result_inputs.get("rule_metadata")
        frozen_metadata = frozen_payload.get("rule_metadata") if isinstance(frozen_payload, dict) else None
        if isinstance(result_metadata, dict) and isinstance(frozen_metadata, dict):
            result_metadata = {
                key: value for key, value in result_metadata.items()
                if key != "financial_calculation"
            }
            frozen_metadata = {
                key: value for key, value in frozen_metadata.items()
                if key != "financial_calculation"
            }
            result_inputs["rule_metadata"] = result_metadata
            frozen_payload["rule_metadata"] = frozen_metadata
        if not isinstance(frozen_payload, dict) or result_inputs != frozen_payload:
            fail(
                "PAYROLL_QA_WORKFORCE_SNAPSHOT_MISMATCH",
                "Result snapshot inputs differ from the frozen current-attempt Workforce snapshot.",
            )

    snapshot_components = calculation["components"]
    snapshot_by_id: dict[int, Mapping[str, object]] = {}
    segment_totals: dict[int, dict[str, object]] = defaultdict(
        lambda: {
            "compensation_amount": Decimal("0"),
            "workforce_adjustment": Decimal("0"),
            "overtime_adjustment": Decimal("0"),
            "final_amount": Decimal("0"),
            "component_type": None,
            "calculation_order": None,
        }
    )
    for row in snapshot_components:
        if not isinstance(row, Mapping):
            fail("PAYROLL_QA_SNAPSHOT_COMPONENT_INVALID", "Calculation snapshot contains a malformed component row.")
            continue
        component_id = row.get("component_id")
        if isinstance(component_id, bool) or not isinstance(component_id, int):
            fail("PAYROLL_QA_SNAPSHOT_COMPONENT_INVALID", "Calculation snapshot component identity is invalid.")
            continue
        if component_id in snapshot_by_id:
            fail("PAYROLL_QA_SNAPSHOT_COMPONENT_DUPLICATE", "Calculation snapshot repeats a salary component.")
            continue
        snapshot_by_id[component_id] = row
        required = (
            "component_type",
            "compensation_amount",
            "workforce_adjustment",
            "overtime_adjustment",
            "final_amount",
            "calculation_order",
        )
        if any(name not in row for name in required):
            fail("PAYROLL_QA_SNAPSHOT_COMPONENT_INVALID", "Calculation snapshot component breakdown is incomplete.")
            continue
        persisted = persisted_components.get(component_id)
        if persisted is None:
            fail("PAYROLL_QA_SNAPSHOT_COMPONENT_MISMATCH", "Snapshot component has no persisted result component.")
            continue
        if row.get("component_type") != persisted.component_type:
            fail("PAYROLL_QA_SNAPSHOT_COMPONENT_MISMATCH", "Snapshot component type differs from persisted result component.")
        snapshot_final = _finite_decimal(row.get("final_amount"))
        if snapshot_final is None or snapshot_final != _finite_decimal(persisted.amount):
            fail("PAYROLL_QA_SNAPSHOT_COMPONENT_MISMATCH", "Snapshot component amount differs from persisted result component.")
        snapshot_order = row.get("calculation_order")
        if isinstance(snapshot_order, bool) or not isinstance(snapshot_order, int) or snapshot_order != persisted.calculation_order:
            fail("PAYROLL_QA_SNAPSHOT_COMPONENT_MISMATCH", "Snapshot calculation order differs from persisted result component.")
        for name in ("compensation_amount", "workforce_adjustment", "overtime_adjustment"):
            if _finite_decimal(row.get(name)) is None:
                fail("PAYROLL_QA_SNAPSHOT_COMPONENT_INVALID", "Snapshot component breakdown contains an invalid amount.")

    for segment in calculation["segments"]:
        if not isinstance(segment, Mapping) or not isinstance(segment.get("components"), list):
            fail("PAYROLL_QA_SNAPSHOT_SEGMENT_INVALID", "Calculation snapshot contains a malformed segment.")
            continue
        for row in segment["components"]:
            if not isinstance(row, Mapping):
                fail("PAYROLL_QA_SNAPSHOT_SEGMENT_INVALID", "Calculation snapshot contains a malformed segment component.")
                continue
            component_id = row.get("component_id")
            aggregate_row = snapshot_by_id.get(component_id) if isinstance(component_id, int) and not isinstance(component_id, bool) else None
            if aggregate_row is None:
                fail("PAYROLL_QA_SNAPSHOT_SEGMENT_INVALID", "A segment component has no aggregate snapshot component.")
                continue
            amounts = {
                name: _finite_decimal(row.get(name))
                for name in (
                    "compensation_amount",
                    "workforce_adjustment",
                    "overtime_adjustment",
                    "final_amount",
                )
            }
            if any(value is None for value in amounts.values()):
                fail("PAYROLL_QA_SNAPSHOT_SEGMENT_INVALID", "Segment component breakdown contains an invalid amount.")
                continue
            summary = segment_totals[component_id]
            if summary["component_type"] not in (None, row.get("component_type")):
                fail("PAYROLL_QA_SNAPSHOT_SEGMENT_INVALID", "Segment component type differs across segments.")
            if summary["calculation_order"] not in (None, row.get("calculation_order")):
                fail("PAYROLL_QA_SNAPSHOT_SEGMENT_INVALID", "Segment component order differs across segments.")
            if row.get("component_type") != aggregate_row.get("component_type"):
                fail("PAYROLL_QA_SNAPSHOT_SEGMENT_INVALID", "Segment component type differs from its aggregate.")
            if row.get("calculation_order") != aggregate_row.get("calculation_order"):
                fail("PAYROLL_QA_SNAPSHOT_SEGMENT_INVALID", "Segment component order differs from its aggregate.")
            summary["component_type"] = row.get("component_type")
            summary["calculation_order"] = row.get("calculation_order")
            for name, amount in amounts.items():
                summary[name] = Decimal(summary[name]) + amount

    if set(snapshot_by_id) != set(persisted_components):
        fail("PAYROLL_QA_SNAPSHOT_COMPONENT_MISMATCH", "Snapshot and persisted component identities differ.")
    if set(segment_totals) != set(snapshot_by_id):
        fail("PAYROLL_QA_SNAPSHOT_SEGMENT_INVALID", "Segment and aggregate component identities differ.")
    for component_id, summary in segment_totals.items():
        aggregate_row = snapshot_by_id.get(component_id)
        if aggregate_row is None:
            continue
        if _finite_decimal(aggregate_row.get("compensation_amount")) != summary["compensation_amount"]:
            fail("PAYROLL_QA_SNAPSHOT_SEGMENT_MISMATCH", "Segment compensation amounts do not match the aggregate.")
        if _finite_decimal(aggregate_row.get("workforce_adjustment")) != summary["workforce_adjustment"]:
            fail("PAYROLL_QA_SNAPSHOT_SEGMENT_MISMATCH", "Segment Workforce adjustments do not match the aggregate.")
        rounding = Decimal("0.01")
        rounded_ot = Decimal(summary["overtime_adjustment"]).quantize(rounding, rounding=ROUND_HALF_UP)
        if _finite_decimal(aggregate_row.get("overtime_adjustment")) != rounded_ot:
            fail("PAYROLL_QA_SNAPSHOT_SEGMENT_MISMATCH", "Segment OT adjustments do not match the aggregate rounding boundary.")
        rounded_final = Decimal(summary["final_amount"]).quantize(rounding, rounding=ROUND_HALF_UP)
        if _finite_decimal(aggregate_row.get("final_amount")) != rounded_final:
            fail("PAYROLL_QA_SNAPSHOT_SEGMENT_MISMATCH", "Segment final amounts do not match the aggregate rounding boundary.")

    if gross is not None and _finite_decimal(calculation.get("gross_earnings")) != gross:
        fail("PAYROLL_QA_SNAPSHOT_TOTAL_MISMATCH", "Snapshot gross earnings differ from the persisted result.")
    if deductions is not None and _finite_decimal(calculation.get("total_deductions")) != deductions:
        fail("PAYROLL_QA_SNAPSHOT_TOTAL_MISMATCH", "Snapshot deductions differ from the persisted result.")
    if net is not None and _finite_decimal(calculation.get("net_salary")) != net:
        fail("PAYROLL_QA_SNAPSHOT_TOTAL_MISMATCH", "Snapshot net salary differs from the persisted result.")
    return errors


def _finite_decimal(value: object) -> Decimal | None:
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except (ArithmeticError, TypeError, ValueError):
        return None
    return amount if amount.is_finite() else None


def _json_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _unique_findings(findings: Sequence[_Finding]) -> tuple[_Finding, ...]:
    unique: dict[tuple[int | None, str, str], _Finding] = {}
    for finding in findings:
        unique.setdefault(
            (finding.employee_id, finding.code, finding.message), finding
        )
    return tuple(unique.values())
