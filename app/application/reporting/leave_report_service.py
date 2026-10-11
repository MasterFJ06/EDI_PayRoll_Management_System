"""Application services and signed keyset cursors for Leave reports."""

import base64
import binascii
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import date, datetime

from app.application.common.unit_of_work import UnitOfWork
from app.application.reporting.schemas import (
    LeaveAllocationReportPage,
    LeaveAllocationReportRow,
    LeaveBalanceReportPage,
    LeaveBalanceReportRow,
    LeaveReportPagination,
)
from app.core.config import get_settings
from app.domain.leave.leave_report import (
    LeaveAllocationReportRecord,
    LeaveBalanceReportRecord,
)


_ALLOCATION_CURSOR_DOMAIN = b"epms:leave-allocations-report:v1:"
_BALANCE_CURSOR_DOMAIN = b"epms:leave-balances-report:v1:"
_ALLOCATION_FILTER_KEYS = (
    "date_from",
    "date_to",
    "employee_id",
    "department_id",
    "leave_type_id",
    "status",
)
_BALANCE_FILTER_KEYS = (
    "employee_id",
    "department_id",
    "leave_type_id",
    "balance_year",
)
_LEAVE_STATUSES = {"PENDING", "APPROVED", "REJECTED", "CANCELLED"}
_MAX_PAGE_SIZE = 100


class InvalidLeaveReportCursor(ValueError):
    """Raised for malformed, tampered, or mismatched Leave report cursors."""


class InvalidLeaveReportFilters(ValueError):
    """Raised when Leave report filters or page sizes are invalid."""


@dataclass(frozen=True)
class LeaveAllocationReportFilters:
    date_from: date | None = None
    date_to: date | None = None
    employee_id: int | None = None
    department_id: int | None = None
    leave_type_id: int | None = None
    status: str | None = None

    def __post_init__(self) -> None:
        if any(
            value is not None
            and (not isinstance(value, date) or isinstance(value, datetime))
            for value in (self.date_from, self.date_to)
        ):
            raise InvalidLeaveReportFilters("Report dates must be calendar dates.")
        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise InvalidLeaveReportFilters("date_from must be on or before date_to.")
        if any(
            value is not None
            and (isinstance(value, bool) or not isinstance(value, int) or value <= 0)
            for value in (self.employee_id, self.department_id, self.leave_type_id)
        ):
            raise InvalidLeaveReportFilters("Report IDs must be positive integers.")
        if self.status is not None and (
            not isinstance(self.status, str) or self.status not in _LEAVE_STATUSES
        ):
            raise InvalidLeaveReportFilters("Unsupported leave request status.")

    def as_payload(self) -> dict[str, str | int | None]:
        return {
            "date_from": self.date_from.isoformat() if self.date_from is not None else None,
            "date_to": self.date_to.isoformat() if self.date_to is not None else None,
            "employee_id": self.employee_id,
            "department_id": self.department_id,
            "leave_type_id": self.leave_type_id,
            "status": self.status,
        }


@dataclass(frozen=True)
class LeaveBalanceReportFilters:
    employee_id: int | None = None
    department_id: int | None = None
    leave_type_id: int | None = None
    balance_year: int | None = None

    def __post_init__(self) -> None:
        if any(
            value is not None
            and (isinstance(value, bool) or not isinstance(value, int) or value <= 0)
            for value in (self.employee_id, self.department_id, self.leave_type_id)
        ):
            raise InvalidLeaveReportFilters("Report IDs must be positive integers.")
        if self.balance_year is not None and (
            isinstance(self.balance_year, bool)
            or not isinstance(self.balance_year, int)
            or not 0 <= self.balance_year <= 65535
        ):
            raise InvalidLeaveReportFilters("balance_year must be between 0 and 65535.")

    def as_payload(self) -> dict[str, int | None]:
        return {
            "employee_id": self.employee_id,
            "department_id": self.department_id,
            "leave_type_id": self.leave_type_id,
            "balance_year": self.balance_year,
        }


@dataclass(frozen=True)
class LeaveAllocationReportPosition:
    leave_date: date
    leave_request_day_id: int


@dataclass(frozen=True)
class LeaveBalanceReportPosition:
    employee_id: int
    leave_type_id: int
    balance_year: int


