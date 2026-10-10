from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.payroll.employee_eligibility_resolver import (
    EligibleEmployee,
    EmployeeEligibilityResult,
)
from app.application.payroll.payroll_quality_assurance_service import (
    PayrollQualityAssuranceService,
)


_DEFAULT_SNAPSHOT = object()


class _Repository:
    def __init__(self, rows=(), *, locked=True):
        self.rows = list(rows)
        self.locked = locked
        self.items = []

    def lock_active_attempt(self, *_args):
        return object() if self.locked else None

    def get_by_id(self, _item_id):
        return SimpleNamespace(employee_id=7)

    def list_by_run(self, *_args):
        return list(self.rows)

    def get_by_ids(self, _ids):
        return list(self.rows)

    def add(self, item):
        item.payroll_issue_id = len(self.items) + 100
        self.items.append(item)
        return item

    def mark_processed_if_processing(self, *_args):
        return True

    def mark_failed_if_processing(self, *_args):
        return True


class _UnitOfWork:
    def __init__(self, *, results=(), components=(), issues=(), definitions=(), workforce_snapshots=None, locked=True):
        self.payroll_runs = _Repository(locked=locked)
        self.payroll_results = _Repository(results)
        self.payroll_result_components = _Repository(components)
        self.payroll_processing_issues = _Repository(issues)
        self.salary_components = _Repository(definitions)
        self.payroll_run_workforce_snapshots = _Repository(
            workforce_snapshots
            if workforce_snapshots is not None
            else [
                snapshot for row in results
                if (snapshot := _workforce_snapshot(row)) is not None
            ]
        )
        self.payroll_run_workforce_snapshots.list_by_run_and_attempt = (
            lambda *_args: list(self.payroll_run_workforce_snapshots.rows)
        )
        self.employees = _Repository()
        self.audit_events = SimpleNamespace(items=[], add=self._add_audit)
        self.commits = 0
        self.rollbacks = 0
        self.transitions = []
        self.payroll_runs.mark_processed_if_processing = self._processed
        self.payroll_runs.mark_failed_if_processing = self._failed

    def _processed(self, run_id, attempt):
        self.transitions.append(("PROCESSED", run_id, attempt))
        return True

    def _failed(self, run_id, attempt):
        self.transitions.append(("FAILED", run_id, attempt))
        return True

    def _add_audit(self, event, changes=()):
        self.audit_events.items.append((event, tuple(changes)))

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def _eligibility(eligible=(7,), excluded=()):
    return EmployeeEligibilityResult(
        payroll_period_start=date(2026, 1, 1),
        payroll_period_end=date(2026, 1, 31),
        eligible_employees=tuple(
            EligibleEmployee(employee_id, date(2026, 1, 1), date(2026, 1, 31))
            for employee_id in eligible
        ),
        excluded_employee_ids=tuple(excluded),
    )


def _result(
    *,
    employee_id=7,
    run_id=5,
    gross="100.00",
    deductions="0.00",
    net="100.00",
    snapshot=_DEFAULT_SNAPSHOT,
):
    if snapshot is _DEFAULT_SNAPSHOT:
        snapshot = {
            "payroll_run_id": run_id,
            "employee_id": employee_id,
            "attempt_number": 1,
            "rule_metadata": {"financial_calculation": "performed"},
            "financial_calculation": {
                "calculation_status": "CALCULATED",
                "payroll_run_id": run_id,
                "employee_id": employee_id,
                "attempt_number": 1,
                "rounding": "ROUND_HALF_UP to 0.01 at component boundaries",
                "segments": [
                    {
                        "components": [
                            {
                                "component_id": 3,
                                "component_type": "EARNING",
                                "compensation_amount": "100.00",
                                "workforce_adjustment": "0.00",
                                "overtime_adjustment": "0.00",
                                "final_amount": "100.00",
                                "calculation_order": 0,
                            }
                        ]
                    }
                ],
                "components": [
                    {
                        "component_id": 3,
                        "component_type": "EARNING",
                        "compensation_amount": "100.00",
                        "workforce_adjustment": "0.00",
                        "overtime_adjustment": "0.00",
                        "final_amount": "100.00",
                        "calculation_order": 0,
                    }
                ],
                "gross_earnings": gross,
                "total_deductions": deductions,
                "net_salary": net,
            },
        }
    return SimpleNamespace(
        payroll_result_id=11,
        payroll_run_id=run_id,
        employee_id=employee_id,
        salary_assignment_id=8,
        gross_earnings=Decimal(gross),
        total_deductions=Decimal(deductions),
        net_salary=Decimal(net),
        workforce_calculation_snapshot=snapshot,
    )


