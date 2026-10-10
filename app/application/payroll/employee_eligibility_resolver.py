from calendar import monthrange
from dataclasses import dataclass
from datetime import date

from app.application.common.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class EligibleEmployee:
    employee_id: int
    applicable_employment_start: date
    applicable_employment_end: date


@dataclass(frozen=True)
class EmployeeEligibilityResult:
    payroll_period_start: date
    payroll_period_end: date
    eligible_employees: tuple[EligibleEmployee, ...]
    excluded_employee_ids: tuple[int, ...]


class EmployeeEligibilityResolver:
    """Classifies employees by inclusive employment overlap with a payroll month."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def resolve(self, payroll_year: int, payroll_month: int) -> EmployeeEligibilityResult:
        payroll_period_start = date(payroll_year, payroll_month, 1)
        payroll_period_end = date(
            payroll_year,
            payroll_month,
            monthrange(payroll_year, payroll_month)[1],
        )

        eligible: list[EligibleEmployee] = []
        excluded: list[int] = []
        for employee in self.uow.employees.list_all():
            employment_end = employee.employment_end_date
            overlaps_period = (
                employee.joining_date <= payroll_period_end
                and (
                    employment_end is None
                    or employment_end >= payroll_period_start
                )
            )
            if overlaps_period:
                eligible.append(
                    EligibleEmployee(
                        employee_id=employee.employee_id,
                        applicable_employment_start=max(
                            employee.joining_date, payroll_period_start
                        ),
                        applicable_employment_end=min(
                            payroll_period_end
                            if employment_end is None
                            else employment_end,
                            payroll_period_end,
                        ),
                    )
                )
            else:
                excluded.append(employee.employee_id)

        return EmployeeEligibilityResult(
            payroll_period_start=payroll_period_start,
            payroll_period_end=payroll_period_end,
            eligible_employees=tuple(eligible),
            excluded_employee_ids=tuple(excluded),
        )
