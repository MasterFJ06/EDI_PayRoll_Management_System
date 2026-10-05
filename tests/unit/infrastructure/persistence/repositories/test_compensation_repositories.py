from unittest.mock import MagicMock

from app.infrastructure.persistence.models.employee_salary_assignment import (
    EmployeeSalaryAssignmentModel,
)
from app.infrastructure.persistence.models.salary_component import SalaryComponentModel
from app.infrastructure.persistence.models.salary_revision import SalaryRevisionModel
from app.infrastructure.persistence.models.salary_revision_component import (
    SalaryRevisionComponentModel,
)
from app.infrastructure.persistence.models.salary_structure import SalaryStructureModel
from app.infrastructure.persistence.repositories.employee_salary_assignment_repository import (
    EmployeeSalaryAssignmentRepository,
)
from app.infrastructure.persistence.repositories.salary_component_repository import (
    SalaryComponentRepository,
)
from app.infrastructure.persistence.repositories.salary_revision_component_repository import (
    SalaryRevisionComponentRepository,
)
from app.infrastructure.persistence.repositories.salary_revision_repository import (
    SalaryRevisionRepository,
)
from app.infrastructure.persistence.repositories.salary_structure_repository import (
    SalaryStructureRepository,
)


def test_salary_structure_repository_retrieves_and_adds() -> None:
    session = MagicMock()
    expected = SalaryStructureModel(salary_structure_id=1)
    session.scalar.return_value = expected
    repository = SalaryStructureRepository(session)

    assert repository.get_by_id(1) is expected
    assert repository.get_by_code("BASE") is expected
    assert repository.add(expected) is expected
    session.scalar.assert_called()
    session.add.assert_called_once_with(expected)
    session.flush.assert_called_once()
    session.commit.assert_not_called()


def test_salary_component_repository_retrieves_and_adds() -> None:
    session = MagicMock()
    expected = SalaryComponentModel(salary_component_id=1)
    session.scalar.return_value = expected
    repository = SalaryComponentRepository(session)

    assert repository.get_by_id(1) is expected
    assert repository.get_by_code("BASIC") is expected
    assert repository.add(expected) is expected
    session.scalar.assert_called()
    session.add.assert_called_once_with(expected)
    session.flush.assert_called_once()
    session.commit.assert_not_called()


def test_salary_revision_repository_retrieves_and_adds() -> None:
    session = MagicMock()
    expected = SalaryRevisionModel(salary_revision_id=1)
    session.scalar.return_value = expected
    repository = SalaryRevisionRepository(session)

    assert repository.get_by_id(1) is expected
    assert repository.get_by_structure_and_number(2, 3) is expected
    assert repository.add(expected) is expected
    session.scalar.assert_called()
    session.add.assert_called_once_with(expected)
    session.flush.assert_called_once()
    session.commit.assert_not_called()


def test_salary_revision_component_repository_retrieves_and_adds() -> None:
    session = MagicMock()
    expected = SalaryRevisionComponentModel(salary_revision_id=1, salary_component_id=2)
    session.scalar.return_value = expected
    repository = SalaryRevisionComponentRepository(session)

    assert repository.get_by_revision_and_component(1, 2) is expected
    assert repository.add(expected) is expected
    session.scalar.assert_called_once()
    session.add.assert_called_once_with(expected)
    session.flush.assert_called_once()
    session.commit.assert_not_called()


def test_employee_salary_assignment_repository_retrieves_and_adds() -> None:
    session = MagicMock()
    expected = EmployeeSalaryAssignmentModel(salary_assignment_id=1)
    session.scalar.return_value = expected
    repository = EmployeeSalaryAssignmentRepository(session)

    assert repository.get_by_id(1) is expected
    assert repository.add(expected) is expected
    session.scalar.assert_called_once()
    session.add.assert_called_once_with(expected)
    session.flush.assert_called_once()
    session.commit.assert_not_called()
