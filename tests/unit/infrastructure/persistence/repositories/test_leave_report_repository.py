from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.application.reporting.schemas import (
    LeaveAllocationReportRow,
    LeaveBalanceReportRow,
)
from app.domain.leave.leave_report import (
    LeaveAllocationReportRecord,
    LeaveBalanceReportRecord,
)
from app.infrastructure.persistence.repositories.leave_report_repository import (
    LeaveReportRepository,
)


def _report_engine():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for statement in (
            "CREATE TABLE departments (department_id INTEGER PRIMARY KEY, department_name TEXT NOT NULL)",
            "CREATE TABLE designations (designation_id INTEGER PRIMARY KEY, designation_name TEXT NOT NULL)",
            "CREATE TABLE employees (employee_id INTEGER PRIMARY KEY, employee_code TEXT NOT NULL, "
            "first_name TEXT NOT NULL, last_name TEXT NOT NULL, department_id INTEGER NOT NULL, "
            "designation_id INTEGER NOT NULL, employment_status TEXT NOT NULL)",
            "CREATE TABLE leave_types (leave_type_id INTEGER PRIMARY KEY, leave_type_name TEXT NOT NULL, is_active BOOLEAN NOT NULL)",
            "CREATE TABLE leave_requests (leave_request_id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL, "
            "leave_type_id INTEGER NOT NULL, start_date DATE NOT NULL, end_date DATE NOT NULL, "
            "requested_days NUMERIC(6, 2) NOT NULL, status TEXT NOT NULL, reason TEXT, review_comment TEXT, "
            "reviewed_by_employee_id INTEGER, reviewed_at DATETIME)",
            "CREATE TABLE leave_request_days (leave_request_day_id INTEGER PRIMARY KEY, "
            "leave_request_id INTEGER NOT NULL, leave_date DATE NOT NULL, day_fraction NUMERIC(4, 2) NOT NULL)",
            "CREATE TABLE leave_balances (leave_balance_id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL, "
            "leave_type_id INTEGER NOT NULL, balance_year INTEGER NOT NULL, allocated_days NUMERIC(6, 2) NOT NULL, "
            "used_days NUMERIC(6, 2) NOT NULL)",
            "INSERT INTO departments VALUES (1, 'Finance'), (2, 'Operations')",
            "INSERT INTO designations VALUES (10, 'Analyst'), (20, 'Coordinator')",
            "INSERT INTO employees VALUES "
            "(10, 'E10', 'Asha', 'Patel', 1, 10, 'ACTIVE'), "
            "(11, 'E11', 'Ben', 'Lee', 1, 10, 'TERMINATED'), "
            "(12, 'E12', 'Cara', 'Wu', 2, 20, 'INACTIVE'), "
            "(99, 'E99', 'Robin', 'Manager', 1, 10, 'ACTIVE')",
            "INSERT INTO leave_types VALUES (1, 'Annual', 1), (2, 'Legacy', 0)",
            "INSERT INTO leave_requests VALUES "
            "(100, 10, 1, '2026-04-10', '2026-04-11', 1.50, 'PENDING', 'excluded', NULL, NULL, NULL), "
            "(101, 11, 1, '2026-04-10', '2026-04-10', 0.50, 'APPROVED', NULL, 'excluded', 99, '2026-04-01'), "
            "(102, 12, 2, '2026-04-11', '2026-04-11', 1.00, 'REJECTED', NULL, 'excluded', 99, '2026-04-02'), "
            "(103, 10, 1, '2026-04-11', '2026-04-11', 0.25, 'CANCELLED', NULL, NULL, NULL, NULL)",
            "INSERT INTO leave_request_days VALUES "
            "(501, 100, '2026-04-10', 1.00), (502, 101, '2026-04-10', 0.50), "
            "(503, 102, '2026-04-11', 1.00), (504, 103, '2026-04-11', 0.25), "
            "(505, 100, '2026-04-11', 0.50)",
            "INSERT INTO leave_balances VALUES "
            "(601, 10, 1, 0, 10.00, 1.25), (602, 10, 1, 1, 20.00, 2.00), "
            "(603, 11, 1, 1, 15.00, 3.50), (604, 12, 2, 1, 8.00, 0.00)",
        ):
            connection.exec_driver_sql(statement)
    return engine


