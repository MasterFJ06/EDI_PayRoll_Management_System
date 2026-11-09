from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.api.dependencies.current_user import get_current_user
from app.api.dependencies.unit_of_work import get_unit_of_work
from app.application.common.unit_of_work import UnitOfWork
from app.application.identity.rbac_service import RBACService, normalize_role_name
from app.infrastructure.persistence.models.user import User


def require_permission(permission_code: str) -> Callable[[User, UnitOfWork], User]:
    """Dependency that enforces a specific permission code on an endpoint."""

    def dependency(
        current_user: Annotated[User, Depends(get_current_user)],
        uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    ) -> User:
        service = RBACService(uow)
        has_perm = service.user_has_permission(current_user.user_id, permission_code)

        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: missing required permission '{permission_code}'.",
            )

        return current_user

    return dependency


def require_role(*allowed_roles: str) -> Callable[[User, UnitOfWork], User]:
    """Dependency that restricts an endpoint to specific role names."""

    canonical_allowed = {normalize_role_name(r) for r in allowed_roles}

    def dependency(
        current_user: Annotated[User, Depends(get_current_user)],
        uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
    ) -> User:
        service = RBACService(uow)
        user_role = service.get_user_role_name(current_user.user_id)

        # System Administrator always has administrative access
        if user_role == "System Administrator":
            return current_user

        if user_role not in canonical_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: your role is not authorized for this resource.",
            )

        return current_user

    return dependency
