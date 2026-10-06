from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.employee.employee_service import EmployeeService
from app.application.employee.schemas import (
    EmployeeCreateRequest,
    EmployeeResponse,
    EmployeeUpdateRequest,
)
from app.infrastructure.persistence.models.user import User

router = APIRouter(prefix="", tags=["Employee"])


@router.get(
    "/employees",
    response_model=list[EmployeeResponse],
)
def list_employees(
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> list[EmployeeResponse]:
    service = EmployeeService(uow)
    return service.list_all()


@router.get(
    "/employees/{employee_id}",
    response_model=EmployeeResponse,
)
def get_employee(
    employee_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> EmployeeResponse:
    service = EmployeeService(uow)
    emp = service.get_by_id(employee_id)
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found.")
    return emp


@router.post(
    "/employees",
    response_model=EmployeeResponse,
    status_code=201,
)
def create_employee(
    request: EmployeeCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> EmployeeResponse:
    service = EmployeeService(uow)
    return service.create(request)


@router.put(
    "/employees/{employee_id}",
    response_model=EmployeeResponse,
)
def update_employee(
    employee_id: str,
    request: EmployeeUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> EmployeeResponse:
    service = EmployeeService(uow)
    emp = service.update(employee_id, request)
    if emp is None:
        raise HTTPException(status_code=404, detail="Employee not found.")
    return emp


@router.delete(
    "/employees/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_employee(
    employee_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> Response:
    service = EmployeeService(uow)
    service.delete(employee_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)