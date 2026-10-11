from decimal import Decimal

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.infrastructure.persistence.repositories.payroll_result_component_repository import (
    PayrollResultComponentRepository,
)


def _engine_with_report_rows():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE payroll_runs (payroll_run_id INTEGER PRIMARY KEY)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE employees (employee_id INTEGER PRIMARY KEY, "
            "employee_code TEXT, first_name TEXT, last_name TEXT)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE payroll_results (payroll_result_id INTEGER PRIMARY KEY, "
            "payroll_run_id INTEGER, employee_id INTEGER)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE salary_components (salary_component_id INTEGER PRIMARY KEY, "
            "component_code TEXT, component_name TEXT, component_type TEXT, status TEXT)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE payroll_result_components ("
            "payroll_result_component_id INTEGER PRIMARY KEY, "
            "payroll_result_id INTEGER, salary_component_id INTEGER, "
            "component_type TEXT, amount NUMERIC(15, 2), calculation_order INTEGER)"
        )
        connection.exec_driver_sql("INSERT INTO payroll_runs VALUES (7), (8)")
        connection.exec_driver_sql(
            "INSERT INTO employees VALUES "
            "(10, 'E10', 'Asha', 'Patel'), (11, NULL, NULL, NULL)"
        )
        connection.exec_driver_sql(
            "INSERT INTO payroll_results VALUES (70, 7, 10), (71, 7, 11), (80, 8, 10)"
        )
        connection.exec_driver_sql(
            "INSERT INTO salary_components VALUES "
            "(2, 'BASE', 'Base Salary', 'EARNING', 'INACTIVE'), "
            "(3, 'TAX', 'Tax', 'DEDUCTION', 'ACTIVE'), "
            "(4, 'BONUS', 'Bonus', 'EARNING', 'ACTIVE')"
        )
        connection.exec_driver_sql(
            "INSERT INTO payroll_result_components VALUES "
            "(1, 70, 2, 'EARNING', 1000.25, 1), "
            "(2, 70, 3, 'DEDUCTION', 100.25, 2), "
            "(3, 71, 4, 'EARNING', 50.00, 1), "
            "(4, 80, 2, 'EARNING', 9000.00, 1), "
            "(5, 70, 99, 'EARNING', 7.00, 3)"
        )
    return engine


def _page(
    repository: PayrollResultComponentRepository,
    *,
    run_id: int = 7,
    after_result_id: int | None = None,
    after_component_id: int | None = None,
    employee_id: int | None = None,
    salary_component_id: int | None = None,
    component_type: str | None = None,
    limit: int = 100,
):
    return repository.list_report_page(
        payroll_run_id=run_id,
        after_payroll_result_id=after_result_id,
        after_salary_component_id=after_component_id,
        employee_id=employee_id,
        salary_component_id=salary_component_id,
        component_type=component_type,
        limit=limit,
    )


def test_report_page_projects_persisted_values_and_current_labels() -> None:
    engine = _engine_with_report_rows()
    statements: list[str] = []
    event.listen(
        engine,
        "before_cursor_execute",
        lambda connection, cursor, statement, parameters, context, executemany:
            statements.append(statement),
    )
    try:
        with Session(engine) as session:
            rows = _page(PayrollResultComponentRepository(session), limit=10)

        assert [
            (row.payroll_result_id, row.salary_component_id) for row in rows
        ] == [(70, 2), (70, 3), (70, 99), (71, 4)]
        first = rows[0]
        assert first.payroll_result_component_id == 1
        assert first.payroll_run_id == 7
        assert first.employee_id == 10
        assert first.employee_code == "E10"
        assert first.employee_name == "Asha Patel"
        assert first.component_code == "BASE"
        assert first.component_name == "Base Salary"
        assert first.component_type == "EARNING"
        assert first.amount == Decimal("1000.25")
        assert first.calculation_order == 1
        assert first.salary_component_definition_exists is True
        assert rows[0].component_code is not None  # inactive definitions are included
        assert rows[2].salary_component_definition_exists is False
        assert rows[2].component_code is None and rows[2].component_name is None
        assert rows[3].employee_code is None and rows[3].employee_name is None

        query = statements[0]
        assert "LEFT OUTER JOIN salary_components" in query
        assert "LEFT OUTER JOIN employees" in query
        assert "payroll_runs.payroll_run_id = ?" in query
        assert "ORDER BY payroll_results.payroll_result_id ASC, payroll_result_components.salary_component_id ASC" in query
        assert "LIMIT" in query.upper()
        assert "salary_components.status" not in query
        assert "gross_earnings" not in query
        assert len(statements) == 1
    finally:
        engine.dispose()


def test_report_page_applies_each_optional_filter_and_scopes_to_run() -> None:
    engine = _engine_with_report_rows()
    statements: list[str] = []
    event.listen(
        engine,
        "before_cursor_execute",
        lambda connection, cursor, statement, parameters, context, executemany:
            statements.append(statement),
    )
    try:
        with Session(engine) as session:
            repository = PayrollResultComponentRepository(session)
            by_employee = _page(repository, employee_id=10)
            by_component = _page(repository, salary_component_id=3)
            by_type = _page(repository, component_type="DEDUCTION")
            other_run = _page(repository, run_id=8)

        assert [(row.payroll_result_id, row.salary_component_id) for row in by_employee] == [
            (70, 2), (70, 3), (70, 99)
        ]
        assert [(row.payroll_result_id, row.salary_component_id) for row in by_component] == [
            (70, 3)
        ]
        assert [(row.payroll_result_id, row.salary_component_id) for row in by_type] == [
            (70, 3)
        ]
        assert [(row.payroll_result_id, row.salary_component_id) for row in other_run] == [
            (80, 2)
        ]
        assert len(statements) == 4
        assert "payroll_results.employee_id = ?" in statements[0]
        assert "payroll_result_components.salary_component_id = ?" in statements[1]
        assert "payroll_result_components.component_type = ?" in statements[2]
        assert all("payroll_runs.payroll_run_id = ?" in sql for sql in statements)
    finally:
        engine.dispose()


def test_report_page_continues_lexicographically_across_shared_result_id() -> None:
    engine = _engine_with_report_rows()
    statements: list[str] = []
    event.listen(
        engine,
        "before_cursor_execute",
        lambda connection, cursor, statement, parameters, context, executemany:
            statements.append(statement),
    )
    try:
        with Session(engine) as session:
            repository = PayrollResultComponentRepository(session)
            first_page = _page(repository, limit=1)
            second_page = _page(
                repository,
                after_result_id=first_page[-1].payroll_result_id,
                after_component_id=first_page[-1].salary_component_id,
                limit=2,
            )

        assert [(row.payroll_result_id, row.salary_component_id) for row in first_page] == [
            (70, 2)
        ]
        assert [(row.payroll_result_id, row.salary_component_id) for row in second_page] == [
            (70, 3), (70, 99)
        ]
        assert "payroll_results.payroll_result_id > ?" in statements[1]
        assert "payroll_results.payroll_result_id = ?" in statements[1]
        assert "payroll_result_components.salary_component_id > ?" in statements[1]
        assert "ORDER BY payroll_results.payroll_result_id ASC, payroll_result_components.salary_component_id ASC" in statements[1]
        assert "LIMIT ? OFFSET ?" in statements[0]
    finally:
        engine.dispose()
