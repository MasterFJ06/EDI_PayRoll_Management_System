from datetime import date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.payroll.compensation_snapshot import (
    CompensationSnapshot,
    EmployeeCompensationSnapshot,
    EmployeeSalaryAssignmentSnapshot,
    SalaryRevisionSnapshot,
)
from app.application.payroll.employee_eligibility_resolver import (
    EligibleEmployee,
    EmployeeEligibilityResult,
)
from app.application.payroll.period_segmentation import PayrollPeriodSegmenter
from app.application.compensation.segmentation import CompensationSegmentationResolver


class SegmentationUnitOfWork:
    def __init__(self, assignments, revisions, revision_components=None, components=None):
        self.assignments = assignments
        self.revisions = revisions
        self.revision_components = revision_components or {}
        self.components = components or {}
        self.issues = []
        self.queried_employees = []
        self.employee_salary_assignments = SimpleNamespace(
            get_intersecting_for_employee=self._get_assignments
        )
        self.salary_revisions = SimpleNamespace(
            get_by_id=lambda revision_id: self.revisions.get(revision_id)
        )
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

    def _get_assignments(self, employee_id, period_start, period_end):
        self.queried_employees.append(employee_id)
        return [
            assignment
            for assignment in self.assignments
            if assignment.employee_id == employee_id
            and assignment.effective_from <= period_end
            and (assignment.effective_to is None or assignment.effective_to >= period_start)
        ]

    def _add_issue(self, issue):
        issue.payroll_issue_id = len(self.issues) + 1
        self.issues.append(issue)

    def commit(self):
        pass


def _assignment(assignment_id, revision_id, start, end):
    return SimpleNamespace(
        salary_assignment_id=assignment_id,
        employee_id=7,
        salary_revision_id=revision_id,
        effective_from=start,
        effective_to=end,
    )


def _revision(revision_id, start, end):
    return SimpleNamespace(
        salary_revision_id=revision_id,
        salary_structure_id=30,
        revision_number=revision_id,
        effective_from=start,
        effective_to=end,
    )


def _employee_snapshot(assignment, revision):
    return EmployeeCompensationSnapshot(
        employee_id=7,
        assignment=EmployeeSalaryAssignmentSnapshot(
            salary_assignment_id=assignment.salary_assignment_id,
            salary_revision_id=assignment.salary_revision_id,
            effective_from=assignment.effective_from,
            effective_to=assignment.effective_to,
        ),
        revision=SalaryRevisionSnapshot(
            salary_revision_id=revision.salary_revision_id,
            salary_structure_id=revision.salary_structure_id,
            revision_number=revision.revision_number,
            effective_from=revision.effective_from,
            effective_to=revision.effective_to,
            components=(),
        ),
    )


def _resolve(
    assignments,
    revisions,
    *,
    employee_start=date(2026, 5, 1),
    employee_end=date(2026, 5, 31),
    excluded=(),
    snapshot_boundary=date(2026, 5, 1),
    revision_components=None,
    components=None,
):
    eligibility = EmployeeEligibilityResult(
        payroll_period_start=date(2026, 5, 1),
        payroll_period_end=date(2026, 5, 31),
        eligible_employees=(
            EligibleEmployee(7, employee_start, employee_end),
        ),
        excluded_employee_ids=tuple(excluded),
    )
    snapshot_assignment = next(
        assignment
        for assignment in assignments
        if assignment.effective_from <= snapshot_boundary
        and (assignment.effective_to is None or assignment.effective_to >= snapshot_boundary)
    )
    snapshot_revision = revisions[snapshot_assignment.salary_revision_id]
    snapshot = CompensationSnapshot(
        payroll_run_id=77,
        processing_started_at=datetime.combine(snapshot_boundary, datetime.min.time()),
        snapshot_date=snapshot_boundary,
        employees=(_employee_snapshot(snapshot_assignment, snapshot_revision),),
    )
    uow = SegmentationUnitOfWork(
        assignments, revisions, revision_components, components
    )
    result = PayrollPeriodSegmenter(uow).resolve(77, 1, eligibility, snapshot)
    return result, uow