def _component(*, component_type="EARNING", amount="100.00", component_id=3):
    return SimpleNamespace(
        payroll_result_component_id=21,
        payroll_result_id=11,
        salary_component_id=component_id,
        component_type=component_type,
        amount=Decimal(amount),
        calculation_order=0,
    )


def _workforce_snapshot(result, *, attempt_number=1):
    if not isinstance(result.workforce_calculation_snapshot, dict):
        return None
    snapshot = deepcopy(result.workforce_calculation_snapshot)
    snapshot.pop("financial_calculation", None)
    return SimpleNamespace(
        payroll_run_id=result.payroll_run_id,
        employee_id=result.employee_id,
        attempt_number=attempt_number,
        snapshot_at=datetime(2026, 1, 1),
        snapshot=snapshot,
    )


def _definition(component_id=3, component_type="EARNING"):
    return SimpleNamespace(
        salary_component_id=component_id,
        component_type=component_type,
    )


def _evaluate(uow, *, eligibility=None):
    return PayrollQualityAssuranceService(uow).evaluate_and_transition(
        payroll_run_id=5,
        attempt_number=1,
        actor_user_id=9,
        correlation_id="qa-correlation",
        eligibility=eligibility or _eligibility(),
        expected_salary_assignment_ids={7: 8},
    )


def _valid_uow(**kwargs):
    kwargs.setdefault("results", [_result()])
    kwargs.setdefault("components", [_component()])
    kwargs.setdefault("definitions", [_definition()])
    return _UnitOfWork(**kwargs)


def test_valid_persisted_result_transitions_to_processed_and_audits_atomically():
    uow = _valid_uow()

    outcome = _evaluate(uow, eligibility=_eligibility(excluded=(8,)))

    assert outcome.status == "PROCESSED"
    assert outcome.successful_employee_ids == (7,)
    assert outcome.failed_employee_ids == ()
    assert outcome.open_issue_ids == ()
    assert uow.transitions == [("PROCESSED", 5, 1)]
    assert uow.commits == 1
    event, changes = uow.audit_events.items[0]
    assert event.action_type == "PAYROLL_RUN_PROCESSING_COMPLETED"
    assert (changes[0].old_value, changes[0].new_value) == ("PROCESSING", "PROCESSED")


@pytest.mark.parametrize(
    ("result_kwargs", "component_kwargs", "definitions", "issue_code"),
    [
        ({"run_id": 99}, {}, [_definition()], "PAYROLL_QA_RESULT_IDENTITY_INVALID"),
        ({}, {"component_type": "DEDUCTION"}, [_definition()], "PAYROLL_QA_COMPONENT_TYPE_MISMATCH"),
        ({}, {}, [], "PAYROLL_QA_COMPONENT_DEFINITION_MISSING"),
        ({}, {"amount": "90.00"}, [_definition()], "PAYROLL_QA_GROSS_MISMATCH"),
        ({"gross": "99.00", "net": "99.00"}, {}, [_definition()], "PAYROLL_QA_GROSS_MISMATCH"),
        ({"deductions": "1.00", "net": "99.00"}, {}, [_definition()], "PAYROLL_QA_DEDUCTIONS_MISMATCH"),
        ({"net": "99.00"}, {}, [_definition()], "PAYROLL_QA_NET_MISMATCH"),
        ({"snapshot": None}, {}, [_definition()], "PAYROLL_QA_SNAPSHOT_MISSING"),
    ],
)
def test_invalid_persisted_employee_result_fails_qa(
    result_kwargs, component_kwargs, definitions, issue_code
):
    uow = _UnitOfWork(
        results=[_result(**result_kwargs)],
        components=[_component(**component_kwargs)],
        definitions=definitions,
    )

    outcome = _evaluate(uow)

    assert outcome.status == "FAILED"
    assert outcome.successful_employee_ids == ()
    assert outcome.failed_employee_ids == (7,)
    assert uow.transitions == [("FAILED", 5, 1)]
    assert uow.commits == 1
    assert any(issue.issue_code == issue_code for issue in uow.payroll_processing_issues.items)
    assert all(issue.status == "OPEN" for issue in uow.payroll_processing_issues.items)


