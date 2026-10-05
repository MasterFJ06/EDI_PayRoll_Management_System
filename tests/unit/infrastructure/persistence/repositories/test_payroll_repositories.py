from unittest.mock import MagicMock

import pytest

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
