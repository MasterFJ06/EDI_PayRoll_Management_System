import base64
import binascii
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import date

from app.application.common.unit_of_work import UnitOfWork
from app.application.reporting.schemas import (
    AttendanceReportPage,
    AttendanceReportPagination,
    AttendanceReportRow,
)
from app.core.config import get_settings
from app.domain.attendance.attendance_report import AttendanceReportRecord


_CURSOR_DOMAIN = b"epms:attendance-report:v1:"
_FILTER_KEYS = ("date_from", "date_to", "employee_id", "department_id", "attendance_status")
_ATTENDANCE_STATUSES = {"PRESENT", "ABSENT", "HALF_DAY", "ON_LEAVE", "HOLIDAY"}


class InvalidAttendanceReportCursor(ValueError):
    """Raised when an attendance report cursor is malformed or mismatched."""


class InvalidAttendanceReportFilters(ValueError):
    """Raised when a report filter combination is invalid."""


@dataclass(frozen=True)
class AttendanceReportFilters:
    date_from: date | None = None
    date_to: date | None = None
    employee_id: int | None = None
    department_id: int | None = None
    attendance_status: str | None = None

    def __post_init__(self) -> None:
        if self.date_from is not None and self.date_to is not None and self.date_from > self.date_to:
            raise InvalidAttendanceReportFilters("date_from must be on or before date_to.")
        if any(
            value is not None and (isinstance(value, bool) or value <= 0)
            for value in (self.employee_id, self.department_id)
        ):
            raise InvalidAttendanceReportFilters("Employee and department IDs must be positive.")
        if self.attendance_status is not None and self.attendance_status not in _ATTENDANCE_STATUSES:
            raise InvalidAttendanceReportFilters("Unsupported attendance status.")

    def as_payload(self) -> dict[str, str | int | None]:
        return {
            "date_from": self.date_from.isoformat() if self.date_from else None,
            "date_to": self.date_to.isoformat() if self.date_to else None,
            "employee_id": self.employee_id,
            "department_id": self.department_id,
            "attendance_status": self.attendance_status,
        }


@dataclass(frozen=True)
class AttendanceReportPosition:
    attendance_date: date
    attendance_id: int


def encode_attendance_report_cursor(
    position: AttendanceReportPosition,
    filters: AttendanceReportFilters,
) -> str:
    payload = json.dumps(
        {
            "v": 1,
            "report": "attendance",
            "attendance_date": position.attendance_date.isoformat(),
            "attendance_id": position.attendance_id,
            "filters": filters.as_payload(),
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    signature = hmac.new(_cursor_key(), _CURSOR_DOMAIN + payload, hashlib.sha256).digest()
    return f"{_b64encode(payload)}.{_b64encode(signature)}"


def decode_attendance_report_cursor(
    encoded: str,
    filters: AttendanceReportFilters,
) -> AttendanceReportPosition:
    try:
        payload_part, signature_part = encoded.split(".", 1)
        payload = _b64decode(payload_part)
        signature = _b64decode(signature_part)
        expected_signature = hmac.new(
            _cursor_key(), _CURSOR_DOMAIN + payload, hashlib.sha256
        ).digest()
        if (
            not hmac.compare_digest(signature, expected_signature)
            or _b64encode(signature) != signature_part
            or _b64encode(payload) != payload_part
        ):
            raise ValueError("Invalid cursor signature or encoding.")

        data = json.loads(payload.decode("ascii"))
        if not isinstance(data, dict) or set(data) != {
            "v", "report", "attendance_date", "attendance_id", "filters"
        }:
            raise ValueError("Invalid cursor fields.")
        if (
            isinstance(data["v"], bool)
            or not isinstance(data["v"], int)
            or data["v"] != 1
            or data["report"] != "attendance"
            or not isinstance(data["attendance_date"], str)
            or isinstance(data["attendance_id"], bool)
            or not isinstance(data["attendance_id"], int)
            or data["attendance_id"] <= 0
            or not isinstance(data["filters"], dict)
            or set(data["filters"]) != set(_FILTER_KEYS)
            or not _cursor_filters_are_well_typed(data["filters"])
            or data["filters"] != filters.as_payload()
        ):
            raise ValueError("Invalid cursor values.")
        attendance_date = date.fromisoformat(data["attendance_date"])
        if attendance_date.isoformat() != data["attendance_date"]:
            raise ValueError("Cursor date is not canonical.")
        return AttendanceReportPosition(attendance_date, data["attendance_id"])
    except (
        ValueError,
        TypeError,
        KeyError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        binascii.Error,
    ) as exc:
        raise InvalidAttendanceReportCursor("Invalid attendance report cursor.") from exc


class AttendanceReportService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def get_page(
        self,
        limit: int,
        filters: AttendanceReportFilters,
        cursor: str | None,
    ) -> AttendanceReportPage:
        position = decode_attendance_report_cursor(cursor, filters) if cursor else None
        records = self.uow.attendance.list_report_page(
            date_from=filters.date_from,
            date_to=filters.date_to,
            employee_id=filters.employee_id,
            department_id=filters.department_id,
            attendance_status=filters.attendance_status,
            after_attendance_date=position.attendance_date if position else None,
            after_attendance_id=position.attendance_id if position else None,
            limit=limit + 1,
        )
        has_more = len(records) > limit
        page_records = records[:limit]
        next_cursor = (
            encode_attendance_report_cursor(
                AttendanceReportPosition(
                    page_records[-1].attendance_date,
                    page_records[-1].attendance_id,
                ),
                filters,
            )
            if has_more and page_records
            else None
        )
        return AttendanceReportPage(
            attendance_records=[_to_response(record) for record in page_records],
            pagination=AttendanceReportPagination(
                limit=limit,
                has_more=has_more,
                next_cursor=next_cursor,
            ),
        )


def _to_response(record: AttendanceReportRecord) -> AttendanceReportRow:
    return AttendanceReportRow(
        attendance_id=record.attendance_id,
        employee_id=record.employee_id,
        employee_code=record.employee_code,
        first_name=record.first_name,
        last_name=record.last_name,
        department_id=record.department_id,
        department_name=record.department_name,
        designation_id=record.designation_id,
        designation_name=record.designation_name,
        attendance_date=record.attendance_date,
        attendance_status=record.attendance_status,
        check_in_time=record.check_in_time,
        check_out_time=record.check_out_time,
    )


def _cursor_key() -> bytes:
    return get_settings().jwt_secret_key.encode("utf-8")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    valid = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    if not value or any(character not in valid for character in value):
        raise ValueError("Invalid base64url value.")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _cursor_filters_are_well_typed(value: dict[str, object]) -> bool:
    return (
        all(value[key] is None or isinstance(value[key], str) for key in ("date_from", "date_to"))
        and all(
            value[key] is None
            or (
                isinstance(value[key], int)
                and not isinstance(value[key], bool)
                and value[key] > 0
            )
            for key in ("employee_id", "department_id")
        )
        and (
            value["attendance_status"] is None
            or value["attendance_status"] in _ATTENDANCE_STATUSES
        )
        and _valid_payload_date(value["date_from"])
        and _valid_payload_date(value["date_to"])
    )


def _valid_payload_date(value: object) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False
