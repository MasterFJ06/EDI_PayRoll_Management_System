import base64
import hashlib
import hmac
import json
from dataclasses import replace
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.config import get_settings
from app.application.reporting.leave_report_service import (
    InvalidLeaveReportCursor,
    InvalidLeaveReportFilters,
    LeaveAllocationReportFilters,
    LeaveAllocationReportPosition,
    LeaveBalanceReportFilters,
    LeaveBalanceReportPosition,
    LeaveReportService,
    decode_leave_allocation_report_cursor,
    decode_leave_balance_report_cursor,
    encode_leave_allocation_report_cursor,
    encode_leave_balance_report_cursor,
)
from app.domain.leave.leave_report import (
    LeaveAllocationReportRecord,
    LeaveBalanceReportRecord,
)


def _allocation(day_id: int, day: date) -> LeaveAllocationReportRecord:
    return LeaveAllocationReportRecord(
        leave_request_id=71,
        leave_request_day_id=day_id,
        employee_id=12,
        employee_code="EMP-12",
        first_name="Asha",
        last_name="Patel",
        department_id=3,
        department_name="Finance",
        designation_id=4,
        designation_name="Analyst",
        leave_type_id=5,
        leave_type_name="Annual",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 3),
        requested_days=Decimal("2.00"),
        status="APPROVED",
        leave_date=day,
        day_fraction=Decimal("0.50"),
    )


def _balance(employee_id: int, leave_type_id: int, year: int) -> LeaveBalanceReportRecord:
    return LeaveBalanceReportRecord(
        employee_id=employee_id,
        employee_code=f"EMP-{employee_id}",
        first_name="Asha",
        last_name="Patel",
        department_id=3,
        department_name="Finance",
        designation_id=4,
        designation_name="Analyst",
        leave_type_id=leave_type_id,
        leave_type_name="Annual",
        balance_year=year,
        allocated_days=Decimal("10.00"),
        used_days=Decimal("2.50"),
    )


class _LeaveReportUow:
    def __init__(self, allocations=(), balances=()) -> None:
        self.allocations = list(allocations)
        self.balances = list(balances)
        self.allocation_calls: list[dict[str, object]] = []
        self.balance_calls: list[dict[str, object]] = []
        self.leave_reports = SimpleNamespace(
            list_allocation_report_page=self.list_allocation_report_page,
            list_balance_report_page=self.list_balance_report_page,
        )

    def list_allocation_report_page(self, **kwargs):
        self.allocation_calls.append(kwargs)
        rows = [
            row for row in self.allocations
            if (kwargs["date_from"] is None or row.leave_date >= kwargs["date_from"])
            and (kwargs["date_to"] is None or row.leave_date <= kwargs["date_to"])
            and (kwargs["employee_id"] is None or row.employee_id == kwargs["employee_id"])
            and (kwargs["department_id"] is None or row.department_id == kwargs["department_id"])
            and (kwargs["leave_type_id"] is None or row.leave_type_id == kwargs["leave_type_id"])
            and (kwargs["status"] is None or row.status == kwargs["status"])
            and (
                kwargs["after_leave_date"] is None
                or (row.leave_date, row.leave_request_day_id)
                > (kwargs["after_leave_date"], kwargs["after_leave_request_day_id"])
            )
        ]
        rows.sort(key=lambda row: (row.leave_date, row.leave_request_day_id))
        return rows[:kwargs["limit"]]

    def list_balance_report_page(self, **kwargs):
        self.balance_calls.append(kwargs)
        rows = [
            row for row in self.balances
            if (kwargs["employee_id"] is None or row.employee_id == kwargs["employee_id"])
            and (kwargs["department_id"] is None or row.department_id == kwargs["department_id"])
            and (kwargs["leave_type_id"] is None or row.leave_type_id == kwargs["leave_type_id"])
            and (kwargs["balance_year"] is None or row.balance_year == kwargs["balance_year"])
            and (
                kwargs["after_employee_id"] is None
                or (
                    row.employee_id,
                    row.leave_type_id,
                    row.balance_year,
                )
                > (
                    kwargs["after_employee_id"],
                    kwargs["after_leave_type_id"],
                    kwargs["after_balance_year"],
                )
            )
        ]
        rows.sort(key=lambda row: (row.employee_id, row.leave_type_id, row.balance_year))
        return rows[:kwargs["limit"]]


def test_allocation_cursor_is_deterministic_signed_and_filter_bound() -> None:
    filters = LeaveAllocationReportFilters(
        date_from=date(2026, 1, 1), date_to=date(2026, 1, 31), status="APPROVED"
    )
    position = LeaveAllocationReportPosition(date(2026, 1, 8), 23)
    cursor = encode_leave_allocation_report_cursor(position, filters)

    assert cursor == encode_leave_allocation_report_cursor(position, filters)
    assert decode_leave_allocation_report_cursor(cursor, filters) == position
    with pytest.raises(InvalidLeaveReportCursor):
        decode_leave_allocation_report_cursor(
            cursor, replace(filters, status="PENDING")
        )
    with pytest.raises(InvalidLeaveReportCursor):
        decode_leave_balance_report_cursor(cursor, LeaveBalanceReportFilters())
    with pytest.raises(InvalidLeaveReportCursor):
        decode_leave_allocation_report_cursor(cursor[:-1] + ("A" if cursor[-1] != "A" else "B"), filters)
    for malformed in ("", "not-a-cursor", "e30.", "!.!"):
        with pytest.raises(InvalidLeaveReportCursor):
            decode_leave_allocation_report_cursor(malformed, filters)


