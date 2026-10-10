from dataclasses import FrozenInstanceError
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.payroll.compensation_snapshot import (
    CompensationSnapshotResolver,
)


class SnapshotUnitOfWork:
    def __init__(self, assignments=None, revisions=None, revision_components=None, components=None):
        self.assignments = assignments or {}
        self.revisions = revisions or {}
        self.revision_components = revision_components or {}
        self.components = components or {}
        self.issues = []
        self.employee_salary_assignments = SimpleNamespace(
            get_applicable_for_employee=self._applicable_assignments
        )
        self.salary_revisions = SimpleNamespace(get_by_id=self._get_revision)
        self.salary_revision_components = SimpleNamespace(
            get_by_revision=lambda revision_id: self.revision_components.get(
                revision_id, []
            )
        )
        self.salary_components = SimpleNamespace(
            get_by_ids=lambda component_ids: [
                item for item_id, item in self.components.items() if item_id in component_ids
            ]
        )
        self.payroll_runs = SimpleNamespace(
            get_by_id=lambda run_id: object(),
            lock_active_attempt=lambda run_id, attempt_number: object(),
        )
        self.employees = SimpleNamespace(get_by_id=lambda employee_id: object())
        self.payroll_processing_issues = SimpleNamespace(add=self._add_issue)

    def _get_revision(self, revision_id):
        return self.revisions.get(revision_id)

    def _applicable_assignments(self, employee_id, snapshot_date):
        return [
            assignment
            for assignment in self.assignments.get(employee_id, [])
            if assignment.effective_from <= snapshot_date
            and (assignment.effective_to is None or assignment.effective_to >= snapshot_date)
        ]

    def _add_issue(self, issue):
        issue.payroll_issue_id = len(self.issues) + 1
        self.issues.append(issue)

    def commit(self):
        pass


def _assignment(assignment_id=10, employee_id=7, revision_id=20, start=date(2026, 1, 1), end=None):
    return SimpleNamespace(
        salary_assignment_id=assignment_id,
        employee_id=employee_id,
        salary_revision_id=revision_id,
        effective_from=start,
        effective_to=end,
    )


def _revision(revision_id=20, start=date(2026, 1, 1), end=None):
    return SimpleNamespace(
        salary_revision_id=revision_id,
        salary_structure_id=30,
        revision_number=1,
        effective_from=start,
        effective_to=end,
    )


def _component(component_id, name, kind):
    return SimpleNamespace(
        salary_component_id=component_id,
        component_code=f"C{component_id}",
        component_name=name,
        component_type=kind,
        status="ACTIVE",
    )


def _revision_component(
    component_id,
    calculation_type,
    amount=None,
    rate=None,
    base=None,
    is_overtime_base=False,
):
    return SimpleNamespace(
        salary_revision_id=20,
        salary_component_id=component_id,
        calculation_type=calculation_type,
        is_overtime_base=is_overtime_base,
        fixed_amount=amount,
        percentage_value=rate,
        base_component_id=base,
    )


def _resolve(uow, employee_ids=(7,), boundary=datetime(2026, 1, 1, 12, 30)):
    return CompensationSnapshotResolver(uow).resolve(77, 1, boundary, employee_ids)


def test_snapshot_captures_persisted_boundary_assignment_revision_and_components():
    fixed_source = _component(1, "Base Pay", "EARNING")
    percent_source = _component(2, "Tax", "DEDUCTION")
    uow = SnapshotUnitOfWork(
        assignments={7: [_assignment(start=date(2026, 1, 1), end=date(2026, 1, 1))]},
        revisions={20: _revision(start=date(2026, 1, 1), end=date(2026, 1, 1))},
        revision_components={
            20: [
                _revision_component(1, "FIXED", amount=Decimal("1200.00")),
                _revision_component(2, "PERCENTAGE", rate=Decimal("2.5000"), base=1),
            ]
        },
        components={1: fixed_source, 2: percent_source},
    )

    result = _resolve(uow)
    employee = result.snapshot.employees[0]
    assert result.blocking_issue_ids == ()
    assert result.snapshot.processing_started_at == datetime(2026, 1, 1, 12, 30)
    assert result.snapshot.snapshot_date == date(2026, 1, 1)
    assert employee.employee_id == 7
    assert employee.assignment.salary_assignment_id == 10
    assert employee.assignment.salary_revision_id == 20
    assert employee.assignment.effective_to == date(2026, 1, 1)
    assert employee.revision.salary_structure_id == 30
    assert employee.revision.effective_to == date(2026, 1, 1)
    assert employee.revision.components[0].fixed_amount == Decimal("1200.00")
    assert employee.revision.components[0].component_type == "EARNING"
    assert employee.revision.components[0].calculation_type == "FIXED"
    assert employee.revision.components[0].is_overtime_base is False
    assert employee.revision.components[1].percentage_value == Decimal("2.5000")
    assert employee.revision.components[1].base_component_id == 1
    assert employee.revision.components[1].component_type == "DEDUCTION"
    assert employee.revision.components[1].calculation_type == "PERCENTAGE"

    fixed_source.component_name = "Changed"
    uow.assignments[7][0].salary_revision_id = 999
    uow.revisions[20].revision_number = 999
    assert employee.revision.components[0].component_name == "Base Pay"
    assert employee.assignment.salary_revision_id == 20
    assert employee.revision.revision_number == 1
    with pytest.raises(FrozenInstanceError):
        employee.employee_id = 8


