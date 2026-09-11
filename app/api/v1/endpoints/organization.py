from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.organization.department_service import DepartmentService
from app.application.organization.designation_service import DesignationService
from app.application.organization.schemas import (
    DepartmentCreateRequest,
    DepartmentResponse,
    DesignationCreateRequest,
    DesignationResponse,
)
from app.infrastructure.persistence.models.user import User


router = APIRouter(
    prefix="",
    tags=["Organization"],
)


@router.post(
    "/departments",
    response_model=DepartmentResponse,
    status_code=201,
)
def create_department(
    request: DepartmentCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> DepartmentResponse:
    service = DepartmentService(uow)

    return service.create(request)


@router.post(
    "/designations",
    response_model=DesignationResponse,
    status_code=201,
)
def create_designation(
    request: DesignationCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> DesignationResponse:
    service = DesignationService(uow)

    return service.create(request)