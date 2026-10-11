"""Finalized Payroll Component Breakdown report and signed keyset cursors."""

import base64
import binascii
import hashlib
import hmac
import json
from dataclasses import dataclass

from app.application.common.unit_of_work import UnitOfWork
from app.application.reporting.schemas import (
    PayrollComponentReportPage,
    PayrollComponentReportPagination,
    PayrollComponentReportRow,
)
from app.core.config import get_settings
from app.domain.payroll.payroll_result_component_report import (
    PayrollResultComponentReportRecord,
)
from app.domain.shared.exceptions import BusinessRuleViolation


_CURSOR_DOMAIN = b"epms:payroll-component-report:v1:"
_FILTER_KEYS = ("employee_id", "salary_component_id", "component_type")
_COMPONENT_TYPES = {"EARNING", "DEDUCTION"}
_MAX_PAGE_SIZE = 100


class InvalidPayrollComponentReportCursor(ValueError):
    """Raised for malformed, tampered, or mismatched component report cursors."""


class InvalidPayrollComponentReportFilters(ValueError):
    """Raised for invalid component report filters, identifiers, or limits."""


class PayrollComponentReportIntegrityError(RuntimeError):
    """Raised when a persisted component references a missing master definition."""


@dataclass(frozen=True)
class PayrollComponentReportFilters:
    employee_id: int | None = None
    salary_component_id: int | None = None
    component_type: str | None = None

    def __post_init__(self) -> None:
        for name in ("employee_id", "salary_component_id"):
            value = getattr(self, name)
            if value is not None and not _is_positive_int(value):
                raise InvalidPayrollComponentReportFilters(
                    f"{name} must be a positive integer."
                )
        if self.component_type is not None and (
            not isinstance(self.component_type, str)
            or self.component_type not in _COMPONENT_TYPES
        ):
            raise InvalidPayrollComponentReportFilters(
                "component_type must be EARNING or DEDUCTION."
            )

    def as_payload(self) -> dict[str, int | str | None]:
        return {
            "employee_id": self.employee_id,
            "salary_component_id": self.salary_component_id,
            "component_type": self.component_type,
        }


@dataclass(frozen=True)
class PayrollComponentReportPosition:
    payroll_result_id: int
    salary_component_id: int


