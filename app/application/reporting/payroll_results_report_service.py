import base64
import binascii
import hashlib
import hmac
import json
from dataclasses import dataclass

from app.application.common.unit_of_work import UnitOfWork
from app.application.reporting.schemas import (
    EmployeePayrollResultReportPage,
    EmployeePayrollResultReportRow,
    PayrollResultsReportPagination,
)
from app.core.config import get_settings
from app.domain.payroll.payroll_result_report import PayrollResultReportRecord
from app.domain.shared.exceptions import BusinessRuleViolation


_CURSOR_DOMAIN = b"epms:payroll-results-report:v1:"


class InvalidPayrollResultsCursor(ValueError):
    """Raised when a report cursor is malformed, altered, or cross-run."""


@dataclass(frozen=True)
class PayrollResultsCursor:
    payroll_run_id: int
    employee_id: int
    payroll_result_id: int


def encode_payroll_results_cursor(
    payroll_run_id: int, employee_id: int, payroll_result_id: int
) -> str:
    payload = json.dumps(
        {
            "v": 1,
            "run": payroll_run_id,
            "employee": employee_id,
            "result": payroll_result_id,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    signature = hmac.new(
        _cursor_key(), _CURSOR_DOMAIN + payload, hashlib.sha256
    ).digest()
    return f"{_b64encode(payload)}.{_b64encode(signature)}"


def decode_payroll_results_cursor(
    encoded: str, requested_run_id: int
) -> PayrollResultsCursor:
    key = _cursor_key()
    try:
        payload_part, signature_part = encoded.split(".", 1)
        payload = _b64decode(payload_part)
        signature = _b64decode(signature_part)
        expected_signature = hmac.new(
            key, _CURSOR_DOMAIN + payload, hashlib.sha256
        ).digest()
        if (
            not hmac.compare_digest(signature, expected_signature)
            or _b64encode(signature) != signature_part
        ):
            raise ValueError("Invalid cursor signature.")

        data = json.loads(payload.decode("ascii"))
        if not isinstance(data, dict) or set(data) != {
            "v",
            "run",
            "employee",
            "result",
        }:
            raise ValueError("Invalid cursor fields.")
        if (
            isinstance(data["v"], bool)
            or not isinstance(data["v"], int)
            or data["v"] != 1
            or any(
                isinstance(data[key], bool)
                or not isinstance(data[key], int)
                or data[key] <= 0
                for key in ("run", "employee", "result")
            )
        ):
            raise ValueError("Invalid cursor values.")
        if data["run"] != requested_run_id:
            raise ValueError("Cursor belongs to another Payroll Run.")
        # Require the exact deterministic serialization emitted by the encoder.
        if _b64encode(payload) != payload_part:
            raise ValueError("Cursor is not canonically encoded.")
        return PayrollResultsCursor(
            payroll_run_id=data["run"],
            employee_id=data["employee"],
            payroll_result_id=data["result"],
        )
    except (
        ValueError,
        TypeError,
        KeyError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        binascii.Error,
    ) as exc:
        raise InvalidPayrollResultsCursor(
            "Invalid payroll results cursor."
        ) from exc


class PayrollResultsReportService:
    """Reads a bounded page of persisted results for a finalized run."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    def get_page(
        self,
        payroll_run_id: int,
        limit: int,
        cursor: str | None,
    ) -> EmployeePayrollResultReportPage | None:
        run = self.uow.payroll_runs.get_by_id(payroll_run_id)
        if run is None:
            return None
        if run.status != "FINALIZED":
            raise BusinessRuleViolation(
                "Employee payroll results are available only for a FINALIZED Payroll Run."
            )

        position = (
            decode_payroll_results_cursor(cursor, payroll_run_id)
            if cursor is not None
            else None
        )
        records = self.uow.payroll_results.list_report_page(
            payroll_run_id=payroll_run_id,
            after_employee_id=position.employee_id if position else None,
            after_payroll_result_id=position.payroll_result_id if position else None,
            limit=limit + 1,
        )
        has_more = len(records) > limit
        page_records = records[:limit]
        next_cursor = None
        if has_more and page_records:
            last = page_records[-1]
            next_cursor = encode_payroll_results_cursor(
                payroll_run_id,
                last.employee_id,
                last.payroll_result_id,
            )

        return EmployeePayrollResultReportPage(
            payroll_run_id=payroll_run_id,
            results=[_to_response(record) for record in page_records],
            pagination=PayrollResultsReportPagination(
                limit=limit,
                has_more=has_more,
                next_cursor=next_cursor,
            ),
        )


def _to_response(
    record: PayrollResultReportRecord,
) -> EmployeePayrollResultReportRow:
    return EmployeePayrollResultReportRow(
        payroll_result_id=record.payroll_result_id,
        payroll_run_id=record.payroll_run_id,
        employee_id=record.employee_id,
        salary_assignment_id=record.salary_assignment_id,
        gross_earnings=record.gross_earnings,
        total_deductions=record.total_deductions,
        net_salary=record.net_salary,
        employee_code=record.employee_code,
        employee_name=record.employee_name,
    )


def _cursor_key() -> bytes:
    return get_settings().jwt_secret_key.encode("utf-8")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    valid_characters = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    )
    if not value or any(char not in valid_characters for char in value):
        raise ValueError("Invalid base64url value.")
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