def _resolve_core(
    assignments,
    revisions,
    *,
    start=date(2026, 5, 1),
    end=date(2026, 5, 31),
    revision_components=None,
    components=None,
):
    uow = SegmentationUnitOfWork(
        assignments, revisions, revision_components, components
    )
    result = CompensationSegmentationResolver(uow).resolve(7, start, end)
    return result, uow


def _intervals(result):
    return [(segment.segment_start, segment.segment_end) for segment in result.segments]


def _assert_exact_daily_coverage(result, start, end):
    dates = []
    for segment in result.segments:
        assert segment.segment_start <= segment.segment_end
        current = segment.segment_start
        while current <= segment.segment_end:
            dates.append(current)
            current += timedelta(days=1)
    expected = []
    current = start
    while current <= end:
        expected.append(current)
        current += timedelta(days=1)
    assert dates == expected


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (date(2026, 5, 1), date(2026, 5, 31), [(date(2026, 5, 1), date(2026, 5, 31))]),
        (date(2026, 5, 15), date(2026, 5, 31), [(date(2026, 5, 15), date(2026, 5, 31))]),
        (date(2026, 5, 1), date(2026, 5, 15), [(date(2026, 5, 1), date(2026, 5, 15))]),
        (date(2026, 5, 10), date(2026, 5, 20), [(date(2026, 5, 10), date(2026, 5, 20))]),
    ],
)
def test_employment_intersection_produces_inclusive_single_segment(start, end, expected):
    assignment = _assignment(10, 20, date(2026, 1, 1), None)
    revision = _revision(20, date(2026, 1, 1), None)
    result, _ = _resolve(
        [assignment], {20: revision}, employee_start=start, employee_end=end
    )
    assert _intervals(result) == expected
    _assert_exact_daily_coverage(result, start, end)


def test_multiple_adjacent_compensation_changes_form_ordered_segments():
    assignments = [
        _assignment(10, 20, date(2026, 5, 1), date(2026, 5, 9)),
        _assignment(11, 21, date(2026, 5, 10), date(2026, 5, 19)),
        _assignment(12, 22, date(2026, 5, 20), date(2026, 5, 31)),
    ]
    revisions = {
        20: _revision(20, date(2026, 5, 1), date(2026, 5, 9)),
        21: _revision(21, date(2026, 5, 10), date(2026, 5, 19)),
        22: _revision(22, date(2026, 5, 20), date(2026, 5, 31)),
    }
    result, _ = _resolve(assignments, revisions)
    assert _intervals(result) == [
        (date(2026, 5, 1), date(2026, 5, 9)),
        (date(2026, 5, 10), date(2026, 5, 19)),
        (date(2026, 5, 20), date(2026, 5, 31)),
    ]
    assert [
        segment.compensation.assignment.salary_assignment_id
        for segment in result.segments
    ] == [10, 11, 12]
    _assert_exact_daily_coverage(result, date(2026, 5, 1), date(2026, 5, 31))


def test_each_segment_retains_its_direct_revision_component_configuration():
    assignments = [
        _assignment(10, 20, date(2026, 5, 1), date(2026, 5, 14)),
        _assignment(11, 21, date(2026, 5, 15), date(2026, 5, 31)),
    ]
    revisions = {
        20: _revision(20, date(2026, 5, 1), date(2026, 5, 14)),
        21: _revision(21, date(2026, 5, 15), date(2026, 5, 31)),
    }
    revision_component = SimpleNamespace(
        salary_revision_id=21,
        salary_component_id=3,
        calculation_type="FIXED",
        is_overtime_base=True,
        fixed_amount=Decimal("900.00"),
        percentage_value=None,
        base_component_id=None,
    )
    component = SimpleNamespace(
        salary_component_id=3,
        component_code="BASE",
        component_name="Base Salary",
        component_type="EARNING",
        status="ACTIVE",
    )
    result, _ = _resolve(
        assignments,
        revisions,
        revision_components={21: [revision_component]},
        components={3: component},
    )
    second = result.segments[1]
    assert second.compensation.revision.salary_revision_id == 21
    assert second.compensation.revision.components[0].component_name == "Base Salary"
    assert second.compensation.revision.components[0].component_type == "EARNING"
    assert second.compensation.revision.components[0].calculation_type == "FIXED"
    assert second.compensation.revision.components[0].fixed_amount == Decimal("900.00")
    assert second.compensation.revision.components[0].is_overtime_base is True
    assert not hasattr(second, "calculated_amount")


