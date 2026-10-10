from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.reporting.payroll_results_report_service import (
    PayrollResultsReportService,
    decode_payroll_results_cursor,
    encode_payroll_results_cursor,
)
from app.domain.payroll.payroll_result_report import PayrollResultReportRecord
from app.domain.shared.exceptions import BusinessRuleViolation


class ReportUnitOfWork:
    def __init__(self, status: str = "FINALIZED") -> None:
        self.payroll_runs = SimpleNamespace(
            get_by_id=lambda run_id: (
                SimpleNamespace(payroll_run_id=run_id, status=status)
                if run_id == 44
                else None
            )
        )
        self.records = [
            PayrollResultReportRecord(
                payroll_result_id=result_id,
                payroll_run_id=44,
                employee_id=employee_id,
                salary_assignment_id=employee_id + 100,
                gross_earnings=Decimal("1200.01"),
                total_deductions=Decimal("20.00"),
                net_salary=Decimal("1180.01"),
                employee_code=f"E-{employee_id}",
                employee_name=f"First {employee_id} Last {employee_id}",
            )
            for result_id, employee_id in (
                (8, 2),
                (9, 4),
                (10, 7),
                (11, 9),
                (12, 12),
            )
        ]
        self.page_calls: list[tuple[int, int | None, int | None, int]] = []
        self.payroll_results = SimpleNamespace(list_report_page=self._list_page)

    def _list_page(
        self,
        payroll_run_id: int,
        after_employee_id: int | None,
        after_payroll_result_id: int | None,
        limit: int,
    ) -> list[PayrollResultReportRecord]:
        self.page_calls.append(
            (payroll_run_id, after_employee_id, after_payroll_result_id, limit)
        )
        rows = [row for row in self.records if row.payroll_run_id == payroll_run_id]
        if after_employee_id is not None and after_payroll_result_id is not None:
            rows = [
                row
                for row in rows
                if (row.employee_id, row.payroll_result_id)
                > (after_employee_id, after_payroll_result_id)
            ]
        return rows[:limit]


def test_cursor_encoding_is_deterministic_signed_and_run_bound() -> None:
    first = encode_payroll_results_cursor(44, 2, 8)
    assert first == encode_payroll_results_cursor(44, 2, 8)
    assert decode_payroll_results_cursor(first, 44).employee_id == 2
    with pytest.raises(ValueError, match="Invalid payroll results cursor"):
        decode_payroll_results_cursor(first, 45)

    tampered = first[:-1] + ("A" if first[-1] != "A" else "B")
    with pytest.raises(ValueError, match="Invalid payroll results cursor"):
        decode_payroll_results_cursor(tampered, 44)


def test_service_pages_persisted_rows_without_gaps_and_preserves_decimals() -> None:
    uow = ReportUnitOfWork()
    service = PayrollResultsReportService(uow)

    first = service.get_page(44, 2, None)
    assert first is not None
    assert [row.employee_id for row in first.results] == [2, 4]
    assert first.results[0].gross_earnings == Decimal("1200.01")
    assert first.results[0].net_salary == Decimal("1180.01")
    assert first.pagination.has_more is True
    assert first.pagination.next_cursor

    second = service.get_page(44, 2, first.pagination.next_cursor)
    assert second is not None
    assert [row.employee_id for row in second.results] == [7, 9]
    assert second.pagination.has_more is True

    third = service.get_page(44, 2, second.pagination.next_cursor)
    assert third is not None
    assert [row.employee_id for row in third.results] == [12]
    assert third.pagination.has_more is False
    assert third.pagination.next_cursor is None
    assert [
        row.employee_id
        for row in [*first.results, *second.results, *third.results]
    ] == [2, 4, 7, 9, 12]
    assert uow.page_calls == [
        (44, None, None, 3),
        (44, 4, 9, 3),
        (44, 9, 11, 3),
    ]


def test_service_returns_empty_page_with_null_cursor() -> None:
    uow = ReportUnitOfWork()
    uow.records = []
    page = PayrollResultsReportService(uow).get_page(44, 50, None)
    assert page is not None
    assert page.results == []
    assert page.pagination.has_more is False
    assert page.pagination.next_cursor is None


def test_service_returns_empty_subsequent_page_after_last_result() -> None:
    uow = ReportUnitOfWork()
    cursor = encode_payroll_results_cursor(44, 12, 12)
    page = PayrollResultsReportService(uow).get_page(44, 2, cursor)
    assert page is not None
    assert page.results == []
    assert page.pagination.has_more is False
    assert page.pagination.next_cursor is None


@pytest.mark.parametrize("status", ["CREATED", "PROCESSING", "PROCESSED", "FAILED"])
def test_service_never_queries_results_for_non_finalized_run(status: str) -> None:
    uow = ReportUnitOfWork(status)
    with pytest.raises(BusinessRuleViolation):
        PayrollResultsReportService(uow).get_page(44, 10, None)
    assert uow.page_calls == []


def test_service_missing_run_returns_none_without_result_query() -> None:
    uow = ReportUnitOfWork()
    assert PayrollResultsReportService(uow).get_page(99, 10, None) is None
    assert uow.page_calls == []
