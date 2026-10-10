from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.reporting.payroll_summary_service import (
    FinalizedPayrollSummaryService,
)
from app.domain.shared.exceptions import BusinessRuleViolation


class SummaryUnitOfWork:
    def __init__(self, status: str = "FINALIZED", aggregate=None) -> None:
        self.run = SimpleNamespace(
            payroll_run_id=44,
            payroll_year=2026,
            payroll_month=10,
            status=status,
            initiated_by_user_id=7,
        )
        self.payroll_runs = SimpleNamespace(
            get_by_id=lambda run_id: self.run if run_id == 44 else None
        )
        self.aggregate_calls: list[int] = []
        self.aggregate = aggregate or (
            2,
            Decimal("1234.56"),
            Decimal("34.56"),
            Decimal("1200.00"),
        )
        self.payroll_results = SimpleNamespace(aggregate_by_run=self._aggregate)

    def _aggregate(self, run_id: int):
        self.aggregate_calls.append(run_id)
        return self.aggregate


def test_summary_returns_persisted_aggregates_without_mutation() -> None:
    uow = SummaryUnitOfWork()
    summary = FinalizedPayrollSummaryService(uow).get(44)

    assert summary is not None
    assert summary.employee_result_count == 2
    assert summary.total_gross_pay == Decimal("1234.56")
    assert summary.total_deductions == Decimal("34.56")
    assert summary.total_net_pay == Decimal("1200.00")
    assert uow.aggregate_calls == [44]
    assert uow.run.status == "FINALIZED"


def test_missing_run_returns_none_without_aggregate_query() -> None:
    uow = SummaryUnitOfWork()
    assert FinalizedPayrollSummaryService(uow).get(99) is None
    assert uow.aggregate_calls == []


@pytest.mark.parametrize("state", ["CREATED", "PROCESSING", "PROCESSED", "FAILED"])
def test_non_finalized_run_is_rejected_before_aggregate_query(state: str) -> None:
    uow = SummaryUnitOfWork(status=state)
    with pytest.raises(BusinessRuleViolation):
        FinalizedPayrollSummaryService(uow).get(44)
    assert uow.aggregate_calls == []


def test_zero_result_finalized_run_is_rejected_without_fabricating_totals() -> None:
    uow = SummaryUnitOfWork(aggregate=(0, None, None, None))
    with pytest.raises(BusinessRuleViolation, match="at least one Payroll Result"):
        FinalizedPayrollSummaryService(uow).get(44)