@pytest.mark.parametrize(
    ("second_start", "first_end", "expected_issue"),
    [
        (date(2026, 5, 15), date(2026, 5, 20), "COMPENSATION_COVERAGE_OVERLAP"),
        (date(2026, 5, 15), date(2026, 5, 14), None),
        (date(2026, 5, 14), date(2026, 5, 14), "COMPENSATION_COVERAGE_OVERLAP"),
    ],
)
def test_compensation_overlap_or_adjacency(second_start, first_end, expected_issue):
    assignments = [
        _assignment(10, 20, date(2026, 5, 1), first_end),
        _assignment(11, 21, second_start, date(2026, 5, 31)),
    ]
    revisions = {
        20: _revision(20, date(2026, 5, 1), first_end),
        21: _revision(21, second_start, date(2026, 5, 31)),
    }
    result, uow = _resolve(assignments, revisions)
    if expected_issue:
        assert result.segments == ()
        assert result.blocked_employee_ids == (7,)
        assert result.blocking_issue_ids == (1,)
        assert uow.issues[0].issue_code == expected_issue
        assert uow.issues[0].status == "OPEN"
    else:
        assert result.blocked_employee_ids == ()
        assert _intervals(result) == [
            (date(2026, 5, 1), date(2026, 5, 14)),
            (date(2026, 5, 15), date(2026, 5, 31)),
        ]


def test_compensation_gap_creates_open_blocking_issue():
    assignments = [
        _assignment(10, 20, date(2026, 5, 1), date(2026, 5, 10)),
        _assignment(11, 21, date(2026, 5, 15), date(2026, 5, 31)),
    ]
    revisions = {
        20: _revision(20, date(2026, 5, 1), date(2026, 5, 10)),
        21: _revision(21, date(2026, 5, 15), date(2026, 5, 31)),
    }
    result, uow = _resolve(assignments, revisions)
    assert result.segments == ()
    assert result.blocked_employee_ids == (7,)
    assert uow.issues[0].issue_code == "COMPENSATION_COVERAGE_GAP"
    assert uow.issues[0].status == "OPEN"


def test_intersecting_assignment_with_missing_revision_creates_open_issue():
    assignments = [
        _assignment(10, 20, date(2026, 5, 1), date(2026, 5, 14)),
        _assignment(11, 99, date(2026, 5, 15), date(2026, 5, 31)),
    ]
    revisions = {20: _revision(20, date(2026, 5, 1), date(2026, 5, 14))}
    result, uow = _resolve(assignments, revisions)
    assert result.segments == ()
    assert result.blocked_employee_ids == (7,)
    assert uow.issues[0].issue_code == "SALARY_REVISION_MISSING"
    assert uow.issues[0].status == "OPEN"


def test_revision_effective_dates_participate_in_coverage_and_boundaries():
    assignment = _assignment(10, 20, date(2026, 5, 1), date(2026, 5, 31))
    revision = _revision(20, date(2026, 5, 5), date(2026, 5, 31))
    result, uow = _resolve(
        [assignment], {20: revision}, snapshot_boundary=date(2026, 5, 5)
    )
    assert result.segments == ()
    assert uow.issues[0].issue_code == "COMPENSATION_COVERAGE_GAP"