def encode_leave_allocation_report_cursor(
    position: LeaveAllocationReportPosition,
    filters: LeaveAllocationReportFilters,
) -> str:
    payload = json.dumps(
        {
            "v": 1,
            "report": "leave_allocations",
            "leave_date": position.leave_date.isoformat(),
            "leave_request_day_id": position.leave_request_day_id,
            "filters": filters.as_payload(),
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return _encode_signed_cursor(payload, _ALLOCATION_CURSOR_DOMAIN)


def decode_leave_allocation_report_cursor(
    encoded: str,
    filters: LeaveAllocationReportFilters,
) -> LeaveAllocationReportPosition:
    data = _decode_signed_cursor(encoded, _ALLOCATION_CURSOR_DOMAIN)
    try:
        if (
            not isinstance(data, dict)
            or set(data) != {"v", "report", "leave_date", "leave_request_day_id", "filters"}
            or not _valid_version_and_report(data, "leave_allocations")
            or not isinstance(data["leave_date"], str)
            or not _is_positive_int(data["leave_request_day_id"])
            or not _valid_allocation_filter_payload(data["filters"])
            or data["filters"] != filters.as_payload()
        ):
            raise ValueError
        cursor_date = date.fromisoformat(data["leave_date"])
        if cursor_date.isoformat() != data["leave_date"]:
            raise ValueError
        return LeaveAllocationReportPosition(cursor_date, data["leave_request_day_id"])
    except (ValueError, TypeError, KeyError) as exc:
        raise InvalidLeaveReportCursor("Invalid Leave allocation report cursor.") from exc


def encode_leave_balance_report_cursor(
    position: LeaveBalanceReportPosition,
    filters: LeaveBalanceReportFilters,
) -> str:
    payload = json.dumps(
        {
            "v": 1,
            "report": "leave_balances",
            "employee_id": position.employee_id,
            "leave_type_id": position.leave_type_id,
            "balance_year": position.balance_year,
            "filters": filters.as_payload(),
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return _encode_signed_cursor(payload, _BALANCE_CURSOR_DOMAIN)


def decode_leave_balance_report_cursor(
    encoded: str,
    filters: LeaveBalanceReportFilters,
) -> LeaveBalanceReportPosition:
    data = _decode_signed_cursor(encoded, _BALANCE_CURSOR_DOMAIN)
    try:
        if (
            not isinstance(data, dict)
            or set(data)
            != {"v", "report", "employee_id", "leave_type_id", "balance_year", "filters"}
            or not _valid_version_and_report(data, "leave_balances")
            or not _is_positive_int(data["employee_id"])
            or not _is_positive_int(data["leave_type_id"])
            or not _is_balance_year(data["balance_year"])
            or not _valid_balance_filter_payload(data["filters"])
            or data["filters"] != filters.as_payload()
        ):
            raise ValueError
        return LeaveBalanceReportPosition(
            data["employee_id"], data["leave_type_id"], data["balance_year"]
        )
    except (ValueError, TypeError, KeyError) as exc:
        raise InvalidLeaveReportCursor("Invalid Leave balance report cursor.") from exc


class LeaveReportService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def get_allocation_page(
        self,
        limit: int,
        filters: LeaveAllocationReportFilters,
        cursor: str | None = None,
    ) -> LeaveAllocationReportPage:
        _validate_limit(limit)
        position = (
            decode_leave_allocation_report_cursor(cursor, filters)
            if cursor is not None
            else None
        )
        records = self.uow.leave_reports.list_allocation_report_page(
            date_from=filters.date_from,
            date_to=filters.date_to,
            employee_id=filters.employee_id,
            department_id=filters.department_id,
            leave_type_id=filters.leave_type_id,
            status=filters.status,
            after_leave_date=position.leave_date if position else None,
            after_leave_request_day_id=(position.leave_request_day_id if position else None),
            limit=limit + 1,
        )
        has_more = len(records) > limit
        page_records = records[:limit]
        next_cursor = (
            encode_leave_allocation_report_cursor(
                LeaveAllocationReportPosition(
                    page_records[-1].leave_date,
                    page_records[-1].leave_request_day_id,
                ),
                filters,
            )
            if has_more and page_records
            else None
        )
        return LeaveAllocationReportPage(
            allocations=[_allocation_response(record) for record in page_records],
            pagination=LeaveReportPagination(
                limit=limit, has_more=has_more, next_cursor=next_cursor
            ),
        )

    def get_balance_page(
        self,
        limit: int,
        filters: LeaveBalanceReportFilters,
        cursor: str | None = None,
    ) -> LeaveBalanceReportPage:
        _validate_limit(limit)
        position = (
            decode_leave_balance_report_cursor(cursor, filters)
            if cursor is not None
            else None
        )
        records = self.uow.leave_reports.list_balance_report_page(
            employee_id=filters.employee_id,
            department_id=filters.department_id,
            leave_type_id=filters.leave_type_id,
            balance_year=filters.balance_year,
            after_employee_id=position.employee_id if position else None,
            after_leave_type_id=position.leave_type_id if position else None,
            after_balance_year=position.balance_year if position else None,
            limit=limit + 1,
        )
        has_more = len(records) > limit
        page_records = records[:limit]
        next_cursor = (
            encode_leave_balance_report_cursor(
                LeaveBalanceReportPosition(
                    page_records[-1].employee_id,
                    page_records[-1].leave_type_id,
                    page_records[-1].balance_year,
                ),
                filters,
            )
            if has_more and page_records
            else None
        )
        return LeaveBalanceReportPage(
            balances=[_balance_response(record) for record in page_records],
            pagination=LeaveReportPagination(
                limit=limit, has_more=has_more, next_cursor=next_cursor
            ),
        )


def _allocation_response(record: LeaveAllocationReportRecord) -> LeaveAllocationReportRow:
    return LeaveAllocationReportRow(
        leave_request_id=record.leave_request_id,
        leave_request_day_id=record.leave_request_day_id,
        employee_id=record.employee_id,
        employee_code=record.employee_code,
        first_name=record.first_name,
        last_name=record.last_name,
        department_id=record.department_id,
        department_name=record.department_name,
        designation_id=record.designation_id,
        designation_name=record.designation_name,
        leave_type_id=record.leave_type_id,
        leave_type_name=record.leave_type_name,
        start_date=record.start_date,
        end_date=record.end_date,
        requested_days=record.requested_days,
        status=record.status,
        leave_date=record.leave_date,
        day_fraction=record.day_fraction,
    )


def _balance_response(record: LeaveBalanceReportRecord) -> LeaveBalanceReportRow:
    return LeaveBalanceReportRow(
        employee_id=record.employee_id,
        employee_code=record.employee_code,
        first_name=record.first_name,
        last_name=record.last_name,
        department_id=record.department_id,
        department_name=record.department_name,
        designation_id=record.designation_id,
        designation_name=record.designation_name,
        leave_type_id=record.leave_type_id,
        leave_type_name=record.leave_type_name,
        balance_year=record.balance_year,
        allocated_days=record.allocated_days,
        used_days=record.used_days,
    )


def _validate_limit(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= _MAX_PAGE_SIZE:
        raise InvalidLeaveReportFilters("limit must be between 1 and 100.")


def _cursor_key() -> bytes:
    return get_settings().jwt_secret_key.encode("utf-8")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    valid = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    if not value or any(character not in valid for character in value):
        raise ValueError
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _encode_signed_cursor(payload: bytes, domain: bytes) -> str:
    signature = hmac.new(_cursor_key(), domain + payload, hashlib.sha256).digest()
    return f"{_b64encode(payload)}.{_b64encode(signature)}"


def _decode_signed_cursor(encoded: str, domain: bytes) -> dict[str, object]:
    try:
        payload_part, signature_part = encoded.split(".", 1)
        payload = _b64decode(payload_part)
        signature = _b64decode(signature_part)
        expected = hmac.new(_cursor_key(), domain + payload, hashlib.sha256).digest()
        if (
            not hmac.compare_digest(signature, expected)
            or _b64encode(signature) != signature_part
            or _b64encode(payload) != payload_part
        ):
            raise ValueError
        data = json.loads(payload.decode("ascii"))
        if not isinstance(data, dict):
            raise ValueError
        return data
    except (ValueError, TypeError, AttributeError, UnicodeDecodeError, json.JSONDecodeError, binascii.Error) as exc:
        raise InvalidLeaveReportCursor("Invalid Leave report cursor.") from exc


def _valid_version_and_report(data: dict[str, object], report: str) -> bool:
    return (
        not isinstance(data["v"], bool)
        and isinstance(data["v"], int)
        and data["v"] == 1
        and data["report"] == report
    )


def _is_positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _is_balance_year(value: object) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and 0 <= value <= 65535
    )


def _valid_allocation_filter_payload(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != set(_ALLOCATION_FILTER_KEYS):
        return False
    return (
        _valid_payload_date(value["date_from"])
        and _valid_payload_date(value["date_to"])
        and _payload_positive_int(value["employee_id"])
        and _payload_positive_int(value["department_id"])
        and _payload_positive_int(value["leave_type_id"])
        and (value["status"] is None or value["status"] in _LEAVE_STATUSES)
        and not (
            value["date_from"] is not None
            and value["date_to"] is not None
            and value["date_from"] > value["date_to"]
        )
    )


def _valid_balance_filter_payload(value: object) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == set(_BALANCE_FILTER_KEYS)
        and _payload_positive_int(value["employee_id"])
        and _payload_positive_int(value["department_id"])
        and _payload_positive_int(value["leave_type_id"])
        and (value["balance_year"] is None or _is_balance_year(value["balance_year"]))
    )


def _payload_positive_int(value: object) -> bool:
    return value is None or _is_positive_int(value)


def _valid_payload_date(value: object) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False
