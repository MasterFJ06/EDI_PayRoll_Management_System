from datetime import date
from types import SimpleNamespace

import pytest

from app.application.payroll.employee_eligibility_resolver import (
    EmployeeEligibilityResolver,
    EmployeeEligibilityResult,
)


class EmployeeRepositoryFake:
    def __init__(self, *employees: SimpleNamespace) -> None:
        self.employees = list(employees)

    def list_all(self) -> list[SimpleNamespace]:
        return sorted(self.employees, key=lambda item: item.employee_id)


def employee(
    employee_id: int,
    joining_date: date,
    employment_end_date: date | None = None,
    employment_status: str = "ACTIVE",
) -> SimpleNamespace:
    return SimpleNamespace(
        employee_id=employee_id,
        joining_date=joining_date,
        employment_end_date=employment_end_date,
        employment_status=employment_status,
    )


def resolve(
    *employees: SimpleNamespace,
    year: int = 2026,
    month: int = 5,
) -> EmployeeEligibilityResult:
    uow = SimpleNamespace(employees=EmployeeRepositoryFake(*employees))
    return EmployeeEligibilityResolver(uow).resolve(year, month)


@pytest.mark.parametrize(
    ("joining_date", "employment_end_date"),
    [
        (date(2026, 1, 1), None),
        (date(2026, 1, 1), date(2026, 6, 1)),
        (date(2026, 5, 15), None),
        (date(2025, 1, 1), date(2026, 5, 15)),
        (date(2026, 5, 1), None),
        (date(2026, 5, 31), None),
        (date(2025, 1, 1), date(2026, 5, 1)),
        (date(2025, 1, 1), date(2026, 5, 31)),
    ],
)
def test_inclusive_employment_period_overlap_is_eligible(
    joining_date: date,
    employment_end_date: date | None,
) -> None:
    result = resolve(employee(7, joining_date, employment_end_date))

    assert [item.employee_id for item in result.eligible_employees] == [7]
    assert result.excluded_employee_ids == ()


@pytest.mark.parametrize(
    ("joining_date", "employment_end_date"),
    [
        (date(2025, 1, 1), date(2026, 4, 30)),
        (date(2026, 6, 1), None),
    ],
)
def test_non_overlapping_employment_interval_is_excluded(
    joining_date: date,
    employment_end_date: date | None,
) -> None:
    result = resolve(employee(8, joining_date, employment_end_date))

    assert result.eligible_employees == ()
    assert result.excluded_employee_ids == (8,)


@pytest.mark.parametrize(
    ("year", "month", "expected_end"),
    [
        (2026, 2, date(2026, 2, 28)),
        (2024, 2, date(2024, 2, 29)),
        (2026, 4, date(2026, 4, 30)),
        (2026, 5, date(2026, 5, 31)),
    ],
)
def test_payroll_period_uses_calendar_month_end(
    year: int,
    month: int,
    expected_end: date,
) -> None:
    result = resolve(year=year, month=month)

    assert result.payroll_period_start == date(year, month, 1)
    assert result.payroll_period_end == expected_end


def test_classifies_multiple_employees_in_repository_order_and_ignores_status():
    result = resolve(
        employee(3, date(2026, 1, 1), date(2026, 5, 15), "TERMINATED"),
        employee(1, date(2026, 6, 1)),
        employee(2, date(2026, 5, 31), None, "INACTIVE"),
    )

    assert [item.employee_id for item in result.eligible_employees] == [2, 3]
    assert result.excluded_employee_ids == (1,)
    assert result.eligible_employees[0].applicable_employment_start == date(
        2026, 5, 31
    )
    assert result.eligible_employees[0].applicable_employment_end == date(
        2026, 5, 31
    )
    assert result.eligible_employees[1].applicable_employment_start == date(
        2026, 5, 1
    )
    assert result.eligible_employees[1].applicable_employment_end == date(
        2026, 5, 15
    )


def test_empty_employee_population_is_returned_without_failure():
    result = resolve()

    assert result.eligible_employees == ()
    assert result.excluded_employee_ids == ()


def test_resolver_needs_no_employment_history_or_other_payroll_inputs():
    employees = EmployeeRepositoryFake(employee(11, date(2026, 5, 1)))
    uow = SimpleNamespace(employees=employees)

    result = EmployeeEligibilityResolver(uow).resolve(2026, 5)

    assert not hasattr(uow, "employment_history")
    assert [item.employee_id for item in result.eligible_employees] == [11]
