from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.permission import Permission
from app.infrastructure.persistence.models.role import Role
from app.infrastructure.persistence.models.role_permission import RolePermission
from app.infrastructure.persistence.models.user_role import UserRole


class AuthorizationRepository:
    """Queries effective permissions through the persisted RBAC relationships."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def has_permission(self, user_id: int, permission_code: str) -> bool:
        statement = (
            select(Permission.permission_id)
            .select_from(UserRole)
            .join(Role, Role.role_id == UserRole.role_id)
            .join(RolePermission, RolePermission.role_id == Role.role_id)
            .join(
                Permission,
                Permission.permission_id == RolePermission.permission_id,
            )
            .where(
                UserRole.user_id == user_id,
                Role.is_active.is_(True),
                Permission.permission_code == permission_code,
            )
            .limit(1)
        )
        return self.session.scalar(statement) is not None
