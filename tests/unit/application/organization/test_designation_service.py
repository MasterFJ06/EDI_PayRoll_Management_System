import pytest

from app.application.organization.designation_service import DesignationService
from app.application.organization.schemas import DesignationCreateRequest
from app.domain.shared.exceptions import BusinessRuleViolation
from app.infrastructure.persistence.models.designation import Designation


class FakeDesignationRepository:
    def __init__(self) -> None:
        self.designations: list[Designation] = []

    def get_by_code(self, designation_code: str) -> Designation | None:
        return next(
            (
                designation
                for designation in self.designations
                if designation.designation_code == designation_code
            ),
            None,
        )

    def get_by_name(self, designation_name: str) -> Designation | None:
        return next(
            (
                designation
                for designation in self.designations
                if designation.designation_name == designation_name
            ),
            None,
        )

    def add(self, designation: Designation) -> Designation:
        designation.designation_id = len(self.designations) + 1
        self.designations.append(designation)
        return designation


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.designations = FakeDesignationRepository()
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def test_create_designation() -> None:
    uow = FakeUnitOfWork()
    service = DesignationService(uow)

    request = DesignationCreateRequest(
        designation_code="DEV",
        designation_name="Software Developer",
    )

    response = service.create(request)

    assert response.designation_id == 1
    assert response.designation_code == "DEV"
    assert response.designation_name == "Software Developer"
    assert response.status == "ACTIVE"
    assert uow.committed is True


def test_create_designation_strips_code_and_name() -> None:
    uow = FakeUnitOfWork()
    service = DesignationService(uow)

    request = DesignationCreateRequest(
        designation_code=" DEV ",
        designation_name=" Software Developer ",
    )

    response = service.create(request)

    assert response.designation_code == "DEV"
    assert response.designation_name == "Software Developer"


def test_create_designation_rejects_duplicate_code() -> None:
    uow = FakeUnitOfWork()

    existing_designation = Designation(
        designation_id=1,
        designation_code="DEV",
        designation_name="Software Developer",
        status="ACTIVE",
    )

    uow.designations.add(existing_designation)

    service = DesignationService(uow)

    request = DesignationCreateRequest(
        designation_code="DEV",
        designation_name="Another Designation",
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="code is already registered",
    ):
        service.create(request)


def test_create_designation_rejects_duplicate_name() -> None:
    uow = FakeUnitOfWork()

    existing_designation = Designation(
        designation_id=1,
        designation_code="DEV",
        designation_name="Software Developer",
        status="ACTIVE",
    )

    uow.designations.add(existing_designation)

    service = DesignationService(uow)

    request = DesignationCreateRequest(
        designation_code="SDEV",
        designation_name="Software Developer",
    )

    with pytest.raises(
        BusinessRuleViolation,
        match="name is already registered",
    ):
        service.create(request)


def test_create_designation_requires_started_unit_of_work() -> None:
    class UnstartedUnitOfWork:
        designations = None

    service = DesignationService(UnstartedUnitOfWork())

    request = DesignationCreateRequest(
        designation_code="DEV",
        designation_name="Software Developer",
    )

    with pytest.raises(
        RuntimeError,
        match="Unit of Work has not been started",
    ):
        service.create(request)