@pytest.mark.parametrize("is_overtime_base", [True, False])
def test_snapshot_copies_authoritative_overtime_base_flag_without_name_inference(
    is_overtime_base,
):
    uow = SnapshotUnitOfWork(
        assignments={7: [_assignment()]},
        revisions={20: _revision()},
        revision_components={
            20: [
                _revision_component(
                    1,
                    "FIXED",
                    amount=Decimal("1200.00"),
                    is_overtime_base=is_overtime_base,
                )
            ]
        },
        components={1: _component(1, "Not a Base Component Name", "EARNING")},
    )
    result = _resolve(uow)
    component = result.snapshot.employees[0].revision.components[0]
    assert component.is_overtime_base is is_overtime_base
    assert component.fixed_amount == Decimal("1200.00")


@pytest.mark.parametrize(
    ("assignments", "revisions", "expected_code"),
    [
        ([], {20: _revision()}, "SALARY_ASSIGNMENT_MISSING"),
        (
            [_assignment(10), _assignment(11)],
            {20: _revision()},
            "SALARY_ASSIGNMENT_AMBIGUOUS",
        ),
        ([_assignment(start=date(2026, 1, 2))], {}, "SALARY_ASSIGNMENT_MISSING"),
        ([_assignment(revision_id=99)], {}, "SALARY_REVISION_MISSING"),
        (
            [_assignment()],
            {20: _revision(start=date(2026, 1, 2))},
            "SALARY_REVISION_NOT_EFFECTIVE",
        ),
        (
            [_assignment()],
            {20: _revision(end=date(2025, 12, 31))},
            "SALARY_REVISION_NOT_EFFECTIVE",
        ),
    ],
)
def test_blocking_conditions_create_open_processing_issues(
    assignments, revisions, expected_code
):
    uow = SnapshotUnitOfWork(
        assignments={7: assignments}, revisions=revisions
    )
    result = _resolve(uow)
    assert result.snapshot.employees == ()
    assert result.blocking_issue_ids == (1,)
    assert len(uow.issues) == 1
    assert uow.issues[0].issue_code == expected_code
    assert uow.issues[0].status == "OPEN"


def test_blocking_issues_can_be_deferred_until_after_consistent_read():
    uow = SnapshotUnitOfWork(assignments={7: []})
    deferred_issues = []

    result = CompensationSnapshotResolver(uow).resolve(
        payroll_run_id=1,
        attempt_number=1,
        processing_started_at=datetime(2026, 10, 8, 12),
        eligible_employee_ids=(7,),
        deferred_issues=deferred_issues,
    )

    assert result.blocking_issue_ids == ()
    assert uow.issues == []
    assert len(deferred_issues) == 1
    assert deferred_issues[0].issue_code == "SALARY_ASSIGNMENT_MISSING"
    assert deferred_issues[0].employee_id == 7


def test_only_eligible_ids_are_snapshotted_and_excluded_employees_are_not_issues():
    uow = SnapshotUnitOfWork()
    result = _resolve(uow, employee_ids=(7,))
    assert result.snapshot.employees == ()
    assert [issue.employee_id for issue in uow.issues] == [7]
    assert all(issue.employee_id != 99 for issue in uow.issues)


def test_assignment_revision_reference_is_followed_without_revision_selection():
    assignments = {7: [_assignment(revision_id=21)]}
    revisions = {20: _revision(20), 21: _revision(21)}
    uow = SnapshotUnitOfWork(assignments=assignments, revisions=revisions)
    looked_up = []
    original = uow.salary_revisions.get_by_id

    def record_lookup(revision_id):
        looked_up.append(revision_id)
        return original(revision_id)

    uow.salary_revisions.get_by_id = record_lookup
    result = _resolve(uow)
    assert result.snapshot.employees[0].revision.salary_revision_id == 21
    assert looked_up == [21]


def test_multiple_eligible_employees_resolve_independently():
    uow = SnapshotUnitOfWork(
        assignments={7: [_assignment(employee_id=7)], 8: []},
        revisions={20: _revision()},
    )
    result = _resolve(uow, employee_ids=(7, 8))
    assert [employee.employee_id for employee in result.snapshot.employees] == [7]
    assert result.blocking_issue_ids == (1,)
    assert uow.issues[0].employee_id == 8


@pytest.mark.parametrize(
    ("revision_components", "components"),
    [
        (
            [_revision_component(1, "FIXED", amount=Decimal("-1.00"))],
            {1: _component(1, "Invalid pay", "EARNING")},
        ),
        (
            [_revision_component(1, "FIXED", amount=Decimal("1.00"))],
            {},
        ),
    ],
)
def test_invalid_component_configuration_creates_open_issue(
    revision_components, components
):
    uow = SnapshotUnitOfWork(
        assignments={7: [_assignment()]},
        revisions={20: _revision()},
        revision_components={20: revision_components},
        components=components,
    )
    result = _resolve(uow)
    assert result.snapshot.employees == ()
    assert result.blocking_issue_ids == (1,)
    assert uow.issues[0].issue_code == "INVALID_COMPENSATION_CONFIGURATION"
    assert uow.issues[0].status == "OPEN"
