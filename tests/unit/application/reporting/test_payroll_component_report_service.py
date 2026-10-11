import base64
import hashlib
import hmac
import json
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.application.reporting.payroll_component_report_service import (
    InvalidPayrollComponentReportCursor,
    InvalidPayrollComponentReportFilters,
    PayrollComponentReportFilters,
    PayrollComponentReportIntegrityError,
    PayrollComponentReportPosition,
    PayrollComponentReportService,
    decode_payroll_component_report_cursor,
    encode_payroll_component_report_cursor,
)
from app.application.reporting.payroll_results_report_service import (
    encode_payroll_results_cursor,
)
from app.core.config import get_settings
from app.domain.payroll.payroll_result_component_report import (
    PayrollResultComponentReportRecord,
)
from app.domain.shared.exceptions import BusinessRuleViolation


def _record(
    result_id: int,
    component_id: int,
    *,
    definition_exists: bool = True,
    employee_code: str | None = "E-10",
    employee_name: str | None = "Asha Patel",
) -> PayrollResultComponentReportRecord:
    return PayrollResultComponentReportRecord(
        payroll_result_component_id=result_id * 100 + component_id,
        payroll_run_id=44,
        payroll_result_id=result_id,
        employee_id=10,
        employee_code=employee_code,
        employee_name=employee_name,
        salary_component_id=component_id,
        salary_component_definition_exists=definition_exists,
        component_code=f"C-{component_id}" if definition_exists else None,
        component_name=f"Component {component_id}" if definition_exists else None,
        component_type="EARNING" if component_id != 3 else "DEDUCTION",
        amount=Decimal("1200.25"),
        calculation_order=component_id,
    )


class _ReportUow:
    def __init__(
        self,
        records: list[PayrollResultComponentReportRecord] | None = None,
        *,
        status: str = "FINALIZED",
        run_exists: bool = True,
    ) -> None:
        self.run_exists = run_exists
        self.status = status
        self.records = records if records is not None else [
            _record(70, 2), _record(70, 3), _record(71, 4)
        ]
        self.run_calls: list[int] = []
        self.page_calls: list[dict[str, object]] = []
        self.payroll_runs = SimpleNamespace(get_by_id=self._get_run)
        self.payroll_result_components = SimpleNamespace(
            list_report_page=self._list_report_page
        )

    def _get_run(self, payroll_run_id: int):
        self.run_calls.append(payroll_run_id)
        if not self.run_exists:
            return None
        return SimpleNamespace(payroll_run_id=payroll_run_id, status=self.status)

    def _list_report_page(self, **kwargs):
        self.page_calls.append(kwargs)
        rows = [row for row in self.records if row.payroll_run_id == kwargs["payroll_run_id"]]
        if kwargs["employee_id"] is not None:
            rows = [row for row in rows if row.employee_id == kwargs["employee_id"]]
        if kwargs["salary_component_id"] is not None:
            rows = [
                row for row in rows
                if row.salary_component_id == kwargs["salary_component_id"]
            ]
        if kwargs["component_type"] is not None:
            rows = [row for row in rows if row.component_type == kwargs["component_type"]]
        if kwargs["after_payroll_result_id"] is not None:
            rows = [
                row for row in rows
                if (row.payroll_result_id, row.salary_component_id)
                > (
                    kwargs["after_payroll_result_id"],
                    kwargs["after_salary_component_id"],
                )
            ]
        return rows[: kwargs["limit"]]


def _signed_payload(payload: bytes) -> str:
    domain = b"epms:payroll-component-report:v1:"
    signature = hmac.new(
        get_settings().jwt_secret_key.encode("utf-8"), domain + payload, hashlib.sha256
    ).digest()
    encode = lambda value: base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")
    return f"{encode(payload)}.{encode(signature)}"


def _signed_cursor(data: dict[str, object]) -> str:
    payload = json.dumps(data, separators=(",", ":"), sort_keys=True).encode("ascii")
    return _signed_payload(payload)


