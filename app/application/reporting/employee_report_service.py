import base64
import binascii
import hashlib
import hmac
import json
from dataclasses import dataclass

from app.application.common.unit_of_work import UnitOfWork
from app.application.reporting.schemas import (
    EmployeeReportPage,
    EmployeeReportPagination,
    EmployeeReportRow,
)
from app.core.config import get_settings
from app.domain.employee.employee_report import EmployeeReportRecord


_CURSOR_DOMAIN = b"epms:employee-report:v1:"
_FILTER_KEYS = (
    "employee_code",
    "department_id",
    "designation_id",
    "employment_status",
)


class InvalidEmployeeReportCursor(ValueError):
    """Raised when an employee report cursor is invalid or filter-mismatched."""


@dataclass(frozen=True)
class EmployeeReportFilters:
    employee_code: str | None = None
    department_id: int | None = None
    designation_id: int | None = None
    employment_status: str | None = None

    def as_payload(self) -> dict[str, str | int | None]:
        return {
            "employee_code": self.employee_code,
            "department_id": self.department_id,
            "designation_id": self.designation_id,
            "employment_status": self.employment_status,
        }


def encode_employee_report_cursor(
    employee_id: int, filters: EmployeeReportFilters
) -> str:
    payload = json.dumps(
        {
            "v": 1,
            "report": "employees",
            "employee_id": employee_id,
            "filters": filters.as_payload(),
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    signature = hmac.new(
        _cursor_key(), _CURSOR_DOMAIN + payload, hashlib.sha256
    ).digest()
    return f"{_b64encode(payload)}.{_b64encode(signature)}"


def decode_employee_report_cursor(
    encoded: str, filters: EmployeeReportFilters
) -> int:
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
            "v", "report", "employee_id", "filters"
        }:
            raise ValueError("Invalid cursor fields.")
        if (
            isinstance(data["v"], bool)
            or not isinstance(data["v"], int)
            or data["v"] != 1
            or data["report"] != "employees"
            or isinstance(data["employee_id"], bool)
            or not isinstance(data["employee_id"], int)
            or data["employee_id"] <= 0
            or not isinstance(data["filters"], dict)
            or set(data["filters"]) != set(_FILTER_KEYS)
            or not _cursor_filters_are_well_typed(data["filters"])
            or data["filters"] != filters.as_payload()
        ):
            raise ValueError("Invalid cursor values.")
        return data["employee_id"]
    except (
        ValueError,
        TypeError,
        KeyError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        binascii.Error,
    ) as exc:
        raise InvalidEmployeeReportCursor("Invalid employee report cursor.") from exc


class EmployeeReportService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def get_page(
        self,
        limit: int,
        filters: EmployeeReportFilters,
        cursor: str | None,
    ) -> EmployeeReportPage:
        after_employee_id = (
            decode_employee_report_cursor(cursor, filters)
            if cursor is not None
            else None
        )
        records = self.uow.employees.list_report_page(
            employee_code=filters.employee_code,
            department_id=filters.department_id,
            designation_id=filters.designation_id,
            employment_status=filters.employment_status,
            after_employee_id=after_employee_id,
            limit=limit + 1,
        )
        has_more = len(records) > limit
        page_records = records[:limit]
        next_cursor = (
            encode_employee_report_cursor(page_records[-1].employee_id, filters)
            if has_more and page_records
            else None
        )
        return EmployeeReportPage(
            employees=[_to_response(record) for record in page_records],
            pagination=EmployeeReportPagination(
                limit=limit, has_more=has_more, next_cursor=next_cursor
            ),
        )


def _to_response(record: EmployeeReportRecord) -> EmployeeReportRow:
    return EmployeeReportRow(
        employee_id=record.employee_id,
        employee_code=record.employee_code,
        first_name=record.first_name,
        last_name=record.last_name,
        department_id=record.department_id,
        department_name=record.department_name,
        designation_id=record.designation_id,
        designation_name=record.designation_name,
        joining_date=record.joining_date,
        employment_end_date=record.employment_end_date,
        employment_status=record.employment_status,
    )


def _cursor_key() -> bytes:
    return get_settings().jwt_secret_key.encode("utf-8")


def _cursor_filters_are_well_typed(value: dict[str, object]) -> bool:
    return (
        (value["employee_code"] is None or isinstance(value["employee_code"], str))
        and (
            value["department_id"] is None
            or (
                isinstance(value["department_id"], int)
                and not isinstance(value["department_id"], bool)
                and value["department_id"] > 0
            )
        )
        and (
            value["designation_id"] is None
            or (
                isinstance(value["designation_id"], int)
                and not isinstance(value["designation_id"], bool)
                and value["designation_id"] > 0
            )
        )
        and (
            value["employment_status"] is None
            or value["employment_status"] in {"ACTIVE", "INACTIVE", "TERMINATED"}
        )
    )


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    valid = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    if not value or any(char not in valid for char in value):
        raise ValueError("Invalid base64url value.")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