def test_balance_cursor_is_deterministic_and_binds_complete_key_and_filters() -> None:
    filters = LeaveBalanceReportFilters(department_id=3, balance_year=0)
    position = LeaveBalanceReportPosition(12, 5, 0)
    cursor = encode_leave_balance_report_cursor(position, filters)

    assert cursor == encode_leave_balance_report_cursor(position, filters)
    assert decode_leave_balance_report_cursor(cursor, filters) == position
    with pytest.raises(InvalidLeaveReportCursor):
        decode_leave_balance_report_cursor(cursor, replace(filters, balance_year=1))
    with pytest.raises(InvalidLeaveReportCursor):
        decode_leave_allocation_report_cursor(cursor, LeaveAllocationReportFilters())


def test_allocation_service_paginates_shared_dates_and_preserves_persisted_values() -> None:
    day = date(2026, 1, 8)
    uow = _LeaveReportUow(
        [_allocation(10, day), _allocation(12, day), _allocation(15, date(2026, 1, 9))]
    )
    filters = LeaveAllocationReportFilters(
        date_from=day, date_to=date(2026, 1, 9), status=None
    )
    service = LeaveReportService(uow)

    first = service.get_allocation_page(1, filters)
    second = service.get_allocation_page(1, filters, first.pagination.next_cursor)
    final = service.get_allocation_page(1, filters, second.pagination.next_cursor)

    assert [row.leave_request_day_id for row in first.allocations] == [10]
    assert [row.leave_request_day_id for row in second.allocations] == [12]
    assert [row.leave_request_day_id for row in final.allocations] == [15]
    assert first.pagination.has_more and second.pagination.has_more
    assert final.pagination.has_more is False and final.pagination.next_cursor is None
    assert first.allocations[0].requested_days == Decimal("2.00")
    assert first.allocations[0].day_fraction == Decimal("0.50")
    assert [call["limit"] for call in uow.allocation_calls] == [2, 2, 2]
    assert uow.allocation_calls[0]["date_from"] == day
    assert uow.allocation_calls[0]["date_to"] == date(2026, 1, 9)
    assert uow.allocation_calls[0]["status"] is None
    assert uow.allocation_calls[1]["after_leave_date"] == day
    assert uow.allocation_calls[1]["after_leave_request_day_id"] == 10


def test_balance_service_pages_by_complete_key_and_returns_values_unchanged() -> None:
    uow = _LeaveReportUow(
        balances=[_balance(12, 4, 2025), _balance(12, 4, 2026), _balance(12, 5, 0)]
    )
    service = LeaveReportService(uow)

    first = service.get_balance_page(1, LeaveBalanceReportFilters())
    second = service.get_balance_page(1, LeaveBalanceReportFilters(), first.pagination.next_cursor)
    final = service.get_balance_page(1, LeaveBalanceReportFilters(), second.pagination.next_cursor)

    assert [(r.employee_id, r.leave_type_id, r.balance_year) for r in first.balances] == [(12, 4, 2025)]
    assert [(r.employee_id, r.leave_type_id, r.balance_year) for r in second.balances] == [(12, 4, 2026)]
    assert [(r.employee_id, r.leave_type_id, r.balance_year) for r in final.balances] == [(12, 5, 0)]
    assert [call["limit"] for call in uow.balance_calls] == [2, 2, 2]
    assert uow.balance_calls[1]["after_employee_id"] == 12
    assert uow.balance_calls[1]["after_leave_type_id"] == 4
    assert uow.balance_calls[1]["after_balance_year"] == 2025
    assert first.balances[0].allocated_days == Decimal("10.00")
    assert first.balances[0].used_days == Decimal("2.50")
    assert not hasattr(first.balances[0], "remaining_days")


def test_empty_pages_and_page_limit_validation() -> None:
    service = LeaveReportService(_LeaveReportUow())
    page = service.get_allocation_page(50, LeaveAllocationReportFilters())
    assert page.allocations == []
    assert page.pagination.has_more is False
    assert page.pagination.next_cursor is None
    for invalid in (0, 101, True, 1.5):
        with pytest.raises(InvalidLeaveReportFilters):
            service.get_balance_page(invalid, LeaveBalanceReportFilters())


@pytest.mark.parametrize(
    "kwargs",
    [
        {"date_from": date(2026, 2, 1), "date_to": date(2026, 1, 1)},
        {"employee_id": True},
        {"department_id": 0},
        {"leave_type_id": 1.5},
        {"status": "UNKNOWN"},
    ],
)
def test_allocation_filter_validation(kwargs) -> None:
    with pytest.raises(InvalidLeaveReportFilters):
        LeaveAllocationReportFilters(**kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"employee_id": False},
        {"leave_type_id": 0},
        {"balance_year": True},
        {"balance_year": -1},
        {"balance_year": 65536},
    ],
)
def test_balance_filter_validation(kwargs) -> None:
    with pytest.raises(InvalidLeaveReportFilters):
        LeaveBalanceReportFilters(**kwargs)


def test_signed_cursor_with_boolean_numeric_key_is_rejected() -> None:
    filters = LeaveAllocationReportFilters()
    payload = json.dumps(
        {
            "v": 1,
            "report": "leave_allocations",
            "leave_date": "2026-01-08",
            "leave_request_day_id": True,
            "filters": filters.as_payload(),
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    payload_token = base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")
    domain = b"epms:leave-allocations-report:v1:"
    secret = get_settings().jwt_secret_key.encode("utf-8")
    signature = hmac.new(secret, domain + payload, hashlib.sha256).digest()
    signature_token = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")

    with pytest.raises(InvalidLeaveReportCursor):
        decode_leave_allocation_report_cursor(f"{payload_token}.{signature_token}", filters)