def test_finalized_report_returns_only_approved_persisted_fields_and_requests_limit_plus_one() -> None:
    uow = _ReportUow()
    page = PayrollComponentReportService(uow).get_page(44, 2)

    assert page is not None
    assert page.payroll_run_id == 44
    assert [
        (row.payroll_result_id, row.salary_component_id) for row in page.components
    ] == [(70, 2), (70, 3)]
    row = page.components[0]
    assert row.amount == Decimal("1200.25")
    assert row.calculation_order == 2
    assert row.employee_name == "Asha Patel"
    assert set(type(row).model_fields) == {
        "payroll_result_component_id", "payroll_run_id", "payroll_result_id",
        "employee_id", "employee_code", "employee_name", "salary_component_id",
        "component_code", "component_name", "component_type", "amount",
        "calculation_order",
    }
    assert page.pagination.limit == 2
    assert page.pagination.has_more is True
    assert page.pagination.next_cursor is not None
    assert uow.page_calls == [{
        "payroll_run_id": 44,
        "after_payroll_result_id": None,
        "after_salary_component_id": None,
        "employee_id": None,
        "salary_component_id": None,
        "component_type": None,
        "limit": 3,
    }]


def test_missing_run_returns_none_without_component_query() -> None:
    uow = _ReportUow(run_exists=False)
    assert PayrollComponentReportService(uow).get_page(44) is None
    assert uow.run_calls == [44]
    assert uow.page_calls == []


@pytest.mark.parametrize("status", ["CREATED", "PROCESSING", "PROCESSED", "FAILED"])
def test_non_finalized_run_raises_conflict_rule_before_component_query(status: str) -> None:
    uow = _ReportUow(status=status)
    with pytest.raises(BusinessRuleViolation, match="FINALIZED"):
        PayrollComponentReportService(uow).get_page(44)
    assert uow.page_calls == []


def test_empty_finalized_run_returns_empty_page_without_cursor() -> None:
    page = PayrollComponentReportService(_ReportUow(records=[])).get_page(44)
    assert page is not None
    assert page.components == []
    assert page.pagination.has_more is False
    assert page.pagination.next_cursor is None


@pytest.mark.parametrize("limit", [1, 100])
def test_limit_accepts_inclusive_boundaries(limit: int) -> None:
    uow = _ReportUow()
    page = PayrollComponentReportService(uow).get_page(44, limit)
    assert page is not None and page.pagination.limit == limit
    assert uow.page_calls[0]["limit"] == limit + 1


@pytest.mark.parametrize("limit", [0, 101, True, 1.5, "2"])
def test_limit_rejects_out_of_range_or_invalid_types(limit: object) -> None:
    with pytest.raises(InvalidPayrollComponentReportFilters):
        PayrollComponentReportService(_ReportUow()).get_page(44, limit)  # type: ignore[arg-type]


def test_keyset_cursor_continues_with_no_duplicate_or_missing_boundary_rows() -> None:
    uow = _ReportUow()
    service = PayrollComponentReportService(uow)
    page1 = service.get_page(44, 1)
    assert page1 is not None and page1.pagination.next_cursor
    page2 = service.get_page(44, 1, cursor=page1.pagination.next_cursor)
    assert page2 is not None and page2.pagination.next_cursor
    page3 = service.get_page(44, 1, cursor=page2.pagination.next_cursor)
    assert page3 is not None
    assert [
        (row.payroll_result_id, row.salary_component_id)
        for row in [*page1.components, *page2.components, *page3.components]
    ] == [(70, 2), (70, 3), (71, 4)]
    assert uow.page_calls[1]["after_payroll_result_id"] == 70
    assert uow.page_calls[1]["after_salary_component_id"] == 2
    assert [call["limit"] for call in uow.page_calls] == [2, 2, 2]
    assert page3.pagination.has_more is False
    assert page3.pagination.next_cursor is None


def test_cursor_is_deterministic_and_preserves_filter_bound_position() -> None:
    filters = PayrollComponentReportFilters(10, 2, "EARNING")
    position = PayrollComponentReportPosition(70, 2)
    first = encode_payroll_component_report_cursor(44, position, filters)
    assert first == encode_payroll_component_report_cursor(44, position, filters)
    assert decode_payroll_component_report_cursor(first, 44, filters) == position


@pytest.mark.parametrize("cursor", ["", "bad", "***.***", 42])
def test_cursor_rejects_malformed_values(cursor: object) -> None:
    with pytest.raises(InvalidPayrollComponentReportCursor):
        decode_payroll_component_report_cursor(cursor, 44, PayrollComponentReportFilters())  # type: ignore[arg-type]


