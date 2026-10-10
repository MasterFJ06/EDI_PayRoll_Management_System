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
