from dataclasses import dataclass
from datetime import date, timedelta

from app.application.common.unit_of_work import UnitOfWork
from app.application.compensation.contracts import (
    EmployeeCompensationSnapshot,
    EmployeeSalaryAssignmentSnapshot,
    SalaryComponentSnapshot,
    SalaryRevisionSnapshot,
)
from app.domain.compensation.salary_component import SalaryComponent
from app.domain.compensation.salary_revision import SalaryRevision
from app.domain.compensation.salary_revision_component import SalaryRevisionComponent
from app.domain.shared.exceptions import BusinessRuleViolation


@dataclass(frozen=True)
class CompensationSegmentationCondition:
    code: str
    message: str


@dataclass(frozen=True)
class CompensationSegment:
    employee_id: int
    segment_start: date
    segment_end: date
    compensation: EmployeeCompensationSnapshot


@dataclass(frozen=True)
class CompensationSegmentationResult:
    employee_id: int
    range_start: date
    range_end: date
    segments: tuple[CompensationSegment, ...]
    conditions: tuple[CompensationSegmentationCondition, ...]


@dataclass(frozen=True)
class _CompensationInterval:
    effective_from: date
    effective_to: date
    compensation: EmployeeCompensationSnapshot


class CompensationSegmentationResolver:
    """Read-only resolver for inclusive compensation segments."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def resolve(
        self,
        employee_id: int,
        range_start: date,
        range_end: date,
        current_compensation: EmployeeCompensationSnapshot | None = None,
    ) -> CompensationSegmentationResult:
        employee_range = (employee_id, range_start, range_end)
        if range_start > range_end:
            raise ValueError("Compensation segmentation range must be ordered.")

        intervals, condition = self._get_compensation_intervals(
            employee_id,
            range_start,
            range_end,
            current_compensation,
        )
        if condition is not None:
            return self._blocked(employee_range, condition)

        segments, condition = self._segment_employee(
            employee_id, range_start, range_end, intervals
        )
        if condition is not None:
            return self._blocked(employee_range, condition)
        return CompensationSegmentationResult(
            employee_id=employee_id,
            range_start=range_start,
            range_end=range_end,
            segments=tuple(segments),
            conditions=(),
        )

    def _get_compensation_intervals(
        self,
        employee_id: int,
        range_start: date,
        range_end: date,
        current_compensation: EmployeeCompensationSnapshot | None,
    ) -> tuple[list[_CompensationInterval], CompensationSegmentationCondition | None]:
        assignments = self.uow.employee_salary_assignments.get_intersecting_for_employee(
            employee_id, range_start, range_end
        )
        intervals: list[_CompensationInterval] = []
        revision_cache: dict[int, SalaryRevisionSnapshot] = {}

        for assignment in assignments:
            revision = self.uow.salary_revisions.get_by_id(assignment.salary_revision_id)
            if revision is None:
                return [], CompensationSegmentationCondition(
                    "SALARY_REVISION_MISSING",
                    "An intersecting salary assignment references a missing revision.",
                )

            start = max(range_start, assignment.effective_from, revision.effective_from)
            end = min(
                range_end,
                _effective_end(assignment.effective_to, range_end),
                _effective_end(revision.effective_to, range_end),
            )
            if start > end:
                continue

            if (
                current_compensation is not None
                and current_compensation.assignment.salary_assignment_id
                == assignment.salary_assignment_id
                and current_compensation.revision.salary_revision_id
                == revision.salary_revision_id
            ):
                revision_snapshot = current_compensation.revision
            else:
                revision_snapshot = revision_cache.get(revision.salary_revision_id)
                if revision_snapshot is None:
                    revision_snapshot, condition = self._snapshot_revision(revision)
                    if condition is not None:
                        return [], condition
                    assert revision_snapshot is not None
                    revision_cache[revision.salary_revision_id] = revision_snapshot

            intervals.append(
                _CompensationInterval(
                    effective_from=start,
                    effective_to=end,
                    compensation=EmployeeCompensationSnapshot(
                        employee_id=employee_id,
                        assignment=EmployeeSalaryAssignmentSnapshot(
                            salary_assignment_id=assignment.salary_assignment_id,
                            salary_revision_id=assignment.salary_revision_id,
                            effective_from=assignment.effective_from,
                            effective_to=assignment.effective_to,
                        ),
                        revision=revision_snapshot,
                    ),
                )
            )
        return intervals, None

    def _snapshot_revision(
        self, revision: SalaryRevision
    ) -> tuple[SalaryRevisionSnapshot | None, CompensationSegmentationCondition | None]:
        revision_components = self.uow.salary_revision_components.get_by_revision(
            revision.salary_revision_id
        )
        component_ids = {item.salary_component_id for item in revision_components}
        component_ids.update(
            item.base_component_id
            for item in revision_components
            if item.base_component_id is not None
        )
        components = {
            item.salary_component_id: item
            for item in self.uow.salary_components.get_by_ids(component_ids)
        }

        snapshots: list[SalaryComponentSnapshot] = []
        for revision_component in revision_components:
            component = components.get(revision_component.salary_component_id)
            if component is None:
                return None, CompensationSegmentationCondition(
                    "INVALID_COMPENSATION_CONFIGURATION",
                    "A revision component references a missing salary component.",
                )
            try:
                SalaryComponent(
                    salary_component_id=component.salary_component_id,
                    component_code=component.component_code,
                    component_name=component.component_name,
                    component_type=component.component_type,
                    status=component.status,
                )
                SalaryRevisionComponent(
                    salary_revision_id=revision_component.salary_revision_id,
                    salary_component_id=revision_component.salary_component_id,
                    calculation_type=revision_component.calculation_type,
                    fixed_amount=revision_component.fixed_amount,
                    percentage_value=revision_component.percentage_value,
                    base_component_id=revision_component.base_component_id,
                )
            except BusinessRuleViolation as exc:
                return None, CompensationSegmentationCondition(
                    "INVALID_COMPENSATION_CONFIGURATION", str(exc)
                )
            if (
                revision_component.base_component_id is not None
                and revision_component.base_component_id not in components
            ):
                return None, CompensationSegmentationCondition(
                    "INVALID_COMPENSATION_CONFIGURATION",
                    "A percentage component references a missing base component.",
                )
            snapshots.append(
                SalaryComponentSnapshot(
                    salary_component_id=component.salary_component_id,
                    component_name=component.component_name,
                    component_type=component.component_type,
                    calculation_type=revision_component.calculation_type,
                    is_overtime_base=revision_component.is_overtime_base,
                    fixed_amount=revision_component.fixed_amount,
                    percentage_value=revision_component.percentage_value,
                    base_component_id=revision_component.base_component_id,
                )
            )
        return (
            SalaryRevisionSnapshot(
                salary_revision_id=revision.salary_revision_id,
                salary_structure_id=revision.salary_structure_id,
                revision_number=revision.revision_number,
                effective_from=revision.effective_from,
                effective_to=revision.effective_to,
                components=tuple(snapshots),
            ),
            None,
        )

    @staticmethod
    def _segment_employee(
        employee_id: int,
        range_start: date,
        range_end: date,
        intervals: list[_CompensationInterval],
    ) -> tuple[list[CompensationSegment], CompensationSegmentationCondition | None]:
        boundaries = {range_start, range_end + timedelta(days=1)}
        for interval in intervals:
            boundaries.add(interval.effective_from)
            boundaries.add(interval.effective_to + timedelta(days=1))
        ordered_boundaries = sorted(boundaries)

        segments: list[CompensationSegment] = []
        for index, segment_start in enumerate(ordered_boundaries[:-1]):
            segment_end = ordered_boundaries[index + 1] - timedelta(days=1)
            if segment_start > range_end:
                break
            applicable = [
                interval
                for interval in intervals
                if interval.effective_from <= segment_start
                and interval.effective_to >= segment_end
            ]
            if not applicable:
                return [], CompensationSegmentationCondition(
                    "COMPENSATION_COVERAGE_GAP",
                    "No unique compensation configuration covers the employee's processing range.",
                )
            if len(applicable) > 1:
                return [], CompensationSegmentationCondition(
                    "COMPENSATION_COVERAGE_OVERLAP",
                    "Multiple compensation configurations overlap the employee's processing range.",
                )
            segments.append(
                CompensationSegment(
                    employee_id=employee_id,
                    segment_start=segment_start,
                    segment_end=segment_end,
                    compensation=applicable[0].compensation,
                )
            )

        if not _segment_invariants_hold(employee_id, range_start, range_end, segments):
            return [], CompensationSegmentationCondition(
                "SEGMENT_INVARIANT_VIOLATION",
                "The generated compensation segments do not exactly cover the employee's processing range.",
            )
        return segments, None

    @staticmethod
    def _blocked(
        employee_range: tuple[int, date, date],
        condition: CompensationSegmentationCondition,
    ) -> CompensationSegmentationResult:
        employee_id, range_start, range_end = employee_range
        return CompensationSegmentationResult(
            employee_id=employee_id,
            range_start=range_start,
            range_end=range_end,
            segments=(),
            conditions=(condition,),
        )


def _effective_end(effective_to: date | None, range_end: date) -> date:
    return range_end if effective_to is None else min(effective_to, range_end)


def _segment_invariants_hold(
    employee_id: int,
    range_start: date,
    range_end: date,
    segments: list[CompensationSegment],
) -> bool:
    if not segments or segments[0].segment_start != range_start or segments[-1].segment_end != range_end:
        return False
    for index, segment in enumerate(segments):
        if segment.segment_start > segment.segment_end or segment.employee_id != employee_id:
            return False
        if index and segment.segment_start != segments[index - 1].segment_end + timedelta(days=1):
            return False
    return True
