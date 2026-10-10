from datetime import date
from types import SimpleNamespace

import pytest

from app.application.reporting.employee_report_service import (
    EmployeeReportFilters,
    EmployeeReportService,
    InvalidEmployeeReportCursor,
    decode_employee_report_cursor,
    encode_employee_report_cursor,
)
from app.domain.employee.employee_report import EmployeeReportRecord


class EmployeeReportUow:
    def __init__(self) -> None:
        self.records = [
            EmployeeReportRecord(
                employee_id=employee_id,
                employee_code=f"EMP-{employee_id}",
                first_name="First",
                last_name=str(employee_id),
                department_id=2,
                department_name="Current Department",
                designation_id=3,
                designation_name="Current Designation",
                joining_date=date(2020, 1, 1),
                employment_end_date=None,
                employment_status="ACTIVE",
            )
            for employee_id in (2, 4, 8)
        ]
        self.calls: list[dict[str, object]] = []
        self.employees = SimpleNamespace(list_report_page=self.list_report_page)

    def list_report_page(self, **kwargs):
        self.calls.append(kwargs)
        rows = [
            item
            for item in self.records
            if (kwargs["employee_code"] is None or item.employee_code == kwargs["employee_code"])
            and (kwargs["department_id"] is None or item.department_id == kwargs["department_id"])
            and (kwargs["designation_id"] is None or item.designation_id == kwargs["designation_id"])
            and (kwargs["employment_status"] is None or item.employment_status == kwargs["employment_status"])
            and (kwargs["after_employee_id"] is None or item.employee_id > kwargs["after_employee_id"])
        ]
        return rows[: kwargs["limit"]]


def test_cursor_is_deterministic_and_bound_to_report_filters() -> None:
    filters = EmployeeReportFilters(employee_code="EMP-2", department_id=2)
    cursor = encode_employee_report_cursor(2, filters)
    assert cursor == encode_employee_report_cursor(2, filters)
    assert decode_employee_report_cursor(cursor, filters) == 2
    with pytest.raises(InvalidEmployeeReportCursor):
        decode_employee_report_cursor(
            cursor, EmployeeReportFilters(employee_code="EMP-4", department_id=2)
        )
    with pytest.raises(InvalidEmployeeReportCursor):
        decode_employee_report_cursor(cursor[:-1] + ("A" if cursor[-1] != "A" else "B"), filters)


def test_service_fetches_limit_plus_one_and_pages_by_employee_id() -> None:
    uow = EmployeeReportUow()
    service = EmployeeReportService(uow)
    filters = EmployeeReportFilters()

    first = service.get_page(2, filters, None)
    assert [row.employee_id for row in first.employees] == [2, 4]
    assert first.pagination.has_more is True
    assert first.pagination.next_cursor

    second = service.get_page(2, filters, first.pagination.next_cursor)
    assert [row.employee_id for row in second.employees] == [8]
    assert second.pagination.has_more is False
    assert second.pagination.next_cursor is None
    assert [call["limit"] for call in uow.calls] == [3, 3]
    assert uow.calls[1]["after_employee_id"] == 4


def test_service_forwards_all_filters_and_returns_empty_page() -> None:
    uow = EmployeeReportUow()
    filters = EmployeeReportFilters(
        employee_code="missing", department_id=9, designation_id=10,
        employment_status="TERMINATED",
    )
    page = EmployeeReportService(uow).get_page(50, filters, None)
    assert page.employees == []
    assert page.pagination.has_more is False
    assert page.pagination.next_cursor is None
    assert uow.calls == [{
        "employee_code": "missing", "department_id": 9,
        "designation_id": 10, "employment_status": "TERMINATED",
        "after_employee_id": None, "limit": 51,
    }]
