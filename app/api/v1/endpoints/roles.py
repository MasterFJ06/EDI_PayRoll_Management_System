from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.permissions import require_permission
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.identity.role_service import RoleService
from app.application.identity.schemas import (
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
)
from app.infrastructure.persistence.models.user import User

router = APIRouter(
    prefix="/roles",
    tags=["Roles"],
)


@router.get(
    "",
    response_model=list[RoleResponse],
)
def list_roles(
    _: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> list[RoleResponse]:
    service = RoleService(uow)
    return service.list_roles()


@router.get(
    "/{role_id}",
    response_model=RoleResponse,
)
def get_role(
    role_id: int,
    _: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> RoleResponse:
    service = RoleService(uow)
    role = service.get_role_by_id(role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found.")
    return role


@router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_role(
    request: RoleCreateRequest,
    _: Annotated[User, Depends(require_permission("roles.manage"))],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> RoleResponse:
    service = RoleService(uow)
    return service.create_role(request)


@router.put(
    "/{role_id}",
    response_model=RoleResponse,
)
def update_role(
    role_id: int,
    request: RoleUpdateRequest,
    _: Annotated[User, Depends(require_permission("roles.manage"))],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> RoleResponse:
    service = RoleService(uow)
    updated = service.update_role(role_id, request)
    if updated is None:
        raise HTTPException(status_code=404, detail="Role not found.")
    return updated

