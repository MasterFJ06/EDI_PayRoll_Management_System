from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.organization.department_service import DepartmentService
from app.application.organization.designation_service import DesignationService
from app.application.organization.schemas import (
    DepartmentCreateRequest,
    DepartmentResponse,
    DepartmentUpdateRequest,
    DesignationCreateRequest,
    DesignationResponse,
    DesignationUpdateRequest,
)
from app.infrastructure.persistence.models.user import User

router = APIRouter(
    prefix="",
    tags=["Organization"],
)


def _parse_id(val: str | int, prefix: str) -> int:
    s = str(val).upper().replace(prefix, "")
    return int(s) if s.isdigit() else 1


# -----------------------------------------------------------------------------
# Departments
# -----------------------------------------------------------------------------

@router.get(
    "/departments",
    response_model=list[DepartmentResponse],
)
def list_departments(
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> list[DepartmentResponse]:
    service = DepartmentService(uow)
    return service.list_all()


@router.get(
    "/departments/{department_id}",
    response_model=DepartmentResponse,
)
def get_department(
    department_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> DepartmentResponse:
    service = DepartmentService(uow)
    num_id = _parse_id(department_id, "D")
    dept = service.get_by_id(num_id)
    if dept is None:
        raise HTTPException(status_code=404, detail="Department not found.")
    return dept


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


@router.put(
    "/departments/{department_id}",
    response_model=DepartmentResponse,
)
def update_department(
    department_id: str,
    request: DepartmentUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> DepartmentResponse:
    service = DepartmentService(uow)
    num_id = _parse_id(department_id, "D")
    dept = service.update(num_id, request)
    if dept is None:
        raise HTTPException(status_code=404, detail="Department not found.")
    return dept


@router.delete(
    "/departments/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_department(
    department_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> Response:
    service = DepartmentService(uow)
    num_id = _parse_id(department_id, "D")
    service.delete(num_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# -----------------------------------------------------------------------------
# Designations
# -----------------------------------------------------------------------------

@router.get(
    "/designations",
    response_model=list[DesignationResponse],
)
def list_designations(
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> list[DesignationResponse]:
    service = DesignationService(uow)
    return service.list_all()


@router.get(
    "/designations/{designation_id}",
    response_model=DesignationResponse,
)
def get_designation(
    designation_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> DesignationResponse:
    service = DesignationService(uow)
    num_id = _parse_id(designation_id, "DS")
    desig = service.get_by_id(num_id)
    if desig is None:
        raise HTTPException(status_code=404, detail="Designation not found.")
    return desig


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


@router.put(
    "/designations/{designation_id}",
    response_model=DesignationResponse,
)
def update_designation(
    designation_id: str,
    request: DesignationUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> DesignationResponse:
    service = DesignationService(uow)
    num_id = _parse_id(designation_id, "DS")
    desig = service.update(num_id, request)
    if desig is None:
        raise HTTPException(status_code=404, detail="Designation not found.")
    return desig


@router.delete(
    "/designations/{designation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_designation(
    designation_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> Response:
    service = DesignationService(uow)
    num_id = _parse_id(designation_id, "DS")
    service.delete(num_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)