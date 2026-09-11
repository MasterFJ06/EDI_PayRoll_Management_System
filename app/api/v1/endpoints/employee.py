from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.employee.employee_service import EmployeeService
from app.application.employee.schemas import (
    EmployeeCreateRequest,
    EmployeeResponse,
)
from app.infrastructure.persistence.models.user import User


router = APIRouter(prefix="", tags=["Employee"])


@router.post(
    "/employees",
    response_model=EmployeeResponse,
    status_code=201,
)
def create_employee(
    request: EmployeeCreateRequest,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    uow: Annotated[
        UnitOfWork,
        Depends(get_unit_of_work),
    ],
) -> EmployeeResponse:
    service = EmployeeService(uow)
    return service.create(request)