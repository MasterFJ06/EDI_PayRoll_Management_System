from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.identity.authorization_service import AuthorizationService
from app.infrastructure.persistence.models.user import User


def require_permission(permission_code: str) -> Callable[..., User]:
    """Build a reusable dependency that requires a persisted RBAC permission."""

    def permission_dependency(
        current_user: Annotated[User, Depends(get_current_user)],
        uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    ) -> User:
        if not AuthorizationService(uow).has_permission(
            current_user.user_id, permission_code
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )
        return current_user

    return permission_dependency
