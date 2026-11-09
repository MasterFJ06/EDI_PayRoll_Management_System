from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.permissions import require_permission
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.identity.rbac_service import RBACService
from app.application.identity.schemas import (
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.application.identity.user_service import UserService
from app.infrastructure.persistence.models.user import User

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "",
    response_model=list[UserResponse],
)
def list_users(
    _: Annotated[User, Depends(require_permission("users.manage"))],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> list[UserResponse]:
    service = UserService(uow)
    return service.list_users()


@router.get(
    "/{user_id}",
    response_model=UserResponse,
)
def get_user(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> UserResponse:
    if user_id != current_user.user_id:
        rbac = RBACService(uow)
        if not rbac.user_has_permission(current_user.user_id, "users.manage"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: missing required permission 'users.manage'.",
            )

    service = UserService(uow)
    user = service.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    request: UserCreateRequest,
    current_user: Annotated[User, Depends(require_permission("users.manage"))],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> UserResponse:
    service = UserService(uow)
    return service.create_user(request, creator_user_id=current_user.user_id)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
)
def update_user(
    user_id: int,
    request: UserUpdateRequest,
    current_user: Annotated[User, Depends(require_permission("users.manage"))],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> UserResponse:
    service = UserService(uow)
    updated = service.update_user(user_id, request, updater_user_id=current_user.user_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return updated


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user(
    user_id: int,
    current_user: Annotated[User, Depends(require_permission("users.manage"))],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> Response:
    if user_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own user account.",
        )
    service = UserService(uow)
    service.delete_user(user_id, actor_user_id=current_user.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