def test_missing_result_creates_employee_failure_and_fails_run():
    uow = _UnitOfWork()

    outcome = _evaluate(uow)

    assert outcome.status == "FAILED"
    assert outcome.failed_employee_ids == (7,)
    assert uow.payroll_processing_issues.items[0].issue_code == "PAYROLL_QA_RESULT_MISSING"
    assert uow.payroll_processing_issues.items[0].employee_id == 7


def test_result_without_current_attempt_workforce_snapshot_fails_qa():
    result = _result()
    uow = _UnitOfWork(
        results=[result],
        components=[_component()],
        definitions=[_definition()],
        workforce_snapshots=[],
    )

    outcome = _evaluate(uow)

    assert outcome.status == "FAILED"
    assert any(
        issue.issue_code == "PAYROLL_QA_WORKFORCE_SNAPSHOT_MISSING"
        for issue in uow.payroll_processing_issues.items
    )


def test_result_snapshot_rounding_metadata_is_required():
    result = _result()
    del result.workforce_calculation_snapshot["financial_calculation"]["rounding"]
    uow = _UnitOfWork(
        results=[result], components=[_component()], definitions=[_definition()]
    )

    outcome = _evaluate(uow)

    assert outcome.status == "FAILED"
    assert any(
        issue.issue_code == "PAYROLL_QA_SNAPSHOT_INVALID"
        for issue in uow.payroll_processing_issues.items
    )


@pytest.mark.parametrize("rounding", ["ROUND_HALF_UP", "ROUND_DOWN to 0.01", 123])
def test_unapproved_or_malformed_rounding_metadata_fails_qa(rounding):
    result = _result()
    result.workforce_calculation_snapshot["financial_calculation"]["rounding"] = rounding
    uow = _UnitOfWork(
        results=[result], components=[_component()], definitions=[_definition()]
    )

    outcome = _evaluate(uow)

    assert outcome.status == "FAILED"
    assert outcome.successful_employee_ids == ()
    assert outcome.failed_employee_ids == (7,)
    assert any(
        issue.issue_code == "PAYROLL_QA_SNAPSHOT_INVALID"
        for issue in uow.payroll_processing_issues.items
    )


def test_segment_breakdown_must_reconcile_to_aggregate_component():
    result = _result()
    result.workforce_calculation_snapshot["financial_calculation"]["segments"][0][
        "components"
    ][0]["compensation_amount"] = "99.00"
    uow = _UnitOfWork(
        results=[result], components=[_component()], definitions=[_definition()]
    )

    outcome = _evaluate(uow)

    assert outcome.status == "FAILED"
    assert any(
        issue.issue_code == "PAYROLL_QA_SNAPSHOT_SEGMENT_MISMATCH"
        for issue in uow.payroll_processing_issues.items
    )


def test_result_inputs_must_match_frozen_workforce_snapshot():
    result = _result()
    uow = _UnitOfWork(
        results=[result],
        components=[_component()],
        definitions=[_definition()],
        workforce_snapshots=[
            SimpleNamespace(
                payroll_run_id=5,
                employee_id=7,
                attempt_number=1,
                snapshot_at=datetime(2026, 1, 1),
                snapshot={"payroll_run_id": 5, "employee_id": 7, "attempt_number": 1},
            )
        ],
    )

    outcome = _evaluate(uow)

    assert outcome.status == "FAILED"
    assert any(
        issue.issue_code == "PAYROLL_QA_WORKFORCE_SNAPSHOT_MISMATCH"
        for issue in uow.payroll_processing_issues.items
    )