def test_allocation_report_projects_daily_rows_filters_inclusively_and_keyset_paginates() -> None:
    engine = _report_engine()
    statements: list[str] = []
    event.listen(
        engine,
        "before_cursor_execute",
        lambda connection, cursor, statement, parameters, context, executemany:
            statements.append(statement),
    )
    try:
        with Session(engine) as session:
            repository = LeaveReportRepository(session)
            first = repository.list_allocation_report_page(
                date_from=date(2026, 4, 10),
                date_to=date(2026, 4, 11),
                employee_id=None,
                department_id=1,
                leave_type_id=1,
                status=None,
                after_leave_date=None,
                after_leave_request_day_id=None,
                limit=2,
            )
            assert [row.leave_request_day_id for row in first] == [501, 502]
            assert [row.leave_date for row in first] == [
                date(2026, 4, 10),
                date(2026, 4, 10),
            ]
            assert [row.status for row in first] == ["PENDING", "APPROVED"]
            assert first[0].requested_days == Decimal("1.50")
            assert first[0].day_fraction == Decimal("1.00")
            assert first[1].requested_days == Decimal("0.50")
            assert first[1].day_fraction == Decimal("0.50")
            assert first[0].department_name == "Finance"
            assert first[0].designation_name == "Analyst"
            assert first[0].leave_type_name == "Annual"

            next_page = repository.list_allocation_report_page(
                date_from=date(2026, 4, 10),
                date_to=date(2026, 4, 11),
                employee_id=None,
                department_id=None,
                leave_type_id=None,
                status=None,
                after_leave_date=date(2026, 4, 10),
                after_leave_request_day_id=502,
                limit=2,
            )
            assert [row.leave_request_day_id for row in next_page] == [503, 504]
            assert [row.status for row in next_page] == ["REJECTED", "CANCELLED"]
            assert next_page[0].employee_id == 12  # INACTIVE employees remain visible.
            final_page = repository.list_allocation_report_page(
                date_from=date(2026, 4, 10),
                date_to=date(2026, 4, 11),
                employee_id=None,
                department_id=None,
                leave_type_id=None,
                status=None,
                after_leave_date=date(2026, 4, 11),
                after_leave_request_day_id=504,
                limit=2,
            )
            assert [row.leave_request_day_id for row in final_page] == [505]
            assert final_page[0].leave_request_id == first[0].leave_request_id
            assert final_page[0].requested_days == first[0].requested_days

            filtered = repository.list_allocation_report_page(
                date_from=date(2026, 4, 10),
                date_to=date(2026, 4, 10),
                employee_id=11,
                department_id=1,
                leave_type_id=1,
                status="APPROVED",
                after_leave_date=None,
                after_leave_request_day_id=None,
                limit=5,
            )
            assert [row.leave_request_day_id for row in filtered] == [502]
            assert repository.list_allocation_report_page(
                date_from=None,
                date_to=None,
                employee_id=999,
                department_id=None,
                leave_type_id=None,
                status=None,
                after_leave_date=None,
                after_leave_request_day_id=None,
                limit=5,
            ) == []

        selects = [sql for sql in statements if sql.lstrip().upper().startswith("SELECT")]
        assert len(selects) == 5
        first_sql = selects[0]
        for selected_column in (
            "leave_requests.leave_request_id",
            "leave_request_days.leave_request_day_id",
            "employees.employee_code",
            "employees.first_name",
            "employees.last_name",
            "departments.department_name",
            "designations.designation_name",
            "leave_types.leave_type_name",
            "leave_requests.requested_days",
            "leave_request_days.day_fraction",
        ):
            assert selected_column in first_sql
        for excluded_column in (
            "leave_requests.reason",
            "leave_requests.review_comment",
            "leave_types.payroll_treatment",
            "employees.user_id",
            "employees.manager_employee_id",
        ):
            assert excluded_column not in first_sql
        assert "leave_request_days.leave_date >= " in first_sql
        assert "leave_request_days.leave_date <= " in first_sql
        assert "employees.employment_status" not in first_sql
        assert "ORDER BY leave_request_days.leave_date ASC, leave_request_days.leave_request_day_id ASC" in first_sql
        assert "LIMIT" in first_sql.upper()
        assert "leave_request_days.leave_date >" in selects[1]
        assert "leave_request_days.leave_request_day_id >" in selects[1]
        assert "leave_requests.status =" not in first_sql
    finally:
        engine.dispose()


