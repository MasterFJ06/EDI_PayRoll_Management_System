from unittest.mock import MagicMock

import pytest
from sqlalchemy.dialects import mysql

from app.infrastructure.persistence.repositories.payroll_processing_issue_repository import (
    PayrollProcessingIssueRepository,
)
from app.infrastructure.persistence.repositories.payroll_result_component_repository import (
    PayrollResultComponentRepository,
)
from app.infrastructure.persistence.repositories.payroll_result_repository import (
    PayrollResultRepository,
)
from app.infrastructure.persistence.repositories.payroll_run_repository import (
    PayrollRunRepository,
)
from app.infrastructure.persistence.repositories.payslip_repository import PayslipRepository


@pytest.mark.parametrize(
    "repository_type,model_name",
    [
        (PayrollRunRepository, "PayrollRunModel"),
        (PayrollResultRepository, "PayrollResultModel"),
        (PayrollResultComponentRepository, "PayrollResultComponentModel"),
        (PayrollProcessingIssueRepository, "PayrollProcessingIssueModel"),
        (PayslipRepository, "PayslipModel"),
    ],
)
def test_payroll_repository_add_flushes_shared_session_without_commit(
    repository_type: type,
    model_name: str,
) -> None:
    from app.infrastructure.persistence.models import __dict__ as models

    session = MagicMock()
    repository = repository_type(session)
    model_type = models[model_name]
    model = model_type()
    repository.add(model)
    session.add.assert_called_once_with(model)
    session.flush.assert_called_once()
    session.commit.assert_not_called()


def test_payroll_repositories_query_using_shared_session() -> None:
    session = MagicMock()
    repos_and_calls = [
        (PayrollRunRepository(session), "get_by_period", (2026, 10)),
        (PayrollResultRepository(session), "get_by_run_and_employee", (1, 2)),
        (PayrollResultComponentRepository(session), "get_by_result_and_component", (1, 2)),
        (PayrollProcessingIssueRepository(session), "get_by_id", (1,)),
        (PayslipRepository(session), "get_by_number", ("PS-1",)),
    ]
    for repository, method, arguments in repos_and_calls:
        getattr(repository, method)(*arguments)
    assert session.scalar.call_count == len(repos_and_calls)
    session.commit.assert_not_called()


def test_payroll_result_aggregate_is_scoped_and_uses_persisted_totals() -> None:
    from decimal import Decimal
    from unittest.mock import MagicMock

    session = MagicMock()
    session.execute.return_value.one.return_value = (
        2,
        Decimal("3000.20"),
        Decimal("200.10"),
        Decimal("2800.10"),
    )
    result = PayrollResultRepository(session).aggregate_by_run(77)

    statement = session.execute.call_args.args[0]
    compiled = str(statement.compile(dialect=mysql.dialect())).upper()
    assert "PAYROLL_RESULTS.PAYROLL_RUN_ID =" in compiled
    assert "COUNT(" in compiled and "SUM(" in compiled
    assert result == (
        2,
        Decimal("3000.20"),
        Decimal("200.10"),
        Decimal("2800.10"),
    )
    session.commit.assert_not_called()


def test_payroll_result_aggregate_excludes_results_from_other_runs() -> None:
    from decimal import Decimal

    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE payroll_results ("
                "payroll_result_id INTEGER PRIMARY KEY, payroll_run_id INTEGER, "
                "gross_earnings NUMERIC(15, 2), total_deductions NUMERIC(15, 2), "
                "net_salary NUMERIC(15, 2))"
            )
        )
        connection.execute(
            text(
                "INSERT INTO payroll_results VALUES "
                "(1, 7, 100.10, 10.10, 90.00), "
                "(2, 7, 200.20, 20.20, 180.00), "
                "(3, 8, 9000.00, 1000.00, 8000.00)"
            )
        )

    with Session(engine) as session:
        result = PayrollResultRepository(session).aggregate_by_run(7)

    assert result[0] == 2
    assert result[1:] == (
        Decimal("300.30"),
        Decimal("30.30"),
        Decimal("270.00"),
    )
    engine.dispose()