def encode_payroll_component_report_cursor(
    payroll_run_id: int,
    position: PayrollComponentReportPosition,
    filters: PayrollComponentReportFilters,
) -> str:
    payload = json.dumps(
        {
            "v": 1,
            "report": "payroll_component_breakdown",
            "run": payroll_run_id,
            "filters": filters.as_payload(),
            "result": position.payroll_result_id,
            "component": position.salary_component_id,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    signature = hmac.new(
        _cursor_key(), _CURSOR_DOMAIN + payload, hashlib.sha256
    ).digest()
    return f"{_b64encode(payload)}.{_b64encode(signature)}"


def decode_payroll_component_report_cursor(
    encoded: str,
    payroll_run_id: int,
    filters: PayrollComponentReportFilters,
) -> PayrollComponentReportPosition:
    try:
        if not isinstance(encoded, str):
            raise ValueError
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
            raise ValueError

        data = json.loads(payload.decode("ascii"))
        if (
            not isinstance(data, dict)
            or set(data) != {"v", "report", "run", "filters", "result", "component"}
            or isinstance(data["v"], bool)
            or not isinstance(data["v"], int)
            or data["v"] != 1
            or data["report"] != "payroll_component_breakdown"
            or not _is_positive_int(data["run"])
            or data["run"] != payroll_run_id
            or not _is_positive_int(data["result"])
            or not _is_positive_int(data["component"])
            or not _valid_filter_payload(data["filters"])
            or data["filters"] != filters.as_payload()
            or json.dumps(data, separators=(",", ":"), sort_keys=True).encode("ascii")
            != payload
        ):
            raise ValueError
        return PayrollComponentReportPosition(
            payroll_result_id=data["result"],
            salary_component_id=data["component"],
        )
    except (
        ValueError,
        TypeError,
        KeyError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        binascii.Error,
    ) as exc:
        raise InvalidPayrollComponentReportCursor(
            "Invalid Payroll Component Breakdown report cursor."
        ) from exc


class PayrollComponentReportService:
    """Reads persisted component rows for finalized Payroll Runs."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def get_page(
        self,
        payroll_run_id: int,
        limit: int = 50,
        filters: PayrollComponentReportFilters | None = None,
        cursor: str | None = None,
    ) -> PayrollComponentReportPage | None:
        if not _is_positive_int(payroll_run_id):
            raise InvalidPayrollComponentReportFilters(
                "payroll_run_id must be a positive integer."
            )
        _validate_limit(limit)
        normalized_filters = (
            filters if filters is not None else PayrollComponentReportFilters()
        )
        if not isinstance(normalized_filters, PayrollComponentReportFilters):
            raise InvalidPayrollComponentReportFilters("Invalid report filters.")

        run = self.uow.payroll_runs.get_by_id(payroll_run_id)
        if run is None:
            # Existing Payroll report services use None for the API layer's 404 mapping.
            return None
        if run.status != "FINALIZED":
            raise BusinessRuleViolation(
                "Payroll Component Breakdown is available only for a FINALIZED Payroll Run."
            )

        position = (
            decode_payroll_component_report_cursor(
                cursor, payroll_run_id, normalized_filters
            )
            if cursor is not None
            else None
        )
        records = self.uow.payroll_result_components.list_report_page(
            payroll_run_id=payroll_run_id,
            after_payroll_result_id=(
                position.payroll_result_id if position is not None else None
            ),
            after_salary_component_id=(
                position.salary_component_id if position is not None else None
            ),
            employee_id=normalized_filters.employee_id,
            salary_component_id=normalized_filters.salary_component_id,
            component_type=normalized_filters.component_type,
            limit=limit + 1,
        )
        if any(not record.salary_component_definition_exists for record in records):
            raise PayrollComponentReportIntegrityError(
                "A Payroll Result Component references a missing Salary Component definition."
            )

        has_more = len(records) > limit
        page_records = records[:limit]
        next_cursor = (
            encode_payroll_component_report_cursor(
                payroll_run_id,
                PayrollComponentReportPosition(
                    page_records[-1].payroll_result_id,
                    page_records[-1].salary_component_id,
                ),
                normalized_filters,
            )
            if has_more and page_records
            else None
        )
        return PayrollComponentReportPage(
            payroll_run_id=payroll_run_id,
            components=[_to_response(record) for record in page_records],
            pagination=PayrollComponentReportPagination(
                limit=limit,
                has_more=has_more,
                next_cursor=next_cursor,
            ),
        )


def _to_response(
    record: PayrollResultComponentReportRecord,
) -> PayrollComponentReportRow:
    return PayrollComponentReportRow(
        payroll_result_component_id=record.payroll_result_component_id,
        payroll_run_id=record.payroll_run_id,
        payroll_result_id=record.payroll_result_id,
        employee_id=record.employee_id,
        employee_code=record.employee_code,
        employee_name=record.employee_name,
        salary_component_id=record.salary_component_id,
        component_code=record.component_code,
        component_name=record.component_name,
        component_type=record.component_type,
        amount=record.amount,
        calculation_order=record.calculation_order,
    )


def _validate_limit(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= _MAX_PAGE_SIZE:
        raise InvalidPayrollComponentReportFilters("limit must be between 1 and 100.")


def _cursor_key() -> bytes:
    return get_settings().jwt_secret_key.encode("utf-8")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    valid = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    if not value or any(character not in valid for character in value):
        raise ValueError
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _is_positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _valid_filter_payload(value: object) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == set(_FILTER_KEYS)
        and (value["employee_id"] is None or _is_positive_int(value["employee_id"]))
        and (
            value["salary_component_id"] is None
            or _is_positive_int(value["salary_component_id"])
        )
        and (
            value["component_type"] is None
            or value["component_type"] in _COMPONENT_TYPES
        )
    )