def test_excluded_employees_do_not_reach_segmentation():
    assignment = _assignment(10, 20, date(2026, 1, 1), None)
    revision = _revision(20, date(2026, 1, 1), None)
    result, uow = _resolve([assignment], {20: revision}, excluded=(99,))
    assert uow.queried_employees == [7]
    assert 99 not in result.blocked_employee_ids
    assert all(issue.employee_id != 99 for issue in uow.issues)


def test_first_or_last_period_boundary_does_not_create_out_of_range_segment():
    assignments = [
        _assignment(10, 20, date(2026, 5, 1), date(2026, 5, 30)),
        _assignment(11, 21, date(2026, 5, 31), date(2026, 5, 31)),
    ]
    revisions = {
        20: _revision(20, date(2026, 5, 1), date(2026, 5, 30)),
        21: _revision(21, date(2026, 5, 31), date(2026, 5, 31)),
    }
    result, _ = _resolve(assignments, revisions)
    assert _intervals(result) == [
        (date(2026, 5, 1), date(2026, 5, 30)),
        (date(2026, 5, 31), date(2026, 5, 31)),
    ]


def test_compensation_change_on_joining_boundary_creates_no_empty_segment():
    assignments = [
        _assignment(10, 20, date(2026, 5, 1), date(2026, 5, 14)),
        _assignment(11, 21, date(2026, 5, 15), None),
    ]
    revisions = {
        20: _revision(20, date(2026, 5, 1), date(2026, 5, 14)),
        21: _revision(21, date(2026, 5, 15), None),
    }
    result, _ = _resolve(
        assignments,
        revisions,
        employee_start=date(2026, 5, 15),
        snapshot_boundary=date(2026, 5, 15),
    )
    assert _intervals(result) == [(date(2026, 5, 15), date(2026, 5, 31))]


def test_compensation_change_on_leaving_boundary_creates_no_empty_segment():
    assignments = [
        _assignment(10, 20, date(2026, 5, 1), date(2026, 5, 14)),
        _assignment(11, 21, date(2026, 5, 15), None),
    ]
    revisions = {
        20: _revision(20, date(2026, 5, 1), date(2026, 5, 14)),
        21: _revision(21, date(2026, 5, 15), None),
    }
    result, _ = _resolve(
        assignments,
        revisions,
        employee_end=date(2026, 5, 15),
    )
    assert _intervals(result) == [
        (date(2026, 5, 1), date(2026, 5, 14)),
        (date(2026, 5, 15), date(2026, 5, 15)),
    ]


def test_read_only_core_resolves_single_segment_and_inclusive_boundaries():
    assignment = _assignment(10, 20, date(2026, 5, 1), None)
    revision = _revision(20, date(2026, 4, 1), None)
    result, uow = _resolve_core([assignment], {20: revision})
    assert [(item.segment_start, item.segment_end) for item in result.segments] == [
        (date(2026, 5, 1), date(2026, 5, 31))
    ]
    assert result.segments[0].compensation.assignment.salary_assignment_id == 10
    assert result.segments[0].compensation.revision.salary_revision_id == 20
    assert result.conditions == ()
    assert uow.issues == []


def test_read_only_core_resolves_adjacent_segments_on_exact_boundary_dates():
    assignments = [
        _assignment(10, 20, date(2026, 5, 1), date(2026, 5, 14)),
        _assignment(11, 21, date(2026, 5, 15), date(2026, 5, 31)),
    ]
    revisions = {
        20: _revision(20, date(2026, 5, 1), date(2026, 5, 14)),
        21: _revision(21, date(2026, 5, 15), date(2026, 5, 31)),
    }
    result, uow = _resolve_core(assignments, revisions)
    assert [(item.segment_start, item.segment_end) for item in result.segments] == [
        (date(2026, 5, 1), date(2026, 5, 14)),
        (date(2026, 5, 15), date(2026, 5, 31)),
    ]
    assert result.conditions == ()
    assert uow.issues == []