def test_zero_eligible_employees_is_blocking():
    uow = _UnitOfWork()

    outcome = _evaluate(uow, eligibility=_eligibility(eligible=(), excluded=(8,)))

    assert outcome.status == "FAILED"
    assert outcome.successful_employee_ids == ()
    assert outcome.failed_employee_ids == ()
    assert uow.payroll_processing_issues.items[0].issue_code == "PAYROLL_QA_ZERO_ELIGIBLE_EMPLOYEES"
    assert uow.payroll_processing_issues.items[0].employee_id is None


@pytest.mark.parametrize("status", ["OPEN", "RESOLVED"])
def test_issue_status_gates_qa_by_open_state_only(status):
    issue = SimpleNamespace(
        payroll_issue_id=91,
        employee_id=7,
        issue_code="PRIOR_ATTEMPT",
        status=status,
    )
    uow = _valid_uow(issues=[issue])

    outcome = _evaluate(uow)

    expected = "FAILED" if status == "OPEN" else "PROCESSED"
    assert outcome.status == expected
    assert outcome.successful_employee_ids == (() if status == "OPEN" else (7,))
    assert outcome.failed_employee_ids == ((7,) if status == "OPEN" else ())
    assert uow.payroll_processing_issues.items == []


def test_open_run_level_issue_blocks_without_auto_resolution():
    issue = SimpleNamespace(
        payroll_issue_id=92,
        employee_id=None,
        issue_code="HISTORICAL_RUN_ISSUE",
        status="OPEN",
    )
    uow = _valid_uow(issues=[issue])

    outcome = _evaluate(uow)

    assert outcome.status == "FAILED"
    assert outcome.open_issue_ids == (92,)
    assert issue.status == "OPEN"
    assert uow.payroll_processing_issues.items == []


def test_unexpected_result_employee_fails_run():
    uow = _valid_uow(results=[_result(employee_id=99)])

    outcome = _evaluate(uow)

    assert outcome.status == "FAILED"
    assert outcome.successful_employee_ids == ()
    codes = {issue.issue_code for issue in uow.payroll_processing_issues.items}
    assert "PAYROLL_QA_UNEXPECTED_RESULT_EMPLOYEE" in codes
    assert "PAYROLL_QA_RESULT_MISSING" in codes


def test_duplicate_employee_accounting_and_result_are_blocking():
    duplicate_result = _result()
    duplicate_result.payroll_result_id = 12
    duplicate_component = _component()
    duplicate_component.payroll_result_id = 12
    uow = _UnitOfWork(
        results=[_result(), duplicate_result],
        components=[_component(), duplicate_component],
        definitions=[_definition()],
    )

    outcome = _evaluate(uow, eligibility=_eligibility(eligible=(7, 7)))

    assert outcome.status == "FAILED"
    codes = {issue.issue_code for issue in uow.payroll_processing_issues.items}
    assert "PAYROLL_QA_DUPLICATE_EMPLOYEE_ACCOUNTING" in codes
    assert "PAYROLL_QA_DUPLICATE_EMPLOYEE_RESULT" in codes


def test_eligible_employee_with_open_issue_is_not_counted_successful():
    issue = SimpleNamespace(
        payroll_issue_id=93,
        employee_id=7,
        issue_code="CALCULATION_FAILURE",
        status="OPEN",
    )
    uow = _valid_uow(issues=[issue])

    outcome = _evaluate(uow)

    assert outcome.status == "FAILED"
    assert outcome.successful_employee_ids == ()
    assert outcome.failed_employee_ids == (7,)


def test_stale_attempt_is_rejected_before_qa_reads_or_transitions():
    uow = _valid_uow(locked=False)

    with pytest.raises(Exception, match="no longer active"):
        _evaluate(uow)

    assert uow.transitions == []
    assert uow.commits == 0