def test_allocation_report_status_filter_and_empty_page() -> None:
    engine = _report_engine()
    try:
        with Session(engine) as session:
            repository = LeaveReportRepository(session)
            rows = repository.list_allocation_report_page(
                date_from=None,
                date_to=None,
                employee_id=None,
                department_id=None,
                leave_type_id=None,
                status="CANCELLED",
                after_leave_date=None,
                after_leave_request_day_id=None,
                limit=10,
            )
            assert len(rows) == 1
            assert rows[0].status == "CANCELLED"
            assert rows[0].requested_days == Decimal("0.25")
            assert rows[0].day_fraction == Decimal("0.25")

            assert repository.list_allocation_report_page(
                date_from=date(2027, 1, 1),
                date_to=date(2027, 1, 31),
                employee_id=None,
                department_id=None,
                leave_type_id=None,
                status=None,
                after_leave_date=None,
                after_leave_request_day_id=None,
                limit=2,
            ) == []
    finally:
        engine.dispose()


def test_balance_report_preserves_values_filters_and_keyset_paginates() -> None:
    engine = _report_engine()
    statements: list[str] = []
    event.listen(
        engine,
        "before_cursor_execute",
        lambda connection, cursor, statement, parameters, context, executemany:
            statements.append(statement),
    )
    try:
        with Session(engine) as session:
            repository = LeaveReportRepository(session)
            first = repository.list_balance_report_page(
                employee_id=10,
                department_id=1,
                leave_type_id=1,
                balance_year=None,
                after_employee_id=None,
                after_leave_type_id=None,
                after_balance_year=None,
                limit=1,
            )
            assert len(first) == 1
            assert (first[0].employee_id, first[0].leave_type_id, first[0].balance_year) == (10, 1, 0)
            assert first[0].allocated_days == Decimal("10.00")
            assert first[0].used_days == Decimal("1.25")

            second = repository.list_balance_report_page(
                employee_id=None,
                department_id=None,
                leave_type_id=None,
                balance_year=None,
                after_employee_id=10,
                after_leave_type_id=1,
                after_balance_year=0,
                limit=2,
            )
            assert [
                (row.employee_id, row.leave_type_id, row.balance_year) for row in second
            ] == [(10, 1, 1), (11, 1, 1)]
            assert second[1].employee_code == "E11"  # TERMINATED employee remains visible.

            year_filter = repository.list_balance_report_page(
                employee_id=None,
                department_id=None,
                leave_type_id=None,
                balance_year=0,
                after_employee_id=None,
                after_leave_type_id=None,
                after_balance_year=None,
                limit=10,
            )
            assert [(row.employee_id, row.balance_year) for row in year_filter] == [(10, 0)]

            inactive_type = repository.list_balance_report_page(
                employee_id=12,
                department_id=2,
                leave_type_id=2,
                balance_year=1,
                after_employee_id=None,
                after_leave_type_id=None,
                after_balance_year=None,
                limit=5,
            )
            assert len(inactive_type) == 1
            assert inactive_type[0].leave_type_name == "Legacy"
            assert inactive_type[0].allocated_days == Decimal("8.00")

        selects = [sql for sql in statements if sql.lstrip().upper().startswith("SELECT")]
        assert len(selects) == 4
        first_sql = selects[0]
        for selected_column in (
            "employees.employee_code",
            "employees.first_name",
            "employees.last_name",
            "departments.department_name",
            "designations.designation_name",
            "leave_types.leave_type_name",
            "leave_balances.balance_year",
            "leave_balances.allocated_days",
            "leave_balances.used_days",
        ):
            assert selected_column in first_sql
        for excluded_column in (
            "employees.employment_status",
            "leave_types.is_active",
            "leave_balances.allocated_days -",
            "leave_balances.used_days -",
        ):
            assert excluded_column not in first_sql
        assert "ORDER BY leave_balances.employee_id ASC, leave_balances.leave_type_id ASC, leave_balances.balance_year ASC" in first_sql
        assert "LIMIT" in first_sql.upper()
        assert "leave_balances.employee_id >" in selects[1]
        assert "leave_balances.leave_type_id >" in selects[1]
        assert "leave_balances.balance_year >" in selects[1]
        assert "leave_balances.balance_year =" in selects[2]
    finally:
        engine.dispose()