def test_cursor_rejects_tampering_cross_run_cross_filter_and_other_report() -> None:
    filters = PayrollComponentReportFilters(employee_id=10)
    cursor = encode_payroll_component_report_cursor(
        44, PayrollComponentReportPosition(70, 2), filters
    )
    tampered = cursor[:-1] + ("A" if cursor[-1] != "A" else "B")
    with pytest.raises(InvalidPayrollComponentReportCursor):
        decode_payroll_component_report_cursor(tampered, 44, filters)
    with pytest.raises(InvalidPayrollComponentReportCursor):
        decode_payroll_component_report_cursor(cursor, 45, filters)
    with pytest.raises(InvalidPayrollComponentReportCursor):
        decode_payroll_component_report_cursor(
            cursor, 44, PayrollComponentReportFilters(employee_id=11)
        )
    payroll_results_cursor = encode_payroll_results_cursor(44, 10, 70)
    with pytest.raises(InvalidPayrollComponentReportCursor):
        decode_payroll_component_report_cursor(payroll_results_cursor, 44, filters)


def test_cursor_rejects_unsupported_version_and_noncanonical_or_invalid_position() -> None:
    filters = PayrollComponentReportFilters()
    base = {
        "v": 2,
        "report": "payroll_component_breakdown",
        "run": 44,
        "filters": filters.as_payload(),
        "result": 70,
        "component": 2,
    }
    with pytest.raises(InvalidPayrollComponentReportCursor):
        decode_payroll_component_report_cursor(_signed_cursor(base), 44, filters)
    invalid_position = {**base, "v": 1, "result": True}
    with pytest.raises(InvalidPayrollComponentReportCursor):
        decode_payroll_component_report_cursor(
            _signed_cursor(invalid_position), 44, filters
        )

    noncanonical_json = json.dumps(
        {
            "v": 1,
            "report": "payroll_component_breakdown",
            "run": 44,
            "filters": filters.as_payload(),
            "result": 70,
            "component": 2,
        },
        separators=(",", ":"),
        sort_keys=False,
    ).encode("ascii")
    with pytest.raises(InvalidPayrollComponentReportCursor):
        decode_payroll_component_report_cursor(
            _signed_payload(noncanonical_json), 44, filters
        )


@pytest.mark.parametrize(
    "filters",
    [
        {"employee_id": True},
        {"employee_id": 0},
        {"employee_id": "10"},
        {"salary_component_id": -1},
        {"component_type": "earning"},
        {"component_type": "OTHER"},
    ],
)
def test_invalid_filter_ids_and_component_types_are_rejected(filters: dict[str, object]) -> None:
    with pytest.raises(InvalidPayrollComponentReportFilters):
        PayrollComponentReportFilters(**filters)  # type: ignore[arg-type]


@pytest.mark.parametrize("run_id", [0, -1, True, "44"])
def test_invalid_run_id_types_are_rejected(run_id: object) -> None:
    with pytest.raises(InvalidPayrollComponentReportFilters):
        PayrollComponentReportService(_ReportUow()).get_page(run_id)  # type: ignore[arg-type]


def test_missing_component_definition_raises_internal_integrity_error() -> None:
    record = _record(70, 99, definition_exists=False)
    with pytest.raises(PayrollComponentReportIntegrityError) as error:
        PayrollComponentReportService(_ReportUow([record])).get_page(44)
    assert "missing Salary Component definition" in str(error.value)
    assert "99" not in str(error.value)


def test_null_employee_labels_are_valid_and_inactive_component_is_included() -> None:
    record = _record(70, 2, employee_code=None, employee_name=None)
    page = PayrollComponentReportService(_ReportUow([record])).get_page(44)
    assert page is not None
    assert page.components[0].employee_code is None
    assert page.components[0].employee_name is None
    assert page.components[0].component_name == "Component 2"


def test_filters_are_forwarded_without_recalculation_or_derived_totals() -> None:
    uow = _ReportUow()
    filters = PayrollComponentReportFilters(
        employee_id=10, salary_component_id=2, component_type="EARNING"
    )
    page = PayrollComponentReportService(uow).get_page(44, 10, filters)
    assert page is not None
    assert len(page.components) == 1
    assert uow.page_calls[0]["employee_id"] == 10
    assert uow.page_calls[0]["salary_component_id"] == 2
    assert uow.page_calls[0]["component_type"] == "EARNING"
    assert not hasattr(page, "gross_earnings")
    assert not hasattr(page, "total_deductions")
    assert not hasattr(page, "net_salary")
