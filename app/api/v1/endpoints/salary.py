from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.compensation.salary_service import SalaryService
from app.application.compensation.schemas import (
    SalaryStructureRequest,
    SalaryStructureResponse,
)
from app.infrastructure.persistence.models.user import User

router = APIRouter(
    prefix="/salary-structures",
    tags=["Salary Structures"],
)


@router.get(
    "",
    response_model=list[SalaryStructureResponse],
)
def list_salary_structures(
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> list[SalaryStructureResponse]:
    service = SalaryService(uow)
    return service.list_structures()


@router.get(
    "/{structure_id}",
    response_model=SalaryStructureResponse,
)
def get_salary_structure(
    structure_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> SalaryStructureResponse:
    service = SalaryService(uow)
    struct = service.get_structure_by_id(structure_id)
    if struct is None:
        raise HTTPException(status_code=404, detail="Salary structure not found.")
    return struct


@router.post(
    "",
    response_model=SalaryStructureResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_salary_structure(
    request: SalaryStructureRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> SalaryStructureResponse:
    service = SalaryService(uow)
    return service.create_structure(request)


@router.put(
    "/{structure_id}",
    response_model=SalaryStructureResponse,
)
def update_salary_structure(
    structure_id: str,
    patch: dict[str, Any],
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> SalaryStructureResponse:
    service = SalaryService(uow)
    updated = service.update_structure(structure_id, patch)
    if updated is None:
        raise HTTPException(status_code=404, detail="Salary structure not found.")
    return updated
