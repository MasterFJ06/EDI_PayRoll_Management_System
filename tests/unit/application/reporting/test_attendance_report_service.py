from dataclasses import replace
from datetime import date
from types import SimpleNamespace

import pytest

from app.application.reporting.attendance_report_service import (
    AttendanceReportFilters,
    AttendanceReportPosition,
    AttendanceReportService,
    InvalidAttendanceReportCursor,
    InvalidAttendanceReportFilters,
    decode_attendance_report_cursor,
    encode_attendance_report_cursor,
)
from app.application.reporting.employee_report_service import (
    EmployeeReportFilters,
    encode_employee_report_cursor,
)
from app.domain.attendance.attendance_report import AttendanceReportRecord


def _record(attendance_id: int, day: date) -> AttendanceReportRecord:
    return AttendanceReportRecord(
        attendance_id=attendance_id,
        employee_id=attendance_id,
        employee_code=f"EMP-{attendance_id}",
        first_name="Test",
        last_name=str(attendance_id),
        department_id=4,
        department_name="Finance",
        designation_id=8,
        designation_name="Analyst",
        attendance_date=day,
        attendance_status="PRESENT",
        check_in_time=None,
        check_out_time=None,
    )


class _AttendanceReportUow:
    def __init__(self, records: list[AttendanceReportRecord]) -> None:
        self.records = records
        self.calls: list[dict[str, object]] = []
        self.attendance = SimpleNamespace(list_report_page=self.list_report_page)

    def list_report_page(self, **kwargs):
        self.calls.append(kwargs)
        rows = [
            row
            for row in self.records
            if (kwargs["date_from"] is None or row.attendance_date >= kwargs["date_from"])
            and (kwargs["date_to"] is None or row.attendance_date <= kwargs["date_to"])
            and (kwargs["employee_id"] is None or row.employee_id == kwargs["employee_id"])
            and (kwargs["department_id"] is None or row.department_id == kwargs["department_id"])
            and (
                kwargs["attendance_status"] is None
                or row.attendance_status == kwargs["attendance_status"]
            )
            and (
                kwargs["after_attendance_date"] is None
                or (row.attendance_date, row.attendance_id)
                > (kwargs["after_attendance_date"], kwargs["after_attendance_id"])
            )
        ]
        return rows[: kwargs["limit"]]


def test_cursor_is_deterministic_filter_bound_and_report_specific() -> None:
    filters = AttendanceReportFilters(
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
        department_id=4,
        attendance_status="PRESENT",
    )
    position = AttendanceReportPosition(date(2026, 1, 10), 23)
    cursor = encode_attendance_report_cursor(position, filters)

    assert cursor == encode_attendance_report_cursor(position, filters)
    assert decode_attendance_report_cursor(cursor, filters) == position
    with pytest.raises(InvalidAttendanceReportCursor):
        decode_attendance_report_cursor(
            cursor,
            AttendanceReportFilters(
                date_from=date(2026, 1, 1),
                date_to=date(2026, 1, 31),
                department_id=4,
                attendance_status="ABSENT",
            ),
        )
    with pytest.raises(InvalidAttendanceReportCursor):
        decode_attendance_report_cursor(cursor[:-1] + ("A" if cursor[-1] != "A" else "B"), filters)
    with pytest.raises(InvalidAttendanceReportCursor):
        decode_attendance_report_cursor("not-a-cursor", filters)
    with pytest.raises(InvalidAttendanceReportCursor):
        decode_attendance_report_cursor(
            encode_employee_report_cursor(2, EmployeeReportFilters()), filters
        )


def test_service_paginates_same_date_rows_without_duplicates_and_preserves_nulls() -> None:
    day = date(2026, 2, 3)
    uow = _AttendanceReportUow([_record(10, day), _record(12, day), _record(20, date(2026, 2, 4))])
    service = AttendanceReportService(uow)
    filters = AttendanceReportFilters(date_from=day, date_to=date(2026, 2, 4))

    first = service.get_page(1, filters, None)
    second = service.get_page(1, filters, first.pagination.next_cursor)
    third = service.get_page(1, filters, second.pagination.next_cursor)

    assert [row.attendance_id for row in first.attendance_records] == [10]
    assert [row.attendance_id for row in second.attendance_records] == [12]
    assert [row.attendance_id for row in third.attendance_records] == [20]
    assert first.pagination.has_more and second.pagination.has_more
    assert third.pagination.has_more is False
    assert third.pagination.next_cursor is None
    assert first.attendance_records[0].check_in_time is None
    assert first.attendance_records[0].check_out_time is None
    assert [call["limit"] for call in uow.calls] == [2, 2, 2]
    assert uow.calls[1]["after_attendance_date"] == day
    assert uow.calls[1]["after_attendance_id"] == 10


def test_service_forwards_all_filters_and_handles_empty_page() -> None:
    uow = _AttendanceReportUow([])
    filters = AttendanceReportFilters(
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
        employee_id=5,
        department_id=4,
        attendance_status="HOLIDAY",
    )
    page = AttendanceReportService(uow).get_page(50, filters, None)

    assert page.attendance_records == []
    assert page.pagination.has_more is False
    assert page.pagination.next_cursor is None
    assert uow.calls == [{
        "date_from": date(2026, 1, 1),
        "date_to": date(2026, 1, 31),
        "employee_id": 5,
        "department_id": 4,
        "attendance_status": "HOLIDAY",
        "after_attendance_date": None,
        "after_attendance_id": None,
        "limit": 51,
    }]


def test_response_preserves_nullable_department_and_designation_labels() -> None:
    record = _record(10, date(2026, 2, 3))
    record = replace(
        record,
        department_name=None,
        designation_name=None,
    )
    page = AttendanceReportService(_AttendanceReportUow([record])).get_page(
        50, AttendanceReportFilters(), None
    )

    row = page.attendance_records[0]
    assert row.department_name is None
    assert row.designation_name is None
    assert row.model_dump()["department_name"] is None
    assert row.model_dump()["designation_name"] is None


def test_filter_validation_rejects_reversed_dates_and_nonpositive_ids() -> None:
    with pytest.raises(InvalidAttendanceReportFilters):
        AttendanceReportFilters(date_from=date(2026, 2, 1), date_to=date(2026, 1, 31))
    with pytest.raises(InvalidAttendanceReportFilters):
        AttendanceReportFilters(employee_id=0)
