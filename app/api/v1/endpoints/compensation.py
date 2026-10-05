from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.compensation.employee_salary_assignment_service import (
    EmployeeSalaryAssignmentService,
)
from app.application.compensation.salary_component_service import SalaryComponentService
from app.application.compensation.salary_revision_component_service import (
    SalaryRevisionComponentService,
)
from app.application.compensation.salary_revision_service import SalaryRevisionService
from app.application.compensation.salary_structure_service import SalaryStructureService
from app.application.compensation.schemas import (
    EmployeeSalaryAssignmentCreateRequest,
    EmployeeSalaryAssignmentResponse,
    SalaryComponentCreateRequest,
    SalaryComponentResponse,
    SalaryRevisionComponentCreateRequest,
    SalaryRevisionComponentResponse,
    SalaryRevisionCreateRequest,
    SalaryRevisionResponse,
    SalaryStructureCreateRequest,
    SalaryStructureResponse,
)
from app.infrastructure.persistence.models.user import User


router = APIRouter(prefix="", tags=["Compensation"])


@router.post(
    "/salary-structures",
    response_model=SalaryStructureResponse,
    status_code=201,
)
def create_salary_structure(
    request: SalaryStructureCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> SalaryStructureResponse:
    return SalaryStructureService(uow).create(request)


@router.post(
    "/salary-components",
    response_model=SalaryComponentResponse,
    status_code=201,
)
def create_salary_component(
    request: SalaryComponentCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> SalaryComponentResponse:
    return SalaryComponentService(uow).create(request)


@router.post(
    "/salary-revisions",
    response_model=SalaryRevisionResponse,
    status_code=201,
)
def create_salary_revision(
    request: SalaryRevisionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> SalaryRevisionResponse:
    return SalaryRevisionService(uow).create(request)


@router.post(
    "/salary-revision-components",
    response_model=SalaryRevisionComponentResponse,
    status_code=201,
)
def create_salary_revision_component(
    request: SalaryRevisionComponentCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> SalaryRevisionComponentResponse:
    return SalaryRevisionComponentService(uow).create(request)


@router.post(
    "/employee-salary-assignments",
    response_model=EmployeeSalaryAssignmentResponse,
    status_code=201,
)
def create_employee_salary_assignment(
    request: EmployeeSalaryAssignmentCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> EmployeeSalaryAssignmentResponse:
    return EmployeeSalaryAssignmentService(uow).create(request)