@pytest.mark.parametrize(
    ("assignments", "revisions", "expected_code"),
    [
        (
            [_assignment(10, 20, date(2026, 5, 1), date(2026, 5, 10)),
             _assignment(11, 21, date(2026, 5, 15), date(2026, 5, 31))],
            {20: _revision(20, date(2026, 5, 1), date(2026, 5, 10)),
             21: _revision(21, date(2026, 5, 15), date(2026, 5, 31))},
            "COMPENSATION_COVERAGE_GAP",
        ),
        (
            [_assignment(10, 20, date(2026, 5, 1), date(2026, 5, 15)),
             _assignment(11, 21, date(2026, 5, 15), date(2026, 5, 31))],
            {20: _revision(20, date(2026, 5, 1), date(2026, 5, 15)),
             21: _revision(21, date(2026, 5, 15), date(2026, 5, 31))},
            "COMPENSATION_COVERAGE_OVERLAP",
        ),
        (
            [_assignment(10, 99, date(2026, 5, 1), None)],
            {},
            "SALARY_REVISION_MISSING",
        ),
    ],
)
def test_read_only_core_returns_structured_conditions_without_persisting(
    assignments, revisions, expected_code
):
    result, uow = _resolve_core(assignments, revisions)
    assert result.segments == ()
    assert [condition.code for condition in result.conditions] == [expected_code]
    assert uow.issues == []


def test_read_only_core_does_not_fallback_to_another_revision():
    # Revision 20 exists, but the assignment's direct reference to 99 is missing.
    assignment = _assignment(10, 99, date(2026, 5, 1), None)
    unrelated_revision = _revision(20, date(2026, 5, 1), None)
    result, uow = _resolve_core([assignment], {20: unrelated_revision})
    assert [condition.code for condition in result.conditions] == [
        "SALARY_REVISION_MISSING"
    ]
    assert uow.issues == []


def test_read_only_core_returns_invalid_configuration_condition():
    assignment = _assignment(10, 20, date(2026, 5, 1), None)
    revision = _revision(20, date(2026, 5, 1), None)
    revision_component = SimpleNamespace(
        salary_revision_id=20,
        salary_component_id=3,
        calculation_type="FIXED",
        is_overtime_base=False,
        fixed_amount=Decimal("-1.00"),
        percentage_value=None,
        base_component_id=None,
    )
    component = SimpleNamespace(
        salary_component_id=3,
        component_code="BASE",
        component_name="Base Salary",
        component_type="EARNING",
        status="ACTIVE",
    )
    result, uow = _resolve_core(
        [assignment],
        {20: revision},
        revision_components={20: [revision_component]},
        components={3: component},
    )
    assert [condition.code for condition in result.conditions] == [
        "INVALID_COMPENSATION_CONFIGURATION"
    ]
    assert uow.issues == []


@pytest.mark.parametrize("is_overtime_base", [True, False])
def test_segmentation_resolver_copies_authoritative_overtime_base_flag(
    is_overtime_base,
):
    assignment = _assignment(10, 20, date(2026, 5, 1), None)
    revision = _revision(20, date(2026, 5, 1), None)
    revision_component = SimpleNamespace(
        salary_revision_id=20,
        salary_component_id=3,
        calculation_type="FIXED",
        is_overtime_base=is_overtime_base,
        fixed_amount=Decimal("900.00"),
        percentage_value=None,
        base_component_id=None,
    )
    component = SimpleNamespace(
        salary_component_id=3,
        component_code="C3",
        component_name="Unrelated Component Name",
        component_type="EARNING",
        status="ACTIVE",
    )
    result, uow = _resolve_core(
        [assignment],
        {20: revision},
        revision_components={20: [revision_component]},
        components={3: component},
    )
    value = result.segments[0].compensation.revision.components[0]
    assert value.is_overtime_base is is_overtime_base
    assert value.fixed_amount == Decimal("900.00")
    assert uow.issues == []