def test_leave_report_projection_and_response_fields_match_contract() -> None:
    allocation_fields = {
        "leave_request_id", "leave_request_day_id", "employee_id", "employee_code",
        "first_name", "last_name", "department_id", "department_name",
        "designation_id", "designation_name", "leave_type_id", "leave_type_name",
        "start_date", "end_date", "requested_days", "status", "leave_date", "day_fraction",
    }
    balance_fields = {
        "employee_id", "employee_code", "first_name", "last_name", "department_id",
        "department_name", "designation_id", "designation_name", "leave_type_id",
        "leave_type_name", "balance_year", "allocated_days", "used_days",
    }
    assert set(LeaveAllocationReportRecord.__dataclass_fields__) == allocation_fields
    assert set(LeaveAllocationReportRow.model_fields) == allocation_fields
    assert set(LeaveBalanceReportRecord.__dataclass_fields__) == balance_fields
    assert set(LeaveBalanceReportRow.model_fields) == balance_fields

    allocation = LeaveAllocationReportRow(
        leave_request_id=1,
        leave_request_day_id=2,
        employee_id=3,
        employee_code="E3",
        first_name="Alex",
        last_name="Lee",
        department_id=4,
        department_name="Finance",
        designation_id=5,
        designation_name="Analyst",
        leave_type_id=6,
        leave_type_name="Annual",
        start_date=date(2026, 4, 10),
        end_date=date(2026, 4, 10),
        requested_days=Decimal("0.50"),
        status="APPROVED",
        leave_date=date(2026, 4, 10),
        day_fraction=Decimal("0.50"),
    )
    assert isinstance(allocation.start_date, date)
    assert isinstance(allocation.requested_days, Decimal)
    assert isinstance(allocation.day_fraction, Decimal)
    assert not {"reason", "review_comment", "reviewed_by_employee_id", "payroll_treatment"} & allocation_fields

    balance = LeaveBalanceReportRow(
        employee_id=3,
        employee_code="E3",
        first_name="Alex",
        last_name="Lee",
        department_id=4,
        department_name="Finance",
        designation_id=5,
        designation_name="Analyst",
        leave_type_id=6,
        leave_type_name="Annual",
        balance_year=0,
        allocated_days=Decimal("0.00"),
        used_days=Decimal("0.00"),
    )
    assert isinstance(balance.allocated_days, Decimal)
    assert isinstance(balance.used_days, Decimal)
    with pytest.raises(ValidationError):
        LeaveBalanceReportRow(**{**balance.model_dump(), "balance_year": 65536})