def test_payroll_result_report_page_is_bounded_ordered_and_keeps_missing_labels() -> None:
    from decimal import Decimal

    from sqlalchemy import create_engine, event, text
    from sqlalchemy.orm import Session

    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE employees ("
                "employee_id INTEGER PRIMARY KEY, employee_code VARCHAR(30), "
                "first_name VARCHAR(100), last_name VARCHAR(100))"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE payroll_results ("
                "payroll_result_id INTEGER PRIMARY KEY, payroll_run_id INTEGER, "
                "employee_id INTEGER, salary_assignment_id INTEGER, "
                "gross_earnings NUMERIC(15, 2), total_deductions NUMERIC(15, 2), "
                "net_salary NUMERIC(15, 2), workforce_calculation_snapshot JSON)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO employees VALUES "
                "(2, 'E-2', 'Current', 'Name'), (4, 'E-4', 'Next', 'Person')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO payroll_results VALUES "
                "(8, 7, 2, 22, 1200.01, 20.00, 1180.01, 'snapshot'), "
                "(9, 7, 4, 24, 1300.02, 30.00, 1270.02, 'snapshot'), "
                "(10, 7, 6, 26, 1400.03, 40.00, 1360.03, 'snapshot'), "
                "(11, 8, 1, 21, 9000.00, 0.00, 9000.00, NULL)"
            )
        )

    executed_sql: list[str] = []

    def capture_sql(
        _connection, _cursor, statement, _parameters, _context, _executemany
    ) -> None:
        executed_sql.append(statement)

    event.listen(
        engine,
        "before_cursor_execute",
        capture_sql,
    )
    with Session(engine) as session:
        repository = PayrollResultRepository(session)
        first_page = repository.list_report_page(7, None, None, 3)
        second_page = repository.list_report_page(7, 4, 9, 3)

    assert [row.employee_id for row in first_page] == [2, 4, 6]
    assert first_page[0].employee_name == "Current Name"
    assert first_page[0].gross_earnings == Decimal("1200.01")
    assert first_page[0].net_salary == Decimal("1180.01")
    assert first_page[2].employee_code is None
    assert first_page[2].employee_name is None
    assert [row.employee_id for row in second_page] == [6]
    assert all(row.payroll_run_id == 7 for row in first_page + second_page)
    assert len(executed_sql) == 2
    assert all("LEFT OUTER JOIN employees" in sql for sql in executed_sql)
    assert all("payroll_results.payroll_run_id =" in sql for sql in executed_sql)
    assert all("LIMIT" in sql for sql in executed_sql)
    assert all("workforce_calculation_snapshot" not in sql for sql in executed_sql)
    assert "payroll_results.employee_id >" in executed_sql[1]
    engine.dispose()


def test_payroll_run_attempt_fence_compiles_as_mysql_for_update() -> None:
    session = MagicMock()
    session.get_bind.return_value.dialect.name = "mysql"
    repository = PayrollRunRepository(session)
    repository.lock_active_attempt(77, 3)

    statement = session.scalar.call_args.args[0]
    compiled = str(
        statement.compile(
            dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}
        )
    ).upper()
    assert "FOR UPDATE" in compiled
    assert "STATUS = 'PROCESSING'" in compiled
    assert "ATTEMPT_NUMBER = 3" in compiled
    assert "ATTEMPT_LEASE_EXPIRES_AT > CURRENT_TIMESTAMP(6)" in compiled

    result_session = MagicMock()
    result_repository = PayrollResultRepository(result_session)
    result_repository.get_by_id_for_update(9)
    result_statement = result_session.scalar.call_args.args[0]
    result_sql = str(result_statement.compile(dialect=mysql.dialect())).upper()
    assert "FOR UPDATE" in result_sql
    assert "PAYROLL_RESULT_ID" in result_sql
